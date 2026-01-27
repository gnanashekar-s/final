"""Server-Sent Events (SSE) manager for real-time updates."""
import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Optional


class SSEEventType(str, Enum):
    """SSE event types."""
    STAGE_UPDATE = "stage_update"
    PROGRESS = "progress"
    FILE_UPDATE = "file_update"
    COMPLETION = "completion"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    ARTIFACT_CREATED = "artifact_created"
    APPROVAL_REQUIRED = "approval_required"


@dataclass
class SSEEvent:
    """SSE event data class."""

    event_type: SSEEventType
    data: dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def format(self) -> str:
        """Format event for SSE transmission."""
        event_data = {
            "type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }
        return f"event: {self.event_type.value}\ndata: {json.dumps(event_data)}\n\n"


class SSEManager:
    """Manager for Server-Sent Events connections."""

    def __init__(self):
        self._subscribers: dict[int, list[asyncio.Queue]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def subscribe(self, run_id: int) -> AsyncGenerator[str, None]:
        """Subscribe to SSE events for a specific run."""
        queue: asyncio.Queue = asyncio.Queue()

        async with self._lock:
            self._subscribers[run_id].append(queue)

        try:
            # Send initial connection event
            yield SSEEvent(
                event_type=SSEEventType.HEARTBEAT,
                data={"message": "Connected", "run_id": run_id},
            ).format()

            while True:
                try:
                    # Wait for events with timeout for heartbeat
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event.format()

                    # Check for completion event
                    if event.event_type in (
                        SSEEventType.COMPLETION,
                        SSEEventType.ERROR,
                    ):
                        break
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield SSEEvent(
                        event_type=SSEEventType.HEARTBEAT,
                        data={"message": "keepalive"},
                    ).format()
        finally:
            async with self._lock:
                if run_id in self._subscribers:
                    self._subscribers[run_id].remove(queue)
                    if not self._subscribers[run_id]:
                        del self._subscribers[run_id]

    async def publish(self, run_id: int, event: SSEEvent) -> None:
        """Publish an event to all subscribers of a run."""
        async with self._lock:
            if run_id in self._subscribers:
                for queue in self._subscribers[run_id]:
                    await queue.put(event)

    async def publish_stage_update(
        self,
        run_id: int,
        stage: str,
        message: str,
        progress: Optional[float] = None,
    ) -> None:
        """Publish a stage update event."""
        await self.publish(
            run_id,
            SSEEvent(
                event_type=SSEEventType.STAGE_UPDATE,
                data={
                    "stage": stage,
                    "message": message,
                    "progress": progress,
                },
            ),
        )

    async def publish_progress(
        self,
        run_id: int,
        current: int,
        total: int,
        message: str,
    ) -> None:
        """Publish a progress event."""
        await self.publish(
            run_id,
            SSEEvent(
                event_type=SSEEventType.PROGRESS,
                data={
                    "current": current,
                    "total": total,
                    "percentage": (current / total * 100) if total > 0 else 0,
                    "message": message,
                },
            ),
        )

    async def publish_file_update(
        self,
        run_id: int,
        filename: str,
        action: str,
        content_preview: Optional[str] = None,
    ) -> None:
        """Publish a file update event."""
        await self.publish(
            run_id,
            SSEEvent(
                event_type=SSEEventType.FILE_UPDATE,
                data={
                    "filename": filename,
                    "action": action,
                    "content_preview": content_preview,
                },
            ),
        )

    async def publish_completion(
        self,
        run_id: int,
        success: bool,
        message: str,
        artifacts: Optional[dict] = None,
    ) -> None:
        """Publish a completion event."""
        await self.publish(
            run_id,
            SSEEvent(
                event_type=SSEEventType.COMPLETION,
                data={
                    "success": success,
                    "message": message,
                    "artifacts": artifacts,
                },
            ),
        )

    async def publish_error(
        self,
        run_id: int,
        error: str,
        recoverable: bool = False,
    ) -> None:
        """Publish an error event."""
        await self.publish(
            run_id,
            SSEEvent(
                event_type=SSEEventType.ERROR,
                data={
                    "error": error,
                    "recoverable": recoverable,
                },
            ),
        )

    async def publish_artifact_created(
        self,
        run_id: int,
        artifact_type: str,
        artifact_id: int,
        summary: str,
    ) -> None:
        """Publish an artifact created event."""
        await self.publish(
            run_id,
            SSEEvent(
                event_type=SSEEventType.ARTIFACT_CREATED,
                data={
                    "artifact_type": artifact_type,
                    "artifact_id": artifact_id,
                    "summary": summary,
                },
            ),
        )

    async def publish_approval_required(
        self,
        run_id: int,
        stage: str,
        artifact_type: str,
        artifact_ids: list[int],
        message: str,
    ) -> None:
        """Publish an approval required event."""
        await self.publish(
            run_id,
            SSEEvent(
                event_type=SSEEventType.APPROVAL_REQUIRED,
                data={
                    "stage": stage,
                    "artifact_type": artifact_type,
                    "artifact_ids": artifact_ids,
                    "message": message,
                },
            ),
        )

    def get_subscriber_count(self, run_id: int) -> int:
        """Get the number of subscribers for a run."""
        return len(self._subscribers.get(run_id, []))


# Global SSE manager instance
sse_manager = SSEManager()
