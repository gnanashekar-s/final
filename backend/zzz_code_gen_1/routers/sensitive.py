# routers/sensitive.py
"""
Sensitive endpoints: /cleanup and /reset.
Disabled in production.
"""
from fastapi import APIRouter, Depends, Request, status, HTTPException
from dependencies import get_app_settings
from config import Settings

router = APIRouter()

SENSITIVE_ENDPOINTS = ["/cleanup", "/reset"]

@router.api_route("/cleanup", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def cleanup_endpoint(
    request: Request,
    settings: Settings = Depends(get_app_settings),
):
    """
    Sensitive endpoint for cleanup operations. Disabled in production.
    """
    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="/cleanup is disabled in production.")
    return {"message": "Cleanup completed."}

@router.api_route("/reset", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def reset_endpoint(
    request: Request,
    settings: Settings = Depends(get_app_settings),
):
    """
    Sensitive endpoint for reset operations. Disabled in production.
    """
    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="/reset is disabled in production.")
    return {"message": "Reset completed."}
