"""Common Pydantic schemas."""
from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: datetime
    updated_at: Optional[datetime] = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Generic paginated response."""

    items: list[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str
    error_code: Optional[str] = None


class StatusResponse(BaseModel):
    """Status response schema."""

    status: str
    message: Optional[str] = None
