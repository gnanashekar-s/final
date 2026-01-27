"""Code artifact API routes."""
import io
import zipfile
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.code_artifact import CodeArtifact, CodeArtifactStatus
from app.models.epic import Epic
from app.models.project import Project
from app.models.spec import Spec
from app.models.story import Story
from app.models.user import User
from app.schemas.code import (
    CodeArtifactCreate,
    CodeArtifactResponse,
    CodeArtifactUpdate,
    CodeExportResponse,
)
from app.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter(prefix="/code", tags=["Code"])


@router.get("", response_model=PaginatedResponse[CodeArtifactResponse])
async def list_code_artifacts(
    spec_id: Optional[int] = None,
    status_filter: Optional[CodeArtifactStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List code artifacts with optional filtering."""
    # Build base query with user ownership check
    query = (
        select(CodeArtifact)
        .join(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(Project.user_id == current_user.id)
    )

    if spec_id:
        query = query.where(CodeArtifact.spec_id == spec_id)
    if status_filter:
        query = query.where(CodeArtifact.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Get paginated results
    query = query.order_by(CodeArtifact.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    artifacts = result.scalars().all()

    return {
        "items": artifacts,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("", response_model=CodeArtifactResponse, status_code=status.HTTP_201_CREATED)
async def create_code_artifact(
    artifact_data: CodeArtifactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CodeArtifact:
    """Create a new code artifact manually."""
    # Verify spec ownership
    result = await db.execute(
        select(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(
            Spec.id == artifact_data.spec_id,
            Project.user_id == current_user.id,
        )
    )
    spec = result.scalar_one_or_none()

    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec not found",
        )

    artifact = CodeArtifact(
        spec_id=artifact_data.spec_id,
        files=artifact_data.files,
        status=CodeArtifactStatus.DRAFT,
    )
    db.add(artifact)
    await db.flush()
    await db.refresh(artifact)

    return artifact


@router.get("/{artifact_id}", response_model=CodeArtifactResponse)
async def get_code_artifact(
    artifact_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CodeArtifact:
    """Get a specific code artifact."""
    result = await db.execute(
        select(CodeArtifact)
        .join(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(CodeArtifact.id == artifact_id, Project.user_id == current_user.id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code artifact not found",
        )

    return artifact


@router.put("/{artifact_id}", response_model=CodeArtifactResponse)
async def update_code_artifact(
    artifact_id: int,
    artifact_data: CodeArtifactUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CodeArtifact:
    """Update a code artifact."""
    result = await db.execute(
        select(CodeArtifact)
        .join(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(CodeArtifact.id == artifact_id, Project.user_id == current_user.id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code artifact not found",
        )

    # Update fields
    update_data = artifact_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(artifact, field, value)

    # Increment version on file changes
    if "files" in update_data:
        artifact.version += 1

    await db.flush()
    await db.refresh(artifact)

    return artifact


@router.delete("/{artifact_id}", response_model=MessageResponse)
async def delete_code_artifact(
    artifact_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a code artifact."""
    result = await db.execute(
        select(CodeArtifact)
        .join(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(CodeArtifact.id == artifact_id, Project.user_id == current_user.id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code artifact not found",
        )

    await db.delete(artifact)

    return {"message": "Code artifact deleted successfully"}


@router.get("/{artifact_id}/files/{filename}")
async def get_file_content(
    artifact_id: int,
    filename: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get content of a specific file in a code artifact."""
    result = await db.execute(
        select(CodeArtifact)
        .join(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(CodeArtifact.id == artifact_id, Project.user_id == current_user.id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code artifact not found",
        )

    if filename not in artifact.files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in artifact",
        )

    return {
        "filename": filename,
        "content": artifact.files[filename],
    }


@router.get("/{artifact_id}/export")
async def export_code_artifact(
    artifact_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export code artifact as a ZIP file."""
    result = await db.execute(
        select(CodeArtifact)
        .join(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(CodeArtifact.id == artifact_id, Project.user_id == current_user.id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code artifact not found",
        )

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in artifact.files.items():
            zip_file.writestr(filename, content)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=code_artifact_{artifact_id}.zip"
        },
    )


@router.get("/{artifact_id}/validation-report")
async def get_validation_report(
    artifact_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the validation report for a code artifact."""
    result = await db.execute(
        select(CodeArtifact)
        .join(Spec)
        .join(Story)
        .join(Epic)
        .join(Project)
        .where(CodeArtifact.id == artifact_id, Project.user_id == current_user.id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code artifact not found",
        )

    return {
        "artifact_id": artifact_id,
        "status": artifact.status.value,
        "validation_report": artifact.validation_report,
        "lint_results": artifact.lint_results,
        "test_results": artifact.test_results,
        "error_log": artifact.error_log,
        "fix_attempts": artifact.fix_attempts,
    }
