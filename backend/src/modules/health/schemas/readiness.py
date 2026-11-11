from typing import Literal

from pydantic import BaseModel


class ReadinessResponseSchema(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, Literal["up", "down"]]
