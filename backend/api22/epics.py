"""Epic API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.database import get_db
from app.models.epic import Epic, EpicStatus
from app.models.project import Project
from app.models.run import Run
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.epic import (
    EpicApproval,
    EpicCreate,
    EpicResponse,
    EpicUpdate,
    EpicWithStoriesResponse,
)

router = APIRouter(prefix="/epics", tags=["Epics"])


@router.get("", response_model=PaginatedResponse[EpicResponse])
async def list_epics(
    project_id: Optional[int] = None,
    run_id: Optional[int] = None,
    status_filter: Optional[EpicStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List epics with optional filtering."""
    # Build base query with user ownership check
    query = (
        select(Epic)
        .join(Project)
        .where(Project.user_id == current_user.id)
    )

    if project_id:
        query = query.where(Epic.project_id == project_id)
    if run_id:
        query = query.where(Epic.run_id == run_id)
    if status_filter:
        query = query.where(Epic.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Get paginated results
    query = query.order_by(Epic.priority.desc(), Epic.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    epics = result.scalars().all()

    return {
        "items": epics,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("", response_model=EpicResponse, status_code=status.HTTP_201_CREATED)
async def create_epic(
    epic_data: EpicCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Epic:
    """Create a new epic manually."""
    # Verify project ownership
    result = await db.execute(
        select(Project).where(
            Project.id == epic_data.project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Verify run belongs to project
    result = await db.execute(
        select(Run).where(
            Run.id == epic_data.run_id,
            Run.project_id == epic_data.project_id,
        )
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    epic = Epic(
        project_id=epic_data.project_id,
        run_id=epic_data.run_id,
        title=epic_data.title,
        goal=epic_data.goal,
        scope=epic_data.scope,
        priority=epic_data.priority,
        dependencies=epic_data.dependencies,
        status=EpicStatus.DRAFT,
    )
    db.add(epic)
    await db.flush()
    await db.refresh(epic)

    return epic


@router.get("/{epic_id}", response_model=EpicWithStoriesResponse)
async def get_epic(
    epic_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Epic:
    """Get a specific epic with its stories."""
    result = await db.execute(
        select(Epic)
        .options(selectinload(Epic.stories))
        .join(Project)
        .where(Epic.id == epic_id, Project.user_id == current_user.id)
    )
    epic = result.scalar_one_or_none()

    if not epic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Epic not found",
        )

    return epic


@router.put("/{epic_id}", response_model=EpicResponse)
async def update_epic(
    epic_id: int,
    epic_data: EpicUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Epic:
    """Update an epic."""
    result = await db.execute(
        select(Epic)
        .join(Project)
        .where(Epic.id == epic_id, Project.user_id == current_user.id)
    )
    epic = result.scalar_one_or_none()

    if not epic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Epic not found",
        )

    # Update fields
    update_data = epic_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(epic, field, value)

    # Increment version on content changes
    if any(f in update_data for f in ["title", "goal", "scope"]):
        epic.version += 1

    await db.flush()
    await db.refresh(epic)

    return epic


@router.delete("/{epic_id}", response_model=MessageResponse)
async def delete_epic(
    epic_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an epic."""
    result = await db.execute(
        select(Epic)
        .join(Project)
        .where(Epic.id == epic_id, Project.user_id == current_user.id)
    )
    epic = result.scalar_one_or_none()

    if not epic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Epic not found",
        )

    await db.delete(epic)

    return {"message": "Epic deleted successfully"}


@router.post("/{epic_id}/approve", response_model=EpicResponse)
async def approve_epic(
    epic_id: int,
    approval: EpicApproval,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Epic:
    """Approve or reject an epic."""
    result = await db.execute(
        select(Epic)
        .join(Project)
        .where(Epic.id == epic_id, Project.user_id == current_user.id)
    )
    epic = result.scalar_one_or_none()

    if not epic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Epic not found",
        )

    if epic.status != EpicStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Epic is not pending review",
        )

    if approval.approved:
        epic.status = EpicStatus.APPROVED
    else:
        epic.status = EpicStatus.REJECTED
        epic.feedback = approval.feedback

    await db.flush()
    await db.refresh(epic)

    return epic


@router.get("/project/{project_id}/dependency-graph")
async def get_epic_dependency_graph(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the dependency graph for all epics in a project."""
    # Verify project ownership
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get all epics for the project
    result = await db.execute(
        select(Epic).where(Epic.project_id == project_id)
    )
    epics = result.scalars().all()

    # Build dependency graph
    nodes = []
    edges = []

    for epic in epics:
        nodes.append({
            "id": epic.id,
            "title": epic.title,
            "status": epic.status.value,
            "priority": epic.priority.value,
        })

        if epic.dependencies:
            for dep_id in epic.dependencies:
                edges.append({
                    "from": dep_id,
                    "to": epic.id,
                })

    # Generate Mermaid diagram
    mermaid = "graph TD\n"
    for epic in epics:
        mermaid += f'    E{epic.id}["{epic.title}"]\n'

    for epic in epics:
        if epic.dependencies:
            for dep_id in epic.dependencies:
                mermaid += f"    E{dep_id} --> E{epic.id}\n"

    return {
        "nodes": nodes,
        "edges": edges,
        "mermaid": mermaid,
    }
