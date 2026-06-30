"""Pydantic models for API request/response.

Defines data structures for:
- API Response wrapper (Generic)
- Task creation and update payloads
- Task response model

Uses Pydantic for automatic validation.
"""

from pydantic import BaseModel
from typing import Optional, Generic, TypeVar

DataT = TypeVar('DataT')

class ApiResponse(BaseModel, Generic[DataT]):
    code: int
    message: str
    data: Optional[DataT] = None

class TaskCreate(BaseModel):
    name: str
    login_id: str
    password: str
    chat_id: Optional[str] = None
    target_semester_code: Optional[str] = None
    interval: int = 300
    monitor_type: str = 'nilai'
    target_courses: Optional[str] = None
    whatsapp_number: Optional[str] = None

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    login_id: Optional[str] = None
    password: Optional[str] = None
    chat_id: Optional[str] = None
    target_semester_code: Optional[str] = None
    interval: Optional[int] = None
    monitor_type: Optional[str] = None
    target_courses: Optional[str] = None
    whatsapp_number: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    name: str
    login_id: str
    target_semester_code: Optional[str]
    interval: int
    status: str
    pid: Optional[int]
    monitor_type: str
    target_courses: Optional[str]
