# main.py
"""
FastAPI app entry point with routes.
"""
from fastapi import FastAPI
from starlette.responses import PlainTextResponse
from routers import root

app = FastAPI()

# Include routers
app.include_router(root.router)

# Optionally, you can add custom exception handlers here if needed.
