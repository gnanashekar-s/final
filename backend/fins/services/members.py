from typing import List
from schemas import MemberCreate, MemberUpdate
from storage import BaseRepository
from core.errors import NotFoundError, ConflictError

class MemberService:
    """
    Service for member business logic.
    """
    def __init__(self, repo: BaseRepository):
        self._repo = repo

    async def create_member(self, member: MemberCreate) -> dict:
        """
        Create a new member with unique, valid email and non-empty full_name.
        """
        members = await self._repo.list()
        email = member.email.lower()
        for m in members:
            if m['email'].lower() == email:
                raise ConflictError('Email already exists')
        obj = member.model_dump()
        obj['email'] = email
        obj['active'] = True
        created = await self._repo.create(obj)
        return created

    async def list_members(self) -> List[dict]:
        """
        List all members.
        """
        return await self._repo.list()

    async def get_member(self, member_id: int) -> dict:
        """
        Retrieve a member by ID.
        """
        return await self._repo.get(member_id)

    async def update_member(self, member_id: int, member: MemberUpdate) -> dict:
        """
        Update all details of an existing member by ID.
        """
        old = await self._repo.get(member_id)
        members = await self._repo.list()
        email = member.email.lower()
        for m in members:
            if m['id'] != member_id and m['email'].lower() == email:
                raise ConflictError('Email already exists')
        if not member.full_name.strip():
            raise ValueError('full_name must not be empty')
        obj = member.model_dump()
        obj['email'] = email
        updated = await self._repo.update(member_id, obj)
        return updated

    async def delete_member(self, member_id: int) -> None:
        """
        Delete a member by ID.
        """
        await self._repo.delete(member_id)
