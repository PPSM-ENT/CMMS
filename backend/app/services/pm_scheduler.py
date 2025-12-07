"""
PM Scheduling Engine - Background service for generating PM work orders.
"""
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Optional
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.models.preventive_maintenance import (
    PreventiveMaintenance,
    PMTriggerType,
    PMScheduleType,
    PMFrequencyUnit,
    JobPlan,
)
from app.models.work_order import WorkOrder, WorkOrderTask, WorkOrderStatus, WorkOrderType
from app.models.asset import Meter
from app.models.scheduler_control import SchedulerControl
from sqlalchemy import func

logger = logging.getLogger(__name__)


class PMScheduler:
    """
    PM Scheduler service for automatic work order generation.
    """

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker
        self._controls_cache: dict[int, SchedulerControl] = {}

    async def _load_controls(self, db: AsyncSession) -> None:
        result = await db.execute(select(SchedulerControl))
        self._controls_cache = {row.organization_id: row for row in result.scalars().all()}

    async def process_due_pms(self) -> List[int]:
        """
        Process all PMs due for work order generation.
        Returns list of generated work order IDs.
        """
        generated_wos = []

        async with self.session_maker() as db:
            await self._load_controls(db)
            # Get all active PMs due for generation
            today = date.today()

            result = await db.execute(
                select(PreventiveMaintenance)
                .options(
                    selectinload(PreventiveMaintenance.job_plan)
                    .selectinload(JobPlan.tasks)
                )
                .where(PreventiveMaintenance.is_active == True)
                .where(PreventiveMaintenance.next_due_date.isnot(None))
            )
            pms = result.scalars().all()

            for pm in pms:
                control = self._controls_cache.get(pm.organization_id)
                if control and control.pause_pm:
                    continue
                should_generate = await self._should_generate_wo(pm, today, db)

                if should_generate:
                    wo_id = await self._generate_work_order(pm, db)
                    if wo_id:
                        generated_wos.append(wo_id)
                        logger.info(f"Generated WO {wo_id} for PM {pm.pm_number}")

            await db.commit()

        return generated_wos

    async def _should_generate_wo(
        self,
        pm: PreventiveMaintenance,
        today: date,
        db: AsyncSession,
    ) -> bool:
        """
        Determine if a work order should be generated for this PM.
        """
        # Check if within lead time window
        if pm.next_due_date is None:
            return False

        lead_date = pm.next_due_date - timedelta(days=pm.lead_time_days)

        if today < lead_date:
            return False

        # Check seasonal restrictions
        if pm.seasonal_start_month and pm.seasonal_end_month:
            current_month = today.month
            if pm.seasonal_start_month <= pm.seasonal_end_month:
                # Normal range (e.g., April-October)
                if not (pm.seasonal_start_month <= current_month <= pm.seasonal_end_month):
                    return False
            else:
                # Wrapped range (e.g., November-March)
                if not (current_month >= pm.seasonal_start_month or current_month <= pm.seasonal_end_month):
                    return False

        # Check excluded days
        if pm.excluded_days:
            weekday = today.weekday() + 1  # 1=Monday, 7=Sunday
            excluded_weekdays = pm.excluded_days.get("weekdays", [])
            if weekday in excluded_weekdays:
                return False

            excluded_dates = pm.excluded_days.get("dates", [])
            if today.isoformat() in excluded_dates:
                return False

        # Check trigger type
        if pm.trigger_type == PMTriggerType.TIME:
            return True

        elif pm.trigger_type == PMTriggerType.METER:
            return await self._check_meter_trigger(pm, db)

        elif pm.trigger_type == PMTriggerType.TIME_OR_METER:
            # Either condition triggers
            if today >= pm.next_due_date:
                return True
            return await self._check_meter_trigger(pm, db)

        elif pm.trigger_type == PMTriggerType.TIME_AND_METER:
            # Both conditions must be met
            if today < pm.next_due_date:
                return False
            return await self._check_meter_trigger(pm, db)

        elif pm.trigger_type == PMTriggerType.CONDITION:
            return await self._check_condition_trigger(pm, db)

        return False

    async def _check_meter_trigger(
        self,
        pm: PreventiveMaintenance,
        db: AsyncSession,
    ) -> bool:
        """
        Check if meter-based trigger condition is met.
        """
        if not pm.meter_id or not pm.meter_interval:
            return False

        result = await db.execute(
            select(Meter).where(Meter.id == pm.meter_id)
        )
        meter = result.scalar_one_or_none()

        if not meter or meter.last_reading is None:
            return False

        if pm.next_meter_reading is not None:
            return meter.last_reading >= pm.next_meter_reading

        return False

    async def _check_condition_trigger(
        self,
        pm: PreventiveMaintenance,
        db: AsyncSession,
    ) -> bool:
        """
        Check if condition-based trigger is met.
        This would integrate with IoT/sensor data.
        """
        # Placeholder for condition-based maintenance
        # Would need to integrate with sensor readings
        return False

    async def _generate_work_order(
        self,
        pm: PreventiveMaintenance,
        db: AsyncSession,
    ) -> Optional[int]:
        """
        Generate a work order from the PM.
        """
        try:
            # Generate WO number
            wo_count = await db.scalar(
                select(func.count())
                .select_from(WorkOrder)
                .where(WorkOrder.organization_id == pm.organization_id)
            )
            wo_number = f"WO-{wo_count + 1:06d}"

            # Create work order
            work_order = WorkOrder(
                organization_id=pm.organization_id,
                wo_number=wo_number,
                title=f"PM: {pm.name}",
                description=pm.description,
                work_type=WorkOrderType.PREVENTIVE,
                status=WorkOrderStatus.APPROVED,
                priority=pm.priority,
                asset_id=pm.asset_id,
                location_id=pm.location_id,
                assigned_to_id=pm.assigned_to_id,
                assigned_team=pm.assigned_team,
                estimated_hours=pm.estimated_hours,
                pm_id=pm.id,
                due_date=pm.next_due_date,
            )

            db.add(work_order)
            await db.flush()

            # Copy tasks from job plan
            if pm.job_plan:
                for task in pm.job_plan.tasks:
                    wo_task = WorkOrderTask(
                        work_order_id=work_order.id,
                        sequence=task.sequence,
                        description=task.description,
                        instructions=task.instructions,
                        task_type=task.task_type,
                        expected_value=task.expected_value,
                        estimated_hours=task.estimated_hours,
                    )
                    db.add(wo_task)

            # Update PM tracking
            pm.last_wo_date = date.today()
            pm.last_wo_id = work_order.id

            # Calculate next due date
            pm.next_due_date = self._calculate_next_due_date(pm)

            # Update meter tracking if applicable
            if pm.meter_id and pm.meter_interval:
                result = await db.execute(
                    select(Meter).where(Meter.id == pm.meter_id)
                )
                meter = result.scalar_one_or_none()
                if meter and meter.last_reading is not None:
                    pm.last_meter_reading = meter.last_reading
                    pm.next_meter_reading = meter.last_reading + pm.meter_interval

            return work_order.id

        except Exception as e:
            logger.error(f"Error generating WO for PM {pm.pm_number}: {e}")
            return None

    def _calculate_next_due_date(
        self,
        pm: PreventiveMaintenance,
    ) -> Optional[date]:
        """
        Calculate the next due date based on PM configuration.
        """
        if pm.frequency is None or pm.frequency_unit is None:
            return None

        # Determine base date
        if pm.schedule_type == PMScheduleType.FIXED:
            base_date = pm.next_due_date or date.today()
        else:  # FLOATING
            base_date = date.today()

        # Add frequency
        if pm.frequency_unit == PMFrequencyUnit.DAYS:
            return base_date + timedelta(days=pm.frequency)

        elif pm.frequency_unit == PMFrequencyUnit.WEEKS:
            return base_date + timedelta(weeks=pm.frequency)

        elif pm.frequency_unit == PMFrequencyUnit.MONTHS:
            month = base_date.month + pm.frequency
            year = base_date.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            # Handle day overflow
            import calendar
            max_day = calendar.monthrange(year, month)[1]
            day = min(base_date.day, max_day)
            return date(year, month, day)

        elif pm.frequency_unit == PMFrequencyUnit.YEARS:
            try:
                return date(base_date.year + pm.frequency, base_date.month, base_date.day)
            except ValueError:
                # Handle Feb 29 in non-leap years
                return date(base_date.year + pm.frequency, base_date.month, 28)

        return None


async def run_pm_scheduler(session_maker: async_sessionmaker[AsyncSession]):
    """
    Background task to run PM scheduler periodically.
    """
    scheduler = PMScheduler(session_maker)

    while True:
        try:
            logger.info("Running PM scheduler...")
            generated = await scheduler.process_due_pms()
            logger.info(f"PM scheduler completed. Generated {len(generated)} work orders.")
        except Exception as e:
            logger.error(f"PM scheduler error: {e}")

        # Run every hour
        await asyncio.sleep(3600)
