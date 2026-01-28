from typing import TypeVar, Generic, List, Dict, Optional, Protocol, Any
from core.errors import NotFoundError, ConflictError
from core.utils import IDGenerator
from threading import Lock

T = TypeVar('T')
ID = TypeVar('ID')

class BaseRepository(Protocol, Generic[T]):
    """
    Repository interface for CRUD operations.
    """
    async def create(self, obj: T) -> T:
        ...
    async def get(self, id: int) -> T:
        ...
    async def update(self, id: int, obj: T) -> T:
        ...
    async def delete(self, id: int) -> None:
        ...
    async def list(self) -> List[T]:
        ...

class ListBookRepository:
    """
    List-based in-memory repository for books.
    """
    def __init__(self, id_gen: IDGenerator):
        self._storage: List[dict] = []
        self._id_gen = id_gen
        self._lock = Lock()

    async def create(self, obj: dict) -> dict:
        with self._lock:
            obj = obj.copy()
            obj['id'] = self._id_gen.next_id()
            self._storage.append(obj)
        return obj

    async def get(self, id: int) -> dict:
        for item in self._storage:
            if item['id'] == id:
                return item
        raise NotFoundError(f'Book with id {id} not found')

    async def update(self, id: int, obj: dict) -> dict:
        for idx, item in enumerate(self._storage):
            if item['id'] == id:
                obj = obj.copy()
                obj['id'] = id
                self._storage[idx] = obj
                return obj
        raise NotFoundError(f'Book with id {id} not found')

    async def delete(self, id: int) -> None:
        for idx, item in enumerate(self._storage):
            if item['id'] == id:
                del self._storage[idx]
                return
        raise NotFoundError(f'Book with id {id} not found')

    async def list(self) -> List[dict]:
        return list(self._storage)

class DictBookRepository:
    """
    Dict-based in-memory repository for books keyed by id.
    """
    def __init__(self, id_gen: IDGenerator):
        self._storage: Dict[int, dict] = {}
        self._id_gen = id_gen
        self._lock = Lock()

    async def create(self, obj: dict) -> dict:
        with self._lock:
            obj = obj.copy()
            obj['id'] = self._id_gen.next_id()
            self._storage[obj['id']] = obj
        return obj

    async def get(self, id: int) -> dict:
        try:
            return self._storage[id]
        except KeyError:
            raise NotFoundError(f'Book with id {id} not found')

    async def update(self, id: int, obj: dict) -> dict:
        if id not in self._storage:
            raise NotFoundError(f'Book with id {id} not found')
        obj = obj.copy()
        obj['id'] = id
        self._storage[id] = obj
        return obj

    async def delete(self, id: int) -> None:
        if id in self._storage:
            del self._storage[id]
            return
        raise NotFoundError(f'Book with id {id} not found')

    async def list(self) -> List[dict]:
        return list(self._storage.values())

class ListMemberRepository:
    """
    List-based in-memory repository for members.
    """
    def __init__(self, id_gen: IDGenerator):
        self._storage: List[dict] = []
        self._id_gen = id_gen
        self._lock = Lock()

    async def create(self, obj: dict) -> dict:
        with self._lock:
            obj = obj.copy()
            obj['id'] = self._id_gen.next_id()
            self._storage.append(obj)
        return obj

    async def get(self, id: int) -> dict:
        for item in self._storage:
            if item['id'] == id:
                return item
        raise NotFoundError(f'Member with id {id} not found')

    async def update(self, id: int, obj: dict) -> dict:
        for idx, item in enumerate(self._storage):
            if item['id'] == id:
                obj = obj.copy()
                obj['id'] = id
                self._storage[idx] = obj
                return obj
        raise NotFoundError(f'Member with id {id} not found')

    async def delete(self, id: int) -> None:
        for idx, item in enumerate(self._storage):
            if item['id'] == id:
                del self._storage[idx]
                return
        raise NotFoundError(f'Member with id {id} not found')

    async def list(self) -> List[dict]:
        return list(self._storage)

class DictMemberRepository:
    """
    Dict-based in-memory repository for members keyed by id.
    """
    def __init__(self, id_gen: IDGenerator):
        self._storage: Dict[int, dict] = {}
        self._id_gen = id_gen
        self._lock = Lock()

    async def create(self, obj: dict) -> dict:
        with self._lock:
            obj = obj.copy()
            obj['id'] = self._id_gen.next_id()
            self._storage[obj['id']] = obj
        return obj

    async def get(self, id: int) -> dict:
        try:
            return self._storage[id]
        except KeyError:
            raise NotFoundError(f'Member with id {id} not found')

    async def update(self, id: int, obj: dict) -> dict:
        if id not in self._storage:
            raise NotFoundError(f'Member with id {id} not found')
        obj = obj.copy()
        obj['id'] = id
        self._storage[id] = obj
        return obj

    async def delete(self, id: int) -> None:
        if id in self._storage:
            del self._storage[id]
            return
        raise NotFoundError(f'Member with id {id} not found')

    async def list(self) -> List[dict]:
        return list(self._storage.values())

class ListLoanRepository:
    """
    List-based in-memory repository for loans.
    """
    def __init__(self, id_gen: IDGenerator):
        self._storage: List[dict] = []
        self._id_gen = id_gen
        self._lock = Lock()

    async def create(self, obj: dict) -> dict:
        with self._lock:
            obj = obj.copy()
            obj['id'] = self._id_gen.next_id()
            self._storage.append(obj)
        return obj

    async def get(self, id: int) -> dict:
        for item in self._storage:
            if item['id'] == id:
                return item
        raise NotFoundError(f'Loan with id {id} not found')

    async def update(self, id: int, obj: dict) -> dict:
        for idx, item in enumerate(self._storage):
            if item['id'] == id:
                obj = obj.copy()
                obj['id'] = id
                self._storage[idx] = obj
                return obj
        raise NotFoundError(f'Loan with id {id} not found')

    async def delete(self, id: int) -> None:
        for idx, item in enumerate(self._storage):
            if item['id'] == id:
                del self._storage[idx]
                return
        raise NotFoundError(f'Loan with id {id} not found')

    async def list(self) -> List[dict]:
        return list(self._storage)

class DictLoanRepository:
    """
    Dict-based in-memory repository for loans keyed by id.
    """
    def __init__(self, id_gen: IDGenerator):
        self._storage: Dict[int, dict] = {}
        self._id_gen = id_gen
        self._lock = Lock()

    async def create(self, obj: dict) -> dict:
        with self._lock:
            obj = obj.copy()
            obj['id'] = self._id_gen.next_id()
            self._storage[obj['id']] = obj
        return obj

    async def get(self, id: int) -> dict:
        try:
            return self._storage[id]
        except KeyError:
            raise NotFoundError(f'Loan with id {id} not found')

    async def update(self, id: int, obj: dict) -> dict:
        if id not in self._storage:
            raise NotFoundError(f'Loan with id {id} not found')
        obj = obj.copy()
        obj['id'] = id
        self._storage[id] = obj
        return obj

    async def delete(self, id: int) -> None:
        if id in self._storage:
            del self._storage[id]
            return
        raise NotFoundError(f'Loan with id {id} not found')

    async def list(self) -> List[dict]:
        return list(self._storage.values())
