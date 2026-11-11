from src.modules.auth.utils import JWT


def get_jwt_service() -> JWT:
    return JWT()
