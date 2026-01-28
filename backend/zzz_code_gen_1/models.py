# models.py
"""
In-memory BookStore and Book data models.
"""
from typing import Dict, Optional
import threading

class Book:
    """
    Book data model for in-memory store.
    """
    def __init__(self, id: int, title: str, author: str, year: int, availability: bool = True):
        self.id = id
        self.title = title
        self.author = author
        self.year = year
        self.availability = availability

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "year": self.year,
            "availability": self.availability,
        }

class BookStore:
    """
    Thread-safe in-memory book store.
    """
    def __init__(self):
        self.books: Dict[int, Book] = {}
        self.lock = threading.Lock()

    def add_book(self, book: Book) -> None:
        with self.lock:
            if book.id in self.books:
                raise ValueError("Book with this ID already exists.")
            self.books[book.id] = book

    def get_book(self, book_id: int) -> Optional[Book]:
        with self.lock:
            return self.books.get(book_id)

    def get_all_books(self) -> Dict[int, Book]:
        with self.lock:
            return dict(self.books)

    def update_book(self, book_id: int, **kwargs) -> Book:
        with self.lock:
            book = self.books.get(book_id)
            if not book:
                raise KeyError("Book not found.")
            for key, value in kwargs.items():
                if hasattr(book, key) and value is not None:
                    setattr(book, key, value)
            return book

    def delete_book(self, book_id: int) -> None:
        with self.lock:
            if book_id not in self.books:
                raise KeyError("Book not found.")
            del self.books[book_id]
