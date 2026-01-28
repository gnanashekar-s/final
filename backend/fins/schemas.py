from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator

class BookBase(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    isbn: str = Field(..., min_length=1)
    copies_total: int = Field(..., ge=0)
    copies_available: int = Field(..., ge=0)

    @field_validator('isbn')
    @classmethod
    def strip_isbn(cls, v: str) -> str:
        return v.strip()

    @field_validator('copies_available')
    @classmethod
    def available_le_total(cls, v: int, info) -> int:
        data = info.data
        copies_total = data.get('copies_total')
        if copies_total is not None and v > copies_total:
            raise ValueError('copies_available cannot be greater than copies_total')
        return v

class BookCreate(BookBase):
    pass

class BookUpdate(BookBase):
    pass

class BookOut(BookBase):
    id: int

class MemberBase(BaseModel):
    full_name: str = Field(..., min_length=1)
    email: EmailStr

    @field_validator('full_name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('full_name must not be empty')
        return v.strip()

class MemberCreate(MemberBase):
    pass

class MemberUpdate(MemberBase):
    active: bool

class MemberOut(MemberBase):
    id: int
    active: bool

class LoanBase(BaseModel):
    book_id: int
    member_id: int

class LoanCreate(LoanBase):
    pass

class LoanUpdate(BaseModel):
    status: Optional[str] = None
    returned_at: Optional[datetime] = None

class LoanOut(BaseModel):
    id: int
    book_id: int
    member_id: int
    status: str
    loaned_at: datetime
    returned_at: Optional[datetime] = None
