"""SSE streaming API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.sse import sse_manager
from app.database import get_db
from app.models.project import Project
from app.models.run import Run
from app.models.user import User

router = APIRouter(prefix="/stream", tags=["Streaming"])


@router.get("/{run_id}")
async def stream_run_events(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream SSE events for a workflow run."""
    # Verify run ownership
    result = await db.execute(
        select(Run)
        .join(Project)
        .where(Run.id == run_id, Project.user_id == current_user.id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    return StreamingResponse(
        sse_manager.subscribe(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/{run_id}/status")
async def get_stream_status(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the current status of an SSE stream."""
    # Verify run ownership
    result = await db.execute(
        select(Run)
        .join(Project)
        .where(Run.id == run_id, Project.user_id == current_user.id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    return {
        "run_id": run_id,
        "run_status": run.status.value,
        "current_stage": run.current_stage.value,
        "subscriber_count": sse_manager.get_subscriber_count(run_id),
    }
