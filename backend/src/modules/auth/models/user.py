import uuid
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.databases.sql import Base

if TYPE_CHECKING:
    from src.modules.character.models.character import Character


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, primary_key=True
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[bytes] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )

    character: Mapped[list["Character"]] = relationship(back_populates="owner")
