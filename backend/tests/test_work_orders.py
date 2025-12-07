"""
Test work order management functionality
"""
import pytest
from datetime import datetime, date
from sqlalchemy import select

from app.models.work_order import (
    WorkOrder, WorkOrderStatus, WorkOrderType, WorkOrderPriority,
    WorkOrderTask, LaborTransaction, MaterialTransaction
)
from app.models.asset import Asset
from app.models.inventory import Part, StockLevel, Storeroom


class TestWorkOrderManagement:
    """Test work order lifecycle and operations."""

    @pytest.mark.asyncio
    async def test_create_work_order(self, db_session):
        """Test creating a work order."""
        from app.models.organization import Organization
        from app.models.user import User
        from app.core.security import get_password_hash

        # Create test org and user
        org = Organization(code="TEST", name="Test Org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            organization_id=org.id,
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("password"),
            is_active=True
        )
        db_session.add(user)
        await db_session.flush()

        # Create asset
        asset = Asset(
            organization_id=org.id,
            asset_num="WO-TEST-001",
            name="Test Asset for WO",
            created_by_id=user.id
        )
        db_session.add(asset)
        await db_session.flush()

        # Create work order
        wo = WorkOrder(
            organization_id=org.id,
            wo_number="WO-TEST-001",
            title="Test Work Order",
            description="Test work order for unit tests",
            work_type=WorkOrderType.CORRECTIVE,
            status=WorkOrderStatus.DRAFT,
            priority=WorkOrderPriority.MEDIUM,
            asset_id=asset.id,
            created_by_id=user.id
        )

        db_session.add(wo)
        await db_session.commit()
        await db_session.refresh(wo)

        assert wo.wo_number == "WO-TEST-001"
        assert wo.title == "Test Work Order"
        assert wo.status == WorkOrderStatus.DRAFT
        assert wo.work_type == WorkOrderType.CORRECTIVE
        assert wo.asset_id == asset.id

    @pytest.mark.asyncio
    async def test_work_order_status_transitions(self, db_session):
        """Test work order status workflow transitions."""
        from app.models.organization import Organization
        from app.models.user import User
        from app.core.security import get_password_hash

        # Create test org and user
        org = Organization(code="TEST", name="Test Org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            organization_id=org.id,
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("password"),
            is_active=True
        )
        db_session.add(user)
        await db_session.flush()

        # Create work order
        wo = WorkOrder(
            organization_id=org.id,
            wo_number="WO-STATUS-001",
            title="Status Transition Test",
            work_type=WorkOrderType.CORRECTIVE,
            status=WorkOrderStatus.DRAFT,
            priority=WorkOrderPriority.MEDIUM,
            created_by_id=user.id
        )
        db_session.add(wo)
        await db_session.commit()

        # Test valid transitions
        valid_transitions = {
            WorkOrderStatus.DRAFT: [WorkOrderStatus.WAITING_APPROVAL, WorkOrderStatus.APPROVED, WorkOrderStatus.CANCELLED],
            WorkOrderStatus.WAITING_APPROVAL: [WorkOrderStatus.APPROVED, WorkOrderStatus.CANCELLED],
            WorkOrderStatus.APPROVED: [WorkOrderStatus.SCHEDULED, WorkOrderStatus.CANCELLED],
            WorkOrderStatus.SCHEDULED: [WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED],
            WorkOrderStatus.IN_PROGRESS: [WorkOrderStatus.ON_HOLD, WorkOrderStatus.COMPLETED],
            WorkOrderStatus.ON_HOLD: [WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED],
            WorkOrderStatus.COMPLETED: [WorkOrderStatus.CLOSED],
            WorkOrderStatus.CLOSED: [],
            WorkOrderStatus.CANCELLED: []
        }

        # Verify transition logic (simplified)
        assert WorkOrderStatus.DRAFT in valid_transitions[WorkOrderStatus.DRAFT]
        assert WorkOrderStatus.CANCELLED in valid_transitions[WorkOrderStatus.DRAFT]
        assert WorkOrderStatus.COMPLETED not in valid_transitions[WorkOrderStatus.DRAFT]

    @pytest.mark.asyncio
    async def test_work_order_tasks(self, db_session):
        """Test work order task management."""
        from app.models.organization import Organization
        from app.models.user import User
        from app.core.security import get_password_hash

        # Create test org and user
        org = Organization(code="TEST", name="Test Org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            organization_id=org.id,
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("password"),
            is_active=True
        )
        db_session.add(user)
        await db_session.flush()

        # Create work order
        wo = WorkOrder(
            organization_id=org.id,
            wo_number="WO-TASK-001",
            title="Task Test Work Order",
            work_type=WorkOrderType.CORRECTIVE,
            status=WorkOrderStatus.DRAFT,
            created_by_id=user.id
        )
        db_session.add(wo)
        await db_session.flush()

        # Create tasks
        task1 = WorkOrderTask(
            work_order_id=wo.id,
            sequence=1,
            description="Inspect equipment",
            instructions="Check all connections and belts",
            task_type="TASK",
            estimated_hours=1.0
        )

        task2 = WorkOrderTask(
            work_order_id=wo.id,
            sequence=2,
            description="Replace filter",
            instructions="Use part #F-123",
            task_type="TASK",
            estimated_hours=0.5
        )

        db_session.add(task1)
        db_session.add(task2)
        await db_session.commit()

        # Verify tasks
        result = await db_session.execute(
            select(WorkOrderTask).where(WorkOrderTask.work_order_id == wo.id)
            .order_by(WorkOrderTask.sequence)
        )
        tasks = result.scalars().all()

        assert len(tasks) == 2
        assert tasks[0].sequence == 1
        assert tasks[0].description == "Inspect equipment"
        assert tasks[1].sequence == 2
        assert tasks[1].description == "Replace filter"

    @pytest.mark.asyncio
    async def test_labor_and_material_tracking(self, db_session):
        """Test labor and material transaction tracking."""
        from app.models.organization import Organization
        from app.models.user import User
        from app.models.inventory import Part, Storeroom, StockLevel
        from app.core.security import get_password_hash

        # Create test org and users
        org = Organization(code="TEST", name="Test Org")
        db_session.add(org)
        await db_session.flush()

        admin_user = User(
            organization_id=org.id,
            email="admin@example.com",
            username="admin",
            hashed_password=get_password_hash("password"),
            is_active=True
        )
        tech_user = User(
            organization_id=org.id,
            email="tech@example.com",
            username="tech",
            hashed_password=get_password_hash("password"),
            is_active=True,
            hourly_rate=50.0
        )
        db_session.add(admin_user)
        db_session.add(tech_user)
        await db_session.flush()

        # Create storeroom and part
        storeroom = Storeroom(
            organization_id=org.id,
            name="Main Storeroom",
            code="MAIN",
            is_default=True,
            created_by_id=admin_user.id
        )
        db_session.add(storeroom)
        await db_session.flush()

        part = Part(
            organization_id=org.id,
            part_number="FILTER-123",
            name="Air Filter",
            category="Filters",
            unit_cost=25.0,
            minimum_stock=5,
            current_stock=20,
            created_by_id=admin_user.id
        )
        db_session.add(part)
        await db_session.flush()

        stock_level = StockLevel(
            part_id=part.id,
            storeroom_id=storeroom.id,
            current_balance=20,
            available_quantity=20,
            created_by_id=admin_user.id
        )
        db_session.add(stock_level)
        await db_session.flush()

        # Create work order
        wo = WorkOrder(
            organization_id=org.id,
            wo_number="WO-LABOR-001",
            title="Labor & Material Test",
            work_type=WorkOrderType.CORRECTIVE,
            status=WorkOrderStatus.IN_PROGRESS,
            actual_start=datetime.utcnow(),
            created_by_id=admin_user.id
        )
        db_session.add(wo)
        await db_session.flush()

        # Add labor transaction
        labor = LaborTransaction(
            work_order_id=wo.id,
            user_id=tech_user.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            hours=2.0,
            labor_type="REGULAR",
            hourly_rate=tech_user.hourly_rate,
            total_cost=tech_user.hourly_rate * 2.0,
            craft="Mechanic",
            organization_id=org.id,
            created_by_id=admin_user.id
        )
        db_session.add(labor)

        # Add material transaction
        material = MaterialTransaction(
            work_order_id=wo.id,
            part_id=part.id,
            quantity=1,
            unit_cost=part.unit_cost,
            total_cost=part.unit_cost,
            storeroom_id=storeroom.id,
            transaction_type="ISSUE",
            organization_id=org.id,
            created_by_id=admin_user.id
        )
        db_session.add(material)

        # Update stock
        stock_level.current_balance -= 1
        stock_level.available_quantity -= 1

        await db_session.commit()
        await db_session.refresh(wo)

        # Verify totals
        wo.calculate_totals()
        await db_session.commit()

        assert wo.actual_labor_hours == 2.0
        assert wo.actual_labor_cost == 100.0  # 50 * 2
        assert wo.actual_material_cost == 25.0
        assert wo.total_cost == 125.0

    @pytest.mark.asyncio
    async def test_work_order_completion(self, db_session):
        """Test work order completion workflow."""
        from app.models.organization import Organization
        from app.models.user import User
        from app.core.security import get_password_hash

        # Create test org and user
        org = Organization(code="TEST", name="Test Org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            organization_id=org.id,
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("password"),
            is_active=True
        )
        db_session.add(user)
        await db_session.flush()

        # Create work order
        wo = WorkOrder(
            organization_id=org.id,
            wo_number="WO-COMPLETE-001",
            title="Completion Test",
            work_type=WorkOrderType.CORRECTIVE,
            status=WorkOrderStatus.IN_PROGRESS,
            actual_start=datetime.utcnow(),
            created_by_id=user.id
        )
        db_session.add(wo)
        await db_session.commit()

        # Complete work order
        wo.status = WorkOrderStatus.COMPLETED
        wo.actual_end = datetime.utcnow()
        wo.completed_by_id = user.id
        wo.completion_notes = "Work completed successfully"
        wo.failure_code = "NONE"
        wo.failure_cause = "Preventive maintenance"
        wo.failure_remedy = "Replaced filter"

        await db_session.commit()
        await db_session.refresh(wo)

        assert wo.status == WorkOrderStatus.COMPLETED
        assert wo.actual_end is not None
        assert wo.completed_by_id == user.id
        assert wo.completion_notes == "Work completed successfully"
        assert wo.failure_code == "NONE"
