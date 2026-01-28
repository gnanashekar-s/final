"""API routes."""
from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.code import router as code_router
from app.api.epics import router as epics_router
from app.api.projects import router as projects_router
from app.api.specs import router as specs_router
from app.api.stories import router as stories_router
from app.api.stream import router as stream_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(epics_router)
api_router.include_router(stories_router)
api_router.include_router(specs_router)
api_router.include_router(code_router)
api_router.include_router(admin_router)
api_router.include_router(stream_router)

__all__ = ["api_router"]
