from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from .models import TaskStatus, UserRole


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    created_at: datetime


# ---------- Project ----------
class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    start_date: date
    created_at: datetime
    updated_at: datetime


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None


# ---------- Tasks ----------
class TaskCreate(BaseModel):
    area: str
    name: str
    trade: str = ""
    workers: int = 0
    hours: float = 0.0
    start_date: date
    end_date: Optional[date] = None
    status: TaskStatus = TaskStatus.todo
    progress: int = 0


class TaskUpdate(BaseModel):
    area: Optional[str] = None
    name: Optional[str] = None
    trade: Optional[str] = None
    workers: Optional[int] = None
    hours: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[TaskStatus] = None
    progress: Optional[int] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    area: str
    name: str
    trade: str
    workers: int
    hours: float
    start_date: date
    end_date: Optional[date]
    status: TaskStatus
    progress: int
    updated_by: Optional[int]
    created_at: datetime
    updated_at: datetime


# ---------- Grid view (sparse area x date matrix) ----------
class GridEntry(BaseModel):
    area: str
    date: date
    tasks: List[TaskOut]


class GridView(BaseModel):
    project_id: int
    start_date: date
    entries: List[GridEntry]


# ---------- Rollover ----------
class RolloverResult(BaseModel):
    moved: int
    cutoff: date
    moved_to: date
