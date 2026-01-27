"""Streamlit components."""
from components.auth import (
    api_request,
    check_authentication,
    get_auth_header,
    show_login_page,
)
from components.chat import (
    render_approval_interface,
    render_chat_interface,
    render_progress_indicator,
)
from components.mermaid import (
    create_er_diagram,
    create_flowchart,
    create_sequence_diagram,
    render_mermaid,
    render_mermaid_with_fallback,
)
from components.stream_handler import (
    SSEEvent,
    StreamHandler,
    cleanup_stream,
    render_stream_status,
    render_workflow_monitor,
)

__all__ = [
    # Auth
    "check_authentication",
    "show_login_page",
    "get_auth_header",
    "api_request",
    # Chat
    "render_chat_interface",
    "render_approval_interface",
    "render_progress_indicator",
    # Mermaid
    "render_mermaid",
    "render_mermaid_with_fallback",
    "create_flowchart",
    "create_sequence_diagram",
    "create_er_diagram",
    # Stream
    "SSEEvent",
    "StreamHandler",
    "render_stream_status",
    "render_workflow_monitor",
    "cleanup_stream",
]
