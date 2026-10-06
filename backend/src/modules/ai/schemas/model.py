from pydantic import BaseModel


class AIModelCatalogSchema(BaseModel):
    provider: str
    model: str
