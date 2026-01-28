import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_root_and_openapi():
    async with AsyncClient(app=app, base_url='http://test') as ac:
        resp = await ac.get('/')
        assert resp.status_code == 200
        resp = await ac.get('/openapi.json')
        assert resp.status_code == 200
        resp = await ac.get('/docs')
        assert resp.status_code == 200

@pytest.mark.asyncio
async def test_book_crud():
    async with AsyncClient(app=app, base_url='http://test') as ac:
        # Create
        book = {
            'title': 'Book A',
            'author': 'Author A',
            'isbn': 'ISBN123',
            'copies_total': 3,
            'copies_available': 2
        }
        resp = await ac.post('/api/books', json=book)
        assert resp.status_code == 201
        data = resp.json()
        book_id = data['id']
        # Duplicate ISBN
        resp = await ac.post('/api/books', json=book)
        assert resp.status_code == 409
        # List
        resp = await ac.get('/api/books')
        assert resp.status_code == 200
        assert any(b['id'] == book_id for b in resp.json())
        # Get
        resp = await ac.get(f'/api/books/{book_id}')
        assert resp.status_code == 200
        # Update
        update = book.copy()
        update['isbn'] = 'ISBN124'
        resp = await ac.put(f'/api/books/{book_id}', json=update)
        assert resp.status_code == 200
        # Update to duplicate ISBN
        book2 = book.copy()
        book2['isbn'] = 'ISBN125'
        resp2 = await ac.post('/api/books', json=book2)
        assert resp2.status_code == 201
        id2 = resp2.json()['id']
        update2 = book2.copy()
        update2['isbn'] = 'ISBN124'
        resp = await ac.put(f'/api/books/{id2}', json=update2)
        assert resp.status_code == 409
        # Delete
        resp = await ac.delete(f'/api/books/{book_id}')
        assert resp.status_code == 204
        # Delete again
        resp = await ac.delete(f'/api/books/{book_id}')
        assert resp.status_code == 404
        # Get deleted
        resp = await ac.get(f'/api/books/{book_id}')
        assert resp.status_code == 404

@pytest.mark.asyncio
async def test_book_validation():
    async with AsyncClient(app=app, base_url='http://test') as ac:
        # copies_available > copies_total
        book = {
            'title': 'B',
            'author': 'A',
            'isbn': 'X',
            'copies_total': 1,
            'copies_available': 2
        }
        resp = await ac.post('/api/books', json=book)
        assert resp.status_code == 422
        # Empty title
        book['title'] = ''
        book['copies_available'] = 1
        resp = await ac.post('/api/books', json=book)
        assert resp.status_code == 422
        # Missing field
        book = {
            'title': 'B',
            'author': 'A',
            'copies_total': 1,
            'copies_available': 1
        }
        resp = await ac.post('/api/books', json=book)
        assert resp.status_code == 422

@pytest.mark.asyncio
async def test_member_crud():
    async with AsyncClient(app=app, base_url='http://test') as ac:
        member = {
            'full_name': 'John Doe',
            'email': 'john@example.com'
        }
        resp = await ac.post('/api/members', json=member)
        assert resp.status_code == 201
        data = resp.json()
        member_id = data['id']
        # Duplicate email (case-insensitive)
        member2 = member.copy()
        member2['email'] = 'JOHN@EXAMPLE.COM'
        resp = await ac.post('/api/members', json=member2)
        assert resp.status_code == 409
        # List
        resp = await ac.get('/api/members')
        assert resp.status_code == 200
        assert any(m['id'] == member_id for m in resp.json())
        # Get
        resp = await ac.get(f'/api/members/{member_id}')
        assert resp.status_code == 200
        # Update
        update = {
            'full_name': 'John D',
            'email': 'john2@example.com',
            'active': False
        }
        resp = await ac.put(f'/api/members/{member_id}', json=update)
        assert resp.status_code == 200
        # Update to duplicate email
        member3 = {
            'full_name': 'Jane',
            'email': 'jane@example.com'
        }
        resp2 = await ac.post('/api/members', json=member3)
        assert resp2.status_code == 201
        id2 = resp2.json()['id']
        update2 = {
            'full_name': 'Jane',
            'email': 'john2@example.com',
            'active': True
        }
        resp = await ac.put(f'/api/members/{id2}', json=update2)
        assert resp.status_code == 409
        # Delete
        resp = await ac.delete(f'/api/members/{member_id}')
        assert resp.status_code == 204
        # Delete again
        resp = await ac.delete(f'/api/members/{member_id}')
        assert resp.status_code == 404
        # Get deleted
        resp = await ac.get(f'/api/members/{member_id}')
        assert resp.status_code == 404

@pytest.mark.asyncio
async def test_member_validation():
    async with AsyncClient(app=app, base_url='http://test') as ac:
        # Empty full_name
        member = {
            'full_name': '',
            'email': 'a@b.com'
        }
        resp = await ac.post('/api/members', json=member)
        assert resp.status_code == 422
        # Invalid email
        member = {
            'full_name': 'A',
            'email': 'notanemail'
        }
        resp = await ac.post('/api/members', json=member)
        assert resp.status_code == 422
        # Missing email
        member = {
            'full_name': 'A'
        }
        resp = await ac.post('/api/members', json=member)
        assert resp.status_code == 422

@pytest.mark.asyncio
async def test_loan_crud():
    async with AsyncClient(app=app, base_url='http://test') as ac:
        # Create book and member
        book = {
            'title': 'LoanBook',
            'author': 'LoanAuthor',
            'isbn': 'LOANISBN',
            'copies_total': 1,
            'copies_available': 1
        }
        resp = await ac.post('/api/books', json=book)
        assert resp.status_code == 201
        book_id = resp.json()['id']
        member = {
            'full_name': 'LoanUser',
            'email': 'loanuser@example.com'
        }
        resp = await ac.post('/api/members', json=member)
        assert resp.status_code == 201
        member_id = resp.json()['id']
        # Create loan
        loan = {
            'book_id': book_id,
            'member_id': member_id
        }
        resp = await ac.post('/api/loans', json=loan)
        assert resp.status_code == 201
        loan_id = resp.json()['id']
        # List
        resp = await ac.get('/api/loans')
        assert resp.status_code == 200
        assert any(l['id'] == loan_id for l in resp.json())
        # Get
        resp = await ac.get(f'/api/loans/{loan_id}')
        assert resp.status_code == 200
        # Update
        update = {
            'status': 'returned',
            'returned_at': '2024-01-01T00:00:00Z'
        }
        resp = await ac.put(f'/api/loans/{loan_id}', json=update)
        assert resp.status_code == 200
        # Delete
        resp = await ac.delete(f'/api/loans/{loan_id}')
        assert resp.status_code == 204
        # Delete again
        resp = await ac.delete(f'/api/loans/{loan_id}')
        assert resp.status_code == 404
        # Get deleted
        resp = await ac.get(f'/api/loans/{loan_id}')
        assert resp.status_code == 404

@pytest.mark.asyncio
async def test_loan_validation():
    async with AsyncClient(app=app, base_url='http://test') as ac:
        # Non-existent book_id
        member = {
            'full_name': 'LoanUser2',
            'email': 'loanuser2@example.com'
        }
        resp = await ac.post('/api/members', json=member)
        assert resp.status_code == 201
        member_id = resp.json()['id']
        loan = {
            'book_id': 9999,
            'member_id': member_id
        }
        resp = await ac.post('/api/loans', json=loan)
        assert resp.status_code == 404
        # Non-existent member_id
        book = {
            'title': 'LoanBook2',
            'author': 'LoanAuthor2',
            'isbn': 'LOANISBN2',
            'copies_total': 1,
            'copies_available': 1
        }
        resp = await ac.post('/api/books', json=book)
        assert resp.status_code == 201
        book_id = resp.json()['id']
        loan = {
            'book_id': book_id,
            'member_id': 9999
        }
        resp = await ac.post('/api/loans', json=loan)
        assert resp.status_code == 404
        # Invalid status on update
        loan = {
            'book_id': book_id,
            'member_id': member_id
        }
        resp = await ac.post('/api/loans', json=loan)
        assert resp.status_code == 201
        loan_id = resp.json()['id']
        update = {
            'status': 'invalidstatus'
        }
        resp = await ac.put(f'/api/loans/{loan_id}', json=update)
        assert resp.status_code == 400
