from pydantic import BaseModel


class AIProviderCatalogSchema(BaseModel):
    name: str
    models: list[str]
