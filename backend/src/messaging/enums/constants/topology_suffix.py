from enum import StrEnum


class TopologySuffix(StrEnum):
    RETRY_EXCHANGE = ".retryx"
    RETRY_QUEUE = ".retry"
    DEAD_LETTER_EXCHANGE = ".dlx"
    DEAD_LETTER_QUEUE = ".dlq"
