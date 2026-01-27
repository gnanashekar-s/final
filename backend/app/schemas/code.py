"""Code artifact Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.code_artifact import CodeArtifactStatus
from app.schemas.common import BaseSchema


class CodeFile(BaseModel):
    """Code file schema."""

    filename: str
    content: str
    language: str = "python"


class ValidationResult(BaseModel):
    """Validation result schema."""

    passed: bool
    message: str
    details: Optional[dict] = None


class LintResult(BaseModel):
    """Lint result schema."""

    file: str
    line: int
    column: int
    severity: str
    message: str
    rule: Optional[str] = None


class TestResult(BaseModel):
    """Test result schema."""

    test_name: str
    passed: bool
    duration: float
    error_message: Optional[str] = None


class CodeArtifactBase(BaseModel):
    """Base code artifact schema."""

    files: dict[str, str]  # filename -> content


class CodeArtifactCreate(CodeArtifactBase):
    """Schema for creating a code artifact."""

    spec_id: int


class CodeArtifactUpdate(BaseModel):
    """Schema for updating a code artifact."""

    files: Optional[dict[str, str]] = None
    status: Optional[CodeArtifactStatus] = None
    validation_report: Optional[dict] = None
    lint_results: Optional[dict] = None
    test_results: Optional[dict] = None
    error_log: Optional[str] = None


class CodeArtifactResponse(CodeArtifactBase, BaseSchema):
    """Schema for code artifact response."""

    id: int
    spec_id: int
    status: CodeArtifactStatus
    version: int
    fix_attempts: int
    validation_report: Optional[dict] = None
    lint_results: Optional[dict] = None
    test_results: Optional[dict] = None
    error_log: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CodeGenerationRequest(BaseModel):
    """Request schema for code generation."""

    spec_id: int
    constraints: Optional[str] = None


class CodeValidationRequest(BaseModel):
    """Request schema for code validation."""

    code_artifact_id: int
    auto_fix: bool = True


class CodeExportRequest(BaseModel):
    """Request schema for code export."""

    code_artifact_id: int
    format: str = "zip"  # zip, tar.gz


class CodeExportResponse(BaseModel):
    """Response schema for code export."""

    download_url: str
    filename: str
    size_bytes: int
