from fastapi import APIRouter
from src.modules.health.schemas import LivenessResponseSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.get(
    "/live",
    summary="Liveness probe",
    tags=["Health"],
    description="Reports whether the application process is alive without touching external dependencies.",
    response_model=LivenessResponseSchema,
)
async def liveness() -> LivenessResponseSchema:
    return LivenessResponseSchema(status="alive")
