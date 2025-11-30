"""
User management endpoints.
"""
from typing import Any, List

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, CurrentUser, CurrentSuperuser, Pagination
from app.core.security import get_password_hash
from app.models.user import User, Role, Permission, UserRole
from app.services.audit_service import log_create, log_update, log_delete
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserWithRolesResponse,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    PermissionResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    is_active: bool = Query(None, description="Filter by active status"),
    search: str = Query(None, description="Search by name or email"),
) -> Any:
    """
    List users in the organization.
    """
    query = select(User).where(User.organization_id == current_user.organization_id)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_filter))
            | (User.first_name.ilike(search_filter))
            | (User.last_name.ilike(search_filter))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    return PaginatedResponse(
        items=users,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    db: DBSession,
    current_user: CurrentUser,
    user_data: UserCreate,
) -> Any:
    """
    Create a new user in the organization.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        organization_id=current_user.organization_id,
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        job_title=user_data.job_title,
        hourly_rate=user_data.hourly_rate,
    )

    db.add(user)
    await db.flush()

    # Assign roles
    if user_data.role_ids:
        for role_id in user_data.role_ids:
            result = await db.execute(
                select(Role)
                .where(Role.id == role_id)
                .where(Role.organization_id == current_user.organization_id)
            )
            role = result.scalar_one_or_none()
            if role:
                user_role = UserRole(user_id=user.id, role_id=role_id)
                db.add(user_role)

    # Log audit
    await log_create(
        db=db,
        entity=user,
        entity_type="User",
        user=current_user,
        entity_name=f"{user.first_name} {user.last_name} ({user.email})",
        description=f"Created user {user.email}",
    )

    await db.commit()
    await db.refresh(user)

    return user


@router.get("/{user_id}", response_model=UserWithRolesResponse)
async def get_user(
    db: DBSession,
    current_user: CurrentUser,
    user_id: int,
) -> Any:
    """
    Get user by ID.
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_roles).selectinload(UserRole.role).selectinload(Role.permissions))
        .where(User.id == user_id)
        .where(User.organization_id == current_user.organization_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Build response with roles
    roles = [ur.role for ur in user.user_roles]
    return UserWithRolesResponse(
        **UserResponse.model_validate(user).model_dump(),
        roles=roles,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    db: DBSession,
    current_user: CurrentUser,
    user_id: int,
    user_data: UserUpdate,
) -> Any:
    """
    Update user.
    """
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.organization_id == current_user.organization_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Capture old values for audit
    old_values = {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "job_title": user.job_title,
        "hourly_rate": user.hourly_rate,
        "is_active": user.is_active,
    }

    # Check email uniqueness if changing
    if user_data.email and user_data.email != user.email:
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)

    # Handle role updates separately
    role_ids = update_data.pop("role_ids", None)

    for field, value in update_data.items():
        setattr(user, field, value)

    # Update roles if provided
    if role_ids is not None:
        # Remove existing roles
        await db.execute(
            select(UserRole).where(UserRole.user_id == user.id)
        )
        for ur in user.user_roles:
            await db.delete(ur)

        # Add new roles
        for role_id in role_ids:
            result = await db.execute(
                select(Role)
                .where(Role.id == role_id)
                .where(Role.organization_id == current_user.organization_id)
            )
            if result.scalar_one_or_none():
                user_role = UserRole(user_id=user.id, role_id=role_id)
                db.add(user_role)

    # Log audit
    await log_update(
        db=db,
        entity=user,
        entity_type="User",
        old_values=old_values,
        new_values=user_data.model_dump(exclude_unset=True, exclude={"role_ids"}),
        user=current_user,
        entity_name=f"{user.first_name} {user.last_name} ({user.email})",
    )

    await db.commit()
    await db.refresh(user)

    return user


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    db: DBSession,
    current_user: CurrentUser,
    user_id: int,
) -> Any:
    """
    Deactivate user (soft delete).
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.organization_id == current_user.organization_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Log audit before change
    await log_delete(
        db=db,
        entity_type="User",
        entity_id=user.id,
        user=current_user,
        entity_name=f"{user.first_name} {user.last_name} ({user.email})",
        description=f"Deactivated user {user.email}",
        deleted_data={
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "job_title": user.job_title,
        },
    )

    user.is_active = False
    await db.commit()

    return MessageResponse(message="User deactivated successfully")


# Role endpoints

@router.get("/roles/all", response_model=List[RoleResponse])
async def list_roles(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    List all roles in the organization.
    """
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.organization_id == current_user.organization_id)
    )
    roles = result.scalars().all()
    return roles


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    db: DBSession,
    current_user: CurrentUser,
    role_data: RoleCreate,
) -> Any:
    """
    Create a new role.
    """
    role = Role(
        organization_id=current_user.organization_id,
        name=role_data.name,
        code=role_data.code,
        description=role_data.description,
    )

    db.add(role)
    await db.flush()

    # Assign permissions
    if role_data.permission_ids:
        for perm_id in role_data.permission_ids:
            result = await db.execute(select(Permission).where(Permission.id == perm_id))
            permission = result.scalar_one_or_none()
            if permission:
                role.permissions.append(permission)

    await db.commit()
    await db.refresh(role)

    return role


@router.get("/permissions/all", response_model=List[PermissionResponse])
async def list_permissions(db: DBSession, current_user: CurrentUser) -> Any:
    """
    List all available permissions.
    """
    result = await db.execute(select(Permission))
    permissions = result.scalars().all()
    return permissions
