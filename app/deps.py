from fastapi import Depends, HTTPException, Request, status

from .models import User, UserRole


def get_current_user(request: Request) -> User:
    """Return the user attached by the auth middleware, or 401 if none."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# Temporary (2026-09-17): while the project is starting up, the client has the
# same rights as the contractor everywhere. Set to False to make the client
# read-mostly again (contractor-only routes and the task-field allowlist return).
CLIENT_FULL_ACCESS = True


def has_full_access(user: User) -> bool:
    return user.role is UserRole.contractor or CLIENT_FULL_ACCESS


def require_role(*roles: UserRole):
    """Dependency factory: allow only the given role(s). Anything open to the
    contractor is also open to users with full access."""

    def checker(user: User = Depends(get_current_user)) -> User:
        allowed = user.role in roles or (UserRole.contractor in roles and has_full_access(user))
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return checker
