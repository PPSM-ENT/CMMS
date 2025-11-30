from typing import Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func

from app.api.deps import DBSession, CurrentUser, Pagination
from app.schemas.common import PaginatedResponse
from app.models.user_group import UserGroup
from app.models.user_group_member import UserGroupMember
from app.models.user import User
from app.schemas.user_group import (
    UserGroupCreate,
    UserGroupUpdate,
    UserGroupResponse,
    UserGroupDetailResponse,
    UserGroupMemberCreate,
    UserGroupMemberResponse,
)

router = APIRouter()


# Support both /user-groups and /user-groups/ for list
@router.get("", response_model=PaginatedResponse[UserGroupResponse])
@router.get("/", response_model=PaginatedResponse[UserGroupResponse], include_in_schema=False)
async def list_user_groups(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    search: Optional[str] = Query(None, description="Search by name or description"),
    include_inactive: bool = Query(False, description="Include inactive groups"),
) -> Any:
    """
    List user groups in the organization with search and pagination.
    """
    query = select(UserGroup).where(UserGroup.organization_id == current_user.organization_id)

    if not include_inactive:
        query = query.where(UserGroup.is_active == True)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (UserGroup.name.ilike(search_filter))
            | (UserGroup.description.ilike(search_filter))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.order_by(UserGroup.name).offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    groups = result.scalars().all()

    # Build response with member counts (batch query for efficiency)
    group_ids = [g.id for g in groups]
    member_counts = {}
    if group_ids:
        count_result = await db.execute(
            select(UserGroupMember.group_id, func.count(UserGroupMember.id))
            .where(UserGroupMember.group_id.in_(group_ids))
            .group_by(UserGroupMember.group_id)
        )
        member_counts = {row[0]: row[1] for row in count_result}

    response_groups = []
    now = datetime.now(timezone.utc)
    for group in groups:
        response_groups.append(UserGroupResponse(
            id=group.id,
            organization_id=group.organization_id,
            name=group.name,
            description=group.description,
            is_active=group.is_active,
            created_at=group.created_at or now,
            updated_at=group.updated_at or now,
            member_count=member_counts.get(group.id, 0),
        ))

    return PaginatedResponse(
        items=response_groups,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size if total else 0,
    )


@router.get("/{group_id}", response_model=UserGroupDetailResponse)
async def get_user_group(
    db: DBSession,
    current_user: CurrentUser,
    group_id: int,
) -> Any:
    """
    Get user group by ID with members.
    """
    result = await db.execute(
        select(UserGroup)
        .where(UserGroup.id == group_id)
        .where(UserGroup.organization_id == current_user.organization_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User group not found",
        )

    # Get members with user details
    result = await db.execute(
        select(UserGroupMember)
        .join(User, UserGroupMember.user_id == User.id)
        .where(UserGroupMember.group_id == group_id)
        .order_by(UserGroupMember.sequence)
    )
    members = result.scalars().all()

    # Add user details to members
    member_responses = []
    for member in members:
        result = await db.execute(
            select(User)
            .where(User.id == member.user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            member_response = UserGroupMemberResponse(
                id=member.id,
                user_id=member.user_id,
                role=member.role,
                sequence=member.sequence,
                user_name=user.full_name,
                user_email=user.email,
            )
            member_responses.append(member_response)

    group.members = member_responses
    group.member_count = len(member_responses)

    return group


# Support both /user-groups and /user-groups/ for create
@router.post("", response_model=UserGroupResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=UserGroupResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_user_group(
    db: DBSession,
    current_user: CurrentUser,
    group_data: UserGroupCreate,
) -> Any:
    """
    Create a new user group.
    """
    try:
        # Verify all users belong to the organization
        for member_data in group_data.members:
            result = await db.execute(
                select(User)
                .where(User.id == member_data.user_id)
                .where(User.organization_id == current_user.organization_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User {member_data.user_id} not found in organization",
                )

        # Create group with explicit timestamps for SQLite compatibility
        now = datetime.now(timezone.utc)
        group = UserGroup(
            organization_id=current_user.organization_id,
            name=group_data.name,
            description=group_data.description,
            is_active=True,
            created_by_id=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(group)
        await db.flush()

        # Add members
        for member_data in group_data.members:
            member = UserGroupMember(
                group_id=group.id,
                user_id=member_data.user_id,
                role=member_data.role,
                sequence=member_data.sequence or 0,
                created_by_id=current_user.id,
                created_at=now,
                updated_at=now,
            )
            db.add(member)

        await db.commit()
        await db.refresh(group)

        # Return response with member count
        return UserGroupResponse(
            id=group.id,
            organization_id=group.organization_id,
            name=group.name,
            description=group.description,
            is_active=group.is_active,
            created_at=group.created_at or now,
            updated_at=group.updated_at or now,
            member_count=len(group_data.members),
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user group: {str(e)}",
        )


@router.put("/{group_id}", response_model=UserGroupResponse)
async def update_user_group(
    db: DBSession,
    current_user: CurrentUser,
    group_id: int,
    group_data: UserGroupUpdate,
) -> Any:
    """
    Update a user group.
    """
    try:
        result = await db.execute(
            select(UserGroup)
            .where(UserGroup.id == group_id)
            .where(UserGroup.organization_id == current_user.organization_id)
        )
        group = result.scalar_one_or_none()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User group not found",
            )

        # Update fields
        if group_data.name is not None:
            group.name = group_data.name
        if group_data.description is not None:
            group.description = group_data.description
        if group_data.is_active is not None:
            group.is_active = group_data.is_active

        group.updated_by_id = current_user.id
        await db.commit()
        await db.refresh(group)

        # Get member count
        result = await db.execute(
            select(UserGroupMember)
            .where(UserGroupMember.group_id == group.id)
        )
        member_count = len(result.scalars().all())
        now = datetime.now(timezone.utc)

        return UserGroupResponse(
            id=group.id,
            organization_id=group.organization_id,
            name=group.name,
            description=group.description,
            is_active=group.is_active,
            created_at=group.created_at or now,
            updated_at=group.updated_at or now,
            member_count=member_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user group: {str(e)}",
        )


@router.delete("/{group_id}", response_model=dict)
async def delete_user_group(
    db: DBSession,
    current_user: CurrentUser,
    group_id: int,
) -> Any:
    """
    Delete a user group. Admin only.
    """
    try:
        # Check if user is admin (superuser)
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can delete user groups",
            )

        result = await db.execute(
            select(UserGroup)
            .where(UserGroup.id == group_id)
            .where(UserGroup.organization_id == current_user.organization_id)
        )
        group = result.scalar_one_or_none()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User group not found",
            )

        # Delete the group (cascade will handle members)
        await db.delete(group)
        await db.commit()

        return {"message": f"User group '{group.name}' has been deleted"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user group: {str(e)}",
        )


# Member management endpoints

@router.post("/{group_id}/members", response_model=UserGroupDetailResponse)
async def add_group_member(
    db: DBSession,
    current_user: CurrentUser,
    group_id: int,
    member_data: UserGroupMemberCreate,
) -> Any:
    """
    Add a member to a user group.
    """
    try:
        # Verify group exists and belongs to organization
        result = await db.execute(
            select(UserGroup)
            .where(UserGroup.id == group_id)
            .where(UserGroup.organization_id == current_user.organization_id)
        )
        group = result.scalar_one_or_none()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User group not found",
            )

        # Verify user exists and belongs to organization
        result = await db.execute(
            select(User)
            .where(User.id == member_data.user_id)
            .where(User.organization_id == current_user.organization_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Check if user is already a member
        result = await db.execute(
            select(UserGroupMember)
            .where(UserGroupMember.group_id == group_id)
            .where(UserGroupMember.user_id == member_data.user_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this group",
            )

        # Add member with explicit timestamps
        now = datetime.now(timezone.utc)
        member = UserGroupMember(
            group_id=group_id,
            user_id=member_data.user_id,
            role=member_data.role,
            sequence=member_data.sequence or 0,
            created_by_id=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(member)
        await db.commit()
        await db.refresh(group)

        # Build response directly instead of calling get_user_group
        result = await db.execute(
            select(UserGroupMember)
            .where(UserGroupMember.group_id == group_id)
            .order_by(UserGroupMember.sequence)
        )
        members = result.scalars().all()

        member_responses = []
        for m in members:
            result = await db.execute(
                select(User).where(User.id == m.user_id)
            )
            u = result.scalar_one_or_none()
            if u:
                member_responses.append(UserGroupMemberResponse(
                    id=m.id,
                    user_id=m.user_id,
                    role=m.role,
                    sequence=m.sequence,
                    user_name=u.full_name,
                    user_email=u.email,
                ))

        return UserGroupDetailResponse(
            id=group.id,
            organization_id=group.organization_id,
            name=group.name,
            description=group.description,
            is_active=group.is_active,
            created_at=group.created_at or now,
            updated_at=group.updated_at or now,
            member_count=len(member_responses),
            members=member_responses,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add group member: {str(e)}",
        )



@router.delete("/{group_id}/members/{member_id}", response_model=UserGroupDetailResponse)
async def remove_group_member(
    db: DBSession,
    current_user: CurrentUser,
    group_id: int,
    member_id: int,
) -> Any:
    """
    Remove a member from a user group.
    """
    try:
        # Verify group exists and belongs to organization
        result = await db.execute(
            select(UserGroup)
            .where(UserGroup.id == group_id)
            .where(UserGroup.organization_id == current_user.organization_id)
        )
        group = result.scalar_one_or_none()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User group not found",
            )

        # Verify member exists and belongs to group
        result = await db.execute(
            select(UserGroupMember)
            .where(UserGroupMember.id == member_id)
            .where(UserGroupMember.group_id == group_id)
        )
        member = result.scalar_one_or_none()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group member not found",
            )

        # Remove member
        await db.delete(member)
        await db.commit()
        await db.refresh(group)

        # Build response directly instead of calling get_user_group
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(UserGroupMember)
            .where(UserGroupMember.group_id == group_id)
            .order_by(UserGroupMember.sequence)
        )
        members = result.scalars().all()

        member_responses = []
        for m in members:
            result = await db.execute(
                select(User).where(User.id == m.user_id)
            )
            u = result.scalar_one_or_none()
            if u:
                member_responses.append(UserGroupMemberResponse(
                    id=m.id,
                    user_id=m.user_id,
                    role=m.role,
                    sequence=m.sequence,
                    user_name=u.full_name,
                    user_email=u.email,
                ))

        return UserGroupDetailResponse(
            id=group.id,
            organization_id=group.organization_id,
            name=group.name,
            description=group.description,
            is_active=group.is_active,
            created_at=group.created_at or now,
            updated_at=group.updated_at or now,
            member_count=len(member_responses),
            members=member_responses,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove group member: {str(e)}",
        )
