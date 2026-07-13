from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Message, User
from ..schemas import MarkReadResult, MessageCreate, MessageOut, UnreadCount
from .projects import get_project

router = APIRouter(prefix="/messages", tags=["messages"])

MAX_BODY_LEN = 4000


@router.get("", response_model=list[MessageOut])
def list_messages(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_project(db)
    return (
        db.query(Message)
        .filter(Message.project_id == project.id)
        .order_by(Message.id)
        .all()
    )


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty message")
    if len(body) > MAX_BODY_LEN:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message too long")
    project = get_project(db)
    message = Message(project_id=project.id, sender_id=user.id, body=body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.post("/read", response_model=MarkReadResult)
def mark_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark every message from the other party as read."""
    project = get_project(db)
    marked = (
        db.query(Message)
        .filter(
            Message.project_id == project.id,
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
        .update({Message.read_at: func.now()}, synchronize_session=False)
    )
    db.commit()
    return MarkReadResult(marked=marked)


@router.get("/unread", response_model=UnreadCount)
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_project(db)
    unread = (
        db.query(func.count(Message.id))
        .filter(
            Message.project_id == project.id,
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
        .scalar()
    )
    return UnreadCount(unread=unread or 0)
