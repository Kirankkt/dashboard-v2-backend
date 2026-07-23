#!/usr/bin/env python3
"""Change a user's login email and/or password.

The app has no self-service account management (seed.py only ever creates
users, it never updates them), so this one-off script edits the row directly.
Run it from backend/ with DATABASE_URL pointing at the target database:

    DATABASE_URL='postgresql://...' ./venv/bin/python scripts/set_login.py \
        --role client --email someone@hotmail.com --password 'secret'

Omitting --email or --password leaves that field alone. Nothing is written
without --apply.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.models import User, UserRole  # noqa: E402
from app.security import hash_password  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    who = ap.add_mutually_exclusive_group(required=True)
    who.add_argument("--role", choices=[r.value for r in UserRole])
    who.add_argument("--current-email")
    ap.add_argument("--email", help="new login email")
    ap.add_argument("--password", help="new password")
    ap.add_argument("--name", help="new display name")
    ap.add_argument("--apply", action="store_true", help="write the change")
    args = ap.parse_args()

    if not (args.email or args.password or args.name):
        ap.error("nothing to change: pass --email, --password and/or --name")

    db = SessionLocal()
    try:
        q = db.query(User)
        q = (
            q.filter(User.role == UserRole(args.role))
            if args.role
            else q.filter(User.email == args.current_email)
        )
        users = q.all()
        if len(users) != 1:
            print(f"Expected exactly 1 matching user, found {len(users)}:")
            for u in users:
                print(f"  #{u.id} {u.email} ({u.role.value})")
            return 1

        user = users[0]
        print(f"User #{user.id} {user.email} ({user.role.value}, name {user.name!r})")
        if args.email:
            clash = (
                db.query(User)
                .filter(User.email == args.email, User.id != user.id)
                .one_or_none()
            )
            if clash is not None:
                print(f"Email already taken by user #{clash.id}")
                return 1
            print(f"  email    {user.email} -> {args.email}")
        if args.name:
            print(f"  name     {user.name!r} -> {args.name!r}")
        if args.password:
            print("  password -> (new hash)")

        if not args.apply:
            print("\nDry run. Re-run with --apply to write.")
            return 0

        if args.email:
            user.email = args.email
        if args.name:
            user.name = args.name
        if args.password:
            user.password_hash = hash_password(args.password)
        db.commit()
        print("\nSaved.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
