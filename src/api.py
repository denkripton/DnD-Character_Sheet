from fastapi import FastAPI

from src.modules.auth import user_router
from src.utils.interfaces.application import Application
from src.utils.metadata import (
    contact,
    openapi_url,
    summary,
    tags_metadata,
    title,
    version,
)


class API(Application):
    def __init__(self):
        super().__init__()
        self.title = title
        self.summary = summary
        self.version = version
        self.openapi_url = openapi_url
        self.tags_metadata = tags_metadata
        self.contact = contact
        self.routers = [user_router]

    def create(self):
        self.app = FastAPI(
            title=self.title,
            openapi_tags=self.tags_metadata,
            summary=self.summary,
            version=self.version,
            openapi_url=self.openapi_url,
            contact=self.contact,
        )
        for router in self.routers:
            self.app.include_router(router=router)


api = API()
api.create()
