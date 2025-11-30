"""
Work Order service for business logic.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderStatusHistory


class WorkOrderService:
    """Service class for work order operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def change_status(
        self,
        work_order: WorkOrder,
        new_status: WorkOrderStatus,
        user_id: int,
        reason: Optional[str] = None,
    ) -> WorkOrder:
        """
        Change work order status with validation and side effects.
        """
        old_status = work_order.status

        # Handle side effects based on status change
        if new_status == WorkOrderStatus.IN_PROGRESS:
            if not work_order.actual_start:
                work_order.actual_start = datetime.utcnow()

        elif new_status == WorkOrderStatus.COMPLETED:
            work_order.actual_end = datetime.utcnow()
            work_order.completed_by_id = user_id

        elif new_status == WorkOrderStatus.CANCELLED:
            # Clear scheduled dates
            pass

        work_order.status = new_status
        work_order.updated_by_id = user_id

        # Record status change
        history = WorkOrderStatusHistory(
            work_order_id=work_order.id,
            from_status=old_status.value,
            to_status=new_status.value,
            changed_by_id=user_id,
            reason=reason,
            created_by_id=user_id,
        )
        self.db.add(history)

        await self.db.commit()
        await self.db.refresh(work_order)

        return work_order

    def validate_transition(
        self,
        from_status: WorkOrderStatus,
        to_status: WorkOrderStatus,
    ) -> bool:
        """
        Validate if a status transition is allowed.
        """
        valid_transitions = {
            WorkOrderStatus.DRAFT: [
                WorkOrderStatus.WAITING_APPROVAL,
                WorkOrderStatus.APPROVED,
                WorkOrderStatus.CANCELLED,
            ],
            WorkOrderStatus.WAITING_APPROVAL: [
                WorkOrderStatus.APPROVED,
                WorkOrderStatus.DRAFT,
                WorkOrderStatus.CANCELLED,
            ],
            WorkOrderStatus.APPROVED: [
                WorkOrderStatus.SCHEDULED,
                WorkOrderStatus.IN_PROGRESS,
                WorkOrderStatus.CANCELLED,
            ],
            WorkOrderStatus.SCHEDULED: [
                WorkOrderStatus.IN_PROGRESS,
                WorkOrderStatus.APPROVED,
                WorkOrderStatus.CANCELLED,
            ],
            WorkOrderStatus.IN_PROGRESS: [
                WorkOrderStatus.ON_HOLD,
                WorkOrderStatus.COMPLETED,
            ],
            WorkOrderStatus.ON_HOLD: [
                WorkOrderStatus.IN_PROGRESS,
                WorkOrderStatus.CANCELLED,
            ],
            WorkOrderStatus.COMPLETED: [
                WorkOrderStatus.CLOSED,
                WorkOrderStatus.IN_PROGRESS,  # Reopen
            ],
            WorkOrderStatus.CLOSED: [],
            WorkOrderStatus.CANCELLED: [],
        }

        return to_status in valid_transitions.get(from_status, [])
