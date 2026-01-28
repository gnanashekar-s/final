# dependencies.py
"""
FastAPI dependencies for BookStore and settings.
"""
from fastapi import Depends, Request
from models import BookStore
from config import get_settings, Settings

# Singleton BookStore instance
book_store = BookStore()

def get_book_store() -> BookStore:
    """
    Dependency to get the global BookStore instance.
    """
    return book_store

def get_app_settings() -> Settings:
    """
    Dependency to get app settings.
    """
    return get_settings()
