"""Code artifact model."""
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.spec import Spec


class CodeArtifactStatus(str, PyEnum):
    """Code artifact status enum."""
    DRAFT = "draft"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    FIXING = "fixing"


class CodeArtifact(Base):
    """Code artifact model representing generated code."""

    __tablename__ = "code_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("specs.id"), nullable=False, index=True)
    files: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    validation_report: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[CodeArtifactStatus] = mapped_column(
        Enum(CodeArtifactStatus), default=CodeArtifactStatus.DRAFT, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    fix_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Validation details
    lint_results: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    test_results: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    spec: Mapped["Spec"] = relationship("Spec", back_populates="code_artifacts")

    def __repr__(self) -> str:
        return f"<CodeArtifact(id={self.id}, spec_id={self.spec_id}, status={self.status})>"
