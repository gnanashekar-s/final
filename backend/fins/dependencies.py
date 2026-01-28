from fastapi import Depends
from storage import (
    ListBookRepository, DictBookRepository,
    ListMemberRepository, DictMemberRepository,
    ListLoanRepository, DictLoanRepository
)
from services.books import BookService
from services.members import MemberService
from services.loans import LoanService
from core.utils import id_generator

# Choose repository implementation here
book_repo = DictBookRepository(id_generator)
member_repo = DictMemberRepository(id_generator)
loan_repo = DictLoanRepository(id_generator)

book_service = BookService(book_repo)
member_service = MemberService(member_repo)
loan_service = LoanService(loan_repo, book_repo, member_repo)

def get_book_service() -> BookService:
    """
    Dependency provider for BookService.
    """
    return book_service

def get_member_service() -> MemberService:
    """
    Dependency provider for MemberService.
    """
    return member_service

def get_loan_service() -> LoanService:
    """
    Dependency provider for LoanService.
    """
    return loan_service
