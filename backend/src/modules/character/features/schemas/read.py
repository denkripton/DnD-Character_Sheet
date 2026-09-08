import uuid

from src.modules.character.features.schemas.create import FeatureCreateSchema


class FeatureReadSchema(FeatureCreateSchema):
    id: uuid.UUID