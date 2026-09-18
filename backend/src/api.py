import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.dependencies import get_message_bus
from src.infrastructure.redis import cache, rate_limiter, redis
from src.modules.ai import ai_router
from src.modules.auth import user_router
from src.modules.character.router import character_router
from src.utils import register_exception_handlers
from src.utils.interfaces.application import Application
from src.utils.metadata import (
    contact,
    openapi_url,
    summary,
    tags_metadata,
    title,
    version,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bus = get_message_bus()
    await bus.start()
    app.state.message_bus = bus

    try:
        await redis.ping()
    except Exception as exc:
        logger.warning("Redis is not reachable: %s", exc)
    app.state.redis_client = redis
    app.state.cache = cache
    app.state.rate_limiter = rate_limiter

    try:
        yield
    finally:
        await bus.close()
        await redis.aclose()


class API(Application):
    def __init__(self):
        super().__init__()
        self.title = title
        self.summary = summary
        self.version = version
        self.openapi_url = openapi_url
        self.tags_metadata = tags_metadata
        self.contact = contact
        self.routers = [user_router, ai_router, character_router]

    def create(self):
        self.app = FastAPI(
            title=self.title,
            openapi_tags=self.tags_metadata,
            summary=self.summary,
            version=self.version,
            openapi_url=self.openapi_url,
            contact=self.contact,
            lifespan=lifespan,
        )
        for router in self.routers:
            self.app.include_router(router=router)
        register_exception_handlers(app=self.app)


api = API()
api.create()