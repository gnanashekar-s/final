from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from schemas import BookCreate, BookUpdate, BookOut
from services.books import BookService
from dependencies import get_book_service
from core.errors import NotFoundError, ConflictError

router = APIRouter(prefix='/api/books', tags=['books'])

@router.post('', response_model=BookOut, status_code=status.HTTP_201_CREATED)
async def create_book(
    book: BookCreate,
    service: BookService = Depends(get_book_service)
) -> BookOut:
    """
    Create a new Book resource with validation and ISBN uniqueness enforcement.
    """
    try:
        created = await service.create_book(book)
        return BookOut(**created)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.get('', response_model=List[BookOut])
async def list_books(
    service: BookService = Depends(get_book_service)
) -> List[BookOut]:
    """
    List all Book resources.
    """
    books = await service.list_books()
    return [BookOut(**b) for b in books]

@router.get('/{book_id}', response_model=BookOut)
async def get_book(
    book_id: int,
    service: BookService = Depends(get_book_service)
) -> BookOut:
    """
    Retrieve a Book by its ID.
    """
    try:
        book = await service.get_book(book_id)
        return BookOut(**book)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put('/{book_id}', response_model=BookOut)
async def update_book(
    book_id: int,
    book: BookUpdate,
    service: BookService = Depends(get_book_service)
) -> BookOut:
    """
    Update an existing Book by ID, enforcing validation and uniqueness constraints.
    """
    try:
        updated = await service.update_book(book_id, book)
        return BookOut(**updated)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.delete('/{book_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int,
    service: BookService = Depends(get_book_service)
) -> None:
    """
    Delete a Book by its ID.
    """
    try:
        await service.delete_book(book_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
