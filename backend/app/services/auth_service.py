"""Authentication service."""
from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User, UserRole
from app.schemas.user import Token, UserCreate


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user."""
        # Check if email already exists
        existing = await self.get_user_by_email(user_data.email)
        if existing:
            raise ValueError("Email already registered")

        user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            role=UserRole.USER,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    def create_token(self, user: User) -> Token:
        """Create an access token for a user."""
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
            expires_delta=timedelta(hours=settings.jwt_expiration_hours),
        )
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expiration_hours * 3600,
        )

    async def update_password(self, user: User, new_password: str) -> User:
        """Update a user's password."""
        user.password_hash = get_password_hash(new_password)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def promote_to_admin(self, user: User) -> User:
        """Promote a user to admin role."""
        user.role = UserRole.ADMIN
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def demote_to_user(self, user: User) -> User:
        """Demote an admin to regular user role."""
        user.role = UserRole.USER
        await self.db.flush()
        await self.db.refresh(user)
        return user
