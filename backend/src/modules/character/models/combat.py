import uuid

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UUID, Integer, String, Boolean, ForeignKey, DateTime, func

from src.databases.sql import Base


class Combat(Base):
    __tablename__ = "combat"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, primary_key=True
    )

    current_hp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_hp: Mapped[int] = mapped_column(Integer, nullable=False)
    temp_hp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bonus_hp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    armor_class: Mapped[int] = mapped_column(Integer, nullable=False)
    initiative: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    speed: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    proficiency_bonus: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    hit_dice_total: Mapped[str] = mapped_column(String(20), nullable=False)
    hit_dice_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    inspiration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    death_save_successes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    death_save_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

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
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    character: Mapped["Character"] = relationship(back_populates="combat", uselist=False)
