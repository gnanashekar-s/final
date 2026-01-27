"""Admin API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_admin_user, get_password_hash
from app.database import get_db
from app.models.code_artifact import CodeArtifact
from app.models.epic import Epic
from app.models.project import Project, ProjectStatus
from app.models.run import Run, RunStatus
from app.models.spec import Spec
from app.models.story import Story
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import UserResponse, UserUpdate, UserWithProjectCount

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=PaginatedResponse[UserWithProjectCount])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role_filter: Optional[UserRole] = None,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all users (admin only)."""
    # Build query
    query = select(User)
    if role_filter:
        query = query.where(User.role == role_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Get paginated results with project counts
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    # Get project counts for each user
    user_data = []
    for user in users:
        count_result = await db.execute(
            select(func.count()).where(Project.user_id == user.id)
        )
        project_count = count_result.scalar_one()
        user_data.append({
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at,
            "project_count": project_count,
        })

    return {
        "items": user_data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/users/{user_id}", response_model=UserWithProjectCount)
async def get_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a specific user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get project count
    count_result = await db.execute(
        select(func.count()).where(Project.user_id == user.id)
    )
    project_count = count_result.scalar_one()

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at,
        "project_count": project_count,
    }


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)

    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)

    return user


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a user (admin only)."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.delete(user)

    return {"message": "User deleted successfully"}


@router.get("/stats")
async def get_system_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get system-wide statistics (admin only)."""
    # Count users
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()

    # Count projects by status
    project_stats = {}
    for status_val in ProjectStatus:
        count = (
            await db.execute(
                select(func.count()).where(Project.status == status_val)
            )
        ).scalar_one()
        project_stats[status_val.value] = count

    # Count runs by status
    run_stats = {}
    for status_val in RunStatus:
        count = (
            await db.execute(
                select(func.count()).where(Run.status == status_val)
            )
        ).scalar_one()
        run_stats[status_val.value] = count

    # Count artifacts
    epic_count = (await db.execute(select(func.count()).select_from(Epic))).scalar_one()
    story_count = (await db.execute(select(func.count()).select_from(Story))).scalar_one()
    spec_count = (await db.execute(select(func.count()).select_from(Spec))).scalar_one()
    code_count = (await db.execute(select(func.count()).select_from(CodeArtifact))).scalar_one()

    return {
        "users": {
            "total": user_count,
        },
        "projects": project_stats,
        "runs": run_stats,
        "artifacts": {
            "epics": epic_count,
            "stories": story_count,
            "specs": spec_count,
            "code_artifacts": code_count,
        },
    }


@router.get("/projects", response_model=PaginatedResponse[dict])
async def list_all_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[ProjectStatus] = None,
    user_id: Optional[int] = None,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all projects across users (admin only)."""
    # Build query
    query = select(Project, User.email).join(User)

    if status_filter:
        query = query.where(Project.status == status_filter)
    if user_id:
        query = query.where(Project.user_id == user_id)

    # Get total count
    count_subquery = select(Project)
    if status_filter:
        count_subquery = count_subquery.where(Project.status == status_filter)
    if user_id:
        count_subquery = count_subquery.where(Project.user_id == user_id)
    count_query = select(func.count()).select_from(count_subquery.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Get paginated results
    query = query.order_by(Project.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    projects = [
        {
            "id": project.id,
            "name": project.name,
            "status": project.status.value,
            "user_id": project.user_id,
            "user_email": email,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }
        for project, email in rows
    ]

    return {
        "items": projects,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("/users/{user_id}/promote", response_model=UserResponse)
async def promote_to_admin(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Promote a user to admin (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.role = UserRole.ADMIN
    await db.flush()
    await db.refresh(user)

    return user


@router.post("/users/{user_id}/demote", response_model=UserResponse)
async def demote_to_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Demote an admin to regular user (admin only)."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote yourself",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.role = UserRole.USER
    await db.flush()
    await db.refresh(user)

    return user
