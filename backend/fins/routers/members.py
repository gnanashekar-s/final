from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from schemas import MemberCreate, MemberUpdate, MemberOut
from services.members import MemberService
from dependencies import get_member_service
from core.errors import NotFoundError, ConflictError

router = APIRouter(prefix='/api/members', tags=['members'])

@router.post('', response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def create_member(
    member: MemberCreate,
    service: MemberService = Depends(get_member_service)
) -> MemberOut:
    """
    Create a new library member.
    """
    try:
        created = await service.create_member(member)
        return MemberOut(**created)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.get('', response_model=List[MemberOut])
async def list_members(
    service: MemberService = Depends(get_member_service)
) -> List[MemberOut]:
    """
    List all members.
    """
    members = await service.list_members()
    return [MemberOut(**m) for m in members]

@router.get('/{member_id}', response_model=MemberOut)
async def get_member(
    member_id: int,
    service: MemberService = Depends(get_member_service)
) -> MemberOut:
    """
    Retrieve a member by id.
    """
    try:
        member = await service.get_member(member_id)
        return MemberOut(**member)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.put('/{member_id}', response_model=MemberOut)
async def update_member(
    member_id: int,
    member: MemberUpdate,
    service: MemberService = Depends(get_member_service)
) -> MemberOut:
    """
    Update all details of an existing member by ID.
    """
    try:
        updated = await service.update_member(member_id, member)
        return MemberOut(**updated)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.delete('/{member_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    member_id: int,
    service: MemberService = Depends(get_member_service)
) -> None:
    """
    Delete a member by their unique member_id.
    """
    try:
        await service.delete_member(member_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
