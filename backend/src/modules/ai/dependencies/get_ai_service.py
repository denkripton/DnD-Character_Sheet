from src.modules.ai import dependencies
from src.modules.ai.service import AIService


def get_ai_service() -> AIService:
    return AIService(registry=dependencies.get_ai_registry())
