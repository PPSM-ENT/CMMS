"""
Location management endpoints.
"""
from typing import Any, List

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, CurrentUser, Pagination
from app.models.location import Location
from app.schemas.location import (
    LocationCreate,
    LocationUpdate,
    LocationResponse,
    LocationTreeResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[LocationResponse])
async def list_locations(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    location_type: str = Query(None, description="Filter by location type"),
    is_active: bool = Query(None, description="Filter by active status"),
    search: str = Query(None, description="Search by name or code"),
) -> Any:
    """
    List locations in the organization.
    """
    query = select(Location).where(Location.organization_id == current_user.organization_id)

    if location_type:
        query = query.where(Location.location_type == location_type)

    if is_active is not None:
        query = query.where(Location.is_active == is_active)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Location.code.ilike(search_filter))
            | (Location.name.ilike(search_filter))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.order_by(Location.hierarchy_path).offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    locations = result.scalars().all()

    return PaginatedResponse(
        items=locations,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/tree", response_model=List[LocationTreeResponse])
async def get_location_tree(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    Get locations as a hierarchical tree.
    """
    result = await db.execute(
        select(Location)
        .where(Location.organization_id == current_user.organization_id)
        .where(Location.is_active == True)
        .order_by(Location.hierarchy_path)
    )
    all_locations = result.scalars().all()

    # Build tree structure
    location_map = {loc.id: LocationTreeResponse.model_validate(loc) for loc in all_locations}

    root_locations = []
    for loc in all_locations:
        loc_response = location_map[loc.id]
        if loc.parent_id and loc.parent_id in location_map:
            parent = location_map[loc.parent_id]
            parent.children.append(loc_response)
        else:
            root_locations.append(loc_response)

    return root_locations


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    db: DBSession,
    current_user: CurrentUser,
    location_data: LocationCreate,
) -> Any:
    """
    Create a new location.
    """
    # Check code uniqueness within organization
    result = await db.execute(
        select(Location)
        .where(Location.organization_id == current_user.organization_id)
        .where(Location.code == location_data.code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location code already exists",
        )

    # Validate parent if provided
    parent = None
    if location_data.parent_id:
        result = await db.execute(
            select(Location)
            .where(Location.id == location_data.parent_id)
            .where(Location.organization_id == current_user.organization_id)
        )
        parent = result.scalar_one_or_none()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent location not found",
            )

    location = Location(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        **location_data.model_dump(),
    )

    # Set hierarchy info
    if parent:
        location.parent = parent
    location.update_hierarchy()

    db.add(location)
    await db.commit()
    await db.refresh(location)

    return location


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    db: DBSession,
    current_user: CurrentUser,
    location_id: int,
) -> Any:
    """
    Get location by ID.
    """
    result = await db.execute(
        select(Location)
        .where(Location.id == location_id)
        .where(Location.organization_id == current_user.organization_id)
    )
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    return location


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    db: DBSession,
    current_user: CurrentUser,
    location_id: int,
    location_data: LocationUpdate,
) -> Any:
    """
    Update location.
    """
    result = await db.execute(
        select(Location)
        .where(Location.id == location_id)
        .where(Location.organization_id == current_user.organization_id)
    )
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    update_data = location_data.model_dump(exclude_unset=True)

    # Handle parent change
    if "parent_id" in update_data:
        new_parent_id = update_data["parent_id"]
        if new_parent_id:
            # Prevent circular reference
            if new_parent_id == location_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Location cannot be its own parent",
                )

            result = await db.execute(
                select(Location)
                .where(Location.id == new_parent_id)
                .where(Location.organization_id == current_user.organization_id)
            )
            parent = result.scalar_one_or_none()
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent location not found",
                )
            location.parent = parent
        else:
            location.parent = None

    for field, value in update_data.items():
        if field != "parent_id":  # Already handled
            setattr(location, field, value)

    location.updated_by_id = current_user.id
    location.update_hierarchy()

    await db.commit()
    await db.refresh(location)

    return location


@router.delete("/{location_id}", response_model=MessageResponse)
async def delete_location(
    db: DBSession,
    current_user: CurrentUser,
    location_id: int,
) -> Any:
    """
    Deactivate location (soft delete).
    """
    result = await db.execute(
        select(Location)
        .options(selectinload(Location.children))
        .where(Location.id == location_id)
        .where(Location.organization_id == current_user.organization_id)
    )
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    # Check for active children
    if location.children:
        active_children = [c for c in location.children if c.is_active]
        if active_children:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete location with active child locations",
            )

    location.is_active = False
    await db.commit()

    return MessageResponse(message="Location deactivated successfully")
