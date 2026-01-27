"""Core utilities."""
from app.core.exceptions import (
    AgentError,
    AppException,
    AuthenticationError,
    AuthorizationError,
    CheckpointError,
    CodeGenerationError,
    CodeValidationError,
    ExternalServiceError,
    LLMError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    WorkflowError,
)
from app.core.langfuse_client import (
    flush_langfuse,
    get_langfuse,
    log_generation,
    observe,
    shutdown_langfuse,
    trace_span,
)
from app.core.security import (
    RoleChecker,
    create_access_token,
    decode_token,
    get_admin_user,
    get_current_active_user,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.core.sse import SSEEvent, SSEEventType, SSEManager, sse_manager

__all__ = [
    # Security
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_token",
    "get_current_user",
    "get_current_active_user",
    "get_admin_user",
    "RoleChecker",
    # Langfuse
    "get_langfuse",
    "observe",
    "trace_span",
    "log_generation",
    "flush_langfuse",
    "shutdown_langfuse",
    # SSE
    "SSEEvent",
    "SSEEventType",
    "SSEManager",
    "sse_manager",
    # Exceptions
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ValidationError",
    "WorkflowError",
    "AgentError",
    "LLMError",
    "CodeGenerationError",
    "CodeValidationError",
    "CheckpointError",
    "RateLimitError",
    "ExternalServiceError",
]
