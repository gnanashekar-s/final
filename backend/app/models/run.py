"""Run model for workflow execution."""
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.epic import Epic
    from app.models.project import Project


class RunStatus(str, PyEnum):
    """Run status enum."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStage(str, PyEnum):
    """Workflow stage enum."""
    RESEARCH = "research"
    EPIC_GENERATION = "epic_generation"
    EPIC_REVIEW = "epic_review"
    STORY_GENERATION = "story_generation"
    STORY_REVIEW = "story_review"
    SPEC_GENERATION = "spec_generation"
    SPEC_REVIEW = "spec_review"
    CODE_GENERATION = "code_generation"
    VALIDATION = "validation"
    COMPLETED = "completed"


class Run(Base):
    """Run model representing a workflow execution."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus), default=RunStatus.PENDING, nullable=False
    )
    current_stage: Mapped[WorkflowStage] = mapped_column(
        Enum(WorkflowStage), default=WorkflowStage.RESEARCH, nullable=False
    )
    checkpoint_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="runs")
    research_artifacts: Mapped[list["ResearchArtifact"]] = relationship(
        "ResearchArtifact", back_populates="run", cascade="all, delete-orphan"
    )
    epics: Mapped[list["Epic"]] = relationship(
        "Epic", back_populates="run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, project_id={self.project_id}, status={self.status})>"


class ResearchArtifact(Base):
    """Research artifact model for storing research results."""

    __tablename__ = "research_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    urls: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    findings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="research_artifacts")

    def __repr__(self) -> str:
        return f"<ResearchArtifact(id={self.id}, run_id={self.run_id})>"
