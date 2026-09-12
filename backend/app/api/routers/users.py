"""
backend/app/api/routers/users.py
---------------------------------
User endpoints.

POST   /api/users             Create or retrieve a user by email
GET    /api/users/{user_id}   Get user details
GET    /api/users/{user_id}/preferences   Get preferences
PUT    /api/users/{user_id}/preferences   Update preferences
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, require_user
from backend.app.api.schemas import (
    UserCreate,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    UserResponse,
)
from backend.app.database.repository import create_user

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(body: UserCreate, db: Session = Depends(get_db)):
    """Create a new user. Returns existing user if email already registered."""
    user = create_user(db, email=body.email)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user_endpoint(user=Depends(require_user)):
    """Get user details by user_id."""
    return user


@router.get("/{user_id}/preferences", response_model=UserPreferencesResponse)
def get_preferences(user=Depends(require_user)):
    """Get user preferences (currently: is_active flag)."""
    return UserPreferencesResponse.from_user(user)


@router.put("/{user_id}/preferences", response_model=UserPreferencesResponse)
def update_preferences(
    body: UserPreferencesUpdate,
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    """Update user preferences."""
    if body.is_active is not None:
        user.is_active = body.is_active
        db.commit()
        db.refresh(user)
    return UserPreferencesResponse.from_user(user)
