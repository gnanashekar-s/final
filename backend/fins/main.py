from fastapi import FastAPI
from routers import books, members, loans

app = FastAPI()

app.include_router(books.router)
app.include_router(members.router)
app.include_router(loans.router)
