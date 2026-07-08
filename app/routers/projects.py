from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Project, User, UserRole
from ..schemas import ProjectOut, ProjectUpdate
from ..workdays import off_days_between

router = APIRouter(prefix="/project", tags=["project"])


def get_project(db: Session) -> Project:
    project = db.query(Project).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No project found; run the seed (python -m app.seed)",
        )
    return project


@router.get("", response_model=ProjectOut)
def read_project(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_project(db)


@router.patch("", response_model=ProjectOut)
def update_project(
    payload: ProjectUpdate,
    user: User = Depends(require_role(UserRole.contractor)),
    db: Session = Depends(get_db),
):
    project = get_project(db)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.get("/off-days", response_model=list[date])
def off_days(
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Off-days (Sundays + holidays) in [from, to]. The single source of truth
    the frontend should use instead of hardcoding its own holiday list."""
    return off_days_between(from_, to)
