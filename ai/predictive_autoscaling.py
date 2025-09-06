"""AI-Powered Predictive Auto-scaling for QENEX OS"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow import keras
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictiveAutoScaler:
    """ML-based predictive auto-scaling system"""
    
    def __init__(self, lookback_hours: int = 24, forecast_hours: int = 4):
        self.lookback_hours = lookback_hours
        self.forecast_hours = forecast_hours
        self.scaler = StandardScaler()
        self.models = {}
        self.metrics_history = []
        self.scaling_decisions = []
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML models for prediction"""
        # LSTM model for time series prediction
        self.models['lstm'] = self._build_lstm_model()
        
        # Random Forest for feature-based prediction
        self.models['rf'] = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        # Prophet-like model for seasonal patterns
        self.models['seasonal'] = self._build_seasonal_model()
    
    def _build_lstm_model(self) -> keras.Model:
        """Build LSTM model for time series prediction"""
        model = keras.Sequential([
            keras.layers.LSTM(128, return_sequences=True, input_shape=(24, 7)),
            keras.layers.Dropout(0.2),
            keras.layers.LSTM(64, return_sequences=True),
            keras.layers.Dropout(0.2),
            keras.layers.LSTM(32),
            keras.layers.Dense(16, activation='relu'),
            keras.layers.Dense(self.forecast_hours)
        ])
        
        model.compile(
            optimizer='adam',
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def _build_seasonal_model(self) -> keras.Model:
        """Build model for seasonal pattern detection"""
        model = keras.Sequential([
            keras.layers.Dense(64, activation='relu', input_shape=(168,)),  # Week of hourly data
            keras.layers.Dense(32, activation='relu'),
            keras.layers.Dense(16, activation='relu'),
            keras.layers.Dense(self.forecast_hours)
        ])
        
        model.compile(optimizer='adam', loss='mse')
        return model
    
    def collect_metrics(self) -> Dict:
        """Collect current system metrics"""
        # Simulated metrics collection
        current_time = datetime.now()
        metrics = {
            'timestamp': current_time.isoformat(),
            'cpu_usage': np.random.uniform(20, 80),
            'memory_usage': np.random.uniform(30, 90),
            'request_rate': np.random.poisson(100),
            'response_time': np.random.exponential(0.5),
            'error_rate': np.random.uniform(0, 5),
            'active_connections': np.random.poisson(50),
            'queue_length': np.random.poisson(10),
            'hour_of_day': current_time.hour,
            'day_of_week': current_time.weekday(),
            'is_weekend': current_time.weekday() >= 5
        }
        
        self.metrics_history.append(metrics)
        
        # Keep only recent history
        cutoff_time = current_time - timedelta(hours=self.lookback_hours * 2)
        self.metrics_history = [
            m for m in self.metrics_history 
            if datetime.fromisoformat(m['timestamp']) > cutoff_time
        ]
        
        return metrics
    
    def prepare_features(self, metrics_history: List[Dict]) -> np.ndarray:
        """Prepare features for ML models"""
        if len(metrics_history) < self.lookback_hours:
            # Pad with zeros if not enough history
            padding = self.lookback_hours - len(metrics_history)
            metrics_history = [{}] * padding + metrics_history
        
        features = []
        for m in metrics_history[-self.lookback_hours:]:
            if m:
                features.append([
                    m.get('cpu_usage', 0),
                    m.get('memory_usage', 0),
                    m.get('request_rate', 0),
                    m.get('response_time', 0),
                    m.get('error_rate', 0),
                    m.get('active_connections', 0),
                    m.get('queue_length', 0)
                ])
            else:
                features.append([0] * 7)
        
        return np.array(features)
    
    def predict_load(self) -> Dict:
        """Predict future load using ensemble of models"""
        if len(self.metrics_history) < 10:
            # Not enough data for prediction
            return self._default_prediction()
        
        # Prepare features
        features = self.prepare_features(self.metrics_history)
        
        predictions = {}
        
        # LSTM prediction
        try:
            lstm_input = features.reshape(1, self.lookback_hours, 7)
            lstm_pred = self.models['lstm'].predict(lstm_input, verbose=0)[0]
            predictions['lstm'] = lstm_pred
        except Exception as e:
            logger.error(f"LSTM prediction failed: {e}")
            predictions['lstm'] = np.array([50] * self.forecast_hours)
        
        # Random Forest prediction (using flattened features)
        try:
            rf_input = features.flatten().reshape(1, -1)
            # Note: RF needs to be trained first
            # rf_pred = self.models['rf'].predict(rf_input)[0]
            # predictions['rf'] = rf_pred
            predictions['rf'] = np.array([55] * self.forecast_hours)  # Placeholder
        except Exception as e:
            logger.error(f"RF prediction failed: {e}")
            predictions['rf'] = np.array([50] * self.forecast_hours)
        
        # Seasonal prediction
        try:
            # Use last week's data for seasonal pattern
            seasonal_features = self._get_seasonal_features()
            seasonal_pred = self.models['seasonal'].predict(seasonal_features, verbose=0)[0]
            predictions['seasonal'] = seasonal_pred
        except Exception as e:
            logger.error(f"Seasonal prediction failed: {e}")
            predictions['seasonal'] = np.array([50] * self.forecast_hours)
        
        # Ensemble prediction (weighted average)
        weights = {'lstm': 0.5, 'rf': 0.3, 'seasonal': 0.2}
        ensemble_pred = np.zeros(self.forecast_hours)
        
        for model_name, weight in weights.items():
            if model_name in predictions:
                ensemble_pred += predictions[model_name] * weight
        
        return {
            'predictions': ensemble_pred.tolist(),
            'models': predictions,
            'forecast_hours': self.forecast_hours,
            'confidence': self._calculate_confidence(predictions)
        }
    
    def _get_seasonal_features(self) -> np.ndarray:
        """Extract seasonal features from last week"""
        # Get last week's hourly averages
        week_data = []
        for i in range(168):  # 7 days * 24 hours
            # Find metrics from same hour in past days
            hour_metrics = [
                m.get('cpu_usage', 50) 
                for m in self.metrics_history 
                if m and datetime.fromisoformat(m['timestamp']).hour == (i % 24)
            ]
            week_data.append(np.mean(hour_metrics) if hour_metrics else 50)
        
        return np.array(week_data).reshape(1, -1)
    
    def _calculate_confidence(self, predictions: Dict) -> float:
        """Calculate prediction confidence based on model agreement"""
        if len(predictions) < 2:
            return 0.5
        
        # Calculate variance between predictions
        all_preds = np.array(list(predictions.values()))
        variance = np.var(all_preds, axis=0).mean()
        
        # Lower variance = higher confidence
        confidence = max(0, min(1, 1 - (variance / 100)))
        return float(confidence)
    
    def _default_prediction(self) -> Dict:
        """Default prediction when not enough data"""
        return {
            'predictions': [50] * self.forecast_hours,
            'models': {},
            'forecast_hours': self.forecast_hours,
            'confidence': 0.1
        }
    
    def calculate_scaling_decision(self, predictions: Dict) -> Dict:
        """Calculate scaling decision based on predictions"""
        pred_values = predictions['predictions']
        confidence = predictions['confidence']
        
        # Calculate required instances
        max_predicted = max(pred_values)
        avg_predicted = np.mean(pred_values)
        
        # Scaling formula
        base_instances = 3
        scale_factor = max_predicted / 50  # 50% is baseline
        
        if confidence > 0.7:
            # High confidence - be aggressive
            target_instances = int(base_instances * scale_factor * 1.2)
        elif confidence > 0.4:
            # Medium confidence - be moderate
            target_instances = int(base_instances * scale_factor)
        else:
            # Low confidence - be conservative
            target_instances = int(base_instances * scale_factor * 0.8)
        
        # Apply bounds
        target_instances = max(2, min(20, target_instances))
        
        decision = {
            'timestamp': datetime.now().isoformat(),
            'current_load': self._get_current_load(),
            'predicted_max_load': max_predicted,
            'predicted_avg_load': avg_predicted,
            'confidence': confidence,
            'target_instances': target_instances,
            'action': self._determine_action(target_instances),
            'reason': self._explain_decision(predictions, target_instances)
        }
        
        self.scaling_decisions.append(decision)
        return decision
    
    def _get_current_load(self) -> float:
        """Get current system load"""
        if self.metrics_history:
            latest = self.metrics_history[-1]
            return latest.get('cpu_usage', 50)
        return 50
    
    def _determine_action(self, target_instances: int) -> str:
        """Determine scaling action"""
        # Get current instances (simulated)
        current_instances = 5
        
        if target_instances > current_instances:
            return f"SCALE_UP to {target_instances} instances"
        elif target_instances < current_instances:
            return f"SCALE_DOWN to {target_instances} instances"
        else:
            return "MAINTAIN current instances"
    
    def _explain_decision(self, predictions: Dict, target_instances: int) -> str:
        """Explain scaling decision"""
        reasons = []
        
        max_load = max(predictions['predictions'])
        if max_load > 70:
            reasons.append(f"High load predicted ({max_load:.1f}%)")
        elif max_load < 30:
            reasons.append(f"Low load predicted ({max_load:.1f}%)")
        
        if predictions['confidence'] < 0.4:
            reasons.append("Low prediction confidence")
        elif predictions['confidence'] > 0.7:
            reasons.append("High prediction confidence")
        
        if not reasons:
            reasons.append("Normal load patterns detected")
        
        return "; ".join(reasons)
    
    async def run_autoscaler(self):
        """Main autoscaling loop"""
        logger.info("Starting predictive autoscaler")
        
        while True:
            try:
                # Collect metrics
                metrics = self.collect_metrics()
                logger.info(f"Collected metrics: CPU={metrics['cpu_usage']:.1f}%")
                
                # Make predictions
                predictions = self.predict_load()
                logger.info(f"Predictions: {predictions['predictions']}")
                
                # Make scaling decision
                decision = self.calculate_scaling_decision(predictions)
                logger.info(f"Scaling decision: {decision['action']}")
                
                # Apply scaling (would integrate with orchestrator)
                if "SCALE" in decision['action']:
                    await self.apply_scaling(decision)
                
                # Wait before next iteration
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Autoscaler error: {e}")
                await asyncio.sleep(60)
    
    async def apply_scaling(self, decision: Dict):
        """Apply scaling decision to infrastructure"""
        logger.info(f"Applying scaling: {decision['action']}")
        # This would integrate with Kubernetes or cloud provider APIs
        # For now, just log the action
        
    def train_models(self, training_data: pd.DataFrame):
        """Train models with historical data"""
        # This would be called periodically to retrain models
        logger.info("Training predictive models with new data")
        # Implementation would train all models with recent data

if __name__ == "__main__":
    autoscaler = PredictiveAutoScaler()
    asyncio.run(autoscaler.run_autoscaler())