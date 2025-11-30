"""
Reporting and analytics endpoints.
"""
from typing import Any, List, Optional
from collections import defaultdict
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import select, func, and_, case, desc, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, CurrentUser
from app.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderType, LaborTransaction, MaterialTransaction
from app.models.asset import Asset, AssetStatus, AssetCriticality
from app.models.preventive_maintenance import PreventiveMaintenance
from app.models.inventory import Part, StockLevel, PartTransaction
from app.models.user import User

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_metrics(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    Get key metrics for dashboard.
    """
    org_id = current_user.organization_id
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # Work Order counts by status
    wo_counts = await db.execute(
        select(
            WorkOrder.status,
            func.count(WorkOrder.id).label("count")
        )
        .where(WorkOrder.organization_id == org_id)
        .group_by(WorkOrder.status)
    )
    wo_by_status = {getattr(row[0], 'value', row[0]): row[1] for row in wo_counts}

    # Open work orders
    open_statuses = [
        WorkOrderStatus.DRAFT,
        WorkOrderStatus.WAITING_APPROVAL,
        WorkOrderStatus.APPROVED,
        WorkOrderStatus.SCHEDULED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.ON_HOLD,
    ]
    open_wo_count = sum(wo_by_status.get(s.value, 0) for s in open_statuses)

    # Overdue work orders
    overdue_count = await db.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(WorkOrder.organization_id == org_id)
        .where(WorkOrder.status.in_(open_statuses))
        .where(WorkOrder.due_date < today)
    )

    # Completed this month
    first_of_month = today.replace(day=1)
    completed_this_month = await db.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(WorkOrder.organization_id == org_id)
        .where(WorkOrder.status == WorkOrderStatus.COMPLETED)
        .where(WorkOrder.actual_end >= first_of_month)
    )

    # PM compliance (completed on time / total due)
    pms_due = await db.scalar(
        select(func.count())
        .select_from(PreventiveMaintenance)
        .where(PreventiveMaintenance.organization_id == org_id)
        .where(PreventiveMaintenance.is_active == True)
        .where(PreventiveMaintenance.next_due_date <= today)
    )

    # Assets by status
    asset_counts = await db.execute(
        select(
            Asset.status,
            func.count(Asset.id).label("count")
        )
        .where(Asset.organization_id == org_id)
        .where(Asset.is_active == True)
        .group_by(Asset.status)
    )
    assets_by_status = {getattr(row[0], 'value', row[0]): row[1] for row in asset_counts}

    # Low stock parts count
    result = await db.execute(
        select(Part)
        .options(selectinload(Part.stock_levels))
        .where(Part.organization_id == org_id)
        .where(Part.status == "ACTIVE")
    )
    parts = result.scalars().all()
    low_stock_count = sum(
        1 for part in parts
        if any(stock.needs_reorder() for stock in part.stock_levels)
    )

    # Total costs this month
    labor_cost_month = await db.scalar(
        select(func.coalesce(func.sum(LaborTransaction.total_cost), 0))
        .where(LaborTransaction.organization_id == org_id)
        .where(LaborTransaction.created_at >= first_of_month)
    ) or 0

    material_cost_month = await db.scalar(
        select(func.coalesce(func.sum(MaterialTransaction.total_cost), 0))
        .where(MaterialTransaction.organization_id == org_id)
        .where(MaterialTransaction.created_at >= first_of_month)
    ) or 0

    return {
        "work_orders": {
            "open": open_wo_count,
            "overdue": overdue_count,
            "completed_this_month": completed_this_month,
            "by_status": wo_by_status,
        },
        "assets": {
            "total_active": sum(assets_by_status.values()),
            "by_status": assets_by_status,
        },
        "preventive_maintenance": {
            "due_today": pms_due,
        },
        "inventory": {
            "low_stock_items": low_stock_count,
        },
        "costs": {
            "labor_this_month": float(labor_cost_month),
            "material_this_month": float(material_cost_month),
            "total_this_month": float(labor_cost_month + material_cost_month),
        },
    }


@router.get("/work-orders/summary")
async def get_work_order_summary(
    db: DBSession,
    current_user: CurrentUser,
    start_date: date = Query(None),
    end_date: date = Query(None),
) -> Any:
    """
    Get work order summary statistics.
    """
    org_id = current_user.organization_id

    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    # Work orders created in period
    created_count = await db.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(WorkOrder.organization_id == org_id)
        .where(func.date(WorkOrder.created_at) >= start_date)
        .where(func.date(WorkOrder.created_at) <= end_date)
    )

    # Work orders completed in period
    completed_count = await db.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(WorkOrder.organization_id == org_id)
        .where(WorkOrder.status == WorkOrderStatus.COMPLETED)
        .where(func.date(WorkOrder.actual_end) >= start_date)
        .where(func.date(WorkOrder.actual_end) <= end_date)
    )

    # By type
    by_type = await db.execute(
        select(
            WorkOrder.work_type,
            func.count(WorkOrder.id).label("count")
        )
        .where(WorkOrder.organization_id == org_id)
        .where(func.date(WorkOrder.created_at) >= start_date)
        .where(func.date(WorkOrder.created_at) <= end_date)
        .group_by(WorkOrder.work_type)
    )

    # By priority
    by_priority = await db.execute(
        select(
            WorkOrder.priority,
            func.count(WorkOrder.id).label("count")
        )
        .where(WorkOrder.organization_id == org_id)
        .where(func.date(WorkOrder.created_at) >= start_date)
        .where(func.date(WorkOrder.created_at) <= end_date)
        .group_by(WorkOrder.priority)
    )

    # Average completion time (for completed WOs with actual times)
    avg_completion = await db.execute(
        select(
            func.avg(
                func.extract("epoch", WorkOrder.actual_end) -
                func.extract("epoch", WorkOrder.actual_start)
            ) / 3600  # Convert to hours
        )
        .where(WorkOrder.organization_id == org_id)
        .where(WorkOrder.status == WorkOrderStatus.COMPLETED)
        .where(WorkOrder.actual_start.isnot(None))
        .where(WorkOrder.actual_end.isnot(None))
        .where(func.date(WorkOrder.actual_end) >= start_date)
        .where(func.date(WorkOrder.actual_end) <= end_date)
    )
    avg_hours = avg_completion.scalar() or 0

    # Total costs
    total_labor_cost = await db.scalar(
        select(func.coalesce(func.sum(WorkOrder.actual_labor_cost), 0))
        .where(WorkOrder.organization_id == org_id)
        .where(func.date(WorkOrder.created_at) >= start_date)
        .where(func.date(WorkOrder.created_at) <= end_date)
    ) or 0

    total_material_cost = await db.scalar(
        select(func.coalesce(func.sum(WorkOrder.actual_material_cost), 0))
        .where(WorkOrder.organization_id == org_id)
        .where(func.date(WorkOrder.created_at) >= start_date)
        .where(func.date(WorkOrder.created_at) <= end_date)
    ) or 0

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "counts": {
            "created": created_count,
            "completed": completed_count,
        },
        "by_type": {getattr(row[0], 'value', row[0]): row[1] for row in by_type},
        "by_priority": {getattr(row[0], 'value', row[0]): row[1] for row in by_priority},
        "performance": {
            "average_completion_hours": round(float(avg_hours), 2),
        },
        "costs": {
            "total_labor": float(total_labor_cost),
            "total_material": float(total_material_cost),
            "total": float(total_labor_cost + total_material_cost),
        },
    }


@router.get("/assets/summary")
async def get_asset_summary(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    Get asset summary statistics.
    """
    org_id = current_user.organization_id

    # Total assets
    total_assets = await db.scalar(
        select(func.count())
        .select_from(Asset)
        .where(Asset.organization_id == org_id)
        .where(Asset.is_active == True)
    )

    # By status
    by_status = await db.execute(
        select(
            Asset.status,
            func.count(Asset.id).label("count")
        )
        .where(Asset.organization_id == org_id)
        .where(Asset.is_active == True)
        .group_by(Asset.status)
    )

    # By criticality
    by_criticality = await db.execute(
        select(
            Asset.criticality,
            func.count(Asset.id).label("count")
        )
        .where(Asset.organization_id == org_id)
        .where(Asset.is_active == True)
        .group_by(Asset.criticality)
    )

    # By category
    by_category = await db.execute(
        select(
            Asset.category,
            func.count(Asset.id).label("count")
        )
        .where(Asset.organization_id == org_id)
        .where(Asset.is_active == True)
        .where(Asset.category.isnot(None))
        .group_by(Asset.category)
    )

    # Assets with most work orders
    top_assets = await db.execute(
        select(
            Asset.id,
            Asset.asset_num,
            Asset.name,
            func.count(WorkOrder.id).label("wo_count")
        )
        .join(WorkOrder, WorkOrder.asset_id == Asset.id)
        .where(Asset.organization_id == org_id)
        .group_by(Asset.id, Asset.asset_num, Asset.name)
        .order_by(func.count(WorkOrder.id).desc())
        .limit(10)
    )

    return {
        "total_active": total_assets,
        "by_status": {getattr(row[0], 'value', row[0]): row[1] for row in by_status},
        "by_criticality": {getattr(row[0], 'value', row[0]): row[1] for row in by_criticality},
        "by_category": {row[0] or "Uncategorized": row[1] for row in by_category},
        "top_by_work_orders": [
            {
                "id": row[0],
                "asset_num": row[1],
                "name": row[2],
                "work_order_count": row[3],
            }
            for row in top_assets
        ],
    }


@router.get("/pm/compliance")
async def get_pm_compliance(
    db: DBSession,
    current_user: CurrentUser,
    start_date: date = Query(None),
    end_date: date = Query(None),
) -> Any:
    """
    Get PM compliance report.
    """
    org_id = current_user.organization_id

    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    # PM work orders completed in period
    pm_wos = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.organization_id == org_id)
        .where(WorkOrder.work_type == WorkOrderType.PREVENTIVE)
        .where(WorkOrder.pm_id.isnot(None))
        .where(func.date(WorkOrder.created_at) >= start_date)
        .where(func.date(WorkOrder.created_at) <= end_date)
    )
    pm_work_orders = pm_wos.scalars().all()

    total_pm_wos = len(pm_work_orders)
    completed_on_time = 0
    completed_late = 0
    not_completed = 0

    for wo in pm_work_orders:
        if wo.status == WorkOrderStatus.COMPLETED:
            if wo.due_date and wo.actual_end:
                if wo.actual_end.date() <= wo.due_date:
                    completed_on_time += 1
                else:
                    completed_late += 1
            else:
                completed_on_time += 1  # No due date, count as on time
        elif wo.status not in [WorkOrderStatus.CLOSED, WorkOrderStatus.CANCELLED]:
            not_completed += 1

    compliance_rate = (completed_on_time / total_pm_wos * 100) if total_pm_wos > 0 else 0

    # Upcoming PMs
    upcoming_pms = await db.execute(
        select(PreventiveMaintenance)
        .where(PreventiveMaintenance.organization_id == org_id)
        .where(PreventiveMaintenance.is_active == True)
        .where(PreventiveMaintenance.next_due_date.isnot(None))
        .where(PreventiveMaintenance.next_due_date <= end_date + timedelta(days=7))
        .order_by(PreventiveMaintenance.next_due_date)
        .limit(20)
    )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "compliance": {
            "total_pm_work_orders": total_pm_wos,
            "completed_on_time": completed_on_time,
            "completed_late": completed_late,
            "not_completed": not_completed,
            "compliance_rate": round(compliance_rate, 1),
        },
        "upcoming": [
            {
                "id": pm.id,
                "pm_number": pm.pm_number,
                "name": pm.name,
                "next_due_date": pm.next_due_date.isoformat() if pm.next_due_date else None,
                "asset_id": pm.asset_id,
            }
            for pm in upcoming_pms.scalars()
        ],
    }


@router.get("/inventory/value")
async def get_inventory_value(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    Get inventory value report.
    """
    org_id = current_user.organization_id

    # Total inventory value by storeroom
    result = await db.execute(
        select(
            Part,
        )
        .options(selectinload(Part.stock_levels))
        .where(Part.organization_id == org_id)
        .where(Part.status == "ACTIVE")
    )
    parts = result.scalars().all()

    storeroom_values = {}
    total_value = 0
    total_quantity = 0

    for part in parts:
        for stock in part.stock_levels:
            value = stock.current_balance * part.average_cost
            storeroom_id = stock.storeroom_id

            if storeroom_id not in storeroom_values:
                storeroom_values[storeroom_id] = {"quantity": 0, "value": 0}

            storeroom_values[storeroom_id]["quantity"] += stock.current_balance
            storeroom_values[storeroom_id]["value"] += value
            total_value += value
            total_quantity += stock.current_balance

    # Top value items
    items_with_value = []
    for part in parts:
        total_on_hand = sum(s.current_balance for s in part.stock_levels)
        if total_on_hand > 0:
            items_with_value.append({
                "id": part.id,
                "part_number": part.part_number,
                "name": part.name,
                "quantity": total_on_hand,
                "unit_cost": part.average_cost,
                "total_value": total_on_hand * part.average_cost,
            })

    items_with_value.sort(key=lambda x: x["total_value"], reverse=True)

    return {
        "summary": {
            "total_value": round(total_value, 2),
            "total_quantity": total_quantity,
            "unique_parts": len([p for p in parts if any(s.current_balance > 0 for s in p.stock_levels)]),
        },
        "by_storeroom": {
            str(k): {
                "quantity": v["quantity"],
                "value": round(v["value"], 2),
            }
            for k, v in storeroom_values.items()
        },
        "top_value_items": items_with_value[:20],
    }


@router.get("/mtbf-mttr")
async def get_mtbf_mttr(
    db: DBSession,
    current_user: CurrentUser,
    asset_id: int = Query(None, description="Calculate for a specific asset"),
    start_date: date = Query(None, description="Start of the evaluation window"),
    end_date: date = Query(None, description="End of the evaluation window"),
    asset_status: str = Query(None, description="Filter assets by status"),
    criticality: str = Query(None, description="Filter assets by criticality"),
    category: str = Query(None, description="Filter assets by category"),
    location_id: int = Query(None, description="Filter assets by location"),
    min_failures: int = Query(2, ge=1, le=10, description="Minimum failures required for MTBF"),
    include_single_failures: bool = Query(
        False,
        description="Include assets that do not meet the min_failures threshold",
    ),
) -> Any:
    """
    Calculate MTBF (Mean Time Between Failures) and MTTR (Mean Time To Repair) by asset.
    """
    org_id = current_user.organization_id

    if not start_date:
        start_date = date.today() - timedelta(days=365)
    if not end_date:
        end_date = date.today()

    def _enum_or_none(enum_cls, raw_value):
        if not raw_value:
            return None
        try:
            return enum_cls(raw_value)
        except ValueError:
            return None

    status_enum = _enum_or_none(AssetStatus, asset_status)
    crit_enum = _enum_or_none(AssetCriticality, criticality)

    asset_query = select(Asset).where(Asset.organization_id == org_id)
    if asset_id:
        asset_query = asset_query.where(Asset.id == asset_id)
    if status_enum:
        asset_query = asset_query.where(Asset.status == status_enum)
    if crit_enum:
        asset_query = asset_query.where(Asset.criticality == crit_enum)
    if category:
        asset_query = asset_query.where(Asset.category == category)
    if location_id:
        asset_query = asset_query.where(Asset.location_id == location_id)

    assets = (await db.execute(asset_query)).scalars().all()
    if not assets:
        return {
            "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "overall": {"total_failures": 0, "average_mtbf_hours": 0, "average_mttr_hours": 0},
            "by_asset": [],
        }

    asset_lookup = {asset.id: asset for asset in assets}
    asset_ids = list(asset_lookup.keys())

    failure_query = (
        select(
            WorkOrder.asset_id,
            WorkOrder.actual_start,
            WorkOrder.actual_end,
        )
        .where(WorkOrder.organization_id == org_id)
        .where(WorkOrder.asset_id.isnot(None))
        .where(WorkOrder.asset_id.in_(asset_ids))
        .where(WorkOrder.work_type.in_([WorkOrderType.CORRECTIVE, WorkOrderType.EMERGENCY]))
        .where(WorkOrder.status == WorkOrderStatus.COMPLETED)
        .where(WorkOrder.actual_start.isnot(None))
        .where(WorkOrder.actual_end.isnot(None))
        .where(func.date(WorkOrder.actual_end) >= start_date)
        .where(func.date(WorkOrder.actual_end) <= end_date)
        .order_by(WorkOrder.asset_id, WorkOrder.actual_start)
    )

    result = await db.execute(failure_query)
    rows = result.all()

    grouped_events = defaultdict(list)
    for aid, start_ts, end_ts in rows:
        if aid is None:
            continue
        grouped_events[aid].append((start_ts, end_ts))

    asset_metrics = []
    all_repair_times: List[float] = []
    all_intervals: List[float] = []

    for aid, events in grouped_events.items():
        asset = asset_lookup.get(aid)
        if not asset:
            continue

        events.sort(key=lambda e: e[0])
        failure_count = len(events)

        repair_times = []
        time_between = []

        prev_end = None
        for start_ts, end_ts in events:
            if start_ts and end_ts:
                repair_time = (end_ts - start_ts).total_seconds() / 3600
                if repair_time > 0:
                    repair_times.append(repair_time)
                    all_repair_times.append(repair_time)

            if prev_end and start_ts:
                delta = (start_ts - prev_end).total_seconds() / 3600
                if delta > 0:
                    time_between.append(delta)
                    all_intervals.append(delta)
            if end_ts:
                prev_end = end_ts

        sample_size = len(time_between)
        has_enough_failures = failure_count >= max(2, min_failures)

        if not has_enough_failures and not include_single_failures:
            continue

        mtbf = sum(time_between) / sample_size if sample_size else None
        mttr = sum(repair_times) / len(repair_times) if repair_times else None
        availability = 0
        if mtbf and mttr and (mtbf + mttr) > 0:
            availability = round((mtbf / (mtbf + mttr)) * 100, 2)

        asset_metrics.append(
            {
                "asset_id": aid,
                "asset_num": asset.asset_num,
                "asset_name": asset.name,
                "status": asset.status.value if asset.status else None,
                "criticality": asset.criticality.value if asset.criticality else None,
                "failure_count": failure_count,
                "mtbf_hours": round(mtbf, 2) if mtbf is not None else None,
                "mttr_hours": round(mttr, 2) if mttr is not None else None,
                "availability": availability,
                "sample_size": sample_size,
                "last_failure_at": events[-1][1].isoformat() if events[-1][1] else None,
            }
        )

    overall_mttr = sum(all_repair_times) / len(all_repair_times) if all_repair_times else 0
    overall_mtbf = sum(all_intervals) / len(all_intervals) if all_intervals else 0

    asset_metrics.sort(
        key=lambda entry: (
            entry["mtbf_hours"] is None,
            -(entry["failure_count"] or 0),
            -(entry["mtbf_hours"] or 0),
        )
    )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "overall": {
            "total_failures": len(rows),
            "average_mtbf_hours": round(overall_mtbf, 2),
            "average_mttr_hours": round(overall_mttr, 2),
        },
        "by_asset": asset_metrics,
    }


@router.get("/notifications")
async def get_notifications(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    Get system notifications/alerts for the current user.
    Returns critical items that need attention.
    """
    org_id = current_user.organization_id
    today = date.today()
    notifications = []

    # Open work orders status
    open_statuses = [
        WorkOrderStatus.DRAFT,
        WorkOrderStatus.WAITING_APPROVAL,
        WorkOrderStatus.APPROVED,
        WorkOrderStatus.SCHEDULED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.ON_HOLD,
    ]

    # 1. Overdue work orders
    overdue_wos = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.organization_id == org_id)
        .where(WorkOrder.status.in_(open_statuses))
        .where(WorkOrder.due_date < today)
        .order_by(WorkOrder.due_date)
        .limit(10)
    )
    for wo in overdue_wos.scalars():
        days_overdue = (today - wo.due_date).days
        notifications.append({
            "id": f"overdue-wo-{wo.id}",
            "type": "overdue_work_order",
            "severity": "critical" if days_overdue > 7 else "warning",
            "title": f"Overdue Work Order: {wo.wo_number}",
            "message": f"{wo.title} is {days_overdue} days overdue",
            "link": f"/work-orders/{wo.id}",
            "created_at": wo.due_date.isoformat(),
        })

    # 2. Work orders awaiting approval
    pending_approval = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.organization_id == org_id)
        .where(WorkOrder.status == WorkOrderStatus.WAITING_APPROVAL)
        .order_by(WorkOrder.created_at.desc())
        .limit(10)
    )
    for wo in pending_approval.scalars():
        notifications.append({
            "id": f"approval-wo-{wo.id}",
            "type": "pending_approval",
            "severity": "info",
            "title": f"Awaiting Approval: {wo.wo_number}",
            "message": wo.title,
            "link": f"/work-orders/{wo.id}",
            "created_at": wo.created_at.isoformat(),
        })

    # 3. PMs due in next 7 days
    week_ahead = today + timedelta(days=7)
    due_pms = await db.execute(
        select(PreventiveMaintenance)
        .where(PreventiveMaintenance.organization_id == org_id)
        .where(PreventiveMaintenance.is_active == True)
        .where(PreventiveMaintenance.next_due_date.isnot(None))
        .where(PreventiveMaintenance.next_due_date <= week_ahead)
        .order_by(PreventiveMaintenance.next_due_date)
        .limit(10)
    )
    for pm in due_pms.scalars():
        days_until = (pm.next_due_date - today).days if pm.next_due_date else 0
        severity = "critical" if days_until < 0 else ("warning" if days_until <= 2 else "info")
        notifications.append({
            "id": f"pm-due-{pm.id}",
            "type": "pm_due",
            "severity": severity,
            "title": f"PM Due: {pm.pm_number}",
            "message": f"{pm.name} - {'Overdue!' if days_until < 0 else f'Due in {days_until} days'}",
            "link": f"/pm",
            "created_at": pm.next_due_date.isoformat() if pm.next_due_date else today.isoformat(),
        })

    # 4. Low stock alerts
    result = await db.execute(
        select(Part)
        .options(selectinload(Part.stock_levels))
        .where(Part.organization_id == org_id)
        .where(Part.status == "ACTIVE")
    )
    parts = result.scalars().all()
    for part in parts:
        for stock in part.stock_levels:
            if stock.needs_reorder():
                notifications.append({
                    "id": f"low-stock-{part.id}-{stock.storeroom_id}",
                    "type": "low_stock",
                    "severity": "warning" if stock.current_balance > 0 else "critical",
                    "title": f"Low Stock: {part.part_number}",
                    "message": f"{part.name} - Current: {stock.current_balance}, Reorder Point: {stock.reorder_point}",
                    "link": f"/inventory/parts/{part.id}",
                    "created_at": datetime.utcnow().isoformat(),
                })
                break  # Only one notification per part

    # 5. Unassigned work orders
    unassigned = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.organization_id == org_id)
        .where(WorkOrder.status.in_([WorkOrderStatus.APPROVED, WorkOrderStatus.SCHEDULED]))
        .where(WorkOrder.assigned_to_id.is_(None))
        .order_by(WorkOrder.priority.desc(), WorkOrder.due_date)
        .limit(10)
    )
    for wo in unassigned.scalars():
        notifications.append({
            "id": f"unassigned-wo-{wo.id}",
            "type": "unassigned_work_order",
            "severity": "warning",
            "title": f"Unassigned: {wo.wo_number}",
            "message": f"{wo.title} ({wo.priority.value} priority)",
            "link": f"/work-orders/{wo.id}",
            "created_at": wo.created_at.isoformat(),
        })

    # 6. Emergency work orders in progress
    emergency_wos = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.organization_id == org_id)
        .where(WorkOrder.priority == "EMERGENCY")
        .where(WorkOrder.status.in_([WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.ON_HOLD]))
        .order_by(WorkOrder.created_at.desc())
        .limit(5)
    )
    for wo in emergency_wos.scalars():
        notifications.append({
            "id": f"emergency-wo-{wo.id}",
            "type": "emergency_work_order",
            "severity": "critical",
            "title": f"Emergency: {wo.wo_number}",
            "message": f"{wo.title} - Status: {wo.status.value}",
            "link": f"/work-orders/{wo.id}",
            "created_at": wo.created_at.isoformat(),
        })

    # Sort by severity (critical > warning > info) and then by date
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    notifications.sort(key=lambda x: (severity_order.get(x["severity"], 3), x["created_at"]))

    # Count by severity
    counts = {"critical": 0, "warning": 0, "info": 0}
    for n in notifications:
        counts[n["severity"]] = counts.get(n["severity"], 0) + 1

    return {
        "notifications": notifications[:50],  # Limit to 50
        "counts": counts,
        "total": len(notifications),
    }


# Keep both slash/no-slash variants to avoid proxy 404s
@router.get("/dashboard/widgets")
@router.get("/dashboard/widgets/")
async def get_dashboard_widget_data(
    db: DBSession,
    current_user: CurrentUser,
    widget: str = Query(..., description="Widget type to fetch"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None, description="Filter by work order status"),
    priority: Optional[str] = Query(None, description="Filter by work order priority"),
    work_type: Optional[str] = Query(None, description="Filter by work order type"),
    assigned_to: Optional[int] = Query(None, description="Filter by assignee user ID"),
    asset_status: Optional[str] = Query(None, description="Filter by asset status"),
    criticality: Optional[str] = Query(None, description="Filter by asset criticality"),
    storeroom: Optional[int] = Query(None, description="Filter by storeroom ID"),
    craft: Optional[str] = Query(None, description="Filter by labor craft"),
    labor_type: Optional[str] = Query(None, description="Filter by labor type"),
    limit: int = Query(10, ge=1, le=100),
) -> Any:
    """
    Get data for specific dashboard widgets with custom date ranges.
    Supports various widget types for comprehensive dashboard customization.
    """
    org_id = current_user.organization_id

    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    # Helper for date range filter
    def date_filter(column, use_date_func=True):
        if use_date_func:
            return and_(func.date(column) >= start_date, func.date(column) <= end_date)
        return and_(column >= start_date, column <= end_date)

    def apply_work_order_filters(query):
        """Apply common work order filters (status/priority/type/assignee)."""
        if status:
            try:
                query = query.where(WorkOrder.status == WorkOrderStatus(status))
            except ValueError:
                pass
        if priority:
            from app.models.work_order import WorkOrderPriority
            try:
                query = query.where(WorkOrder.priority == WorkOrderPriority(priority))
            except ValueError:
                pass
        if work_type:
            try:
                query = query.where(WorkOrder.work_type == WorkOrderType(work_type))
            except ValueError:
                pass
        if assigned_to:
            query = query.where(WorkOrder.assigned_to_id == assigned_to)
        return query

    # Widget implementations
    if widget == "wo_by_status":
        result = await db.execute(
            apply_work_order_filters(
                select(WorkOrder.status, func.count(WorkOrder.id))
                .where(WorkOrder.organization_id == org_id)
                .where(date_filter(WorkOrder.created_at))
            ).group_by(WorkOrder.status)
        )
        return {"data": {getattr(row[0], 'value', row[0]): row[1] for row in result}}

    elif widget == "wo_by_priority":
        query = apply_work_order_filters(
            select(WorkOrder.priority, func.count(WorkOrder.id))
            .where(WorkOrder.organization_id == org_id)
            .where(date_filter(WorkOrder.created_at))
        ).group_by(WorkOrder.priority)
            
        if status:
            if status == "OPEN":
                query = query.where(WorkOrder.status.in_([
                    WorkOrderStatus.DRAFT, WorkOrderStatus.WAITING_APPROVAL, 
                    WorkOrderStatus.APPROVED, WorkOrderStatus.SCHEDULED, 
                    WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.ON_HOLD
                ]))
            elif status == "CLOSED":
                query = query.where(WorkOrder.status.in_([
                    WorkOrderStatus.COMPLETED, WorkOrderStatus.CLOSED, 
                    WorkOrderStatus.CANCELLED
                ]))
            else:
                # Try to match specific status
                try:
                    s = WorkOrderStatus(status)
                    query = query.where(WorkOrder.status == s)
                except ValueError:
                    pass

        result = await db.execute(query)
        return {"data": {getattr(row[0], 'value', row[0]): row[1] for row in result}}

    elif widget == "wo_by_type":
        query = apply_work_order_filters(
            select(WorkOrder.work_type, func.count(WorkOrder.id))
            .where(WorkOrder.organization_id == org_id)
            .where(date_filter(WorkOrder.created_at))
        ).group_by(WorkOrder.work_type)

        result = await db.execute(query)
        return {"data": {getattr(row[0], 'value', row[0]): row[1] for row in result}}

    elif widget == "wo_created_trend":
        query = select(func.date(WorkOrder.created_at).label("day"), func.count(WorkOrder.id))\
            .where(WorkOrder.organization_id == org_id)\
            .where(date_filter(WorkOrder.created_at))
        if priority:
            from app.models.work_order import WorkOrderPriority
            try:
                query = query.where(WorkOrder.priority == WorkOrderPriority(priority))
            except ValueError:
                pass
        if work_type:
            try:
                query = query.where(WorkOrder.work_type == WorkOrderType(work_type))
            except ValueError:
                pass
        if assigned_to:
            query = query.where(WorkOrder.assigned_to_id == assigned_to)
        result = await db.execute(
            query
            .group_by(func.date(WorkOrder.created_at))
            .order_by(func.date(WorkOrder.created_at))
        )
        return {"data": [{"date": row[0].isoformat(), "count": row[1]} for row in result]}

    elif widget == "wo_completed_trend":
        query = select(func.date(WorkOrder.actual_end).label("day"), func.count(WorkOrder.id))\
            .where(WorkOrder.organization_id == org_id)\
            .where(WorkOrder.status == WorkOrderStatus.COMPLETED)\
            .where(WorkOrder.actual_end.isnot(None))\
            .where(date_filter(WorkOrder.actual_end))
        if priority:
            from app.models.work_order import WorkOrderPriority
            try:
                query = query.where(WorkOrder.priority == WorkOrderPriority(priority))
            except ValueError:
                pass
        if work_type:
            try:
                query = query.where(WorkOrder.work_type == WorkOrderType(work_type))
            except ValueError:
                pass
        if assigned_to:
            query = query.where(WorkOrder.assigned_to_id == assigned_to)
        result = await db.execute(
            query
            .group_by(func.date(WorkOrder.actual_end))
            .order_by(func.date(WorkOrder.actual_end))
        )
        return {"data": [{"date": row[0].isoformat(), "count": row[1]} for row in result]}

    elif widget == "open_wo_by_user":
        open_statuses = [WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.ON_HOLD, WorkOrderStatus.APPROVED, WorkOrderStatus.SCHEDULED]
        result = await db.execute(
            select(User.id, User.first_name, User.last_name, func.count(WorkOrder.id))
            .join(WorkOrder, WorkOrder.assigned_to_id == User.id)
            .where(WorkOrder.organization_id == org_id)
            .where(WorkOrder.status.in_(open_statuses))
            .group_by(User.id, User.first_name, User.last_name)
            .order_by(desc(func.count(WorkOrder.id)))
            .limit(limit)
        )
        return {"data": [{"user_id": row[0], "name": f"{row[1]} {row[2]}", "count": row[3]} for row in result]}

    elif widget == "completed_wo_by_user":
        result = await db.execute(
            select(User.id, User.first_name, User.last_name, func.count(WorkOrder.id))
            .join(WorkOrder, WorkOrder.assigned_to_id == User.id)
            .where(WorkOrder.organization_id == org_id)
            .where(WorkOrder.status == WorkOrderStatus.COMPLETED)
            .where(date_filter(WorkOrder.actual_end))
            .group_by(User.id, User.first_name, User.last_name)
            .order_by(desc(func.count(WorkOrder.id)))
            .limit(limit)
        )
        return {"data": [{"user_id": row[0], "name": f"{row[1]} {row[2]}", "count": row[3]} for row in result]}

    elif widget == "labor_cost_by_user":
        query = select(User.id, User.first_name, User.last_name,
                   func.sum(LaborTransaction.total_cost), func.sum(LaborTransaction.hours))\
            .join(LaborTransaction, LaborTransaction.user_id == User.id)\
            .where(LaborTransaction.organization_id == org_id)\
            .where(date_filter(LaborTransaction.created_at))\
            .group_by(User.id, User.first_name, User.last_name)\
            .order_by(desc(func.sum(LaborTransaction.total_cost)))\
            .limit(limit)
        
        # Apply labor filters
        if craft:
            query = query.where(LaborTransaction.craft == craft)
        if labor_type:
            query = query.where(LaborTransaction.labor_type == labor_type)
            
        result = await db.execute(query)
        return {"data": [{"user_id": row[0], "name": f"{row[1]} {row[2]}", "total_cost": float(row[3] or 0), "total_hours": float(row[4] or 0)} for row in result]}

    elif widget == "material_cost_by_part":
        query = select(Part.id, Part.part_number, Part.name,
                   func.sum(MaterialTransaction.total_cost), func.sum(MaterialTransaction.quantity))\
            .join(MaterialTransaction, MaterialTransaction.part_id == Part.id)\
            .where(MaterialTransaction.organization_id == org_id)\
            .where(date_filter(MaterialTransaction.created_at))\
            .group_by(Part.id, Part.part_number, Part.name)\
            .order_by(desc(func.sum(MaterialTransaction.total_cost)))\
            .limit(limit)
        
        # Apply storeroom filter
        if storeroom:
            query = query.where(MaterialTransaction.storeroom_id == storeroom)
            
        result = await db.execute(query)
        return {"data": [{"part_id": row[0], "part_number": row[1], "name": row[2],
                         "total_cost": float(row[3] or 0), "total_qty": float(row[4] or 0)} for row in result]}

    elif widget == "most_used_parts":
        query = select(Part.id, Part.part_number, Part.name, func.sum(MaterialTransaction.quantity))\
            .join(MaterialTransaction, MaterialTransaction.part_id == Part.id)\
            .where(MaterialTransaction.organization_id == org_id)\
            .where(MaterialTransaction.transaction_type == "ISSUE")\
            .where(date_filter(MaterialTransaction.created_at))\
            .group_by(Part.id, Part.part_number, Part.name)\
            .order_by(desc(func.sum(MaterialTransaction.quantity)))\
            .limit(limit)
        
        # Apply storeroom filter
        if storeroom:
            query = query.where(MaterialTransaction.storeroom_id == storeroom)
            
        result = await db.execute(query)
        return {"data": [{"part_id": row[0], "part_number": row[1], "name": row[2], "quantity": float(row[3] or 0)} for row in result]}

    elif widget == "least_used_parts":
        query = select(Part.id, Part.part_number, Part.name, func.coalesce(func.sum(MaterialTransaction.quantity), 0))\
            .outerjoin(MaterialTransaction, and_(
                MaterialTransaction.part_id == Part.id,
                MaterialTransaction.transaction_type == "ISSUE",
                date_filter(MaterialTransaction.created_at),
                MaterialTransaction.storeroom_id == storeroom if storeroom else True
            ))\
            .where(Part.organization_id == org_id)\
            .where(Part.status == "ACTIVE")\
            .group_by(Part.id, Part.part_number, Part.name)\
            .order_by(func.coalesce(func.sum(MaterialTransaction.quantity), 0))\
            .limit(limit)
            
        result = await db.execute(query)
        return {"data": [{"part_id": row[0], "part_number": row[1], "name": row[2], "quantity": float(row[3] or 0)} for row in result]}

    elif widget == "assets_by_status":
        result = await db.execute(
            select(Asset.status, func.count(Asset.id))
            .where(Asset.organization_id == org_id)
            .where(Asset.is_active == True)
            .group_by(Asset.status)
        )
        return {"data": {getattr(row[0], 'value', row[0]): row[1] for row in result}}

    elif widget == "assets_by_criticality":
        result = await db.execute(
            select(Asset.criticality, func.count(Asset.id))
            .where(Asset.organization_id == org_id)
            .where(Asset.is_active == True)
            .group_by(Asset.criticality)
        )
        return {"data": {getattr(row[0], 'value', row[0]): row[1] for row in result}}

    elif widget == "assets_most_wo":
        query = select(Asset.id, Asset.asset_num, Asset.name, func.count(WorkOrder.id))\
            .join(WorkOrder, WorkOrder.asset_id == Asset.id)\
            .where(Asset.organization_id == org_id)\
            .where(date_filter(WorkOrder.created_at))\
            .group_by(Asset.id, Asset.asset_num, Asset.name)\
            .order_by(desc(func.count(WorkOrder.id)))\
            .limit(limit)
        
        # Apply asset filters
        if asset_status:
            from app.models.asset import AssetStatus
            try:
                s = AssetStatus(asset_status)
                query = query.where(Asset.status == s)
            except ValueError:
                pass
        if criticality:
            from app.models.asset import AssetCriticality
            try:
                c = AssetCriticality(criticality)
                query = query.where(Asset.criticality == c)
            except ValueError:
                pass
                
        result = await db.execute(query)
        return {"data": [{"asset_id": row[0], "asset_num": row[1], "name": row[2], "wo_count": row[3]} for row in result]}

    elif widget == "assets_highest_cost":
        query = select(Asset.id, Asset.asset_num, Asset.name, func.sum(WorkOrder.total_cost))\
            .join(WorkOrder, WorkOrder.asset_id == Asset.id)\
            .where(Asset.organization_id == org_id)\
            .where(date_filter(WorkOrder.created_at))\
            .group_by(Asset.id, Asset.asset_num, Asset.name)\
            .order_by(desc(func.sum(WorkOrder.total_cost)))\
            .limit(limit)
        
        # Apply asset filters
        if asset_status:
            from app.models.asset import AssetStatus
            try:
                s = AssetStatus(asset_status)
                query = query.where(Asset.status == s)
            except ValueError:
                pass
                
        result = await db.execute(query)
        return {"data": [{"asset_id": row[0], "asset_num": row[1], "name": row[2], "total_cost": float(row[3] or 0)} for row in result]}

    elif widget == "cost_trend_labor":
        result = await db.execute(
            select(func.date(LaborTransaction.created_at), func.sum(LaborTransaction.total_cost))
            .where(LaborTransaction.organization_id == org_id)
            .where(date_filter(LaborTransaction.created_at))
            .group_by(func.date(LaborTransaction.created_at))
            .order_by(func.date(LaborTransaction.created_at))
        )
        return {"data": [{"date": row[0].isoformat(), "cost": float(row[1] or 0)} for row in result]}

    elif widget == "cost_trend_material":
        result = await db.execute(
            select(func.date(MaterialTransaction.created_at), func.sum(MaterialTransaction.total_cost))
            .where(MaterialTransaction.organization_id == org_id)
            .where(date_filter(MaterialTransaction.created_at))
            .group_by(func.date(MaterialTransaction.created_at))
            .order_by(func.date(MaterialTransaction.created_at))
        )
        return {"data": [{"date": row[0].isoformat(), "cost": float(row[1] or 0)} for row in result]}

    elif widget == "pm_compliance_rate":
        pm_query = select(WorkOrder)\
            .where(WorkOrder.organization_id == org_id)\
            .where(date_filter(WorkOrder.created_at))
        # Default to preventive, but allow override if a different type is explicitly chosen
        if work_type:
            try:
                pm_query = pm_query.where(WorkOrder.work_type == WorkOrderType(work_type))
            except ValueError:
                pm_query = pm_query.where(WorkOrder.work_type == WorkOrderType.PREVENTIVE)
        else:
            pm_query = pm_query.where(WorkOrder.work_type == WorkOrderType.PREVENTIVE)
        pm_query = apply_work_order_filters(pm_query)

        pm_wos = await db.execute(pm_query)
        wos = pm_wos.scalars().all()
        total = len(wos)
        on_time = sum(1 for wo in wos if wo.status == WorkOrderStatus.COMPLETED and
                     wo.due_date and wo.actual_end and wo.actual_end.date() <= wo.due_date)
        rate = (on_time / total * 100) if total > 0 else 0
        return {"data": {"total": total, "on_time": on_time, "compliance_rate": round(rate, 1)}}

    elif widget == "overdue_wo_count":
        open_statuses = [WorkOrderStatus.DRAFT, WorkOrderStatus.WAITING_APPROVAL, WorkOrderStatus.APPROVED,
                        WorkOrderStatus.SCHEDULED, WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.ON_HOLD]
        count_query = apply_work_order_filters(
            select(func.count())
            .select_from(WorkOrder)
            .where(WorkOrder.organization_id == org_id)
            .where(WorkOrder.status.in_(open_statuses))
            .where(WorkOrder.due_date < date.today())
        )
        count = await db.scalar(count_query)
        return {"data": {"count": count}}

    elif widget == "avg_completion_time":
        result = await db.scalar(
            apply_work_order_filters(
                select(func.avg(
                    func.extract("epoch", WorkOrder.actual_end) - func.extract("epoch", WorkOrder.actual_start)
                ) / 3600)
                .where(WorkOrder.organization_id == org_id)
                .where(WorkOrder.status == WorkOrderStatus.COMPLETED)
                .where(WorkOrder.actual_start.isnot(None))
                .where(WorkOrder.actual_end.isnot(None))
                .where(date_filter(WorkOrder.actual_end))
            )
        )
        return {"data": {"avg_hours": round(float(result or 0), 2)}}

    elif widget == "wo_by_location":
        from app.models.location import Location
        result = await db.execute(
            apply_work_order_filters(
                select(Location.id, Location.name, func.count(WorkOrder.id))
                .join(WorkOrder, WorkOrder.location_id == Location.id)
                .where(WorkOrder.organization_id == org_id)
                .where(date_filter(WorkOrder.created_at))
            )
            .group_by(Location.id, Location.name)
            .order_by(desc(func.count(WorkOrder.id)))
            .limit(limit)
        )
        return {"data": [{"location_id": row[0], "name": row[1], "wo_count": row[2]} for row in result]}

    elif widget == "labor_hours_by_craft":
        result = await db.execute(
            select(LaborTransaction.craft, func.sum(LaborTransaction.hours))
            .where(LaborTransaction.organization_id == org_id)
            .where(LaborTransaction.craft.isnot(None))
            .where(date_filter(LaborTransaction.created_at))
            .group_by(LaborTransaction.craft)
            .order_by(desc(func.sum(LaborTransaction.hours)))
        )
        return {"data": {row[0]: float(row[1] or 0) for row in result}}

    elif widget == "labor_type_breakdown":
        result = await db.execute(
            select(LaborTransaction.labor_type, func.sum(LaborTransaction.hours), func.sum(LaborTransaction.total_cost))
            .where(LaborTransaction.organization_id == org_id)
            .where(date_filter(LaborTransaction.created_at))
            .group_by(LaborTransaction.labor_type)
        )
        return {"data": [{"type": row[0], "hours": float(row[1] or 0), "cost": float(row[2] or 0)} for row in result]}

    elif widget == "inventory_value_by_storeroom":
        from app.models.inventory import Storeroom
        result = await db.execute(
            select(Storeroom.id, Storeroom.code, Storeroom.name,
                   func.sum(StockLevel.current_balance * Part.average_cost))
            .join(StockLevel, StockLevel.storeroom_id == Storeroom.id)
            .join(Part, Part.id == StockLevel.part_id)
            .where(Storeroom.organization_id == org_id)
            .group_by(Storeroom.id, Storeroom.code, Storeroom.name)
        )
        return {"data": [{"storeroom_id": row[0], "code": row[1], "name": row[2], "value": float(row[3] or 0)} for row in result]}

    elif widget == "low_stock_items":
        result = await db.execute(
            select(Part)
            .options(selectinload(Part.stock_levels))
            .where(Part.organization_id == org_id)
            .where(Part.status == "ACTIVE")
        )
        parts = result.scalars().all()
        low_stock = []
        for part in parts:
            for stock in part.stock_levels:
                if stock.needs_reorder():
                    low_stock.append({
                        "part_id": part.id,
                        "part_number": part.part_number,
                        "name": part.name,
                        "current": stock.current_balance,
                        "reorder_point": stock.reorder_point,
                    })
                    break
        return {"data": low_stock[:limit]}

    elif widget == "upcoming_pms":
        week_ahead = date.today() + timedelta(days=14)
        result = await db.execute(
            select(PreventiveMaintenance)
            .where(PreventiveMaintenance.organization_id == org_id)
            .where(PreventiveMaintenance.is_active == True)
            .where(PreventiveMaintenance.next_due_date.isnot(None))
            .where(PreventiveMaintenance.next_due_date <= week_ahead)
            .order_by(PreventiveMaintenance.next_due_date)
            .limit(limit)
        )
        return {"data": [{"pm_id": pm.id, "pm_number": pm.pm_number, "name": pm.name,
                         "next_due": pm.next_due_date.isoformat() if pm.next_due_date else None}
                        for pm in result.scalars()]}

    elif widget == "cost_summary":
        labor = await db.scalar(
            select(func.sum(LaborTransaction.total_cost))
            .where(LaborTransaction.organization_id == org_id)
            .where(date_filter(LaborTransaction.created_at))
        ) or 0
        material = await db.scalar(
            select(func.sum(MaterialTransaction.total_cost))
            .where(MaterialTransaction.organization_id == org_id)
            .where(date_filter(MaterialTransaction.created_at))
        ) or 0
        return {"data": {"labor": float(labor), "material": float(material), "total": float(labor + material)}}

    elif widget == "wo_backlog_age":
        open_statuses = [WorkOrderStatus.APPROVED, WorkOrderStatus.SCHEDULED, WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.ON_HOLD]
        result = await db.execute(
            apply_work_order_filters(
                select(WorkOrder.id, WorkOrder.wo_number, WorkOrder.title, WorkOrder.created_at, WorkOrder.priority)
                .where(WorkOrder.organization_id == org_id)
                .where(WorkOrder.status.in_(open_statuses))
                .where(date_filter(WorkOrder.created_at))
            )
            .order_by(WorkOrder.created_at)
            .limit(limit)
        )
        data = []
        for row in result:
            age_days = (date.today() - row[3].date()).days
            data.append({"wo_id": row[0], "wo_number": row[1], "title": row[2], "age_days": age_days, "priority": row[4].value})
        return {"data": data}

    elif widget == "reactive_vs_preventive":
        reactive_query = apply_work_order_filters(
            select(func.count())
            .select_from(WorkOrder)
            .where(WorkOrder.organization_id == org_id)
            .where(WorkOrder.work_type.in_([WorkOrderType.CORRECTIVE, WorkOrderType.EMERGENCY]))
            .where(date_filter(WorkOrder.created_at))
        )
        preventive_query = apply_work_order_filters(
            select(func.count())
            .select_from(WorkOrder)
            .where(WorkOrder.organization_id == org_id)
            .where(WorkOrder.work_type == WorkOrderType.PREVENTIVE)
            .where(date_filter(WorkOrder.created_at))
        )
        reactive_count = await db.scalar(reactive_query) or 0
        preventive_count = await db.scalar(preventive_query) or 0
        total = reactive_count + preventive_count
        return {"data": {"reactive": reactive_count, "preventive": preventive_count,
                        "reactive_pct": round(reactive_count / total * 100, 1) if total > 0 else 0,
                        "preventive_pct": round(preventive_count / total * 100, 1) if total > 0 else 0}}

    elif widget == "user_workload":
        open_statuses = [WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.APPROVED, WorkOrderStatus.SCHEDULED]
        result = await db.execute(
            select(User.id, User.first_name, User.last_name,
                   func.count(WorkOrder.id),
                   func.sum(WorkOrder.estimated_hours))
            .join(WorkOrder, WorkOrder.assigned_to_id == User.id)
            .where(WorkOrder.organization_id == org_id)
            .where(WorkOrder.status.in_(open_statuses))
            .group_by(User.id, User.first_name, User.last_name)
            .order_by(desc(func.count(WorkOrder.id)))
        )
        return {"data": [{"user_id": row[0], "name": f"{row[1]} {row[2]}",
                         "wo_count": row[3], "est_hours": float(row[4] or 0)} for row in result]}

    elif widget == "recent_completions":
        result = await db.execute(
            select(WorkOrder)
            .where(WorkOrder.organization_id == org_id)
            .where(WorkOrder.status == WorkOrderStatus.COMPLETED)
            .order_by(desc(WorkOrder.actual_end))
            .limit(limit)
        )
        return {"data": [{"wo_id": wo.id, "wo_number": wo.wo_number, "title": wo.title,
                         "completed_at": wo.actual_end.isoformat() if wo.actual_end else None,
                         "total_cost": float(wo.total_cost)} for wo in result.scalars()]}

    elif widget == "downtime_by_asset":
        query = apply_work_order_filters(
            select(Asset.id, Asset.asset_num, Asset.name, func.sum(WorkOrder.downtime_hours))
            .join(WorkOrder, WorkOrder.asset_id == Asset.id)
            .where(Asset.organization_id == org_id)
            .where(WorkOrder.downtime_hours.isnot(None))
            .where(date_filter(WorkOrder.created_at))
        )
        if asset_status:
            from app.models.asset import AssetStatus
            try:
                query = query.where(Asset.status == AssetStatus(asset_status))
            except ValueError:
                pass
        if criticality:
            from app.models.asset import AssetCriticality
            try:
                query = query.where(Asset.criticality == AssetCriticality(criticality))
            except ValueError:
                pass
        result = await db.execute(
            query
            .group_by(Asset.id, Asset.asset_num, Asset.name)
            .order_by(desc(func.sum(WorkOrder.downtime_hours)))
            .limit(limit)
        )
        return {"data": [{"asset_id": row[0], "asset_num": row[1], "name": row[2],
                         "downtime_hours": float(row[3] or 0)} for row in result]}

    elif widget == "failure_codes":
        result = await db.execute(
            select(WorkOrder.failure_code, func.count(WorkOrder.id))
            .where(WorkOrder.organization_id == org_id)
            .where(WorkOrder.failure_code.isnot(None))
            .where(date_filter(WorkOrder.created_at))
            .group_by(WorkOrder.failure_code)
            .order_by(desc(func.count(WorkOrder.id)))
            .limit(limit)
        )
        return {"data": {row[0]: row[1] for row in result}}

    elif widget == "bad_actors":
        query = select(Asset.id, Asset.asset_num, Asset.name, func.sum(WorkOrder.total_cost))\
            .join(WorkOrder, WorkOrder.asset_id == Asset.id)\
            .where(Asset.organization_id == org_id)\
            .where(date_filter(WorkOrder.created_at))\
            .group_by(Asset.id, Asset.asset_num, Asset.name)\
            .order_by(desc(func.sum(WorkOrder.total_cost)))\
            .limit(limit)

        if asset_status:
            from app.models.asset import AssetStatus
            try:
                query = query.where(Asset.status == AssetStatus(asset_status))
            except ValueError:
                pass
        if criticality:
            from app.models.asset import AssetCriticality
            try:
                query = query.where(Asset.criticality == AssetCriticality(criticality))
            except ValueError:
                pass

        result = await db.execute(query)
        return {"data": [{"asset_id": row[0], "asset_num": row[1], "name": row[2],
                         "total_cost": float(row[3] or 0)} for row in result]}

    elif widget == "waiting_for_parts":
        query = apply_work_order_filters(
            select(WorkOrder.id, WorkOrder.wo_number, WorkOrder.title, WorkOrder.created_at, WorkOrder.priority)
            .where(WorkOrder.organization_id == org_id)
            .where(WorkOrder.status == WorkOrderStatus.ON_HOLD)
            .where(date_filter(WorkOrder.created_at))
        ).order_by(WorkOrder.created_at)

        result = await db.execute(query.limit(limit))
        data = []
        for row in result:
            created = row[3].date() if row[3] else date.today()
            age_days = (date.today() - created).days
            data.append({
                "wo_id": row[0],
                "wo_number": row[1],
                "title": row[2],
                "priority": row[4].value if hasattr(row[4], "value") else row[4],
                "age_days": age_days,
            })
        return {"data": data}

    elif widget == "overtime_hours":
        lt_filter = labor_type or "OVERTIME"
        query = select(User.id, User.first_name, User.last_name,
                       func.sum(LaborTransaction.hours), func.sum(LaborTransaction.total_cost))\
            .join(User, User.id == LaborTransaction.user_id)\
            .where(LaborTransaction.organization_id == org_id)\
            .where(LaborTransaction.labor_type == lt_filter)\
            .where(date_filter(LaborTransaction.created_at))\
            .group_by(User.id, User.first_name, User.last_name)\
            .order_by(desc(func.sum(LaborTransaction.hours)))\
            .limit(limit)
        if craft:
            query = query.where(LaborTransaction.craft == craft)
        result = await db.execute(query)
        return {"data": [{"user_id": row[0], "name": f"{row[1]} {row[2]}", "hours": float(row[3] or 0),
                         "cost": float(row[4] or 0)} for row in result]}

    elif widget == "data_integrity_score":
        result = await db.execute(
            apply_work_order_filters(
                select(WorkOrder)
                .where(WorkOrder.organization_id == org_id)
                .where(WorkOrder.status == WorkOrderStatus.COMPLETED)
                .where(WorkOrder.actual_end.isnot(None))
                .where(date_filter(WorkOrder.actual_end))
            )
        )
        work_orders = result.scalars().all()
        total = len(work_orders)
        valid = sum(1 for wo in work_orders if wo.failure_code and wo.failure_cause and wo.failure_remedy)
        score = round((valid / total) * 100, 1) if total else 0
        return {"data": {"score": score, "valid": valid, "total": total}}

    elif widget == "mttr":
        failures_query = apply_work_order_filters(
            select(WorkOrder.actual_start, WorkOrder.actual_end)
            .where(WorkOrder.organization_id == org_id)
            .where(WorkOrder.status == WorkOrderStatus.COMPLETED)
            .where(WorkOrder.actual_start.isnot(None))
            .where(WorkOrder.actual_end.isnot(None))
            .where(date_filter(WorkOrder.actual_end))
        )
        # Default to reactive work only if no explicit type filter provided
        if not work_type:
            failures_query = failures_query.where(WorkOrder.work_type.in_([WorkOrderType.CORRECTIVE, WorkOrderType.EMERGENCY]))

        rows = await db.execute(failures_query)
        repair_times = []
        for row in rows:
            repair_time = (row[1] - row[0]).total_seconds() / 3600
            if repair_time > 0:
                repair_times.append(repair_time)
        avg_hours = round(sum(repair_times) / len(repair_times), 2) if repair_times else 0
        return {"data": {"avg_hours": avg_hours, "sample_size": len(repair_times)}}

    elif widget == "mtbf":
        failure_query = apply_work_order_filters(
            select(WorkOrder.asset_id, WorkOrder.actual_start, WorkOrder.actual_end)
            .where(WorkOrder.organization_id == org_id)
            .where(WorkOrder.status == WorkOrderStatus.COMPLETED)
            .where(WorkOrder.asset_id.isnot(None))
            .where(WorkOrder.actual_start.isnot(None))
            .where(WorkOrder.actual_end.isnot(None))
            .where(date_filter(WorkOrder.actual_end))
        )
        if not work_type:
            failure_query = failure_query.where(WorkOrder.work_type.in_([WorkOrderType.CORRECTIVE, WorkOrderType.EMERGENCY]))

        rows = await db.execute(failure_query.order_by(WorkOrder.asset_id, WorkOrder.actual_start))
        failures_by_asset = {}
        for asset_id, start_time, end_time in rows:
            failures_by_asset.setdefault(asset_id, []).append((start_time, end_time))

        intervals = []
        for events in failures_by_asset.values():
            if len(events) < 2:
                continue
            events.sort(key=lambda x: x[0])
            for i in range(1, len(events)):
                delta = (events[i][0] - events[i - 1][1]).total_seconds() / 3600
                if delta > 0:
                    intervals.append(delta)
        avg_mtbf = round(sum(intervals) / len(intervals), 2) if intervals else 0
        return {"data": {"avg_hours": avg_mtbf, "sample_size": len(intervals)}}

    else:
        return {"error": f"Unknown widget type: {widget}"}
