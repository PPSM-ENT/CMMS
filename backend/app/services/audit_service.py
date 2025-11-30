"""
Audit logging service for tracking data changes.
"""
import json
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect

from app.models.audit_log import AuditLog
from app.models.user import User


async def log_audit(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    action: str,
    user: Optional[User] = None,
    entity_name: Optional[str] = None,
    field_name: Optional[str] = None,
    old_value: Any = None,
    new_value: Any = None,
    changes: Optional[dict] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """
    Create an audit log entry.

    Args:
        db: Database session
        entity_type: Type of entity (e.g., "Asset", "User", "WorkOrder")
        entity_id: ID of the entity
        action: Action performed (CREATE, UPDATE, DELETE, STATUS_CHANGE)
        user: User who performed the action
        entity_name: Human-readable name of the entity
        field_name: Specific field that changed (for single field changes)
        old_value: Previous value
        new_value: New value
        changes: Dictionary of all changes (for multiple field changes)
        description: Human-readable description of the action
        ip_address: Client IP address
        user_agent: Client user agent
    """
    # Convert values to strings for storage
    old_value_str = None
    new_value_str = None

    if old_value is not None:
        if isinstance(old_value, (dict, list)):
            old_value_str = json.dumps(old_value)
        else:
            old_value_str = str(old_value)

    if new_value is not None:
        if isinstance(new_value, (dict, list)):
            new_value_str = json.dumps(new_value)
        else:
            new_value_str = str(new_value)

    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        action=action,
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        user_name=f"{user.first_name} {user.last_name}" if user else None,
        organization_id=user.organization_id if user else None,
        field_name=field_name,
        old_value=old_value_str,
        new_value=new_value_str,
        changes=changes,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(audit_log)
    await db.flush()

    return audit_log


async def log_create(
    db: AsyncSession,
    entity: Any,
    entity_type: str,
    user: Optional[User] = None,
    entity_name: Optional[str] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Log a CREATE action for an entity."""
    # Get all attributes as changes
    changes = {}
    try:
        mapper = inspect(entity.__class__)
        for column in mapper.columns:
            value = getattr(entity, column.key, None)
            if value is not None:
                if hasattr(value, 'value'):  # Handle enums
                    changes[column.key] = value.value
                elif hasattr(value, 'isoformat'):  # Handle datetime
                    changes[column.key] = value.isoformat()
                else:
                    changes[column.key] = value
    except Exception:
        pass

    return await log_audit(
        db=db,
        entity_type=entity_type,
        entity_id=entity.id,
        action="CREATE",
        user=user,
        entity_name=entity_name,
        changes=changes,
        description=description or f"Created {entity_type}",
        ip_address=ip_address,
    )


async def log_update(
    db: AsyncSession,
    entity: Any,
    entity_type: str,
    old_values: dict,
    new_values: dict,
    user: Optional[User] = None,
    entity_name: Optional[str] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Optional[AuditLog]:
    """
    Log an UPDATE action for an entity.
    Only logs if there are actual changes.
    """
    changes = {}

    for key, new_val in new_values.items():
        old_val = old_values.get(key)

        # Normalize values for comparison
        if hasattr(old_val, 'value'):  # Handle enums
            old_val = old_val.value
        if hasattr(new_val, 'value'):
            new_val = new_val.value
        if hasattr(old_val, 'isoformat'):  # Handle datetime
            old_val = old_val.isoformat()
        if hasattr(new_val, 'isoformat'):
            new_val = new_val.isoformat()

        if old_val != new_val:
            changes[key] = {
                "old": old_val,
                "new": new_val
            }

    if not changes:
        return None

    # Create description of changes
    changed_fields = list(changes.keys())
    desc = description or f"Updated {entity_type}: {', '.join(changed_fields)}"

    return await log_audit(
        db=db,
        entity_type=entity_type,
        entity_id=entity.id,
        action="UPDATE",
        user=user,
        entity_name=entity_name,
        changes=changes,
        description=desc,
        ip_address=ip_address,
    )


async def log_delete(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    user: Optional[User] = None,
    entity_name: Optional[str] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
    deleted_data: Optional[dict] = None,
) -> AuditLog:
    """Log a DELETE action for an entity."""
    return await log_audit(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        action="DELETE",
        user=user,
        entity_name=entity_name,
        changes=deleted_data,
        description=description or f"Deleted {entity_type}",
        ip_address=ip_address,
    )


async def log_status_change(
    db: AsyncSession,
    entity: Any,
    entity_type: str,
    old_status: str,
    new_status: str,
    user: Optional[User] = None,
    entity_name: Optional[str] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Log a STATUS_CHANGE action for an entity."""
    return await log_audit(
        db=db,
        entity_type=entity_type,
        entity_id=entity.id,
        action="STATUS_CHANGE",
        user=user,
        entity_name=entity_name,
        field_name="status",
        old_value=old_status,
        new_value=new_status,
        description=description or f"Changed status from {old_status} to {new_status}",
        ip_address=ip_address,
    )
