import uuid

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, UUID, DateTime, func, Integer, ForeignKey

from src.databases.sql import Base


class Character(Base):
    __tablename__ = "charactes"


    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, primary_key=True
    )
    
    name: Mapped[str] = mapped_column(String(100))
    spec_class: Mapped[str] = mapped_column(String(20), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )

    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))

    owner: Mapped["User"] = relationship(back_populates="character")