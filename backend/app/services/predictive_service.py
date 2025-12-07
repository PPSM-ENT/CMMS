"""
AI Predictive Maintenance Service
Uses machine learning to predict equipment failures based on historical data
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, func

from app.models.asset import Asset, Meter, MeterReading
from app.models.work_order import WorkOrder, WorkOrderType, WorkOrderStatus

logger = logging.getLogger(__name__)


class PredictiveMaintenanceService:
    """AI-powered predictive maintenance service."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker
        self.models: Dict[int, Dict[str, Any]] = {}  # asset_id -> model data
        self.scalers: Dict[int, StandardScaler] = {}

    async def load_historical_data(self, asset_id: int, days: int = 365) -> pd.DataFrame:
        """Load historical meter readings and work order data for an asset."""
        async with self.session_maker() as db:
            # Get meter readings
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            result = await db.execute(
                select(MeterReading, Meter)
                .join(Meter, MeterReading.meter_id == Meter.id)
                .where(Meter.asset_id == asset_id)
                .where(MeterReading.reading_date >= cutoff_date)
                .order_by(MeterReading.reading_date)
            )

            readings_data = []
            for reading, meter in result:
                readings_data.append({
                    'date': reading.reading_date,
                    'meter_code': meter.code,
                    'value': reading.reading_value,
                    'delta': reading.delta or 0
                })

            # Get work orders (failure events)
            result = await db.execute(
                select(WorkOrder)
                .where(WorkOrder.asset_id == asset_id)
                .where(WorkOrder.actual_end >= cutoff_date)
                .where(WorkOrder.work_type.in_([WorkOrderType.CORRECTIVE, WorkOrderType.EMERGENCY]))
            )

            failure_dates = [wo.actual_end for wo in result.scalars()]

            # Create time series data
            if readings_data:
                df = pd.DataFrame(readings_data)
                df['date'] = pd.to_datetime(df['date'])

                # Pivot to wide format (one column per meter)
                df_wide = df.pivot_table(
                    index='date',
                    columns='meter_code',
                    values='value',
                    aggfunc='last'
                ).fillna(method='ffill')

                # Add failure labels (1 if failure occurred within next 7 days, 0 otherwise)
                df_wide['failure_risk'] = 0
                for failure_date in failure_dates:
                    mask = (df_wide.index >= failure_date - timedelta(days=7)) & (df_wide.index <= failure_date)
                    df_wide.loc[mask, 'failure_risk'] = 1

                return df_wide

            return pd.DataFrame()

    async def train_predictive_model(self, asset_id: int) -> bool:
        """Train a predictive model for an asset."""
        try:
            df = await self.load_historical_data(asset_id)

            if len(df) < 50:  # Need minimum data
                logger.warning(f"Insufficient data for asset {asset_id}")
                return False

            # Prepare features
            feature_cols = [col for col in df.columns if col != 'failure_risk']
            X = df[feature_cols].fillna(0)
            y = df['failure_risk']

            # Check class balance
            if y.sum() < 5:  # Need at least 5 failure events
                logger.warning(f"Insufficient failure events for asset {asset_id}")
                return False

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
            model.fit(X_train_scaled, y_train)

            # Evaluate
            train_score = model.score(X_train_scaled, y_train)
            test_score = model.score(X_test_scaled, y_test)

            logger.info(f"Trained model for asset {asset_id}: train={train_score:.3f}, test={test_score:.3f}")

            # Store model and scaler
            self.models[asset_id] = {
                'model': model,
                'feature_columns': feature_cols,
                'trained_at': datetime.utcnow(),
                'train_score': train_score,
                'test_score': test_score
            }
            self.scalers[asset_id] = scaler

            return True

        except Exception as e:
            logger.error(f"Error training model for asset {asset_id}: {e}")
            return False

    async def predict_failure_risk(self, asset_id: int) -> Optional[Dict[str, Any]]:
        """Predict failure risk for an asset."""
        if asset_id not in self.models:
            return None

        try:
            # Get latest meter readings
            async with self.session_maker() as db:
                result = await db.execute(
                    select(MeterReading, Meter)
                    .join(Meter, MeterReading.meter_id == Meter.id)
                    .where(Meter.asset_id == asset_id)
                    .order_by(MeterReading.reading_date.desc())
                    .limit(10)  # Last 10 readings per meter
                )

                latest_readings = {}
                for reading, meter in result:
                    if meter.code not in latest_readings:
                        latest_readings[meter.code] = reading.reading_value

            if not latest_readings:
                return None

            # Prepare features for prediction
            model_data = self.models[asset_id]
            feature_values = []

            for col in model_data['feature_columns']:
                feature_values.append(latest_readings.get(col, 0))

            # Scale features
            scaler = self.scalers[asset_id]
            features_scaled = scaler.transform([feature_values])

            # Predict
            model = model_data['model']
            risk_probability = model.predict_proba(features_scaled)[0][1]  # Probability of failure

            # Get feature importance
            feature_importance = dict(zip(model_data['feature_columns'],
                                        model.feature_importances_))

            return {
                'asset_id': asset_id,
                'risk_probability': float(risk_probability),
                'risk_level': 'HIGH' if risk_probability > 0.7 else 'MEDIUM' if risk_probability > 0.3 else 'LOW',
                'feature_importance': feature_importance,
                'prediction_timestamp': datetime.utcnow(),
                'model_trained_at': model_data['trained_at']
            }

        except Exception as e:
            logger.error(f"Error predicting for asset {asset_id}: {e}")
            return None

    async def run_predictive_analysis(self) -> None:
        """Run predictive analysis for all assets with sufficient data."""
        async with self.session_maker() as db:
            # Get assets with meters
            result = await db.execute(
                select(Asset.id, func.count(Meter.id).label('meter_count'))
                .join(Meter, Asset.id == Meter.asset_id)
                .where(Asset.is_active == True)
                .group_by(Asset.id)
                .having(func.count(Meter.id) >= 2)  # Need at least 2 meters
            )

            asset_ids = [row[0] for row in result]

            logger.info(f"Running predictive analysis for {len(asset_ids)} assets")

            for asset_id in asset_ids:
                # Train/retrain model if needed
                if asset_id not in self.models:
                    success = await self.train_predictive_model(asset_id)
                    if success:
                        logger.info(f"Trained predictive model for asset {asset_id}")

                # Make prediction
                prediction = await self.predict_failure_risk(asset_id)
                if prediction:
                    # Store prediction in Redis or database
                    await self._store_prediction(prediction)

                    # Trigger alerts for high-risk assets
                    if prediction['risk_level'] == 'HIGH':
                        await self._trigger_predictive_alert(prediction, db)

    async def _store_prediction(self, prediction: Dict[str, Any]) -> None:
        """Store prediction results (could use Redis or database)."""
        # In a real implementation, store in a predictions table
        logger.info(f"Prediction for asset {prediction['asset_id']}: {prediction['risk_level']} risk "
                   f"({prediction['risk_probability']:.3f})")

    async def _trigger_predictive_alert(self, prediction: Dict[str, Any], db: AsyncSession) -> None:
        """Trigger alert for high-risk prediction."""
        # Create a predictive maintenance work order
        from app.models.preventive_maintenance import PreventiveMaintenance, PMTriggerType
        from app.services.pm_scheduler import PMScheduler

        # Check if we already have a predictive WO for this asset
        result = await db.execute(
            select(WorkOrder).where(
                WorkOrder.asset_id == prediction['asset_id'],
                WorkOrder.work_type == WorkOrderType.PREDICTIVE,
                WorkOrder.status.in_(["DRAFT", "WAITING_APPROVAL", "APPROVED", "SCHEDULED", "IN_PROGRESS", "ON_HOLD"])
            )
        )

        if result.scalar_one_or_none():
            return  # Already have predictive WO

        # Create predictive PM schedule if it doesn't exist
        result = await db.execute(
            select(PreventiveMaintenance).where(
                PreventiveMaintenance.asset_id == prediction['asset_id'],
                PreventiveMaintenance.trigger_type == PMTriggerType.CONDITION
            )
        )

        pm = result.scalar_one_or_none()
        if not pm:
            # Create predictive PM
            pm = PreventiveMaintenance(
                pm_number=f"PRED-{prediction['asset_id']}-{datetime.utcnow().strftime('%Y%m%d')}",
                name=f"Predictive Maintenance - Asset {prediction['asset_id']}",
                asset_id=prediction['asset_id'],
                trigger_type=PMTriggerType.CONDITION,
                description=f"AI-predicted high failure risk ({prediction['risk_probability']:.1%})",
                priority='HIGH',
                estimated_hours=4.0,
                is_active=True
            )
            db.add(pm)
            await db.flush()

        # Generate work order
        scheduler = PMScheduler(self.session_maker)
        await scheduler._generate_work_order(pm, db)

        logger.warning(f"AI-triggered predictive maintenance for asset {prediction['asset_id']} "
                      f"(risk: {prediction['risk_probability']:.1%})")


async def run_predictive_service():
    """Entry point for predictive maintenance service."""
    from app.core.database import async_session_maker

    service = PredictiveMaintenanceService(async_session_maker)

    while True:
        try:
            await service.run_predictive_analysis()
            await asyncio.sleep(3600)  # Run hourly
        except Exception as e:
            logger.error(f"Predictive service error: {e}")
            await asyncio.sleep(300)  # Retry in 5 minutes


if __name__ == "__main__":
    asyncio.run(run_predictive_service())
