"""Spec model."""
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.code_artifact import CodeArtifact
    from app.models.story import Story


class SpecStatus(str, PyEnum):
    """Spec status enum."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class Spec(Base):
    """Spec model representing a technical specification."""

    __tablename__ = "specs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SpecStatus] = mapped_column(
        Enum(SpecStatus), default=SpecStatus.DRAFT, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Structured spec components
    requirements: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    api_design: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    data_model: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    security_requirements: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    test_plan: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    mermaid_diagrams: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    story: Mapped["Story"] = relationship("Story", back_populates="specs")
    code_artifacts: Mapped[list["CodeArtifact"]] = relationship(
        "CodeArtifact", back_populates="spec", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Spec(id={self.id}, story_id={self.story_id}, status={self.status})>"
