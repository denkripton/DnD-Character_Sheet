from enum import Enum


class AIErrorMessage(str, Enum):
    TIMEOUT = "The AI provider timed out. Please try again."
    RATE_LIMIT = "The AI provider rate limit was reached. Please try again later."
    UNAVAILABLE = "The AI provider is unavailable right now."
    MODEL_UNAVAILABLE = "The selected AI model is unavailable. Choose another model."
    AUTH = "AI provider authentication is not available. Please contact support."
