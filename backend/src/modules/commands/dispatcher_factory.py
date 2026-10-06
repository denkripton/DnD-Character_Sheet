from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager

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
from src.utils.exceptions import ServiceError

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
            _publish_generated_event(producer),
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


def _publish_generated_event(producer: MessagePublisher):
    async def handle(envelope) -> None:
        event = create_message(
            MessageType.CHARACTER_GENERATED,
            envelope.payload,
            correlation_id=envelope.correlation_id,
            headers=envelope.headers,
        )
        await producer.publish(event, messaging_route(MessageType.CHARACTER_GENERATED))

    return handle


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


async def _draft_call(draft_service_scope, call) -> dict:
    try:
        async with draft_service_scope() as service:
            result = await call(service)
    except ServiceError as exc:
        return {"ok": False, "error": str(exc)}
    return _draft_payload(result)


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
