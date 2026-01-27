"""Custom exceptions for the application."""
from typing import Any, Optional


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Authentication related errors."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, error_code="AUTH_ERROR")


class AuthorizationError(AppException):
    """Authorization related errors."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, error_code="AUTHZ_ERROR")


class NotFoundError(AppException):
    """Resource not found errors."""

    def __init__(self, resource: str, resource_id: Any):
        super().__init__(
            f"{resource} with id {resource_id} not found",
            error_code="NOT_FOUND",
            details={"resource": resource, "id": resource_id},
        )


class ValidationError(AppException):
    """Validation errors."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            details={"field": field} if field else {},
        )


class WorkflowError(AppException):
    """Workflow execution errors."""

    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        run_id: Optional[int] = None,
    ):
        super().__init__(
            message,
            error_code="WORKFLOW_ERROR",
            details={"stage": stage, "run_id": run_id},
        )


class AgentError(AppException):
    """Agent execution errors."""

    def __init__(
        self,
        message: str,
        agent_name: str,
        run_id: Optional[int] = None,
    ):
        super().__init__(
            message,
            error_code="AGENT_ERROR",
            details={"agent_name": agent_name, "run_id": run_id},
        )


class LLMError(AppException):
    """LLM API errors."""

    def __init__(self, message: str, model: Optional[str] = None):
        super().__init__(
            message,
            error_code="LLM_ERROR",
            details={"model": model} if model else {},
        )


class CodeGenerationError(AppException):
    """Code generation errors."""

    def __init__(
        self,
        message: str,
        spec_id: Optional[int] = None,
        validation_errors: Optional[list] = None,
    ):
        super().__init__(
            message,
            error_code="CODE_GEN_ERROR",
            details={
                "spec_id": spec_id,
                "validation_errors": validation_errors or [],
            },
        )


class CodeValidationError(AppException):
    """Code validation errors."""

    def __init__(
        self,
        message: str,
        lint_errors: Optional[list] = None,
        test_failures: Optional[list] = None,
    ):
        super().__init__(
            message,
            error_code="CODE_VALIDATION_ERROR",
            details={
                "lint_errors": lint_errors or [],
                "test_failures": test_failures or [],
            },
        )


class CheckpointError(AppException):
    """Checkpoint save/restore errors."""

    def __init__(self, message: str, run_id: Optional[int] = None):
        super().__init__(
            message,
            error_code="CHECKPOINT_ERROR",
            details={"run_id": run_id} if run_id else {},
        )


class RateLimitError(AppException):
    """Rate limiting errors."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            message,
            error_code="RATE_LIMIT",
            details={"retry_after": retry_after},
        )


class ExternalServiceError(AppException):
    """External service errors (web search, APIs, etc.)."""

    def __init__(self, service: str, message: str):
        super().__init__(
            f"{service} error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service},
        )
