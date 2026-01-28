from typing import List, Optional
from datetime import datetime, timezone
from schemas import LoanCreate, LoanUpdate
from storage import BaseRepository
from core.errors import NotFoundError, ConflictError

class LoanService:
    """
    Service for loan business logic.
    """
    def __init__(self, repo: BaseRepository, book_repo: BaseRepository, member_repo: BaseRepository):
        self._repo = repo
        self._book_repo = book_repo
        self._member_repo = member_repo

    async def create_loan(self, loan: LoanCreate) -> dict:
        """
        Create a new loan, ensuring referential integrity and correct status/timestamps.
        """
        # Check book exists
        try:
            await self._book_repo.get(loan.book_id)
        except NotFoundError:
            raise NotFoundError(f'Book with id {loan.book_id} not found')
        # Check member exists
        try:
            await self._member_repo.get(loan.member_id)
        except NotFoundError:
            raise NotFoundError(f'Member with id {loan.member_id} not found')
        obj = loan.model_dump()
        obj['status'] = 'active'
        obj['loaned_at'] = datetime.now(timezone.utc)
        obj['returned_at'] = None
        created = await self._repo.create(obj)
        return created

    async def list_loans(self) -> List[dict]:
        """
        List all loans.
        """
        return await self._repo.list()

    async def get_loan(self, loan_id: int) -> dict:
        """
        Retrieve a loan by ID.
        """
        return await self._repo.get(loan_id)

    async def update_loan(self, loan_id: int, loan: LoanUpdate) -> dict:
        """
        Update a loan by ID.
        """
        old = await self._repo.get(loan_id)
        obj = old.copy()
        if loan.status is not None:
            if loan.status not in ('active', 'returned'):
                raise ValueError('Invalid status')
            obj['status'] = loan.status
        if loan.returned_at is not None:
            obj['returned_at'] = loan.returned_at
        updated = await self._repo.update(loan_id, obj)
        return updated

    async def delete_loan(self, loan_id: int) -> None:
        """
        Delete a loan by ID.
        """
        await self._repo.delete(loan_id)
