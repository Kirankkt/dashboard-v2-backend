import enum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base


class UserRole(str, enum.Enum):
    contractor = "contractor"
    client = "client"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskPriority(str, enum.Enum):
    normal = "normal"
    high = "high"


class PurchaseStatus(str, enum.Enum):
    to_order = "to_order"
    ordered = "ordered"
    in_transit = "in_transit"
    delivered = "delivered"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    area = Column(String, index=True, nullable=False)
    trade = Column(String, nullable=False, default="")
    name = Column(String, nullable=False)
    workers = Column(Integer, nullable=False, default=0)
    hours = Column(Float, nullable=False, default=0.0)
    start_date = Column(Date, index=True, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.todo)
    priority = Column(
        Enum(TaskPriority), nullable=False, default=TaskPriority.normal, server_default="normal"
    )
    progress = Column(Integer, nullable=False, default=0)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project = relationship("Project", back_populates="tasks")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    item = Column(String, nullable=False)
    supplier = Column(String, nullable=False, default="")
    cost = Column(Float, nullable=False, default=0.0)
    order_date = Column(Date, nullable=True)
    expected_date = Column(Date, nullable=True)
    arrival_date = Column(Date, nullable=True)
    status = Column(
        Enum(PurchaseStatus), nullable=False, default=PurchaseStatus.to_order,
        server_default="to_order",
    )
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
