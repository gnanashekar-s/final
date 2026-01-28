# routers/v1_books.py
"""
Routers for /api/v1/books endpoints (alternate API version).
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from schemas import BookCreate, BookUpdate, BookOutput, ErrorResponse
from dependencies import get_book_store
from models import BookStore, Book

router = APIRouter()

@router.post(
    "",
    response_model=BookOutput,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Duplicate book ID."},
        422: {"model": ErrorResponse, "description": "Validation error."},
    },
)
async def create_book_v1(
    book: BookCreate = Body(...),
    store: BookStore = Depends(get_book_store),
):
    """
    Create a new book in the thread-safe in-memory data store.
    """
    try:
        new_book = Book(
            id=book.id,
            title=book.title,
            author=book.author,
            year=book.year,
            availability=book.availability,
        )
        store.add_book(new_book)
        return BookOutput(**new_book.to_dict())
    except ValueError:
        raise HTTPException(status_code=400, detail="Book with this ID already exists.")

@router.get(
    "",
    response_model=List[BookOutput],
    status_code=status.HTTP_200_OK,
)
async def list_books_v1(
    store: BookStore = Depends(get_book_store),
):
    """
    Returns a list of all books in the data store.
    """
    books = store.get_all_books().values()
    return [BookOutput(**b.to_dict()) for b in books]

@router.get(
    "/{book_id}",
    response_model=BookOutput,
    responses={
        404: {"model": ErrorResponse, "description": "Book not found."},
        422: {"model": ErrorResponse, "description": "Validation error."},
    },
)
async def get_book_v1(
    book_id: int = Path(..., ge=1),
    store: BookStore = Depends(get_book_store),
):
    """
    Returns the details of the book with the specified ID.
    """
    book = store.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookOutput(**book.to_dict())

@router.patch(
    "/{book_id}",
    response_model=BookOutput,
    responses={
        404: {"model": ErrorResponse, "description": "Book not found."},
        422: {"model": ErrorResponse, "description": "Validation error."},
    },
)
async def patch_book_v1(
    book_id: int = Path(..., ge=1),
    book_update: BookUpdate = Body(...),
    store: BookStore = Depends(get_book_store),
):
    """
    Update details of an existing book by ID. Supports partial updates. Thread-safe.
    """
    try:
        update_data = book_update.model_dump(exclude_unset=True)
        if not update_data:
            # Accept empty body (no-op)
            book = store.get_book(book_id)
            if not book:
                raise HTTPException(status_code=404, detail="Book not found")
            return BookOutput(**book.to_dict())
        updated = store.update_book(book_id, **update_data)
        return BookOutput(**updated.to_dict())
    except KeyError:
        raise HTTPException(status_code=404, detail="Book not found")

@router.delete(
    "/{book_id}",
    status_code=200,
    responses={
        200: {"description": "Book deleted successfully."},
        404: {"model": ErrorResponse, "description": "Book not found."},
    },
)
async def delete_book_v1(
    book_id: int = Path(..., ge=1),
    store: BookStore = Depends(get_book_store),
):
    """
    Delete a book by its ID in a thread-safe manner.
    """
    try:
        store.delete_book(book_id)
        return {"message": "Book deleted successfully."}
    except KeyError:
        raise HTTPException(status_code=404, detail="Book not found")
