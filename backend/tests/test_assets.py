"""
Test asset management functionality
"""
import pytest
from sqlalchemy import select

from app.models.asset import Asset, AssetStatus, AssetCriticality, Meter, MeterReading
from app.schemas.asset import AssetCreate, MeterCreate


class TestAssetManagement:
    """Test asset CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_asset(self, db_session, test_settings):
        """Test creating a new asset."""
        from app.api.v1.endpoints.assets import create_asset
        from app.core.security import get_password_hash
        from app.models.user import User
        from app.models.organization import Organization

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
        asset_data = AssetCreate(
            asset_num="TEST-001",
            name="Test Asset",
            description="Test asset for unit tests",
            category="Test Equipment",
            status=AssetStatus.OPERATING,
            criticality=AssetCriticality.MEDIUM
        )

        # Mock current user (simplified for testing)
        class MockCurrentUser:
            def __init__(self, user):
                self.id = user.id
                self.organization_id = user.organization_id

        current_user = MockCurrentUser(user)

        # This would normally go through the API endpoint
        # For now, test the model creation directly
        asset = Asset(
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
            **asset_data.model_dump(exclude={"specifications"})
        )

        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)

        assert asset.asset_num == "TEST-001"
        assert asset.name == "Test Asset"
        assert asset.status == AssetStatus.OPERATING
        assert asset.criticality == AssetCriticality.MEDIUM
        assert asset.organization_id == org.id

    @pytest.mark.asyncio
    async def test_asset_hierarchy(self, db_session):
        """Test asset hierarchical relationships."""
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

        # Create parent asset
        parent = Asset(
            organization_id=org.id,
            asset_num="PARENT-001",
            name="Parent Asset",
            created_by_id=user.id
        )
        db_session.add(parent)
        await db_session.flush()

        # Create child asset
        child = Asset(
            organization_id=org.id,
            asset_num="CHILD-001",
            name="Child Asset",
            parent_id=parent.id,
            created_by_id=user.id
        )
        child.update_hierarchy()
        db_session.add(child)
        await db_session.commit()

        assert child.parent_id == parent.id
        assert child.hierarchy_level == 1
        assert child.hierarchy_path == f"{parent.id}/{child.id}"

    @pytest.mark.asyncio
    async def test_meter_readings(self, db_session):
        """Test meter reading functionality."""
        from app.models.organization import Organization
        from app.models.user import User
        from app.core.security import get_password_hash
        from datetime import datetime

        # Create test org, user, and asset
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

        asset = Asset(
            organization_id=org.id,
            asset_num="TEST-001",
            name="Test Asset",
            created_by_id=user.id
        )
        db_session.add(asset)
        await db_session.flush()

        # Create meter
        meter = Meter(
            organization_id=org.id,
            asset_id=asset.id,
            name="Runtime Hours",
            code="RUNTIME",
            meter_type="CONTINUOUS",
            unit_of_measure="hours",
            created_by_id=user.id
        )
        db_session.add(meter)
        await db_session.flush()

        # Create meter readings
        reading1 = MeterReading(
            meter_id=meter.id,
            reading_value=100.0,
            reading_date=datetime.utcnow(),
            source="MANUAL"
        )

        reading2 = MeterReading(
            meter_id=meter.id,
            reading_value=150.0,
            reading_date=datetime.utcnow(),
            source="MANUAL"
        )

        db_session.add(reading1)
        db_session.add(reading2)

        # Update meter last reading
        meter.last_reading = 150.0
        meter.last_reading_date = reading2.reading_date

        await db_session.commit()

        # Verify readings
        result = await db_session.execute(
            select(MeterReading).where(MeterReading.meter_id == meter.id)
        )
        readings = result.scalars().all()

        assert len(readings) == 2
        assert meter.last_reading == 150.0
        assert readings[1].delta == 50.0  # 150 - 100

    @pytest.mark.asyncio
    async def test_asset_barcode_lookup(self, db_session):
        """Test asset barcode lookup functionality."""
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

        # Create asset with barcode
        asset = Asset(
            organization_id=org.id,
            asset_num="BARCODE-001",
            name="Barcode Asset",
            barcode="123456789",
            created_by_id=user.id
        )
        db_session.add(asset)
        await db_session.commit()

        # Test barcode lookup
        result = await db_session.execute(
            select(Asset).where(
                Asset.organization_id == org.id,
                Asset.barcode == "123456789"
            )
        )
        found_asset = result.scalar_one_or_none()

        assert found_asset is not None
        assert found_asset.asset_num == "BARCODE-001"
        assert found_asset.barcode == "123456789"
