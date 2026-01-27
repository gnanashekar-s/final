"""Project API routes."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.core.security import get_current_user
from app.database import get_db
from app.models.project import Project, ProjectStatus
from app.models.run import Run, RunStatus, WorkflowStage
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithRunsResponse,
    RunCreate,
    RunResponse,
)
from app.services.workflow_service import WorkflowService

logger = get_logger("api.projects")

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[ProjectStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all projects for the current user."""
    # Build query
    query = select(Project).where(Project.user_id == current_user.id)

    if status_filter:
        query = query.where(Project.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Get paginated results
    query = query.order_by(Project.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().all()

    return {
        "items": projects,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Create a new project."""
    project = Project(
        user_id=current_user.id,
        name=project_data.name,
        product_request=project_data.product_request,
        status=ProjectStatus.DRAFT,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)

    return project


@router.get("/{project_id}", response_model=ProjectWithRunsResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Get a specific project with its runs."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.runs))
        .where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Update a project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id, Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Update fields
    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)

    return project


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id, Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await db.delete(project)

    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    project_id: int,
    run_data: Optional[RunCreate] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Run:
    """
    Create a new workflow run for a project and start the workflow.

    This endpoint:
    1. Creates a new Run record
    2. Starts the LangGraph workflow in the background
    3. Returns the Run immediately (workflow continues asynchronously)

    Use SSE endpoint /stream/{run_id} to monitor progress.
    """
    # Verify project ownership
    result = await db.execute(
        select(Project).where(
            Project.id == project_id, Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get optional constraints from request body
    constraints = run_data.constraints if run_data else None

    logger.info(f"Creating run for project {project_id} (user {current_user.id})")

    # Use workflow service to create run and start workflow
    workflow_service = WorkflowService(db)

    try:
        run = await workflow_service.start_workflow(
            project_id=project_id,
            user_id=current_user.id,
            constraints=constraints,
        )

        logger.info(f"Workflow started for run {run.id}")

        # Commit the transaction to persist the run
        await db.commit()
        await db.refresh(run)

        return run

    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}",
        )


@router.get("/{project_id}/runs", response_model=list[RunResponse])
async def list_runs(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Run]:
    """List all runs for a project."""
    # Verify project ownership
    result = await db.execute(
        select(Project).where(
            Project.id == project_id, Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get runs
    result = await db.execute(
        select(Run)
        .where(Run.project_id == project_id)
        .order_by(Run.created_at.desc())
    )

    return result.scalars().all()


@router.get("/{project_id}/runs/{run_id}", response_model=RunResponse)
async def get_run(
    project_id: int,
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Run:
    """Get a specific run."""
    # Verify project ownership and get run
    result = await db.execute(
        select(Run)
        .join(Project)
        .where(
            Run.id == run_id,
            Run.project_id == project_id,
            Project.user_id == current_user.id,
        )
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    return run
