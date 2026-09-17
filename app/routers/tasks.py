from collections import OrderedDict
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Project, Task, TaskStatus, User, UserRole
from ..schemas import (
    GridEntry,
    GridView,
    RolloverResult,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from ..workdays import next_workday
from .projects import get_project

router = APIRouter(prefix="/tasks", tags=["tasks"])

# The client schedules the build from the Gantt chart, which only exposes the
# task name and its two dates. Everything else stays contractor-only.
CLIENT_EDITABLE = {"name", "start_date", "end_date"}


def _reconcile(task: Task, status_set: bool, progress_set: bool) -> None:
    """Progress is the single source of truth; status is derived from it
    (0 -> todo, 1..99 -> in_progress, 100 -> done). An explicit status with no
    progress given is a shortcut: done -> 100, todo -> 0, and in_progress -> 50
    when progress is sitting at either boundary."""
    if status_set and not progress_set:
        if task.status == TaskStatus.done:
            task.progress = 100
        elif task.status == TaskStatus.todo:
            task.progress = 0
        elif task.progress <= 0 or task.progress >= 100:
            task.progress = 50
    task.progress = max(0, min(100, task.progress))
    if task.progress >= 100:
        task.status = TaskStatus.done
    elif task.progress > 0:
        task.status = TaskStatus.in_progress
    else:
        task.status = TaskStatus.todo


def _get_task(db: Session, project: Project, task_id: int) -> Task:
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.project_id == project.id)
        .one_or_none()
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


# ---------- Reads (any authenticated user) ----------
@router.get("", response_model=list[TaskOut])
def list_tasks(
    area: Optional[str] = None,
    status_: Optional[TaskStatus] = Query(None, alias="status"),
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_project(db)
    q = db.query(Task).filter(Task.project_id == project.id)
    if area is not None:
        q = q.filter(Task.area == area)
    if status_ is not None:
        q = q.filter(Task.status == status_)
    if from_ is not None:
        q = q.filter(Task.start_date >= from_)
    if to is not None:
        q = q.filter(Task.start_date <= to)
    return q.order_by(Task.start_date, Task.area, Task.id).all()


@router.get("/grid", response_model=GridView)
def grid(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_project(db)
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project.id)
        .order_by(Task.area, Task.start_date, Task.id)
        .all()
    )
    buckets: "OrderedDict[tuple, list]" = OrderedDict()
    for t in tasks:
        buckets.setdefault((t.area, t.start_date), []).append(t)
    entries = [GridEntry(area=a, date=d, tasks=ts) for (a, d), ts in buckets.items()]
    return GridView(project_id=project.id, start_date=project.start_date, entries=entries)


# ---------- Writes (contractor only) ----------
@router.post("/rollover", response_model=RolloverResult)
def rollover(
    cutoff: Optional[date] = Query(None, description="Defaults to today"),
    user: User = Depends(require_role(UserRole.contractor)),
    db: Session = Depends(get_db),
):
    """Advance every unfinished task starting on/before `cutoff` to the next
    working day after `cutoff`, preserving each task's duration."""
    project = get_project(db)
    cutoff = cutoff or date.today()
    target = next_workday(cutoff)
    tasks = (
        db.query(Task)
        .filter(
            Task.project_id == project.id,
            Task.start_date <= cutoff,
            Task.status != TaskStatus.done,
        )
        .all()
    )
    moved = 0
    for t in tasks:
        duration = (t.end_date - t.start_date) if t.end_date else None
        t.start_date = target
        t.end_date = (target + duration) if duration is not None else None
        t.updated_by = user.id
        moved += 1
    db.commit()
    return RolloverResult(moved=moved, cutoff=cutoff, moved_to=target)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    user: User = Depends(require_role(UserRole.contractor)),
    db: Session = Depends(get_db),
):
    project = get_project(db)
    provided = payload.model_dump(exclude_unset=True)
    task = Task(project_id=project.id, updated_by=user.id, **payload.model_dump())
    _reconcile(task, status_set="status" in provided, progress_set="progress" in provided)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ---------- Item reads/writes ----------
@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_task(db, get_project(db), task_id)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    user: User = Depends(require_role(UserRole.contractor, UserRole.client)),
    db: Session = Depends(get_db),
):
    project = get_project(db)
    task = _get_task(db, project, task_id)
    data = payload.model_dump(exclude_unset=True)
    if user.role is UserRole.client and not set(data) <= CLIENT_EDITABLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clients can only edit a task's name and dates",
        )
    for field, value in data.items():
        setattr(task, field, value)
    task.updated_by = user.id
    _reconcile(task, status_set="status" in data, progress_set="progress" in data)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    user: User = Depends(require_role(UserRole.contractor)),
    db: Session = Depends(get_db),
):
    project = get_project(db)
    task = _get_task(db, project, task_id)
    db.delete(task)
    db.commit()
