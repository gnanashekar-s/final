"""Story Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.story import StoryPriority, StoryStatus
from app.schemas.common import BaseSchema


class AcceptanceCriterion(BaseModel):
    """Acceptance criterion schema."""

    given: str
    when: str
    then: str


class StoryBase(BaseModel):
    """Base story schema."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)


class StoryCreate(StoryBase):
    """Schema for creating a story."""

    epic_id: int
    acceptance_criteria: list[AcceptanceCriterion] = []
    priority: StoryPriority = StoryPriority.MEDIUM
    story_points: Optional[int] = None
    edge_cases: Optional[list[str]] = None


class StoryUpdate(BaseModel):
    """Schema for updating a story."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    acceptance_criteria: Optional[list[AcceptanceCriterion]] = None
    priority: Optional[StoryPriority] = None
    status: Optional[StoryStatus] = None
    story_points: Optional[int] = None
    edge_cases: Optional[list[str]] = None


class StoryApproval(BaseModel):
    """Schema for story approval/rejection."""

    approved: bool
    feedback: Optional[str] = None


class StoryResponse(StoryBase, BaseSchema):
    """Schema for story response."""

    id: int
    epic_id: int
    acceptance_criteria: list[dict]
    priority: StoryPriority
    status: StoryStatus
    version: int
    story_points: Optional[int] = None
    edge_cases: Optional[list[str]] = None
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StoryWithSpecsResponse(StoryResponse):
    """Story response with specs."""

    specs: list["SpecResponse"] = []


class StoryGenerationRequest(BaseModel):
    """Request schema for story generation."""

    epic_id: int
    constraints: Optional[str] = None


# Import for forward reference
from app.schemas.spec import SpecResponse  # noqa: E402

StoryWithSpecsResponse.model_rebuild()
