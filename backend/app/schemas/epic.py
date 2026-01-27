"""Epic Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.epic import EpicPriority, EpicStatus
from app.schemas.common import BaseSchema


class EpicBase(BaseModel):
    """Base epic schema."""

    title: str = Field(..., min_length=1, max_length=255)
    goal: str = Field(..., min_length=10)
    scope: str = Field(..., min_length=10)


class EpicCreate(EpicBase):
    """Schema for creating an epic."""

    project_id: int
    run_id: int
    priority: EpicPriority = EpicPriority.MEDIUM
    dependencies: Optional[list[int]] = None


class EpicUpdate(BaseModel):
    """Schema for updating an epic."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    goal: Optional[str] = Field(None, min_length=10)
    scope: Optional[str] = Field(None, min_length=10)
    priority: Optional[EpicPriority] = None
    status: Optional[EpicStatus] = None
    dependencies: Optional[list[int]] = None
    mermaid_diagram: Optional[str] = None


class EpicApproval(BaseModel):
    """Schema for epic approval/rejection."""

    approved: bool
    feedback: Optional[str] = None


class EpicResponse(EpicBase, BaseSchema):
    """Schema for epic response."""

    id: int
    project_id: int
    run_id: int
    priority: EpicPriority
    status: EpicStatus
    version: int
    dependencies: Optional[list[int]] = None
    mermaid_diagram: Optional[str] = None
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EpicWithStoriesResponse(EpicResponse):
    """Epic response with stories."""

    stories: list["StoryResponse"] = []


class EpicGenerationRequest(BaseModel):
    """Request schema for epic generation."""

    run_id: int
    constraints: Optional[str] = None


# Import for forward reference
from app.schemas.story import StoryResponse  # noqa: E402

EpicWithStoriesResponse.model_rebuild()
