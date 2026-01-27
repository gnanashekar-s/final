"""Spec Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.spec import SpecStatus
from app.schemas.common import BaseSchema


class APIEndpoint(BaseModel):
    """API endpoint schema."""

    method: str
    path: str
    description: str
    request_body: Optional[dict] = None
    response: Optional[dict] = None
    auth_required: bool = True


class DataModelField(BaseModel):
    """Data model field schema."""

    name: str
    type: str
    nullable: bool = False
    default: Optional[str] = None
    description: Optional[str] = None


class DataModel(BaseModel):
    """Data model schema."""

    name: str
    fields: list[DataModelField]
    relationships: Optional[list[str]] = None


class SecurityRequirement(BaseModel):
    """Security requirement schema."""

    requirement: str
    implementation: str
    priority: str = "medium"


class TestCase(BaseModel):
    """Test case schema."""

    name: str
    description: str
    type: str  # unit, integration, e2e
    expected_result: str


class SpecBase(BaseModel):
    """Base spec schema."""

    content: str = Field(..., min_length=50)


class SpecCreate(SpecBase):
    """Schema for creating a spec."""

    story_id: int
    requirements: Optional[dict] = None
    api_design: Optional[dict] = None
    data_model: Optional[dict] = None
    security_requirements: Optional[dict] = None
    test_plan: Optional[dict] = None
    mermaid_diagrams: Optional[dict] = None


class SpecUpdate(BaseModel):
    """Schema for updating a spec."""

    content: Optional[str] = Field(None, min_length=50)
    status: Optional[SpecStatus] = None
    requirements: Optional[dict] = None
    api_design: Optional[dict] = None
    data_model: Optional[dict] = None
    security_requirements: Optional[dict] = None
    test_plan: Optional[dict] = None
    mermaid_diagrams: Optional[dict] = None


class SpecApproval(BaseModel):
    """Schema for spec approval/rejection."""

    approved: bool
    feedback: Optional[str] = None


class SpecResponse(SpecBase, BaseSchema):
    """Schema for spec response."""

    id: int
    story_id: int
    status: SpecStatus
    version: int
    requirements: Optional[dict] = None
    api_design: Optional[dict] = None
    data_model: Optional[dict] = None
    security_requirements: Optional[dict] = None
    test_plan: Optional[dict] = None
    mermaid_diagrams: Optional[dict] = None
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SpecWithCodeResponse(SpecResponse):
    """Spec response with code artifacts."""

    code_artifacts: list["CodeArtifactResponse"] = []


class SpecGenerationRequest(BaseModel):
    """Request schema for spec generation."""

    story_id: int
    constraints: Optional[str] = None


# Import for forward reference
from app.schemas.code import CodeArtifactResponse  # noqa: E402

SpecWithCodeResponse.model_rebuild()
