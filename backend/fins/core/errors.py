class NotFoundError(Exception):
    """
    Raised when a resource is not found.
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class ConflictError(Exception):
    """
    Raised when a resource conflicts with an existing resource (e.g., duplicate).
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
