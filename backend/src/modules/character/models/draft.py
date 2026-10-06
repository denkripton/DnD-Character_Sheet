import uuid

from sqlalchemy import JSON, UUID, DateTime, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column
from src.databases.sql import Base


class CharacterDraft(Base):
    __tablename__ = "character_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, primary_key=True
    )
    data: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'")
    )
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )
