# main.py
"""
FastAPI app entry point with routes and SSL config.
"""
import sys
import logging
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from config import get_settings, Settings
from routers import books, v1_books, sensitive

logger = logging.getLogger("uvicorn.error")

settings = get_settings()

app = FastAPI(title="Thread-Safe In-Memory Book Store API")

# CORS (optional, can be adjusted as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(books.router, prefix="/books", tags=["Books"])
app.include_router(v1_books.router, prefix="/api/v1/books", tags=["Books v1"])
app.include_router(sensitive.router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

if __name__ == "__main__":
    import uvicorn
    import os

    ssl_cert = settings.ssl_cert_path
    ssl_key = settings.ssl_key_path
    env = settings.env

    uvicorn_kwargs = {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": 8443 if ssl_cert and ssl_key else 8000,
        "reload": env == "development",
    }
    if ssl_cert and ssl_key:
        if not os.path.isfile(ssl_cert):
            logger.error(f"SSL certificate file not found: {ssl_cert}")
            sys.exit(1)
        if not os.path.isfile(ssl_key):
            logger.error(f"SSL key file not found: {ssl_key}")
            sys.exit(1)
        uvicorn_kwargs["ssl_certfile"] = ssl_cert
        uvicorn_kwargs["ssl_keyfile"] = ssl_key
    try:
        uvicorn.run(**uvicorn_kwargs)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
