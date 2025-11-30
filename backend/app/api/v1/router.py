"""
API v1 router aggregating all endpoints.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    organizations,
    locations,
    assets,
    work_orders,
    preventive_maintenance,
    inventory,
    reports,
    audit_logs,
    user_groups,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(locations.router, prefix="/locations", tags=["Locations"])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(work_orders.router, prefix="/work-orders", tags=["Work Orders"])
api_router.include_router(preventive_maintenance.router, prefix="/pm", tags=["Preventive Maintenance"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(user_groups.router, prefix="/user-groups", tags=["User Groups"])