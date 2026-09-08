import uuid

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean, ForeignKey, DateTime, func, UUID

from src.databases.sql import Base


class SavingThrows(Base):
    __tablename__ = "saving_throws"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, primary_key=True
    )

    strength: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dexterity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    constitution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    intelligence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    wisdom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    charisma: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )

    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.id"), nullable=False, unique=True
    )
    character: Mapped["Character"] = relationship(
        back_populates="saving_throws", uselist=False
    )
