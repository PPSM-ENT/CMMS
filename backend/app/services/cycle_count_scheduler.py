"""
Cycle count scheduler - generates planned cycle counts from recurring plans.
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.inventory import (
    CycleCountPlan,
    CycleCount,
    CycleCountLine,
    CycleCountStatus,
    CycleCountFrequencyUnit,
    StockLevel,
    Part,
    Storeroom,
)
from app.models.scheduler_control import SchedulerControl
from app.models.work_order import MaterialTransaction

logger = logging.getLogger(__name__)


async def _get_controls(db: AsyncSession) -> dict[int, SchedulerControl]:
    result = await db.execute(select(SchedulerControl))
    return {row.organization_id: row for row in result.scalars().all()}


async def _ensure_default_plans(db: AsyncSession) -> None:
    """
    Create a couple of default recurring plans per org (if a default storeroom exists):
    - Weekly transacted inventory (last 7 days)
    - Monthly transacted inventory (last 30 days)
    """
    from app.models.organization import Organization  # lazy import to avoid cycle

    org_rows = await db.execute(select(Organization))
    orgs = org_rows.scalars().all()

    for org in orgs:
        # Find default storeroom
        store_row = await db.execute(
            select(Storeroom).where(Storeroom.organization_id == org.id).where(Storeroom.is_default == True)
        )
        storeroom = store_row.scalar_one_or_none()
        if not storeroom:
            continue

        # Weekly
        weekly_exists = await db.scalar(
            select(func.count())
            .select_from(CycleCountPlan)
            .where(CycleCountPlan.organization_id == org.id)
            .where(CycleCountPlan.template_type == "WEEKLY_TRANSACTED")
        )
        if weekly_exists == 0:
            db.add(
                CycleCountPlan(
                    organization_id=org.id,
                    name="Weekly Transacted Inventory",
                    description="Auto-generated: items issued in last 7 days",
                    storeroom_id=storeroom.id,
                    is_active=True,
                    is_paused=False,
                    frequency_value=7,
                    frequency_unit=CycleCountFrequencyUnit.DAYS,
                    next_run_date=date.today(),
                    used_in_last_days=7,
                    transacted_only=True,
                    include_zero_movement=False,
                    template_type="WEEKLY_TRANSACTED",
                )
            )

        # Monthly
        monthly_exists = await db.scalar(
            select(func.count())
            .select_from(CycleCountPlan)
            .where(CycleCountPlan.organization_id == org.id)
            .where(CycleCountPlan.template_type == "MONTHLY_TRANSACTED")
        )
        if monthly_exists == 0:
            db.add(
                CycleCountPlan(
                    organization_id=org.id,
                    name="Monthly Transacted Inventory",
                    description="Auto-generated: items issued in last 30 days",
                    storeroom_id=storeroom.id,
                    is_active=True,
                    is_paused=False,
                    frequency_value=1,
                    frequency_unit=CycleCountFrequencyUnit.MONTHS,
                    next_run_date=date.today(),
                    used_in_last_days=30,
                    transacted_only=True,
                    include_zero_movement=False,
                    template_type="MONTHLY_TRANSACTED",
                )
            )


def _advance_date(current: date, value: int, unit: CycleCountFrequencyUnit) -> date:
    if unit == CycleCountFrequencyUnit.DAYS:
        return current + timedelta(days=value)
    if unit == CycleCountFrequencyUnit.WEEKS:
        return current + timedelta(weeks=value)
    if unit == CycleCountFrequencyUnit.MONTHS:
        month = current.month + value
        year = current.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        import calendar
        max_day = calendar.monthrange(year, month)[1]
        day = min(current.day, max_day)
        return date(year, month, day)
    return current


async def _select_stock_for_plan(db: AsyncSession, plan: CycleCountPlan) -> List[tuple[StockLevel, Part]]:
    query = (
        select(StockLevel, Part)
        .join(Part, StockLevel.part_id == Part.id)
        .where(Part.organization_id == plan.organization_id)
    )
    if plan.storeroom_id:
        query = query.where(StockLevel.storeroom_id == plan.storeroom_id)

    if plan.bin_prefix:
        query = query.where(StockLevel.bin_location.ilike(f"{plan.bin_prefix}%"))

    if plan.category_ids:
        query = query.where(Part.category_id.in_(plan.category_ids))

    if plan.part_type_filter:
        query = query.where(Part.part_type == plan.part_type_filter)

    if plan.used_in_last_days or plan.usage_start_date or plan.usage_end_date or plan.transacted_only:
        usage_query = select(MaterialTransaction.part_id).where(MaterialTransaction.organization_id == plan.organization_id)
        if plan.storeroom_id:
            usage_query = usage_query.where(MaterialTransaction.storeroom_id == plan.storeroom_id)
        if plan.used_in_last_days:
            start_dt = datetime.utcnow() - timedelta(days=plan.used_in_last_days)
            usage_query = usage_query.where(MaterialTransaction.created_at >= start_dt)
        if plan.usage_start_date:
            usage_query = usage_query.where(func.date(MaterialTransaction.created_at) >= plan.usage_start_date)
        if plan.usage_end_date:
            usage_query = usage_query.where(func.date(MaterialTransaction.created_at) <= plan.usage_end_date)
        if plan.transacted_only:
            usage_query = usage_query.where(MaterialTransaction.transaction_type == "ISSUE")
        usage_query = usage_query.distinct()
        query = query.where(StockLevel.part_id.in_(usage_query))
    elif not plan.include_zero_movement:
        query = query.where(
            (StockLevel.last_issue_date.isnot(None)) | (StockLevel.last_receipt_date.isnot(None))
        )

    if plan.line_limit:
        query = query.limit(plan.line_limit)

    result = await db.execute(query)
    return result.all()


async def _create_cycle_count_from_plan(db: AsyncSession, plan: CycleCountPlan) -> Optional[int]:
    stock_rows = await _select_stock_for_plan(db, plan)
    if not stock_rows:
        return None

    count_name = f"{plan.name} - {date.today().isoformat()}"

    cycle_count = CycleCount(
        organization_id=plan.organization_id,
        name=count_name,
        description=plan.description,
        status=CycleCountStatus.PLANNED,
        storeroom_id=plan.storeroom_id or (stock_rows[0][0].storeroom_id if stock_rows else None),
        scheduled_date=date.today(),
        bin_prefix=plan.bin_prefix,
        category_ids=plan.category_ids,
        part_type_filter=plan.part_type_filter,
        used_in_last_days=plan.used_in_last_days,
        usage_start_date=plan.usage_start_date,
        usage_end_date=plan.usage_end_date,
        include_zero_movement=plan.include_zero_movement,
        transacted_only=plan.transacted_only,
        line_limit=plan.line_limit,
        total_lines=len(stock_rows),
    )
    db.add(cycle_count)
    await db.flush()

    for stock, part in stock_rows:
        db.add(
            CycleCountLine(
                organization_id=plan.organization_id,
                cycle_count_id=cycle_count.id,
                part_id=part.id,
                stock_level_id=stock.id,
                expected_quantity=stock.current_balance,
                bin_location=stock.bin_location,
                needs_recount=False,
                part_number=part.part_number,
                part_name=part.name,
                part_type=part.part_type,
                part_category_id=part.category_id,
                last_issue_date=stock.last_issue_date,
                last_receipt_date=stock.last_receipt_date,
            )
        )

    plan.last_run_at = datetime.utcnow()
    plan.next_run_date = _advance_date(plan.next_run_date or date.today(), plan.frequency_value, plan.frequency_unit)

    await db.flush()
    return cycle_count.id


class CycleCountScheduler:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker

    async def process_due_plans(self) -> List[int]:
        generated: List[int] = []
        async with self.session_maker() as db:
            await _ensure_default_plans(db)
            await db.flush()

            controls = await _get_controls(db)
            today = date.today()

            result = await db.execute(
                select(CycleCountPlan)
                .where(CycleCountPlan.is_active == True)
                .where(CycleCountPlan.next_run_date.isnot(None))
                .where(CycleCountPlan.next_run_date <= today)
            )
            plans = result.scalars().all()

            for plan in plans:
                control = controls.get(plan.organization_id)
                if control and control.pause_cycle_counts:
                    continue
                if plan.is_paused:
                    continue

                try:
                    cc_id = await _create_cycle_count_from_plan(db, plan)
                    if cc_id:
                        generated.append(cc_id)
                        logger.info("Generated cycle count %s from plan %s", cc_id, plan.id)
                except Exception as exc:
                    logger.error("Failed to create cycle count from plan %s: %s", plan.id, exc)

            await db.commit()

        return generated


async def run_cycle_count_scheduler(session_maker: async_sessionmaker[AsyncSession]):
    scheduler = CycleCountScheduler(session_maker)
    while True:
        try:
            logger.info("Running cycle count scheduler...")
            generated = await scheduler.process_due_plans()
            logger.info("Cycle count scheduler completed. Generated %d counts.", len(generated))
        except Exception as exc:
            logger.error("Cycle count scheduler error: %s", exc)
        await asyncio.sleep(3600)
