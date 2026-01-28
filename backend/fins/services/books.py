from typing import List
from schemas import BookCreate, BookUpdate
from storage import BaseRepository
from core.errors import NotFoundError, ConflictError

class BookService:
    """
    Service for book business logic.
    """
    def __init__(self, repo: BaseRepository):
        self._repo = repo

    async def create_book(self, book: BookCreate) -> dict:
        """
        Create a new book with validation and ISBN uniqueness enforcement.
        """
        # ISBN uniqueness
        books = await self._repo.list()
        isbn = book.isbn.strip()
        for b in books:
            if b['isbn'].strip() == isbn:
                raise ConflictError('ISBN already exists')
        if book.copies_available > book.copies_total:
            raise ValueError('copies_available cannot be greater than copies_total')
        if book.copies_total == 0 and book.copies_available > 0:
            raise ValueError('copies_available cannot be > 0 if copies_total is 0')
        obj = book.model_dump()
        obj['isbn'] = isbn
        created = await self._repo.create(obj)
        return created

    async def list_books(self) -> List[dict]:
        """
        List all books.
        """
        return await self._repo.list()

    async def get_book(self, book_id: int) -> dict:
        """
        Retrieve a book by ID.
        """
        return await self._repo.get(book_id)

    async def update_book(self, book_id: int, book: BookUpdate) -> dict:
        """
        Update an existing book by ID.
        """
        # Check existence
        old = await self._repo.get(book_id)
        # ISBN uniqueness (excluding self)
        books = await self._repo.list()
        isbn = book.isbn.strip()
        for b in books:
            if b['id'] != book_id and b['isbn'].strip() == isbn:
                raise ConflictError('ISBN already exists')
        if book.copies_available > book.copies_total:
            raise ValueError('copies_available cannot be greater than copies_total')
        if book.copies_total == 0 and book.copies_available > 0:
            raise ValueError('copies_available cannot be > 0 if copies_total is 0')
        obj = book.model_dump()
        obj['isbn'] = isbn
        updated = await self._repo.update(book_id, obj)
        return updated

    async def delete_book(self, book_id: int) -> None:
        """
        Delete a book by ID.
        """
        await self._repo.delete(book_id)
