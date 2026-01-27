"""Epic model."""
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.run import Run
    from app.models.story import Story


class EpicStatus(str, PyEnum):
    """Epic status enum."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class EpicPriority(str, PyEnum):
    """Epic priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Epic(Base):
    """Epic model representing a high-level feature."""

    __tablename__ = "epics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[EpicPriority] = mapped_column(
        Enum(EpicPriority), default=EpicPriority.MEDIUM, nullable=False
    )
    status: Mapped[EpicStatus] = mapped_column(
        Enum(EpicStatus), default=EpicStatus.DRAFT, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    dependencies: Mapped[Optional[list]] = mapped_column(JSONB, default=list, nullable=True)
    mermaid_diagram: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="epics")
    run: Mapped["Run"] = relationship("Run", back_populates="epics")
    stories: Mapped[list["Story"]] = relationship(
        "Story", back_populates="epic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Epic(id={self.id}, title={self.title}, status={self.status})>"
