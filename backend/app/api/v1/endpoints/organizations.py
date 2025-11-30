"""
Organization management endpoints.
"""
from typing import Any, List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DBSession, CurrentUser, CurrentSuperuser
from app.models.organization import Organization
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter()


@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    Get current user's organization.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return org


@router.put("/current", response_model=OrganizationResponse)
async def update_current_organization(
    db: DBSession,
    current_user: CurrentUser,
    org_data: OrganizationUpdate,
) -> Any:
    """
    Update current user's organization.
    Requires admin privileges.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    update_data = org_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org)

    return org


# Superuser-only endpoints for managing all organizations

@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    db: DBSession,
    current_user: CurrentSuperuser,
) -> Any:
    """
    List all organizations (superuser only).
    """
    result = await db.execute(select(Organization))
    orgs = result.scalars().all()
    return orgs


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    db: DBSession,
    current_user: CurrentSuperuser,
    org_data: OrganizationCreate,
) -> Any:
    """
    Create a new organization (superuser only).
    """
    # Check if code already exists
    result = await db.execute(
        select(Organization).where(Organization.code == org_data.code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization code already exists",
        )

    org = Organization(**org_data.model_dump())
    db.add(org)
    await db.commit()
    await db.refresh(org)

    return org


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    db: DBSession,
    current_user: CurrentSuperuser,
    org_id: int,
) -> Any:
    """
    Get organization by ID (superuser only).
    """
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return org


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    db: DBSession,
    current_user: CurrentSuperuser,
    org_id: int,
    org_data: OrganizationUpdate,
) -> Any:
    """
    Update organization (superuser only).
    """
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    update_data = org_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org)

    return org
