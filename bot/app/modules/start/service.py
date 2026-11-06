from app.modules.start.greeting import greeting_text
from app.modules.start.schemas.user import UserIdentity


class StartService:
    def create_greeting(self, user: UserIdentity) -> str:
        name = user.username or user.first_name
        return greeting_text(name)
