# schemas.py
"""
Pydantic schemas for Book API.
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

MAX_TITLE_LENGTH = 255
MAX_AUTHOR_LENGTH = 255

class BookBase(BaseModel):
    """
    Base schema for Book.
    """
    title: str = Field(..., max_length=MAX_TITLE_LENGTH)
    author: str = Field(..., max_length=MAX_AUTHOR_LENGTH)
    year: int = Field(..., ge=0)

class BookCreate(BookBase):
    """
    Schema for creating a new Book.
    """
    id: int = Field(..., ge=1)
    availability: bool = Field(...)

    model_config = ConfigDict(extra="forbid")

class BookUpdate(BaseModel):
    """
    Schema for updating a Book (partial update).
    """
    title: Optional[str] = Field(None, max_length=MAX_TITLE_LENGTH)
    author: Optional[str] = Field(None, max_length=MAX_AUTHOR_LENGTH)
    year: Optional[int] = Field(None, ge=0)
    availability: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")

class BookOutput(BaseModel):
    """
    Output schema for Book.
    """
    id: int
    title: str
    author: str
    year: int
    availability: bool

    model_config = ConfigDict(from_attributes=True)

class ErrorResponse(BaseModel):
    """
    Standard error response schema.
    """
    detail: str
