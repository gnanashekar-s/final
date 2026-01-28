from threading import Lock

class IDGenerator:
    """
    Thread-safe monotonic integer ID generator.
    """
    def __init__(self, start: int = 1):
        self._lock = Lock()
        self._current = start - 1

    def next_id(self) -> int:
        """
        Returns the next unique integer ID.
        """
        with self._lock:
            self._current += 1
            return self._current

id_generator = IDGenerator()
