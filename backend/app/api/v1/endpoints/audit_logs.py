"""
Audit Logs API endpoints.
"""
from typing import Any, Optional, List
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func, desc, and_
from pydantic import BaseModel

from app.api.deps import DBSession, CurrentUser
from app.models.audit_log import AuditLog

router = APIRouter()


class AuditLogResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    entity_name: Optional[str]
    action: str
    user_id: Optional[int]
    user_email: Optional[str]
    user_name: Optional[str]
    field_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    changes: Optional[dict]
    description: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


@router.get("", response_model=AuditLogListResponse)
async def get_audit_logs(
    db: DBSession,
    current_user: CurrentUser,
    entity_type: Optional[str] = Query(None, description="Filter by entity type (Asset, User, WorkOrder, etc.)"),
    entity_id: Optional[int] = Query(None, description="Filter by specific entity ID"),
    action: Optional[str] = Query(None, description="Filter by action (CREATE, UPDATE, DELETE, STATUS_CHANGE)"),
    user_id: Optional[int] = Query(None, description="Filter by user who performed the action"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    search: Optional[str] = Query(None, description="Search in entity name or description"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Any:
    """
    Get audit logs with filtering and pagination.
    Admin only.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view audit logs",
        )

    # Build query
    conditions = [AuditLog.organization_id == current_user.organization_id]

    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)

    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)

    if action:
        conditions.append(AuditLog.action == action)

    if user_id:
        conditions.append(AuditLog.user_id == user_id)

    if start_date:
        conditions.append(AuditLog.created_at >= datetime.combine(start_date, datetime.min.time()))

    if end_date:
        conditions.append(AuditLog.created_at <= datetime.combine(end_date, datetime.max.time()))

    if search:
        search_filter = f"%{search}%"
        conditions.append(
            (AuditLog.entity_name.ilike(search_filter)) |
            (AuditLog.description.ilike(search_filter))
        )

    # Count total
    count_query = select(func.count()).select_from(AuditLog).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get items
    query = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(desc(AuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + page_size - 1) // page_size

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/entity/{entity_type}/{entity_id}", response_model=AuditLogListResponse)
async def get_entity_audit_logs(
    db: DBSession,
    current_user: CurrentUser,
    entity_type: str,
    entity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Any:
    """
    Get audit logs for a specific entity.
    Admin only.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view audit logs",
        )

    conditions = [
        AuditLog.organization_id == current_user.organization_id,
        AuditLog.entity_type == entity_type,
        AuditLog.entity_id == entity_id,
    ]

    # Count total
    count_query = select(func.count()).select_from(AuditLog).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get items
    query = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(desc(AuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + page_size - 1) // page_size

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/stats", response_model=dict)
async def get_audit_stats(
    db: DBSession,
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365),
) -> Any:
    """
    Get audit log statistics.
    Admin only.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view audit logs",
        )

    from datetime import timedelta

    start_date = datetime.utcnow() - timedelta(days=days)
    conditions = [
        AuditLog.organization_id == current_user.organization_id,
        AuditLog.created_at >= start_date,
    ]

    # Total logs
    total_query = select(func.count()).select_from(AuditLog).where(and_(*conditions))
    total_result = await db.execute(total_query)
    total_logs = total_result.scalar() or 0

    # By action
    action_query = (
        select(AuditLog.action, func.count().label("count"))
        .where(and_(*conditions))
        .group_by(AuditLog.action)
    )
    action_result = await db.execute(action_query)
    by_action = {row[0]: row[1] for row in action_result.all()}

    # By entity type
    entity_query = (
        select(AuditLog.entity_type, func.count().label("count"))
        .where(and_(*conditions))
        .group_by(AuditLog.entity_type)
    )
    entity_result = await db.execute(entity_query)
    by_entity = {row[0]: row[1] for row in entity_result.all()}

    # Most active users
    user_query = (
        select(AuditLog.user_name, func.count().label("count"))
        .where(and_(*conditions, AuditLog.user_name.isnot(None)))
        .group_by(AuditLog.user_name)
        .order_by(desc("count"))
        .limit(10)
    )
    user_result = await db.execute(user_query)
    top_users = [{"name": row[0], "count": row[1]} for row in user_result.all()]

    return {
        "total_logs": total_logs,
        "period_days": days,
        "by_action": by_action,
        "by_entity": by_entity,
        "top_users": top_users,
    }
