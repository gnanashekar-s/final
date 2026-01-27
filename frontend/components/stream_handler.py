"""SSE stream handler for real-time updates."""
import json
import threading
from dataclasses import dataclass
from queue import Queue
from typing import Callable, Optional

import requests
import streamlit as st

# API base URL
API_URL = "http://localhost:8000/api/v1"


@dataclass
class SSEEvent:
    """Server-Sent Event data."""
    event_type: str
    data: dict
    timestamp: str


class StreamHandler:
    """Handler for SSE streams."""

    def __init__(self, run_id: int, token: str):
        self.run_id = run_id
        self.token = token
        self.event_queue: Queue = Queue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start listening to the SSE stream."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop listening to the SSE stream."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _listen(self):
        """Listen to SSE events in background thread."""
        url = f"{API_URL}/stream/{self.run_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "text/event-stream",
        }

        try:
            with requests.get(url, headers=headers, stream=True, timeout=300) as response:
                for line in response.iter_lines():
                    if self._stop_event.is_set():
                        break

                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            try:
                                event_data = json.loads(data_str)
                                event = SSEEvent(
                                    event_type=event_data.get("type", "unknown"),
                                    data=event_data.get("data", {}),
                                    timestamp=event_data.get("timestamp", ""),
                                )
                                self.event_queue.put(event)
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            self.event_queue.put(SSEEvent(
                event_type="error",
                data={"error": str(e)},
                timestamp="",
            ))

    def get_events(self) -> list[SSEEvent]:
        """Get all pending events from the queue."""
        events = []
        while not self.event_queue.empty():
            events.append(self.event_queue.get_nowait())
        return events


def render_stream_status(
    run_id: int,
    on_event: Optional[Callable[[SSEEvent], None]] = None,
):
    """
    Render a real-time stream status widget.

    Args:
        run_id: The run ID to stream
        on_event: Optional callback for each event
    """
    # Initialize stream handler in session state
    stream_key = f"stream_handler_{run_id}"

    if stream_key not in st.session_state:
        token = st.session_state.get("token", "")
        handler = StreamHandler(run_id, token)
        handler.start()
        st.session_state[stream_key] = handler

    handler = st.session_state[stream_key]

    # Create placeholders
    status_placeholder = st.empty()
    progress_placeholder = st.empty()
    message_placeholder = st.empty()

    # Process events
    events = handler.get_events()

    for event in events:
        if on_event:
            on_event(event)

        # Update UI based on event type
        if event.event_type == "stage_update":
            status_placeholder.info(
                f"Stage: {event.data.get('stage', 'Unknown')} - "
                f"{event.data.get('message', '')}"
            )
            progress = event.data.get("progress", 0)
            if progress:
                progress_placeholder.progress(progress / 100)

        elif event.event_type == "progress":
            current = event.data.get("current", 0)
            total = event.data.get("total", 1)
            message = event.data.get("message", "")
            progress_placeholder.progress(
                current / total,
                text=f"{message} ({current}/{total})"
            )

        elif event.event_type == "completion":
            success = event.data.get("success", False)
            message = event.data.get("message", "")
            if success:
                status_placeholder.success(f"Completed: {message}")
            else:
                status_placeholder.error(f"Failed: {message}")
            handler.stop()

        elif event.event_type == "error":
            error = event.data.get("error", "Unknown error")
            status_placeholder.error(f"Error: {error}")
            if not event.data.get("recoverable", False):
                handler.stop()

        elif event.event_type == "approval_required":
            stage = event.data.get("stage", "")
            artifact_type = event.data.get("artifact_type", "")
            message = event.data.get("message", "")
            status_placeholder.warning(f"Approval Required: {message}")
            message_placeholder.info(
                f"Please review the {artifact_type}s and approve or reject them."
            )

        elif event.event_type == "artifact_created":
            artifact_type = event.data.get("artifact_type", "")
            summary = event.data.get("summary", "")
            message_placeholder.info(f"Created {artifact_type}: {summary}")


def cleanup_stream(run_id: int):
    """Clean up stream handler for a run."""
    stream_key = f"stream_handler_{run_id}"
    if stream_key in st.session_state:
        handler = st.session_state[stream_key]
        handler.stop()
        del st.session_state[stream_key]


def render_workflow_monitor(run_id: int):
    """
    Render a complete workflow monitoring widget.

    Args:
        run_id: The run ID to monitor
    """
    st.markdown("### Workflow Progress")

    # Stream status
    render_stream_status(run_id)

    # Event log
    with st.expander("Event Log"):
        if "event_log" not in st.session_state:
            st.session_state.event_log = []

        for event in st.session_state.event_log[-20:]:  # Show last 20 events
            st.text(f"[{event.timestamp}] {event.event_type}: {event.data}")

    # Controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Refresh"):
            st.rerun()
    with col2:
        if st.button("Stop Monitoring"):
            cleanup_stream(run_id)
            st.rerun()
