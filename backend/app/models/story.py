"""Story model."""
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.epic import Epic
    from app.models.spec import Spec


class StoryStatus(str, PyEnum):
    """Story status enum."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class StoryPriority(str, PyEnum):
    """Story priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Story(Base):
    """Story model representing a user story."""

    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    epic_id: Mapped[int] = mapped_column(ForeignKey("epics.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    priority: Mapped[StoryPriority] = mapped_column(
        Enum(StoryPriority), default=StoryPriority.MEDIUM, nullable=False
    )
    status: Mapped[StoryStatus] = mapped_column(
        Enum(StoryStatus), default=StoryStatus.DRAFT, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    story_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    edge_cases: Mapped[Optional[list]] = mapped_column(JSONB, default=list, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    epic: Mapped["Epic"] = relationship("Epic", back_populates="stories")
    specs: Mapped[list["Spec"]] = relationship(
        "Spec", back_populates="story", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Story(id={self.id}, title={self.title}, status={self.status})>"
