from fastapi import APIRouter
from src.modules.auth.router.authenticate_external import router as external_auth_router
from src.modules.auth.router.login import router as login_router
from src.modules.auth.router.register import router as register_router
from src.utils import ErrorHandlingRoute

user_router = APIRouter(prefix="/users", route_class=ErrorHandlingRoute)
user_router.include_router(register_router)
user_router.include_router(login_router)
user_router.include_router(external_auth_router)
