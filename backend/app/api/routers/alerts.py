"""
backend/app/api/routers/alerts.py
-----------------------------------
Alert endpoints.

GET /api/users/{user_id}/alerts               Paginated alerts for user
GET /api/users/{user_id}/alerts/{alert_id}    Single alert by alert_id
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, require_user
from backend.app.api.schemas import AlertListResponse, AlertResponse, PaginationMeta
from backend.app.database.models import AlertRecord

router = APIRouter(prefix="/api/users", tags=["Alerts"])


@router.get("/{user_id}/alerts", response_model=AlertListResponse)
def get_user_alerts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    """Return paginated alerts for a user, newest first."""
    query = (
        db.query(AlertRecord)
        .filter(AlertRecord.user_id == user.id)
        .order_by(AlertRecord.created_at.desc())
    )
    total = query.count()
    records = query.offset(offset).limit(limit).all()

    return AlertListResponse(
        items=[AlertResponse.from_orm_record(r) for r in records],
        pagination=PaginationMeta(total=total, limit=limit, offset=offset),
    )


@router.get("/{user_id}/alerts/{alert_id}", response_model=AlertResponse)
def get_user_alert_by_id(
    alert_id: str,
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    """Return a single alert by alert_id, scoped to user."""
    record = (
        db.query(AlertRecord)
        .filter(AlertRecord.alert_id == alert_id, AlertRecord.user_id == user.id)
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id!r} not found for user {user.id}.",
        )
    return AlertResponse.from_orm_record(record)
