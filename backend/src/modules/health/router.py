from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from src.modules.health.dependencies import get_health_service
from src.modules.health.schemas import LivenessResponseSchema, ReadinessResponseSchema
from src.modules.health.service import HealthService
from src.utils import ErrorHandlingRoute

router = APIRouter(prefix="/health", route_class=ErrorHandlingRoute)


@router.get(
    "/live",
    summary="Liveness probe",
    tags=["Health"],
    description="Reports whether the application process is alive without touching external dependencies.",
    response_model=LivenessResponseSchema,
)
async def liveness() -> LivenessResponseSchema:
    return LivenessResponseSchema(status="alive")


@router.get(
    "/ready",
    summary="Readiness probe",
    tags=["Health"],
    description=(
        "Checks PostgreSQL, Redis and RabbitMQ availability. "
        "Returns 503 when any dependency is unavailable."
    ),
    response_model=ReadinessResponseSchema,
    responses={503: {"model": ReadinessResponseSchema}},
)
async def readiness(
    service: HealthService = Depends(get_health_service),
):
    result = await service.readiness()
    if result.status != "ready":
        return JSONResponse(status_code=503, content=result.model_dump())
    return result
