import uuid
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.databases.sql import Base

if TYPE_CHECKING:
    from src.modules.auth.models.user import User


class ExternalIdentity(Base):
    __tablename__ = "external_identities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_external_identities_provider_user",
        ),
    )
