from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")
class ApiResponse(BaseModel, Generic[T]):
    is_success: bool
    message: str
    data: T | None = None
