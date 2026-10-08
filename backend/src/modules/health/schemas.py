from typing import Literal

from pydantic import BaseModel


class LivenessResponseSchema(BaseModel):
    status: Literal["alive"]


class ReadinessResponseSchema(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, Literal["up", "down"]]
