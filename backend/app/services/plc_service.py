"""
PLC Integration Service - Reads live data from industrial PLCs
Supports Allen-Bradley (pycomm3) and OPC UA protocols
"""
import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.models.asset import Meter, MeterReading
from app.models.preventive_maintenance import PreventiveMaintenance, PMTriggerType
from app.models.work_order import WorkOrder

logger = logging.getLogger(__name__)


class PLCService:
    """Service for integrating with industrial PLCs to read live meter data."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession], redis_client: redis.Redis):
        self.session_maker = session_maker
        self.redis = redis_client
        self.plc_configs: Dict[str, Dict[str, Any]] = {}
        self.running = False

    async def load_plc_configs(self) -> None:
        """Load PLC configurations from database or environment."""
        # In a real implementation, this would load from a PLC configuration table
        # For now, use environment variables
        plc_ip = os.getenv("PLC_IP", "192.168.1.100")
        plc_slot = int(os.getenv("PLC_SLOT", "0"))

        self.plc_configs = {
            "main_plc": {
                "ip": plc_ip,
                "slot": plc_slot,
                "protocol": "ab",  # Allen-Bradley
                "tags": {
                    "pump1_runtime": "Pump1.RuntimeHours:DINT",
                    "pump1_temperature": "Pump1.Temperature:REAL",
                    "conveyor_speed": "Conveyor.Speed:REAL",
                    "pressure_sensor": "Pressure.Value:REAL",
                }
            }
        }

    async def read_plc_tags(self, plc_config: Dict[str, Any]) -> Dict[str, Any]:
        """Read tags from PLC using appropriate protocol."""
        try:
            if plc_config["protocol"] == "ab":
                return await self._read_allen_bradley_tags(plc_config)
            elif plc_config["protocol"] == "opcua":
                return await self._read_opcua_tags(plc_config)
            else:
                logger.error(f"Unsupported PLC protocol: {plc_config['protocol']}")
                return {}
        except Exception as e:
            logger.error(f"Error reading PLC tags: {e}")
            return {}

    async def _read_allen_bradley_tags(self, plc_config: Dict[str, Any]) -> Dict[str, Any]:
        """Read tags from Allen-Bradley PLC."""
        try:
            # Import here to avoid dependency issues if PLC libraries not installed
            from pycomm3 import LogixDriver

            with LogixDriver(plc_config["ip"]) as plc:
                plc_slot = plc_config.get("slot", 0)
                if plc_slot > 0:
                    plc.open(slot=plc_slot)
                else:
                    plc.open()

                readings = {}
                for tag_name, tag_address in plc_config["tags"].items():
                    try:
                        value = plc.read(tag_address).value
                        readings[tag_name] = value
                    except Exception as e:
                        logger.warning(f"Failed to read tag {tag_name}: {e}")

                return readings

        except ImportError:
            logger.warning("pycomm3 not installed, skipping Allen-Bradley PLC integration")
            return {}
        except Exception as e:
            logger.error(f"Allen-Bradley PLC error: {e}")
            return {}

    async def _read_opcua_tags(self, plc_config: Dict[str, Any]) -> Dict[str, Any]:
        """Read tags from OPC UA server."""
        try:
            # Import here to avoid dependency issues
            from opcua import Client

            client = Client(plc_config["ip"])
            client.connect()

            readings = {}
            for tag_name, node_id in plc_config["tags"].items():
                try:
                    node = client.get_node(node_id)
                    value = node.get_value()
                    readings[tag_name] = value
                except Exception as e:
                    logger.warning(f"Failed to read OPC UA node {tag_name}: {e}")

            client.disconnect()
            return readings

        except ImportError:
            logger.warning("opcua not installed, skipping OPC UA integration")
            return {}
        except Exception as e:
            logger.error(f"OPC UA error: {e}")
            return {}

    async def update_meter_readings(self, plc_readings: Dict[str, Any]) -> None:
        """Update meter readings in database from PLC data."""
        async with self.session_maker() as db:
            # Map PLC tag names to meter codes
            tag_to_meter_map = {
                "pump1_runtime": "PUMP1_RUNTIME",
                "pump1_temperature": "PUMP1_TEMP",
                "conveyor_speed": "CONVEYOR_SPEED",
                "pressure_sensor": "PRESSURE_MAIN",
            }

            for tag_name, value in plc_readings.items():
                meter_code = tag_to_meter_map.get(tag_name)
                if not meter_code:
                    continue

                # Find meter by code
                result = await db.execute(
                    select(Meter).where(Meter.code == meter_code)
                )
                meter = result.scalar_one_or_none()

                if meter:
                    # Create meter reading
                    reading = MeterReading(
                        meter_id=meter.id,
                        reading_value=float(value),
                        reading_date=datetime.utcnow(),
                        source="PLC",
                        notes=f"Auto-read from PLC tag {tag_name}",
                    )

                    # Update meter last reading
                    meter.last_reading = float(value)
                    meter.last_reading_date = datetime.utcnow()

                    db.add(reading)

                    # Check for condition-based PM triggers
                    await self._check_condition_triggers(meter, db)

            await db.commit()

    async def _check_condition_triggers(self, meter: Meter, db: AsyncSession) -> None:
        """Check if meter reading triggers any condition-based PM."""
        # Find PM schedules that use this meter
        result = await db.execute(
            select(PreventiveMaintenance).where(
                PreventiveMaintenance.meter_id == meter.id,
                PreventiveMaintenance.trigger_type == PMTriggerType.CONDITION,
                PreventiveMaintenance.is_active == True
            )
        )

        for pm in result.scalars():
            # Simple threshold check (in real implementation, this would be more sophisticated)
            if pm.condition_attribute and pm.condition_value is not None:
                if pm.condition_operator == ">" and meter.last_reading > pm.condition_value:
                    await self._trigger_condition_pm(pm, db)
                elif pm.condition_operator == "<" and meter.last_reading < pm.condition_value:
                    await self._trigger_condition_pm(pm, db)

    async def _trigger_condition_pm(self, pm: PreventiveMaintenance, db: AsyncSession) -> None:
        """Trigger a work order for condition-based PM."""
        # Check if we already have an open WO for this PM
        result = await db.execute(
            select(WorkOrder).where(
                WorkOrder.pm_id == pm.id,
                WorkOrder.status.in_(["DRAFT", "WAITING_APPROVAL", "APPROVED", "SCHEDULED", "IN_PROGRESS", "ON_HOLD"])
            )
        )

        if result.scalar_one_or_none():
            return  # Already have open WO

        # Generate WO (reuse existing PM WO generation logic)
        from app.services.pm_scheduler import PMScheduler
        scheduler = PMScheduler(self.session_maker)
        await scheduler._generate_work_order(pm, db)

        logger.info(f"Condition-based PM triggered for {pm.pm_number}")

    async def run_plc_monitoring(self) -> None:
        """Main PLC monitoring loop."""
        self.running = True
        await self.load_plc_configs()

        update_interval = int(os.getenv("METER_UPDATE_INTERVAL", "300"))  # 5 minutes default

        logger.info(f"Starting PLC monitoring with {update_interval}s interval")

        while self.running:
            try:
                for plc_name, plc_config in self.plc_configs.items():
                    readings = await self.read_plc_tags(plc_config)
                    if readings:
                        await self.update_meter_readings(readings)
                        logger.debug(f"Updated {len(readings)} meter readings from {plc_name}")

                await asyncio.sleep(update_interval)

            except Exception as e:
                logger.error(f"PLC monitoring error: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def stop(self) -> None:
        """Stop the PLC monitoring service."""
        self.running = False
        logger.info("PLC monitoring stopped")


async def run_plc_service():
    """Entry point for PLC service."""
    import os
    from app.core.database import async_session_maker

    # Redis client
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True
    )

    service = PLCService(async_session_maker, redis_client)

    try:
        await service.run_plc_monitoring()
    except KeyboardInterrupt:
        await service.stop()


if __name__ == "__main__":
    import os
    asyncio.run(run_plc_service())
