from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from schemas import LoanCreate, LoanUpdate, LoanOut
from services.loans import LoanService
from dependencies import get_loan_service
from core.errors import NotFoundError, ConflictError

router = APIRouter(prefix='/api/loans', tags=['loans'])

@router.post('', response_model=LoanOut, status_code=status.HTTP_201_CREATED)
async def create_loan(
    loan: LoanCreate,
    service: LoanService = Depends(get_loan_service)
) -> LoanOut:
    """
    Create a new loan, ensuring referential integrity and correct status/timestamps.
    """
    try:
        created = await service.create_loan(loan)
        return LoanOut(**created)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.get('', response_model=List[LoanOut])
async def list_loans(
    service: LoanService = Depends(get_loan_service)
) -> List[LoanOut]:
    """
    List all loans.
    """
    loans = await service.list_loans()
    return [LoanOut(**l) for l in loans]

@router.get('/{loan_id}', response_model=LoanOut)
async def get_loan(
    loan_id: int,
    service: LoanService = Depends(get_loan_service)
) -> LoanOut:
    """
    Retrieve a loan by ID.
    """
    try:
        loan = await service.get_loan(loan_id)
        return LoanOut(**loan)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put('/{loan_id}', response_model=LoanOut)
async def update_loan(
    loan_id: int,
    loan: LoanUpdate,
    service: LoanService = Depends(get_loan_service)
) -> LoanOut:
    """
    Update a loan by ID.
    """
    try:
        updated = await service.update_loan(loan_id, loan)
        return LoanOut(**updated)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete('/{loan_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_loan(
    loan_id: int,
    service: LoanService = Depends(get_loan_service)
) -> None:
    """
    Delete a loan by ID.
    """
    try:
        await service.delete_loan(loan_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
