"""Story API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.database import get_db
from app.models.epic import Epic
from app.models.project import Project
from app.models.story import Story, StoryStatus
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.story import (
    StoryApproval,
    StoryCreate,
    StoryResponse,
    StoryUpdate,
    StoryWithSpecsResponse,
)

router = APIRouter(prefix="/stories", tags=["Stories"])


@router.get("", response_model=PaginatedResponse[StoryResponse])
async def list_stories(
    epic_id: Optional[int] = None,
    status_filter: Optional[StoryStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List stories with optional filtering."""
    # Build base query with user ownership check
    query = (
        select(Story)
        .join(Epic)
        .join(Project)
        .where(Project.user_id == current_user.id)
    )

    if epic_id:
        query = query.where(Story.epic_id == epic_id)
    if status_filter:
        query = query.where(Story.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Get paginated results
    query = query.order_by(Story.priority.desc(), Story.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    stories = result.scalars().all()

    return {
        "items": stories,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    story_data: StoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Story:
    """Create a new story manually."""
    # Verify epic ownership
    result = await db.execute(
        select(Epic)
        .join(Project)
        .where(
            Epic.id == story_data.epic_id,
            Project.user_id == current_user.id,
        )
    )
    epic = result.scalar_one_or_none()

    if not epic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Epic not found",
        )

    # Convert acceptance criteria to dict format
    acceptance_criteria = [
        ac.model_dump() for ac in story_data.acceptance_criteria
    ]

    story = Story(
        epic_id=story_data.epic_id,
        title=story_data.title,
        description=story_data.description,
        acceptance_criteria=acceptance_criteria,
        priority=story_data.priority,
        story_points=story_data.story_points,
        edge_cases=story_data.edge_cases,
        status=StoryStatus.DRAFT,
    )
    db.add(story)
    await db.flush()
    await db.refresh(story)

    return story


@router.get("/{story_id}", response_model=StoryWithSpecsResponse)
async def get_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Story:
    """Get a specific story with its specs."""
    result = await db.execute(
        select(Story)
        .options(selectinload(Story.specs))
        .join(Epic)
        .join(Project)
        .where(Story.id == story_id, Project.user_id == current_user.id)
    )
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    return story


@router.put("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: int,
    story_data: StoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Story:
    """Update a story."""
    result = await db.execute(
        select(Story)
        .join(Epic)
        .join(Project)
        .where(Story.id == story_id, Project.user_id == current_user.id)
    )
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    # Update fields
    update_data = story_data.model_dump(exclude_unset=True)

    # Convert acceptance criteria if provided
    if "acceptance_criteria" in update_data and update_data["acceptance_criteria"]:
        update_data["acceptance_criteria"] = [
            ac.model_dump() if hasattr(ac, "model_dump") else ac
            for ac in update_data["acceptance_criteria"]
        ]

    for field, value in update_data.items():
        setattr(story, field, value)

    # Increment version on content changes
    if any(f in update_data for f in ["title", "description", "acceptance_criteria"]):
        story.version += 1

    await db.flush()
    await db.refresh(story)

    return story


@router.delete("/{story_id}", response_model=MessageResponse)
async def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a story."""
    result = await db.execute(
        select(Story)
        .join(Epic)
        .join(Project)
        .where(Story.id == story_id, Project.user_id == current_user.id)
    )
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    await db.delete(story)

    return {"message": "Story deleted successfully"}


@router.post("/{story_id}/approve", response_model=StoryResponse)
async def approve_story(
    story_id: int,
    approval: StoryApproval,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Story:
    """Approve or reject a story."""
    result = await db.execute(
        select(Story)
        .join(Epic)
        .join(Project)
        .where(Story.id == story_id, Project.user_id == current_user.id)
    )
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    if story.status != StoryStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Story is not pending review",
        )

    if approval.approved:
        story.status = StoryStatus.APPROVED
    else:
        story.status = StoryStatus.REJECTED
        story.feedback = approval.feedback

    await db.flush()
    await db.refresh(story)

    return story


@router.get("/epic/{epic_id}/summary")
async def get_epic_stories_summary(
    epic_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a summary of all stories for an epic."""
    # Verify epic ownership
    result = await db.execute(
        select(Epic)
        .join(Project)
        .where(
            Epic.id == epic_id,
            Project.user_id == current_user.id,
        )
    )
    epic = result.scalar_one_or_none()

    if not epic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Epic not found",
        )

    # Get all stories for the epic
    result = await db.execute(
        select(Story).where(Story.epic_id == epic_id)
    )
    stories = result.scalars().all()

    # Calculate summary statistics
    total_points = sum(s.story_points or 0 for s in stories)
    status_counts = {}
    for s in stories:
        status_counts[s.status.value] = status_counts.get(s.status.value, 0) + 1

    return {
        "epic_id": epic_id,
        "epic_title": epic.title,
        "total_stories": len(stories),
        "total_story_points": total_points,
        "status_breakdown": status_counts,
        "stories": [
            {
                "id": s.id,
                "title": s.title,
                "status": s.status.value,
                "priority": s.priority.value,
                "story_points": s.story_points,
            }
            for s in stories
        ],
    }
