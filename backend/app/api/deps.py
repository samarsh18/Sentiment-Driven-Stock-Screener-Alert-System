"""
backend/app/api/deps.py
-----------------------
FastAPI dependency functions shared across all routers.

get_db is re-exported from database.config so that there is a single
function object — FastAPI's dependency override system works by function
identity, so it's critical that all routers Depends() on the same object.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

# Re-export — do NOT redefine — so dependency overrides work in tests
from backend.app.database.config import get_db  # noqa: F401
from backend.app.database.repository import get_user_by_id


def require_user(user_id: int, db: Session = Depends(get_db)):
    """
    Resolve a user_id path parameter to a User ORM object.
    Raises 404 if the user does not exist.
    """
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )
    return user
