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
from src.modules.character.draft import (
    CharacterDraftReadSchema,
    CharacterDraftService,
    character_draft_service_scope,
)
from src.utils.exceptions import RateLimitExceeded, ServiceError

DraftServiceScope = Callable[[], AbstractAsyncContextManager[CharacterDraftService]]


def build_bot_command_dispatcher(
    producer: MessagePublisher,
    secret: str | None = None,
    max_age_seconds: int = 300,
    draft_service_scope: DraftServiceScope | None = None,
) -> CommandDispatcher:
    if draft_service_scope is None:
        draft_service_scope = character_draft_service_scope
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
