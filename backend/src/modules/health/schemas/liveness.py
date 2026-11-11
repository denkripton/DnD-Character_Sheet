from typing import Literal

from pydantic import BaseModel


class LivenessResponseSchema(BaseModel):
    status: Literal["alive"]
