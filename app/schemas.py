from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from .models import PurchaseStatus, TaskPriority, TaskStatus, UserRole


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
    priority: TaskPriority = TaskPriority.normal
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
    priority: Optional[TaskPriority] = None
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
    priority: TaskPriority
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


# ---------- Purchases ----------
class PurchaseCreate(BaseModel):
    item: str
    supplier: str = ""
    cost: float = 0.0
    order_date: Optional[date] = None
    expected_date: Optional[date] = None
    arrival_date: Optional[date] = None
    status: PurchaseStatus = PurchaseStatus.to_order


class PurchaseUpdate(BaseModel):
    item: Optional[str] = None
    supplier: Optional[str] = None
    cost: Optional[float] = None
    order_date: Optional[date] = None
    expected_date: Optional[date] = None
    arrival_date: Optional[date] = None
    status: Optional[PurchaseStatus] = None


class PurchaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    item: str
    supplier: str
    cost: float
    order_date: Optional[date]
    expected_date: Optional[date]
    arrival_date: Optional[date]
    status: PurchaseStatus
    updated_by: Optional[int]
    created_at: datetime
    updated_at: datetime


# ---------- Messages ----------
class MessageCreate(BaseModel):
    body: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_id: int
    body: str
    created_at: datetime
    read_at: Optional[datetime]


class UnreadCount(BaseModel):
    unread: int


class MarkReadResult(BaseModel):
    marked: int
