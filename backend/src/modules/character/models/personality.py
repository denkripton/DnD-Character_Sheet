import uuid

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Text, ForeignKey, DateTime, func, UUID

from src.databases.sql import Base


class Personality(Base):
    __tablename__ = "personality"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, primary_key=True
    )

    personality_traits: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ideals: Mapped[str] = mapped_column(Text, nullable=False, default="")
    bonds: Mapped[str] = mapped_column(Text, nullable=False, default="")
    flaws: Mapped[str] = mapped_column(Text, nullable=False, default="")

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
        back_populates="personality", uselist=False
    )
