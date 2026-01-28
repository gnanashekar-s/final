# routers/root.py
"""
Resource-specific router for the root endpoint.
"""
from fastapi import APIRouter, status
from starlette.responses import PlainTextResponse

router = APIRouter()

@router.get(
    "/",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Root endpoint",
    response_description="Returns the plain text string 'helo world'."
)
async def read_root() -> PlainTextResponse:
    """
    Returns the plain text string 'helo world'.
    """
    return PlainTextResponse(content="helo world", status_code=status.HTTP_200_OK)
