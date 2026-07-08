"""Seed the single project and the two app users.

No self-registration exists — run this once (locally or on Railway) to create
users. Override the defaults with env vars before running in prod:

    CONTRACTOR_EMAIL=... CONTRACTOR_PASSWORD=... \
    CLIENT_EMAIL=... CLIENT_PASSWORD=... \
    ./venv/bin/python -m app.seed
"""

import os
from datetime import date

from . import models  # noqa: F401  (register models on Base)
from .database import Base, SessionLocal, engine
from .models import Project, User, UserRole
from .security import hash_password


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        project = db.query(Project).first()
        if project is None:
            project = Project(
                name=os.getenv("PROJECT_NAME", "Remodel Project"),
                start_date=date.today(),
            )
            db.add(project)
            db.commit()
            print(f"Created project #{project.id}: {project.name} (start {project.start_date})")
        else:
            print(f"Project already exists #{project.id}: {project.name}")

        seed_users = [
            {
                "name": os.getenv("CONTRACTOR_NAME", "Contractor"),
                "email": os.getenv("CONTRACTOR_EMAIL", "contractor@example.com"),
                "password": os.getenv("CONTRACTOR_PASSWORD", "contractor123"),
                "role": UserRole.contractor,
            },
            {
                "name": os.getenv("CLIENT_NAME", "Client"),
                "email": os.getenv("CLIENT_EMAIL", "client@example.com"),
                "password": os.getenv("CLIENT_PASSWORD", "client123"),
                "role": UserRole.client,
            },
        ]
        for spec in seed_users:
            existing = db.query(User).filter(User.email == spec["email"]).one_or_none()
            if existing is not None:
                print(f"User already exists: {existing.email} ({existing.role.value})")
                continue
            user = User(
                name=spec["name"],
                email=spec["email"],
                password_hash=hash_password(spec["password"]),
                role=spec["role"],
            )
            db.add(user)
            db.commit()
            print(f"Created user: {user.email} ({user.role.value})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
