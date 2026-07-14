import uuid

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, UUID, DateTime, func, Integer, ForeignKey, CheckConstraint

from src.databases.sql import Base


class Stat(Base):
    __tablename__ = "stats"
    __table_args__ = (
        CheckConstraint('strength >= 8', name='ck_strength_min'),
        CheckConstraint('dexterity >= 8', name='ck_dexterity_min'),
        CheckConstraint('constitution >= 8', name='ck_constitution_min'),
        CheckConstraint('intelligence >= 8', name='ck_intelligence_min'),
        CheckConstraint('wisdom >= 8', name='ck_wisdom_min'),
        CheckConstraint('charisma >= 8', name='ck_charisma_min'),
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

    character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    character: Mapped["Character"] = relationship(back_populates="stats", uselist=False)
