from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.exc import SQLAlchemyError
from src.messaging.contract import create_message, messaging_route
from src.messaging.dispatcher import CommandDispatcher
from src.messaging.enums import MessageType
from src.messaging.enums.constants import AUTH_USER_ID_HEADER
from src.messaging.interfaces import MessagePublisher
from src.messaging.messages import MessageEnvelope
from src.messaging.security import require_identity_headers, verify_command
from src.modules.ai.dependencies import get_ai_registry
from src.modules.character.backstory import character_backstory_service_scope
from src.modules.character.backstory.schemas import BackstoryCreateSchema
from src.modules.character.backstory.service import BackstoryService
from src.modules.character.draft import (
    CharacterDraftReadSchema,
    CharacterDraftService,
    character_draft_service_scope,
)
from src.utils.exceptions import (
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    RateLimitExceeded,
    ServiceError,
)

DraftServiceScope = Callable[[], AbstractAsyncContextManager[CharacterDraftService]]
BackstoryServiceScope = Callable[[], AbstractAsyncContextManager[BackstoryService]]

AI_TIMEOUT_ERROR_TEXT = "The AI provider timed out. Please try again."
AI_RATE_LIMIT_ERROR_TEXT = (
    "The AI provider rate limit was reached. Please try again later."
)
AI_UNAVAILABLE_ERROR_TEXT = "The AI provider is unavailable right now."


def build_bot_command_dispatcher(
    producer: MessagePublisher,
    secret: str | None = None,
    max_age_seconds: int = 300,
    draft_service_scope: DraftServiceScope | None = None,
    backstory_service_scope: BackstoryServiceScope | None = None,
) -> CommandDispatcher:
    if draft_service_scope is None:
        draft_service_scope = character_draft_service_scope
    if backstory_service_scope is None:
        backstory_service_scope = character_backstory_service_scope
    dispatcher = CommandDispatcher()
    dispatcher.register(
        MessageType.CHARACTER_GENERATE,
        _require_authenticated(
            _handle_draft_generate(producer, draft_service_scope),
            secret,
            max_age_seconds,
        ),
    )
    dispatcher.register(
        MessageType.CHARACTER_CREATE,
        _require_authenticated(
            _handle_draft_create(producer, draft_service_scope),
            secret,
            max_age_seconds,
        ),
    )
    dispatcher.register(
        MessageType.CHARACTER_SAVE,
        _require_authenticated(
            _handle_draft_save(producer, draft_service_scope),
            secret,
            max_age_seconds,
        ),
    )
    dispatcher.register(
        MessageType.CHARACTER_UPDATE_PARAMETER,
        _require_authenticated(
            _handle_draft_update(producer, draft_service_scope),
            secret,
            max_age_seconds,
        ),
    )
    dispatcher.register(
        MessageType.CHARACTER_DELETE,
        _require_authenticated(
            _handle_draft_delete(producer, draft_service_scope),
            secret,
            max_age_seconds,
        ),
    )
    dispatcher.register(
        MessageType.CHARACTER_STATS,
        _require_authenticated(
            _handle_draft_stats(producer, draft_service_scope),
            secret,
            max_age_seconds,
        ),
    )
    dispatcher.register(
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        _require_authenticated(
            _handle_backstory_generate(producer, backstory_service_scope),
            secret,
            max_age_seconds,
        ),
    )
    dispatcher.register(
        MessageType.CHARACTER_SAVE_BACKSTORY,
        _require_authenticated(
            _handle_backstory_save(producer, backstory_service_scope),
            secret,
            max_age_seconds,
        ),
    )
    dispatcher.register(
        MessageType.AI_CATALOG,
        _require_authenticated(_handle_ai_catalog(producer), secret, max_age_seconds),
    )
    return dispatcher


def _require_authenticated(
    handler: Callable[[MessageEnvelope], Awaitable[None]],
    secret: str | None,
    max_age_seconds: int,
) -> Callable[[MessageEnvelope], Awaitable[None]]:
    if not secret:
        return handler

    async def wrapped(envelope: MessageEnvelope) -> None:
        verify_command(envelope, secret, max_age_seconds)
        require_identity_headers(envelope)
        await handler(envelope)

    return wrapped


async def _publish_response(
    producer: MessagePublisher,
    message_type: MessageType,
    envelope: MessageEnvelope,
    payload: dict,
) -> None:
    event = create_message(
        message_type,
        payload,
        correlation_id=envelope.correlation_id,
        headers=envelope.headers,
    )
    await producer.publish(event, messaging_route(message_type))


def _identity(envelope: MessageEnvelope) -> dict[str, str]:
    return require_identity_headers(envelope)


def _draft_payload(result) -> dict:
    if isinstance(result, CharacterDraftReadSchema):
        return {"ok": True, "draft": result.model_dump(mode="json")}
    return {"ok": True}


def _stats_payload(result) -> dict:
    if isinstance(result, dict):
        return {"ok": True, **result}
    return {"ok": True}


def _generate_payload(result) -> dict:
    if isinstance(result, dict) and isinstance(result.get("draft"), CharacterDraftReadSchema):
        return {
            "ok": True,
            "draft": result["draft"].model_dump(mode="json"),
            "stats": result.get("stats"),
            "modifiers": result.get("modifiers"),
        }
    return {"ok": True}


def _saved_payload(result) -> dict:
    if isinstance(result, dict):
        return {"ok": True, **result}
    return {"ok": True}


def _backstory_preview_payload(result) -> dict:
    if isinstance(result, str):
        return {"ok": True, "backstory": result}
    return {"ok": True}


def _backstory_saved_payload(result) -> dict:
    backstory = getattr(result, "backstory", None)
    if isinstance(backstory, str):
        return {"ok": True, "backstory": backstory}
    return {"ok": True}


def _handle_ai_catalog(producer: MessagePublisher):
    async def handle(envelope: MessageEnvelope) -> None:
        try:
            registry = get_ai_registry()
            payload = {
                "ok": True,
                "providers": [
                    {"name": provider, "models": models}
                    for provider, models in registry.provider_models.items()
                ],
            }
        except ServiceError as exc:
            payload = {"ok": False, "error": str(exc)}
        await _publish_response(
            producer, MessageType.AI_CATALOG_RESULT, envelope, payload
        )

    return handle


async def _draft_call(
    draft_service_scope, call, payload_builder=_draft_payload
) -> dict:
    try:
        async with draft_service_scope() as service:
            result = await call(service)
    except RateLimitExceeded as exc:
        return {"ok": False, "error": str(exc)}
    except ServiceError as exc:
        return {"ok": False, "error": str(exc)}
    except SQLAlchemyError:
        return {
            "ok": False,
            "error": "The request could not be completed. Please try again.",
        }
    return payload_builder(result)


async def _backstory_call(
    backstory_service_scope, call, payload_builder=_backstory_preview_payload
) -> dict:
    try:
        async with backstory_service_scope() as service:
            result = await call(service)
    except RateLimitExceeded as exc:
        return {"ok": False, "error": str(exc)}
    except ServiceError as exc:
        return {"ok": False, "error": str(exc)}
    except AIProviderTimeoutError:
        return {"ok": False, "error": AI_TIMEOUT_ERROR_TEXT}
    except AIProviderRateLimitError:
        return {"ok": False, "error": AI_RATE_LIMIT_ERROR_TEXT}
    except AIProviderError:
        return {"ok": False, "error": AI_UNAVAILABLE_ERROR_TEXT}
    except SQLAlchemyError:
        return {
            "ok": False,
            "error": "The request could not be completed. Please try again.",
        }
    return payload_builder(result)


def _handle_draft_generate(producer: MessagePublisher, draft_service_scope):
    async def handle(envelope: MessageEnvelope) -> None:
        user_id = _identity(envelope)[AUTH_USER_ID_HEADER]
        payload = envelope.payload if isinstance(envelope.payload, dict) else {}
        draft_id = payload.get("draft_id")
        method = payload.get("method")

        async def call(service):
            if not draft_id or not isinstance(method, str) or not method:
                raise ServiceError(
                    msg="Invalid character generation request.", code=422
                )
            return await service.generate_character(user_id, draft_id, method)

        result = await _draft_call(draft_service_scope, call, _generate_payload)
        await _publish_response(
            producer, MessageType.CHARACTER_GENERATED, envelope, result
        )

    return handle


def _handle_draft_create(producer: MessagePublisher, draft_service_scope):
    async def handle(envelope: MessageEnvelope) -> None:
        user_id = _identity(envelope)[AUTH_USER_ID_HEADER]

        async def call(service):
            return await service.create_draft(user_id)

        payload = await _draft_call(draft_service_scope, call)
        await _publish_response(
            producer, MessageType.CHARACTER_CREATED, envelope, payload
        )

    return handle


def _handle_draft_save(producer: MessagePublisher, draft_service_scope):
    async def handle(envelope: MessageEnvelope) -> None:
        user_id = _identity(envelope)[AUTH_USER_ID_HEADER]
        payload = envelope.payload if isinstance(envelope.payload, dict) else {}
        draft_id = payload.get("draft_id")

        async def call(service):
            if not draft_id:
                raise ServiceError(
                    msg="Invalid character save request.", code=422
                )
            return await service.save_character(user_id, draft_id)

        result = await _draft_call(draft_service_scope, call, _saved_payload)
        await _publish_response(
            producer, MessageType.CHARACTER_SAVED, envelope, result
        )

    return handle


def _handle_draft_update(producer: MessagePublisher, draft_service_scope):
    async def handle(envelope: MessageEnvelope) -> None:
        user_id = _identity(envelope)[AUTH_USER_ID_HEADER]
        payload = envelope.payload if isinstance(envelope.payload, dict) else {}
        draft_id = payload.get("draft_id")
        parameter = payload.get("parameter")

        async def call(service):
            if not draft_id or not isinstance(parameter, str) or not parameter:
                raise ServiceError(
                    msg="Invalid character draft update request.", code=422
                )
            if payload.get("generate"):
                return await service.generate_parameter(user_id, draft_id, parameter)
            return await service.update_parameter(
                user_id, draft_id, parameter, payload.get("value")
            )

        result = await _draft_call(draft_service_scope, call)
        await _publish_response(
            producer, MessageType.CHARACTER_UPDATED, envelope, result
        )

    return handle


def _handle_draft_delete(producer: MessagePublisher, draft_service_scope):
    async def handle(envelope: MessageEnvelope) -> None:
        user_id = _identity(envelope)[AUTH_USER_ID_HEADER]
        payload = envelope.payload if isinstance(envelope.payload, dict) else {}
        draft_id = payload.get("draft_id")

        async def call(service):
            if not draft_id:
                raise ServiceError(
                    msg="Invalid character draft request.", code=422
                )
            await service.delete_draft(user_id, draft_id)

        result = await _draft_call(draft_service_scope, call)
        await _publish_response(
            producer, MessageType.CHARACTER_DELETED, envelope, result
        )

    return handle


def _handle_draft_stats(producer: MessagePublisher, draft_service_scope):
    async def handle(envelope: MessageEnvelope) -> None:
        user_id = _identity(envelope)[AUTH_USER_ID_HEADER]
        payload = envelope.payload if isinstance(envelope.payload, dict) else {}
        draft_id = payload.get("draft_id")
        method = payload.get("method")
        values = payload.get("values")

        async def call(service):
            if not draft_id:
                raise ServiceError(
                    msg="Invalid character stats request.", code=422
                )
            if method is not None:
                return await service.generate_stats(user_id, draft_id, method)
            if values is not None:
                return await service.set_stats(user_id, draft_id, values)
            raise ServiceError(
                msg="Invalid character stats request.", code=422
            )

        result = await _draft_call(draft_service_scope, call, _stats_payload)
        await _publish_response(
            producer, MessageType.CHARACTER_STATS_CHANGED, envelope, result
        )

    return handle


def _handle_backstory_generate(producer: MessagePublisher, backstory_service_scope):
    async def handle(envelope: MessageEnvelope) -> None:
        user_id = _identity(envelope)[AUTH_USER_ID_HEADER]
        payload = envelope.payload if isinstance(envelope.payload, dict) else {}
        character_id = payload.get("character_id")
        prompt = payload.get("prompt")
        model = payload.get("model")
        provider = payload.get("provider")

        async def call(service):
            if not character_id:
                raise ServiceError(
                    msg="Invalid backstory request.", code=422
                )
            if prompt is not None and (
                not isinstance(prompt, str) or len(prompt) > 1000
            ):
                raise ServiceError(
                    msg="Invalid backstory request.", code=422
                )
            if model is not None and not isinstance(model, str):
                raise ServiceError(
                    msg="Invalid backstory request.", code=422
                )
            if provider is not None and not isinstance(provider, str):
                raise ServiceError(
                    msg="Invalid backstory request.", code=422
                )
            return await service.preview_backstory(
                user_id,
                character_id,
                model=model,
                provider=provider,
                prompt=prompt,
            )

        result = await _backstory_call(
            backstory_service_scope, call, _backstory_preview_payload
        )
        await _publish_response(
            producer,
            MessageType.CHARACTER_BACKSTORY_GENERATED,
            envelope,
            result,
        )

    return handle


def _handle_backstory_save(producer: MessagePublisher, backstory_service_scope):
    async def handle(envelope: MessageEnvelope) -> None:
        user_id = _identity(envelope)[AUTH_USER_ID_HEADER]
        payload = envelope.payload if isinstance(envelope.payload, dict) else {}
        character_id = payload.get("character_id")
        backstory = payload.get("backstory")

        async def call(service):
            if not character_id or not isinstance(backstory, str):
                raise ServiceError(
                    msg="Backstory text is required.", code=422
                )
            if not backstory.strip():
                raise ServiceError(
                    msg="Backstory text is required.", code=422
                )
            if len(backstory) > 10000:
                raise ServiceError(
                    msg="Backstory must be no more than 10000 characters.",
                    code=422,
                )
            return await service.set_backstory(
                user_id,
                character_id,
                BackstoryCreateSchema(backstory=backstory),
            )

        result = await _backstory_call(
            backstory_service_scope, call, _backstory_saved_payload
        )
        await _publish_response(
            producer,
            MessageType.CHARACTER_BACKSTORY_SAVED,
            envelope,
            result,
        )

    return handle
