# routers/books.py
"""
Routers for /books endpoints (CRUD for books).
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from schemas import BookCreate, BookUpdate, BookOutput, ErrorResponse
from dependencies import get_book_store
from models import BookStore, Book

router = APIRouter()

@router.post(
    "/",
    response_model=BookOutput,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Duplicate book ID."},
        422: {"model": ErrorResponse, "description": "Validation error."},
    },
)
async def create_book(
    book: BookCreate = Body(...),
    store: BookStore = Depends(get_book_store),
):
    """
    Add a new book to the in-memory store.
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
    "/",
    response_model=List[BookOutput],
    status_code=status.HTTP_200_OK,
)
async def list_books(
    store: BookStore = Depends(get_book_store),
):
    """
    Retrieve a list of all books in the in-memory store.
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
async def get_book(
    book_id: int = Path(..., ge=1),
    store: BookStore = Depends(get_book_store),
):
    """
    Retrieve a single book by its integer ID.
    """
    book = store.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookOutput(**book.to_dict())

@router.put(
    "/{book_id}",
    response_model=BookOutput,
    responses={
        404: {"model": ErrorResponse, "description": "Book not found."},
        422: {"model": ErrorResponse, "description": "Validation error."},
    },
)
async def update_book(
    book_id: int = Path(..., ge=1),
    book_update: BookCreate = Body(...),
    store: BookStore = Depends(get_book_store),
):
    """
    Update an existing book's details by ID. All fields required.
    """
    try:
        updated = store.update_book(
            book_id,
            title=book_update.title,
            author=book_update.author,
            year=book_update.year,
            availability=book_update.availability,
        )
        return BookOutput(**updated.to_dict())
    except KeyError:
        raise HTTPException(status_code=404, detail="Book not found")

@router.patch(
    "/{book_id}",
    response_model=BookOutput,
    responses={
        404: {"model": ErrorResponse, "description": "Book not found."},
        422: {"model": ErrorResponse, "description": "Validation error."},
    },
)
async def patch_book(
    book_id: int = Path(..., ge=1),
    book_update: BookUpdate = Body(...),
    store: BookStore = Depends(get_book_store),
):
    """
    Partially update a book by ID. Only provided fields are updated.
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
    status_code=204,
    responses={
        204: {"description": "No Content"},
        404: {"model": ErrorResponse, "description": "Book not found."},
        422: {"model": ErrorResponse, "description": "Validation error."},
    },
)
async def delete_book(
    book_id: int = Path(..., ge=1),
    store: BookStore = Depends(get_book_store),
):
    """
    Delete a book by its integer ID from the in-memory store.
    """
    try:
        store.delete_book(book_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Book not found")
