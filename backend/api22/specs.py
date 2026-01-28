"""Spec API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.database import get_db
from app.models.epic import Epic
from app.models.project import Project
from app.models.spec import Spec, SpecStatus
from app.models.story import Story
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.spec import (
    SpecApproval,
    SpecCreate,
    SpecResponse,
    SpecUpdate,
    SpecWithCodeResponse,
)

router = APIRouter(prefix="/specs", tags=["Specs"])


@router.get("", response_model=PaginatedResponse[SpecResponse])
async def list_specs(
    story_id: Optional[int] = None,
    status_filter: Optional[SpecStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List specs with optional filtering."""
    # Build base query with user ownership check
    query = (
        select(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(Project.user_id == current_user.id)
    )

    if story_id:
        query = query.where(Spec.story_id == story_id)
    if status_filter:
        query = query.where(Spec.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Get paginated results
    query = query.order_by(Spec.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    specs = result.scalars().all()

    return {
        "items": specs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("", response_model=SpecResponse, status_code=status.HTTP_201_CREATED)
async def create_spec(
    spec_data: SpecCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Spec:
    """Create a new spec manually."""
    # Verify story ownership
    result = await db.execute(
        select(Story)
        .join(Epic)
        .join(Project)
        .where(
            Story.id == spec_data.story_id,
            Project.user_id == current_user.id,
        )
    )
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    spec = Spec(
        story_id=spec_data.story_id,
        content=spec_data.content,
        requirements=spec_data.requirements,
        api_design=spec_data.api_design,
        data_model=spec_data.data_model,
        security_requirements=spec_data.security_requirements,
        test_plan=spec_data.test_plan,
        mermaid_diagrams=spec_data.mermaid_diagrams,
        status=SpecStatus.DRAFT,
    )
    db.add(spec)
    await db.flush()
    await db.refresh(spec)

    return spec


@router.get("/{spec_id}", response_model=SpecWithCodeResponse)
async def get_spec(
    spec_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Spec:
    """Get a specific spec with its code artifacts."""
    result = await db.execute(
        select(Spec)
        .options(selectinload(Spec.code_artifacts))
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(Spec.id == spec_id, Project.user_id == current_user.id)
    )
    spec = result.scalar_one_or_none()

    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec not found",
        )

    return spec


@router.put("/{spec_id}", response_model=SpecResponse)
async def update_spec(
    spec_id: int,
    spec_data: SpecUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Spec:
    """Update a spec."""
    result = await db.execute(
        select(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(Spec.id == spec_id, Project.user_id == current_user.id)
    )
    spec = result.scalar_one_or_none()

    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec not found",
        )

    # Update fields
    update_data = spec_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(spec, field, value)

    # Increment version on content changes
    if "content" in update_data:
        spec.version += 1

    await db.flush()
    await db.refresh(spec)

    return spec


@router.delete("/{spec_id}", response_model=MessageResponse)
async def delete_spec(
    spec_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a spec."""
    result = await db.execute(
        select(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(Spec.id == spec_id, Project.user_id == current_user.id)
    )
    spec = result.scalar_one_or_none()

    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec not found",
        )

    await db.delete(spec)

    return {"message": "Spec deleted successfully"}


@router.post("/{spec_id}/approve", response_model=SpecResponse)
async def approve_spec(
    spec_id: int,
    approval: SpecApproval,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Spec:
    """Approve or reject a spec."""
    result = await db.execute(
        select(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(Spec.id == spec_id, Project.user_id == current_user.id)
    )
    spec = result.scalar_one_or_none()

    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec not found",
        )

    if spec.status != SpecStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spec is not pending review",
        )

    if approval.approved:
        spec.status = SpecStatus.APPROVED
    else:
        spec.status = SpecStatus.REJECTED
        spec.feedback = approval.feedback

    await db.flush()
    await db.refresh(spec)

    return spec


@router.get("/{spec_id}/diagrams")
async def get_spec_diagrams(
    spec_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all Mermaid diagrams for a spec."""
    result = await db.execute(
        select(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(Spec.id == spec_id, Project.user_id == current_user.id)
    )
    spec = result.scalar_one_or_none()

    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec not found",
        )

    return {
        "spec_id": spec_id,
        "diagrams": spec.mermaid_diagrams or {},
    }
