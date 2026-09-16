from sqlalchemy.exc import IntegrityError

from src.exceptions import ServiceError
from src.modules.auth.repository import UserRepository
from src.modules.auth.schemas.user.creation import UserCreateSchema
from src.modules.auth.schemas.user.login import UserLoginSchema
from src.modules.auth.utils import JWT, pw_manager
from src.utils.unit_of_work import UnitOfWork


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        jwt: JWT,
        unit_of_work: UnitOfWork,
    ):
        self.repo = user_repository
        self.jwt = jwt
        self.uow = unit_of_work

    async def register(self, data: UserCreateSchema):
        data = data.model_dump()

        existing_user = await self.repo.get_by_email(data["email"])

        if existing_user is not None:
            raise ServiceError(code=422, msg="User already exists")

        data["password"] = pw_manager.hash_password(data["password"])

        user = await self.repo.create(**data)

        try:
            await self.uow.commit()
        except IntegrityError:
            await self.uow.rollback()
            raise ServiceError(code=422, msg="User already exists")

        await self.uow.refresh(user)
        return user

    async def login(self, data: UserLoginSchema):
        existing_user = await self.repo.get_by_email(data.email)

        if existing_user is None:
            raise ServiceError(code=422, msg="User does not exist")

        password_check = pw_manager.check_password(
            data.password, existing_user.password
        )
        existing_user.id = str(existing_user.id)

        if password_check is False:
            raise ServiceError(code=403, msg="Incorrect password")

        access = self.jwt.create_access_token(existing_user.id)
        refresh = self.jwt.create_refresh_token(existing_user.id)

        return {
            "access": access,
            "refresh": refresh,
        }