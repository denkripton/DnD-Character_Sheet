import uuid

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, UUID, DateTime, func, Integer, ForeignKey, CheckConstraint

from src.databases.sql import Base


class Stat(Base):
    __tablename__ = "stats"
    __table_args__ = (
        CheckConstraint('strength >= 3 AND strength <= 20', name='ck_strength_range'),
        CheckConstraint('dexterity >= 3 AND dexterity <= 20', name='ck_dexterity_range'),
        CheckConstraint('constitution >= 3 AND constitution <= 20', name='ck_constitution_range'),
        CheckConstraint('intelligence >= 3 AND intelligence <= 20', name='ck_intelligence_range'),
        CheckConstraint('wisdom >= 3 AND wisdom <= 20', name='ck_wisdom_range'),
        CheckConstraint('charisma >= 3 AND charisma <= 20', name='ck_charisma_range'),
    )


    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, primary_key=True
    )
    
    strength: Mapped[int] = mapped_column(Integer, nullable=False)
    dexterity: Mapped[int] = mapped_column(Integer, nullable=False)
    constitution: Mapped[int] = mapped_column(Integer, nullable=False)
    intelligence: Mapped[int] = mapped_column(Integer, nullable=False)
    wisdom: Mapped[int] = mapped_column(Integer, nullable=False)
    charisma: Mapped[int] = mapped_column(Integer, nullable=False)

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
    character: Mapped["Character"] = relationship(back_populates="stats", uselist=False)
