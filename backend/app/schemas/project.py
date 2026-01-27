"""Project Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.project import ProjectStatus
from app.models.run import RunStatus, WorkflowStage
from app.schemas.common import BaseSchema


class ProjectBase(BaseModel):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=255)
    product_request: str = Field(..., min_length=10)


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""

    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    product_request: Optional[str] = Field(None, min_length=10)
    status: Optional[ProjectStatus] = None


class ProjectResponse(ProjectBase, BaseSchema):
    """Schema for project response."""

    id: int
    user_id: int
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class ProjectWithRunsResponse(ProjectResponse):
    """Project response with runs."""

    runs: list["RunResponse"] = []


class RunBase(BaseModel):
    """Base run schema."""

    pass


class RunCreate(RunBase):
    """Schema for creating a run.

    The project_id is taken from the URL path, not the request body.
    """

    constraints: Optional[str] = Field(
        None,
        description="Additional constraints or requirements for the workflow",
        examples=["Use PostgreSQL and Redis", "Must support multi-tenancy"],
    )


class RunResponse(BaseSchema):
    """Schema for run response."""

    id: int
    project_id: int
    status: RunStatus
    current_stage: WorkflowStage
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RunDetailResponse(RunResponse):
    """Detailed run response with artifacts."""

    checkpoint_data: Optional[dict] = None


class ResearchArtifactResponse(BaseSchema):
    """Schema for research artifact response."""

    id: int
    run_id: int
    urls: list[str]
    findings: dict
    summary: Optional[str] = None
    created_at: datetime


class TraceabilityMatrixResponse(BaseSchema):
    """Schema for traceability matrix response."""

    id: int
    project_id: int
    mapping: dict
    created_at: datetime
    updated_at: datetime


# Update forward references
ProjectWithRunsResponse.model_rebuild()
