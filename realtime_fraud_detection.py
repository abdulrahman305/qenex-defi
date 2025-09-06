#!/usr/bin/env python3
"""
Real-Time Fraud Detection System
Production-ready ML-based fraud detection with continuous learning
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import pickle
import json
import logging
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import IsolationForest, RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
import joblib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TransactionFeatures:
    """Transaction features for ML model"""
    amount: float
    merchant_category: str
    merchant_country: str
    customer_country: str
    time_since_last: float  # seconds
    hour_of_day: int
    day_of_week: int
    is_weekend: bool
    velocity_1h: int  # transactions in last hour
    velocity_24h: int  # transactions in last 24 hours
    amount_velocity_1h: float  # total amount in last hour
    amount_velocity_24h: float  # total amount in last 24 hours
    merchant_risk_score: float
    country_risk_score: float
    device_fingerprint: str
    ip_address: str
    is_first_transaction: bool
    days_since_account_creation: int
    failed_attempts_24h: int
    unique_merchants_7d: int
    cross_border: bool
    unusual_amount: bool  # significantly different from usual
    card_present: bool
    
    def to_vector(self) -> np.ndarray:
        """Convert features to numerical vector"""
        return np.array([
            self.amount,
            hash(self.merchant_category) % 1000,
            hash(self.merchant_country) % 200,
            hash(self.customer_country) % 200,
            self.time_since_last,
            self.hour_of_day,
            self.day_of_week,
            int(self.is_weekend),
            self.velocity_1h,
            self.velocity_24h,
            self.amount_velocity_1h,
            self.amount_velocity_24h,
            self.merchant_risk_score,
            self.country_risk_score,
            int(self.is_first_transaction),
            self.days_since_account_creation,
            self.failed_attempts_24h,
            self.unique_merchants_7d,
            int(self.cross_border),
            int(self.unusual_amount),
            int(self.card_present)
        ])

@dataclass
class FraudPattern:
    """Known fraud pattern"""
    pattern_id: str
    pattern_type: str
    features: Dict[str, Any]
    confidence: float
    detected_count: int
    last_seen: datetime

class RealTimeFraudDetector:
    """Advanced fraud detection with multiple ML models"""
    
    def __init__(self):
        self.isolation_forest = IsolationForest(
            n_estimators=100,
            contamination=0.01,
            random_state=42
        )
        self.random_forest = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.gradient_boost = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            random_state=42
        )
        self.scaler = StandardScaler()
        
        self.is_trained = False
        self.model_version = "1.0.0"
        self.last_training = None
        
        # Pattern detection
        self.known_patterns: Dict[str, FraudPattern] = {}
        self.transaction_history: Dict[str, List[Dict]] = defaultdict(list)
        
        # Risk scores
        self.merchant_scores: Dict[str, float] = {}
        self.country_scores: Dict[str, float] = {
            'NG': 0.8, 'RU': 0.7, 'CN': 0.6,  # Higher risk
            'US': 0.2, 'GB': 0.2, 'DE': 0.2,  # Lower risk
        }
        
        # Performance metrics
        self.metrics = {
            'total_transactions': 0,
            'fraud_detected': 0,
            'false_positives': 0,
            'true_positives': 0,
            'processing_time_ms': []
        }
    
    def extract_features(self, transaction: Dict) -> TransactionFeatures:
        """Extract ML features from transaction"""
        customer_id = transaction.get('customer_id')
        merchant_id = transaction.get('merchant_id')
        
        # Get transaction history
        history = self.transaction_history.get(customer_id, [])
        
        # Calculate velocities
        now = datetime.now(timezone.utc)
        velocity_1h = 0
        velocity_24h = 0
        amount_1h = 0.0
        amount_24h = 0.0
        unique_merchants = set()
        
        for hist_tx in history:
            tx_time = datetime.fromisoformat(hist_tx['timestamp'])
            time_diff = (now - tx_time).total_seconds()
            
            if time_diff <= 3600:  # 1 hour
                velocity_1h += 1
                amount_1h += hist_tx['amount']
            if time_diff <= 86400:  # 24 hours
                velocity_24h += 1
                amount_24h += hist_tx['amount']
            if time_diff <= 604800:  # 7 days
                unique_merchants.add(hist_tx.get('merchant_id'))
        
        # Time features
        time_since_last = 999999
        if history:
            last_tx_time = datetime.fromisoformat(history[-1]['timestamp'])
            time_since_last = (now - last_tx_time).total_seconds()
        
        # Unusual amount detection
        amounts = [h['amount'] for h in history[-30:]]  # Last 30 transactions
        usual_amount = np.median(amounts) if amounts else transaction['amount']
        unusual = abs(transaction['amount'] - usual_amount) > 2 * usual_amount
        
        # Risk scores
        merchant_score = self.merchant_scores.get(merchant_id, 0.5)
        country_score = self.country_scores.get(transaction.get('country', 'US'), 0.5)
        
        return TransactionFeatures(
            amount=transaction['amount'],
            merchant_category=transaction.get('merchant_category', 'unknown'),
            merchant_country=transaction.get('merchant_country', 'US'),
            customer_country=transaction.get('customer_country', 'US'),
            time_since_last=min(time_since_last, 999999),
            hour_of_day=now.hour,
            day_of_week=now.weekday(),
            is_weekend=now.weekday() >= 5,
            velocity_1h=velocity_1h,
            velocity_24h=velocity_24h,
            amount_velocity_1h=amount_1h,
            amount_velocity_24h=amount_24h,
            merchant_risk_score=merchant_score,
            country_risk_score=country_score,
            device_fingerprint=transaction.get('device_id', ''),
            ip_address=transaction.get('ip_address', ''),
            is_first_transaction=len(history) == 0,
            days_since_account_creation=transaction.get('account_age_days', 0),
            failed_attempts_24h=transaction.get('failed_attempts', 0),
            unique_merchants_7d=len(unique_merchants),
            cross_border=transaction.get('merchant_country') != transaction.get('customer_country'),
            unusual_amount=unusual,
            card_present=transaction.get('card_present', False)
        )
    
    def train_models(self, training_data: pd.DataFrame = None):
        """Train ML models on historical data"""
        if training_data is None:
            # Generate synthetic training data
            training_data = self._generate_training_data()
        
        # Prepare features and labels
        X = training_data.drop(['is_fraud', 'transaction_id'], axis=1)
        y = training_data['is_fraud']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train Isolation Forest (unsupervised)
        self.isolation_forest.fit(X_train_scaled[y_train == 0])  # Train on normal transactions
        
        # Train Random Forest
        self.random_forest.fit(X_train_scaled, y_train)
        
        # Train Gradient Boosting
        self.gradient_boost.fit(X_train_scaled, y_train)
        
        # Evaluate models
        rf_pred = self.random_forest.predict(X_test_scaled)
        gb_pred = self.gradient_boost.predict(X_test_scaled)
        
        rf_precision = precision_score(y_test, rf_pred)
        rf_recall = recall_score(y_test, rf_pred)
        rf_f1 = f1_score(y_test, rf_pred)
        
        gb_precision = precision_score(y_test, gb_pred)
        gb_recall = recall_score(y_test, gb_pred)
        gb_f1 = f1_score(y_test, gb_pred)
        
        logger.info(f"Random Forest - Precision: {rf_precision:.3f}, Recall: {rf_recall:.3f}, F1: {rf_f1:.3f}")
        logger.info(f"Gradient Boost - Precision: {gb_precision:.3f}, Recall: {gb_recall:.3f}, F1: {gb_f1:.3f}")
        
        self.is_trained = True
        self.last_training = datetime.now(timezone.utc)
        
        return {
            'random_forest': {'precision': rf_precision, 'recall': rf_recall, 'f1': rf_f1},
            'gradient_boost': {'precision': gb_precision, 'recall': gb_recall, 'f1': gb_f1}
        }
    
    def _generate_training_data(self, n_samples: int = 10000) -> pd.DataFrame:
        """Generate synthetic training data"""
        np.random.seed(42)
        
        # Generate normal transactions (95%)
        n_normal = int(n_samples * 0.95)
        n_fraud = n_samples - n_normal
        
        normal_data = {
            'amount': np.random.lognormal(3, 1.5, n_normal),
            'velocity_1h': np.random.poisson(2, n_normal),
            'velocity_24h': np.random.poisson(5, n_normal),
            'hour_of_day': np.random.randint(6, 23, n_normal),
            'merchant_risk': np.random.uniform(0, 0.5, n_normal),
            'country_risk': np.random.uniform(0, 0.5, n_normal),
            'time_since_last': np.random.exponential(3600, n_normal),
            'is_fraud': np.zeros(n_normal)
        }
        
        # Generate fraud transactions (5%)
        fraud_data = {
            'amount': np.concatenate([
                np.random.uniform(0.01, 1, n_fraud // 2),  # Card testing
                np.random.uniform(1000, 10000, n_fraud // 2)  # Large frauds
            ]),
            'velocity_1h': np.random.poisson(10, n_fraud),  # Higher velocity
            'velocity_24h': np.random.poisson(30, n_fraud),
            'hour_of_day': np.random.choice([2, 3, 4, 22, 23], n_fraud),  # Odd hours
            'merchant_risk': np.random.uniform(0.5, 1, n_fraud),
            'country_risk': np.random.uniform(0.5, 1, n_fraud),
            'time_since_last': np.random.uniform(1, 60, n_fraud),  # Rapid succession
            'is_fraud': np.ones(n_fraud)
        }
        
        # Combine and add more features
        df = pd.concat([pd.DataFrame(normal_data), pd.DataFrame(fraud_data)])
        
        # Add additional features
        df['day_of_week'] = np.random.randint(0, 7, len(df))
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['unique_merchants_7d'] = np.random.poisson(10, len(df))
        df['cross_border'] = np.random.choice([0, 1], len(df), p=[0.8, 0.2])
        df['unusual_amount'] = np.random.choice([0, 1], len(df), p=[0.9, 0.1])
        df['card_present'] = np.random.choice([0, 1], len(df), p=[0.3, 0.7])
        df['is_first_transaction'] = np.random.choice([0, 1], len(df), p=[0.95, 0.05])
        df['days_since_account'] = np.random.randint(1, 1000, len(df))
        df['failed_attempts'] = np.random.poisson(0.1, len(df))
        df['amount_velocity_1h'] = df['amount'] * df['velocity_1h'] * np.random.uniform(0.8, 1.2, len(df))
        df['amount_velocity_24h'] = df['amount'] * df['velocity_24h'] * np.random.uniform(0.8, 1.2, len(df))
        df['transaction_id'] = [f"tx_{i}" for i in range(len(df))]
        
        return df.sample(frac=1).reset_index(drop=True)
    
    async def predict_fraud(self, transaction: Dict) -> Tuple[bool, float, Dict]:
        """Predict if transaction is fraudulent"""
        start_time = datetime.now(timezone.utc)
        
        if not self.is_trained:
            # Auto-train if not trained
            self.train_models()
        
        # Extract features
        features = self.extract_features(transaction)
        feature_vector = features.to_vector().reshape(1, -1)
        
        # Scale features
        feature_scaled = self.scaler.transform(feature_vector)
        
        # Get predictions from all models
        isolation_pred = self.isolation_forest.predict(feature_scaled)[0]
        rf_prob = self.random_forest.predict_proba(feature_scaled)[0][1]
        gb_prob = self.gradient_boost.predict_proba(feature_scaled)[0][1]
        
        # Ensemble prediction (weighted average)
        fraud_probability = (
            0.2 * (1 if isolation_pred == -1 else 0) +
            0.4 * rf_prob +
            0.4 * gb_prob
        )
        
        # Rule-based adjustments
        if features.velocity_1h > 10:
            fraud_probability = min(1.0, fraud_probability + 0.2)
        
        if features.amount > 5000 and features.is_first_transaction:
            fraud_probability = min(1.0, fraud_probability + 0.3)
        
        if features.failed_attempts_24h > 3:
            fraud_probability = min(1.0, fraud_probability + 0.2)
        
        # Pattern matching
        pattern_matches = self._check_patterns(transaction, features)
        if pattern_matches:
            fraud_probability = min(1.0, fraud_probability + 0.3)
        
        # Decision
        is_fraud = fraud_probability > 0.5
        
        # Update history
        customer_id = transaction.get('customer_id')
        if customer_id:
            self.transaction_history[customer_id].append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'amount': transaction['amount'],
                'merchant_id': transaction.get('merchant_id'),
                'is_fraud': is_fraud
            })
            
            # Keep only last 1000 transactions
            self.transaction_history[customer_id] = self.transaction_history[customer_id][-1000:]
        
        # Update metrics
        self.metrics['total_transactions'] += 1
        if is_fraud:
            self.metrics['fraud_detected'] += 1
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        self.metrics['processing_time_ms'].append(processing_time)
        
        # Prepare detailed response
        details = {
            'fraud_probability': fraud_probability,
            'model_scores': {
                'isolation_forest': 1 if isolation_pred == -1 else 0,
                'random_forest': rf_prob,
                'gradient_boost': gb_prob
            },
            'risk_factors': [],
            'processing_time_ms': processing_time,
            'model_version': self.model_version
        }
        
        # Add risk factors
        if features.velocity_1h > 10:
            details['risk_factors'].append('High transaction velocity')
        if features.unusual_amount:
            details['risk_factors'].append('Unusual transaction amount')
        if features.failed_attempts_24h > 3:
            details['risk_factors'].append('Multiple failed attempts')
        if pattern_matches:
            details['risk_factors'].extend(pattern_matches)
        
        return is_fraud, fraud_probability, details
    
    def _check_patterns(self, transaction: Dict, features: TransactionFeatures) -> List[str]:
        """Check for known fraud patterns"""
        matches = []
        
        # Card testing pattern
        if features.amount < 1.0 and features.velocity_1h > 3:
            matches.append("Card testing pattern detected")
        
        # Rapid fire pattern
        if features.time_since_last < 10 and features.velocity_1h > 5:
            matches.append("Rapid fire transaction pattern")
        
        # Account takeover pattern
        if features.unusual_amount and features.unique_merchants_7d > 20:
            matches.append("Potential account takeover")
        
        # Cross-border fraud pattern
        if features.cross_border and features.country_risk_score > 0.7:
            matches.append("High-risk cross-border transaction")
        
        return matches
    
    async def update_merchant_score(self, merchant_id: str, is_fraud: bool):
        """Update merchant risk score based on transaction outcome"""
        current_score = self.merchant_scores.get(merchant_id, 0.5)
        
        # Exponential moving average
        alpha = 0.1
        new_score = alpha * (1.0 if is_fraud else 0.0) + (1 - alpha) * current_score
        
        self.merchant_scores[merchant_id] = new_score
    
    def get_metrics(self) -> Dict:
        """Get performance metrics"""
        avg_processing_time = np.mean(self.metrics['processing_time_ms'][-1000:]) if self.metrics['processing_time_ms'] else 0
        
        return {
            'total_transactions': self.metrics['total_transactions'],
            'fraud_detected': self.metrics['fraud_detected'],
            'detection_rate': self.metrics['fraud_detected'] / max(1, self.metrics['total_transactions']),
            'avg_processing_time_ms': avg_processing_time,
            'model_version': self.model_version,
            'last_training': self.last_training.isoformat() if self.last_training else None,
            'is_trained': self.is_trained
        }
    
    def save_models(self, path: str):
        """Save trained models to disk"""
        joblib.dump({
            'isolation_forest': self.isolation_forest,
            'random_forest': self.random_forest,
            'gradient_boost': self.gradient_boost,
            'scaler': self.scaler,
            'merchant_scores': self.merchant_scores,
            'model_version': self.model_version,
            'last_training': self.last_training
        }, path)
        logger.info(f"Models saved to {path}")
    
    def load_models(self, path: str):
        """Load trained models from disk"""
        data = joblib.load(path)
        self.isolation_forest = data['isolation_forest']
        self.random_forest = data['random_forest']
        self.gradient_boost = data['gradient_boost']
        self.scaler = data['scaler']
        self.merchant_scores = data['merchant_scores']
        self.model_version = data['model_version']
        self.last_training = data['last_training']
        self.is_trained = True
        logger.info(f"Models loaded from {path}")

# Example usage
async def main():
    """Example fraud detection"""
    detector = RealTimeFraudDetector()
    
    # Train models
    print("Training fraud detection models...")
    metrics = detector.train_models()
    print(f"Model performance: {metrics}")
    
    # Test transactions
    test_transactions = [
        {
            'customer_id': 'CUST001',
            'amount': 50.00,
            'merchant_id': 'MERCH001',
            'merchant_category': 'grocery',
            'merchant_country': 'US',
            'customer_country': 'US',
            'card_present': True
        },
        {
            'customer_id': 'CUST002',
            'amount': 0.01,  # Suspicious - card testing
            'merchant_id': 'MERCH999',
            'merchant_category': 'online',
            'merchant_country': 'NG',  # High-risk country
            'customer_country': 'US',
            'card_present': False
        },
        {
            'customer_id': 'CUST003',
            'amount': 5000.00,  # Large amount
            'merchant_id': 'MERCH002',
            'merchant_category': 'electronics',
            'merchant_country': 'CN',
            'customer_country': 'US',
            'card_present': False,
            'failed_attempts': 5  # Multiple failed attempts
        }
    ]
    
    print("\nProcessing transactions...")
    for tx in test_transactions:
        is_fraud, probability, details = await detector.predict_fraud(tx)
        
        print(f"\nTransaction: ${tx['amount']:.2f} at {tx['merchant_id']}")
        print(f"  Fraud: {'YES' if is_fraud else 'NO'} (probability: {probability:.2%})")
        print(f"  Risk factors: {details['risk_factors']}")
        print(f"  Processing time: {details['processing_time_ms']:.1f}ms")
    
    # Get metrics
    print(f"\nSystem metrics: {detector.get_metrics()}")

if __name__ == "__main__":
    asyncio.run(main())