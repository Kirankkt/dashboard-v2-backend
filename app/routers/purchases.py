from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Project, Purchase, User, UserRole
from ..schemas import PurchaseCreate, PurchaseOut, PurchaseUpdate
from .projects import get_project

router = APIRouter(prefix="/purchases", tags=["purchases"])


def _get_purchase(db: Session, project: Project, purchase_id: int) -> Purchase:
    purchase = (
        db.query(Purchase)
        .filter(Purchase.id == purchase_id, Purchase.project_id == project.id)
        .one_or_none()
    )
    if purchase is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found")
    return purchase


# Reads + writes are open to both roles; only deletion is contractor-only.
@router.get("", response_model=list[PurchaseOut])
def list_purchases(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_project(db)
    return (
        db.query(Purchase)
        .filter(Purchase.project_id == project.id)
        .order_by(Purchase.id.desc())
        .all()
    )


@router.post("", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
def create_purchase(
    payload: PurchaseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_project(db)
    purchase = Purchase(project_id=project.id, updated_by=user.id, **payload.model_dump())
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    return purchase


@router.patch("/{purchase_id}", response_model=PurchaseOut)
def update_purchase(
    purchase_id: int,
    payload: PurchaseUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_project(db)
    purchase = _get_purchase(db, project, purchase_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(purchase, field, value)
    purchase.updated_by = user.id
    db.commit()
    db.refresh(purchase)
    return purchase


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase(
    purchase_id: int,
    user: User = Depends(require_role(UserRole.contractor)),
    db: Session = Depends(get_db),
):
    project = get_project(db)
    purchase = _get_purchase(db, project, purchase_id)
    db.delete(purchase)
    db.commit()
