from enum import StrEnum


class MessageHeader(StrEnum):
    COMMAND_SIGNATURE = "x-command-signature"
    AUTH_PROVIDER = "x-auth-provider"
    AUTH_PROVIDER_USER_ID = "x-auth-provider-user-id"
    AUTH_USER_ID = "x-user-id"
    RETRY_COUNT = "x-retry-count"
