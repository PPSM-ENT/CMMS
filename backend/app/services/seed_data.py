"""
Seed data for initial setup and demo.
"""
import asyncio
import random
from datetime import datetime, date, timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User, Role, Permission
from app.models.location import Location
from app.models.asset import Asset, Meter, AssetStatus, AssetCriticality, MeterType
from app.models.inventory import Part, Storeroom, StockLevel, Vendor, PartCategory
from app.models.preventive_maintenance import PreventiveMaintenance, JobPlan, JobPlanTask, PMTriggerType, PMFrequencyUnit
from app.models.work_order import (
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderType,
    LaborTransaction,
    MaterialTransaction,
    WorkOrderStatusHistory,
)


async def seed_permissions(db: AsyncSession) -> List[Permission]:
    """Create default permissions."""
    permissions_data = [
        # Assets
        ("assets.read", "View Assets", "assets"),
        ("assets.write", "Create/Edit Assets", "assets"),
        ("assets.delete", "Delete Assets", "assets"),
        # Work Orders
        ("work_orders.read", "View Work Orders", "work_orders"),
        ("work_orders.write", "Create/Edit Work Orders", "work_orders"),
        ("work_orders.approve", "Approve Work Orders", "work_orders"),
        ("work_orders.close", "Close Work Orders", "work_orders"),
        # PM
        ("pm.read", "View PM Schedules", "pm"),
        ("pm.write", "Create/Edit PM Schedules", "pm"),
        # Inventory
        ("inventory.read", "View Inventory", "inventory"),
        ("inventory.write", "Manage Inventory", "inventory"),
        ("inventory.adjust", "Adjust Stock", "inventory"),
        # Purchase Orders
        ("po.read", "View Purchase Orders", "purchase_orders"),
        ("po.write", "Create/Edit POs", "purchase_orders"),
        ("po.approve", "Approve POs", "purchase_orders"),
        # Reports
        ("reports.read", "View Reports", "reports"),
        # Admin
        ("admin.users", "Manage Users", "admin"),
        ("admin.settings", "Manage Settings", "admin"),
    ]

    permissions = []
    for code, name, category in permissions_data:
        result = await db.execute(select(Permission).where(Permission.code == code))
        perm = result.scalar_one_or_none()
        if not perm:
            perm = Permission(code=code, name=name, category=category)
            db.add(perm)
        permissions.append(perm)

    await db.flush()
    return permissions


async def seed_demo_data(db: AsyncSession):
    """Create demo organization with sample data."""
    random.seed(42)

    # Check if demo org exists
    result = await db.execute(select(Organization).where(Organization.code == "DEMO"))
    if result.scalar_one_or_none():
        print("Demo data already exists")
        return

    # Create permissions
    permissions = await seed_permissions(db)

    # Create organization
    org = Organization(
        code="DEMO",
        name="Demo Manufacturing Co.",
        description="Demo organization for testing",
        timezone="America/New_York",
        currency="USD",
    )
    db.add(org)
    await db.flush()

    # Create admin role with all permissions
    admin_role = Role(
        organization_id=org.id,
        code="ADMIN",
        name="Administrator",
        description="Full system access",
        is_system=True,
    )
    admin_role.permissions = permissions
    db.add(admin_role)

    # Create technician role
    tech_role = Role(
        organization_id=org.id,
        code="TECH",
        name="Technician",
        description="Maintenance technician",
        is_system=True,
    )
    tech_perms = [p for p in permissions if p.category in ["assets", "work_orders", "inventory", "pm"]]
    tech_role.permissions = tech_perms
    db.add(tech_role)

    await db.flush()

    # Create admin user
    admin_user = User(
        organization_id=org.id,
        email="admin@demo.com",
        username="admin",
        hashed_password=get_password_hash("admin123"),
        first_name="System",
        last_name="Administrator",
        is_superuser=True,
        is_active=True,
        email_verified=True,
    )
    db.add(admin_user)

    # Create technician user
    tech_user = User(
        organization_id=org.id,
        email="tech@demo.com",
        username="technician",
        hashed_password=get_password_hash("tech123"),
        first_name="John",
        last_name="Technician",
        job_title="Maintenance Technician",
        hourly_rate=45.00,
        is_active=True,
        email_verified=True,
    )
    db.add(tech_user)
    await db.flush()
    technician_team = [tech_user]

    extra_tech_profiles = [
        ("alex.mason@demo.com", "tech_alex", "Alex", "Mason", "Electrical Technician", 44.0),
        ("maria.lopez@demo.com", "tech_maria", "Maria", "Lopez", "Reliability Engineer", 48.0),
        ("li.chen@demo.com", "tech_li", "Li", "Chen", "Packaging Technician", 41.0),
        ("sam.patel@demo.com", "tech_sam", "Sam", "Patel", "Controls Specialist", 50.0),
        ("nina.ramirez@demo.com", "tech_nina", "Nina", "Ramirez", "Utilities Technician", 46.0),
    ]
    for email, username, first, last, job_title, rate in extra_tech_profiles:
        extra_user = User(
            organization_id=org.id,
            email=email,
            username=username,
            hashed_password=get_password_hash("tech123"),
            first_name=first,
            last_name=last,
            job_title=job_title,
            hourly_rate=rate,
            is_active=True,
            email_verified=True,
        )
        db.add(extra_user)
        technician_team.append(extra_user)
    await db.flush()

    # Create locations
    plant = Location(
        organization_id=org.id,
        code="PLANT-A",
        name="Plant A - Main Facility",
        location_type="OPERATING",
        created_by_id=admin_user.id,
    )
    plant.update_hierarchy()
    db.add(plant)
    await db.flush()

    prod_area = Location(
        organization_id=org.id,
        code="PROD-1",
        name="Production Area 1",
        location_type="OPERATING",
        parent_id=plant.id,
        created_by_id=admin_user.id,
    )
    prod_area.parent = plant
    prod_area.update_hierarchy()
    db.add(prod_area)

    maint_shop = Location(
        organization_id=org.id,
        code="MAINT",
        name="Maintenance Shop",
        location_type="OPERATING",
        parent_id=plant.id,
        created_by_id=admin_user.id,
    )
    maint_shop.parent = plant
    maint_shop.update_hierarchy()
    db.add(maint_shop)
    await db.flush()

    utilities_loc = Location(
        organization_id=org.id,
        code="UTIL",
        name="Utilities Room",
        location_type="OPERATING",
        parent_id=plant.id,
        created_by_id=admin_user.id,
    )
    utilities_loc.parent = plant
    utilities_loc.update_hierarchy()
    db.add(utilities_loc)

    line_locations: List[Location] = []
    for line_index in range(1, 6):
        line_loc = Location(
            organization_id=org.id,
            code=f"LINE-{line_index}",
            name=f"Production Line {line_index}",
            location_type="OPERATING",
            parent_id=prod_area.id,
            created_by_id=admin_user.id,
        )
        line_loc.parent = prod_area
        line_loc.update_hierarchy()
        db.add(line_loc)
        line_locations.append(line_loc)
    await db.flush()

    # Create storeroom
    storeroom = Storeroom(
        organization_id=org.id,
        code="STORE-1",
        name="Main Storeroom",
        location_id=maint_shop.id,
        is_default=True,
        created_by_id=admin_user.id,
    )
    db.add(storeroom)
    await db.flush()

    # Create vendor
    vendor = Vendor(
        organization_id=org.id,
        code="VENDOR-1",
        name="Industrial Supply Co.",
        contact_name="Sales Team",
        email="sales@industrial-supply.com",
        phone="555-0100",
        payment_terms="Net 30",
        lead_time_days=5,
        is_active=True,
        is_approved=True,
        created_by_id=admin_user.id,
    )
    db.add(vendor)
    await db.flush()

    # Create part categories
    cat_bearings = PartCategory(
        organization_id=org.id,
        code="BEARINGS",
        name="Bearings",
        created_by_id=admin_user.id,
    )
    db.add(cat_bearings)

    cat_filters = PartCategory(
        organization_id=org.id,
        code="FILTERS",
        name="Filters",
        created_by_id=admin_user.id,
    )
    db.add(cat_filters)
    await db.flush()

    # Create parts
    part1 = Part(
        organization_id=org.id,
        part_number="BRG-6205",
        name="Ball Bearing 6205",
        description="Standard ball bearing 25x52x15mm",
        category_id=cat_bearings.id,
        uom="EA",
        unit_cost=15.50,
        average_cost=15.50,
        last_cost=15.50,
        primary_vendor_id=vendor.id,
        created_by_id=admin_user.id,
    )
    db.add(part1)

    part2 = Part(
        organization_id=org.id,
        part_number="FLT-OIL-01",
        name="Oil Filter",
        description="Standard oil filter for compressors",
        category_id=cat_filters.id,
        uom="EA",
        unit_cost=8.75,
        average_cost=8.75,
        last_cost=8.75,
        primary_vendor_id=vendor.id,
        created_by_id=admin_user.id,
    )
    db.add(part2)

    part3 = Part(
        organization_id=org.id,
        part_number="LUB-GREASE",
        name="Lithium Grease",
        description="Multi-purpose lithium grease",
        uom="TUBE",
        unit_cost=5.25,
        average_cost=5.25,
        last_cost=5.25,
        primary_vendor_id=vendor.id,
        created_by_id=admin_user.id,
    )
    db.add(part3)
    await db.flush()

    # Create stock levels
    for part in [part1, part2, part3]:
        stock = StockLevel(
            part_id=part.id,
            storeroom_id=storeroom.id,
            current_balance=25,
            available_quantity=25,
            reorder_point=10,
            reorder_quantity=20,
            bin_location="A-1-1",
            created_by_id=admin_user.id,
        )
        db.add(stock)

    # Create assets for production lines (25 total across the facility)
    line_asset_templates = [
        {
            "suffix": "FILLER",
            "name": "Filler",
            "category": "Filling",
            "asset_type": "Rotary Filler",
            "manufacturer": "Krones",
            "model": "Modulfill",
            "criticality": AssetCriticality.CRITICAL,
            "base_price": 350000.0,
        },
        {
            "suffix": "CAPPER",
            "name": "Capper",
            "category": "Capping",
            "asset_type": "Rotary Capper",
            "manufacturer": "KHS",
            "model": "Innofill",
            "criticality": AssetCriticality.HIGH,
            "base_price": 210000.0,
        },
        {
            "suffix": "LABELER",
            "name": "Labeler",
            "category": "Labeling",
            "asset_type": "Pressure Sensitive Labeler",
            "manufacturer": "P.E. Labellers",
            "model": "Modular SL",
            "criticality": AssetCriticality.MEDIUM,
            "base_price": 185000.0,
        },
        {
            "suffix": "PACKER",
            "name": "Case Packer",
            "category": "Packaging",
            "asset_type": "Wrap Around Packer",
            "manufacturer": "Sidel",
            "model": "Cermex",
            "criticality": AssetCriticality.HIGH,
            "base_price": 240000.0,
        },
    ]

    assets: List[Asset] = []
    purchase_start = date.today() - timedelta(days=6 * 365)
    for idx, line_loc in enumerate(line_locations, start=1):
        for template in line_asset_templates:
            age_offset = random.randint(120, 1800)
            asset = Asset(
                organization_id=org.id,
                asset_num=f"{line_loc.code}-{template['suffix']}",
                name=f"{line_loc.name} {template['name']}",
                description=f"{template['name']} serving {line_loc.name}",
                location_id=line_loc.id,
                category=template["category"],
                asset_type=template["asset_type"],
                manufacturer=template["manufacturer"],
                model=f"{template['model']} L{idx}",
                status=AssetStatus.OPERATING,
                criticality=template["criticality"],
                purchase_date=purchase_start + timedelta(days=age_offset),
                purchase_price=template["base_price"] + random.randint(-15000, 15000),
                install_date=purchase_start + timedelta(days=age_offset + 30),
                created_by_id=admin_user.id,
            )
            asset.update_hierarchy()
            db.add(asset)
            assets.append(asset)

    support_assets_data = [
        {
            "asset_num": "COMP-001",
            "name": "Plant Air Compressor",
            "description": "Atlas Copco rotary screw compressor feeding all lines",
            "location": utilities_loc,
            "category": "Utilities",
            "asset_type": "Rotary Screw Compressor",
            "manufacturer": "Atlas Copco",
            "model": "GA55+",
            "criticality": AssetCriticality.HIGH,
            "purchase_price": 52000.0,
        },
        {
            "asset_num": "PUMP-001",
            "name": "Cooling Water Pump",
            "description": "Primary cooling water supply pump",
            "location": utilities_loc,
            "category": "Utilities",
            "asset_type": "Centrifugal Pump",
            "manufacturer": "Grundfos",
            "model": "CR 45-5",
            "criticality": AssetCriticality.CRITICAL,
            "purchase_price": 18500.0,
        },
        {
            "asset_num": "CONV-MAIN",
            "name": "Main Conveyor Spine",
            "description": "Transfers product between lines",
            "location": prod_area,
            "category": "Material Handling",
            "asset_type": "Belt Conveyor",
            "manufacturer": "Dorner",
            "model": "3200 Series",
            "criticality": AssetCriticality.MEDIUM,
            "purchase_price": 90000.0,
        },
        {
            "asset_num": "PAST-001",
            "name": "Tunnel Pasteurizer",
            "description": "Tunnel pasteurizer for finished goods",
            "location": prod_area,
            "category": "Thermal Processing",
            "asset_type": "Tunnel Pasteurizer",
            "manufacturer": "Krones",
            "model": "VarioFlash",
            "criticality": AssetCriticality.HIGH,
            "purchase_price": 410000.0,
        },
        {
            "asset_num": "PALLET-001",
            "name": "Robotic Palletizer",
            "description": "End-of-line robotic palletizer",
            "location": prod_area,
            "category": "Material Handling",
            "asset_type": "Robotic Palletizer",
            "manufacturer": "Fanuc",
            "model": "M-410iC",
            "criticality": AssetCriticality.HIGH,
            "purchase_price": 275000.0,
        },
    ]

    for data in support_assets_data:
        asset = Asset(
            organization_id=org.id,
            asset_num=data["asset_num"],
            name=data["name"],
            description=data["description"],
            location_id=data["location"].id,
            category=data["category"],
            asset_type=data["asset_type"],
            manufacturer=data["manufacturer"],
            model=data["model"],
            status=AssetStatus.OPERATING,
            criticality=data["criticality"],
            purchase_date=date.today() - timedelta(days=random.randint(365, 2000)),
            purchase_price=data["purchase_price"],
            install_date=date.today() - timedelta(days=random.randint(200, 400)),
            created_by_id=admin_user.id,
        )
        asset.update_hierarchy()
        db.add(asset)
        assets.append(asset)
    await db.flush()

    asset_lookup = {asset.asset_num: asset for asset in assets}
    compressor = asset_lookup["COMP-001"]
    pump = asset_lookup["PUMP-001"]

    # Create meters
    comp_runtime = Meter(
        organization_id=org.id,
        asset_id=compressor.id,
        code="RUNTIME",
        name="Runtime Hours",
        meter_type=MeterType.CONTINUOUS,
        unit_of_measure="hours",
        last_reading=4520,
        last_reading_date=datetime.now(),
        created_by_id=admin_user.id,
    )
    db.add(comp_runtime)

    pump_runtime = Meter(
        organization_id=org.id,
        asset_id=pump.id,
        code="RUNTIME",
        name="Runtime Hours",
        meter_type=MeterType.CONTINUOUS,
        unit_of_measure="hours",
        last_reading=8750,
        last_reading_date=datetime.now(),
        created_by_id=admin_user.id,
    )
    db.add(pump_runtime)
    await db.flush()

    # Create job plan
    oil_change_jp = JobPlan(
        organization_id=org.id,
        code="JP-OIL-CHANGE",
        name="Compressor Oil Change",
        description="Standard oil change procedure for rotary screw compressors",
        estimated_hours=2.0,
        category="Lubrication",
        required_craft="Mechanic",
        safety_requirements="Lock out/tag out required. Wear safety glasses.",
        lockout_required=True,
        created_by_id=admin_user.id,
    )
    db.add(oil_change_jp)
    await db.flush()

    # Job plan tasks
    tasks = [
        (1, "Shut down compressor and relieve system pressure"),
        (2, "Apply LOTO procedure"),
        (3, "Drain old oil into approved container"),
        (4, "Replace oil filter"),
        (5, "Add new compressor oil to proper level"),
        (6, "Remove LOTO and start compressor"),
        (7, "Check for leaks and proper oil level"),
        (8, "Record oil type and quantity used"),
    ]
    for seq, desc in tasks:
        task = JobPlanTask(
            job_plan_id=oil_change_jp.id,
            sequence=seq,
            description=desc,
            task_type="TASK",
            created_by_id=admin_user.id,
        )
        db.add(task)

    # Create PMs
    comp_oil_pm = PreventiveMaintenance(
        organization_id=org.id,
        pm_number="PM-0001",
        name="Compressor Oil Change",
        description="Quarterly oil change for air compressor",
        asset_id=compressor.id,
        job_plan_id=oil_change_jp.id,
        trigger_type=PMTriggerType.TIME,
        frequency=90,
        frequency_unit=PMFrequencyUnit.DAYS,
        next_due_date=date.today() + timedelta(days=15),
        lead_time_days=7,
        assigned_to_id=tech_user.id,
        priority="MEDIUM",
        estimated_hours=2.0,
        is_active=True,
        created_by_id=admin_user.id,
    )
    db.add(comp_oil_pm)

    pump_inspect_pm = PreventiveMaintenance(
        organization_id=org.id,
        pm_number="PM-0002",
        name="Pump Monthly Inspection",
        description="Monthly inspection of cooling water pump",
        asset_id=pump.id,
        trigger_type=PMTriggerType.TIME,
        frequency=30,
        frequency_unit=PMFrequencyUnit.DAYS,
        next_due_date=date.today() + timedelta(days=5),
        lead_time_days=3,
        assigned_to_id=tech_user.id,
        priority="MEDIUM",
        estimated_hours=1.0,
        is_active=True,
        created_by_id=admin_user.id,
    )
    db.add(pump_inspect_pm)

    # Generate two years of historical work orders across all assets
    parts = [part1, part2, part3]
    today = date.today()
    history_start = today - timedelta(days=730)
    rng = random.Random(42)
    work_type_choices = [
        WorkOrderType.CORRECTIVE,
        WorkOrderType.EMERGENCY,
        WorkOrderType.PREVENTIVE,
        WorkOrderType.INSPECTION,
        WorkOrderType.PROJECT,
    ]
    priority_choices = [
        WorkOrderPriority.EMERGENCY,
        WorkOrderPriority.HIGH,
        WorkOrderPriority.MEDIUM,
        WorkOrderPriority.LOW,
    ]
    issue_library = [
        "Motor vibration detected",
        "Seal leak observed",
        "Temperature trending high",
        "PLC fault alarm",
        "Unexpected noise from gearbox",
        "Replace worn belts",
        "Hydraulic pressure low",
        "Routine lubrication",
        "Sensor calibration drift",
        "Safety guard adjustment",
    ]
    failure_modes = [
        ("BRG", "Bearing wear detected", "Replaced bearing and rebalanced shaft"),
        ("ELEC", "Electrical short in motor leads", "Re-terminated wiring and tested insulation"),
        ("HYD", "Hydraulic leak at fitting", "Replaced fitting and topped up fluid"),
        ("LUBE", "Lubrication starved gear train", "Cleaned housing and replenished grease"),
        ("ALIGN", "Coupling misalignment", "Realigned motor and pump shafts"),
    ]
    craft_options = ["Mechanic", "Electrician", "Controls", "Utilities", "Millwright"]
    recent_statuses = [
        WorkOrderStatus.APPROVED,
        WorkOrderStatus.SCHEDULED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.ON_HOLD,
    ]
    closed_statuses = [WorkOrderStatus.CLOSED, WorkOrderStatus.COMPLETED]
    work_orders_created = 0
    wo_counter = 1

    for asset in assets:
        next_date = history_start + timedelta(days=rng.randint(0, 30))
        while next_date <= today:
            work_type = rng.choice(work_type_choices)
            priority = rng.choice(priority_choices)
            issue = rng.choice(issue_library)
            assigned_tech = rng.choice(technician_team)
            scheduled_start = datetime.combine(next_date, datetime.min.time()) + timedelta(hours=7 + rng.randint(0, 2))
            estimated_hours = round(max(0.5, rng.uniform(1.0, 6.0)), 1)
            scheduled_end = scheduled_start + timedelta(hours=estimated_hours)
            due_date = next_date + timedelta(days=rng.randint(1, 6))
            is_recent = (today - next_date).days < 21
            status = rng.choice(recent_statuses) if is_recent else rng.choice(closed_statuses)
            actual_start = scheduled_start if status in [
                WorkOrderStatus.IN_PROGRESS,
                WorkOrderStatus.ON_HOLD,
                WorkOrderStatus.COMPLETED,
                WorkOrderStatus.CLOSED,
            ] else None
            completion_hours = round(max(1.0, rng.uniform(1.0, 6.5)), 1)
            actual_end = actual_start + timedelta(hours=completion_hours) if actual_start and status in closed_statuses else None

            pm_link = None
            if work_type == WorkOrderType.PREVENTIVE:
                if asset.asset_num == "COMP-001":
                    pm_link = comp_oil_pm.id
                elif asset.asset_num == "PUMP-001":
                    pm_link = pump_inspect_pm.id

            wo = WorkOrder(
                organization_id=org.id,
                wo_number=f"WO-{wo_counter:05d}",
                title=f"{issue} - {asset.name}",
                description=f"{issue} on {asset.name} ({asset.asset_num})",
                work_type=work_type,
                status=status,
                priority=priority,
                asset_id=asset.id,
                location_id=asset.location_id,
                assigned_to_id=assigned_tech.id,
                assigned_team=f"{asset.asset_num}-Crew",
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                due_date=due_date,
                actual_start=actual_start,
                actual_end=actual_end,
                estimated_hours=estimated_hours,
                estimated_cost=round(estimated_hours * (assigned_tech.hourly_rate or 45.0), 2),
                pm_id=pm_link,
                created_by_id=admin_user.id,
                updated_by_id=assigned_tech.id,
                asset_was_down=False,
            )

            if rng.random() < 0.35:
                wo.asset_was_down = True
                wo.downtime_hours = round(rng.uniform(1.0, 8.0), 1)

            if status in closed_statuses:
                if rng.random() < 0.7:
                    failure = rng.choice(failure_modes)
                    wo.failure_code = failure[0]
                    wo.failure_cause = failure[1]
                    wo.failure_remedy = failure[2]
                wo.completion_notes = "Completed and verified operation."
                wo.completed_by_id = assigned_tech.id

            wo.created_at = scheduled_start
            wo.updated_at = actual_end or scheduled_end

            db.add(wo)

            labor_hours = round(max(0.5, rng.uniform(1.0, 5.0)), 1)
            labor_type = "OVERTIME" if rng.random() < 0.2 else "REGULAR"
            rate_multiplier = 1.5 if labor_type != "REGULAR" else 1.0
            labor_transaction = LaborTransaction(
                organization_id=org.id,
                work_order=wo,
                user_id=assigned_tech.id,
                start_time=actual_start or scheduled_start,
                end_time=(actual_start or scheduled_start) + timedelta(hours=labor_hours),
                hours=labor_hours,
                labor_type=labor_type,
                hourly_rate=(assigned_tech.hourly_rate or 45.0) * rate_multiplier,
                total_cost=round(labor_hours * (assigned_tech.hourly_rate or 45.0) * rate_multiplier, 2),
                craft=rng.choice(craft_options),
                created_by_id=assigned_tech.id,
            )
            db.add(labor_transaction)

            if rng.random() < 0.65:
                part = rng.choice(parts)
                quantity = rng.randint(1, 4)
                material_transaction = MaterialTransaction(
                    organization_id=org.id,
                    work_order=wo,
                    part_id=part.id,
                    quantity=quantity,
                    unit_cost=part.unit_cost,
                    total_cost=round(quantity * part.unit_cost, 2),
                    storeroom_id=storeroom.id,
                    transaction_type="ISSUE",
                    created_by_id=assigned_tech.id,
                )
                db.add(material_transaction)

            wo.calculate_totals()

            status_history = WorkOrderStatusHistory(
                work_order=wo,
                from_status=WorkOrderStatus.APPROVED.value,
                to_status=wo.status.value,
                changed_by_id=assigned_tech.id,
                created_by_id=assigned_tech.id,
                updated_by_id=assigned_tech.id,
            )
            db.add(status_history)

            work_orders_created += 1
            wo_counter += 1
            next_date += timedelta(days=rng.randint(18, 45))

    await db.commit()
    print("Demo data seeded successfully!")
    print(f"Generated {work_orders_created} historical work orders across {len(assets)} assets.")
    print("Login credentials:")
    print("  Admin: admin@demo.com / admin123")
    print("  Tech: tech@demo.com / tech123")


async def main():
    """Run seed script."""
    async with async_session_maker() as db:
        await seed_demo_data(db)


if __name__ == "__main__":
    asyncio.run(main())
