#!/usr/bin/env python3
"""
QENEX AI Autonomous CI/CD Engine
Self-learning, continuously training deployment system
Version: 1.0.0
"""

import os
import sys
import json
import numpy as np
import pickle
import threading
import asyncio
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models, optimizers
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import pandas as pd
from collections import deque
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('QENEX-AI-CICD')

# AI Configuration
AI_ROOT = "/opt/qenex-os/cicd/ai"
MODELS_DIR = f"{AI_ROOT}/models"
TRAINING_DATA_DIR = f"{AI_ROOT}/training_data"
CHECKPOINTS_DIR = f"{AI_ROOT}/checkpoints"
METRICS_DIR = f"{AI_ROOT}/metrics"

for directory in [AI_ROOT, MODELS_DIR, TRAINING_DATA_DIR, CHECKPOINTS_DIR, METRICS_DIR]:
    Path(directory).mkdir(parents=True, exist_ok=True)

class DecisionType(Enum):
    DEPLOYMENT_STRATEGY = "deployment_strategy"
    ROLLBACK_DECISION = "rollback_decision"
    SCALING_DECISION = "scaling_decision"
    RESOURCE_ALLOCATION = "resource_allocation"
    PIPELINE_OPTIMIZATION = "pipeline_optimization"
    SECURITY_RESPONSE = "security_response"
    FAILURE_PREDICTION = "failure_prediction"

@dataclass
class DeploymentMetrics:
    success_rate: float
    deployment_time: float
    rollback_count: int
    error_rate: float
    resource_usage: Dict
    user_satisfaction: float
    performance_score: float

@dataclass
class TrainingData:
    timestamp: datetime
    context: Dict
    decision: str
    outcome: Dict
    reward: float

class DeploymentPredictor(nn.Module):
    """PyTorch model for deployment success prediction"""
    
    def __init__(self, input_dim=20, hidden_dim=64):
        super(DeploymentPredictor, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, 32)
        self.fc4 = nn.Linear(32, 3)  # Success, Partial, Failure
        self.dropout = nn.Dropout(0.2)
        self.relu = nn.ReLU()
        
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.relu(self.fc3(x))
        return torch.softmax(self.fc4(x), dim=1)

class ResourceOptimizer(keras.Model):
    """TensorFlow model for resource optimization"""
    
    def __init__(self, input_shape=(15,)):
        super(ResourceOptimizer, self).__init__()
        self.dense1 = layers.Dense(128, activation='relu', input_shape=input_shape)
        self.dropout1 = layers.Dropout(0.3)
        self.dense2 = layers.Dense(64, activation='relu')
        self.dropout2 = layers.Dropout(0.3)
        self.dense3 = layers.Dense(32, activation='relu')
        self.output_layer = layers.Dense(4)  # CPU, Memory, Disk, Network
        
    def call(self, inputs, training=False):
        x = self.dense1(inputs)
        x = self.dropout1(x, training=training)
        x = self.dense2(x)
        x = self.dropout2(x, training=training)
        x = self.dense3(x)
        return self.output_layer(x)

class AutonomousAIEngine:
    """AI-powered autonomous CI/CD decision engine with continuous learning"""
    
    def __init__(self):
        self.deployment_predictor = None
        self.resource_optimizer = None
        self.strategy_selector = None
        self.anomaly_detector = None
        self.training_data = deque(maxlen=10000)
        self.model_versions = {}
        self.current_models = {}
        self.training_thread = None
        self.is_training = False
        self.auto_train_interval = 3600  # 1 hour
        self.min_training_samples = 100
        self.learning_rate = 0.001
        self.reward_history = deque(maxlen=1000)
        
        # Initialize models
        self._initialize_models()
        
        # Load existing models
        self._load_models()
        
        # Start continuous training
        self._start_continuous_training()
    
    def _initialize_models(self):
        """Initialize AI models"""
        # PyTorch deployment predictor
        self.deployment_predictor = DeploymentPredictor()
        self.deployment_optimizer = optim.Adam(
            self.deployment_predictor.parameters(), 
            lr=self.learning_rate
        )
        
        # TensorFlow resource optimizer
        self.resource_optimizer = ResourceOptimizer()
        self.resource_optimizer.compile(
            optimizer=optimizers.Adam(learning_rate=self.learning_rate),
            loss='mse',
            metrics=['mae']
        )
        
        # Scikit-learn strategy selector
        self.strategy_selector = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        # Anomaly detector
        self.anomaly_detector = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5
        )
    
    def make_decision(self, decision_type: DecisionType, context: Dict) -> Dict:
        """Make an autonomous decision based on context"""
        
        # Prepare features
        features = self._extract_features(context)
        
        if decision_type == DecisionType.DEPLOYMENT_STRATEGY:
            return self._decide_deployment_strategy(features, context)
        elif decision_type == DecisionType.ROLLBACK_DECISION:
            return self._decide_rollback(features, context)
        elif decision_type == DecisionType.SCALING_DECISION:
            return self._decide_scaling(features, context)
        elif decision_type == DecisionType.RESOURCE_ALLOCATION:
            return self._decide_resources(features, context)
        elif decision_type == DecisionType.PIPELINE_OPTIMIZATION:
            return self._optimize_pipeline(features, context)
        elif decision_type == DecisionType.SECURITY_RESPONSE:
            return self._respond_to_security(features, context)
        elif decision_type == DecisionType.FAILURE_PREDICTION:
            return self._predict_failure(features, context)
        
        return {'decision': 'default', 'confidence': 0.5}
    
    def _decide_deployment_strategy(self, features: np.ndarray, context: Dict) -> Dict:
        """Decide optimal deployment strategy"""
        
        # Use deployment predictor
        with torch.no_grad():
            input_tensor = torch.FloatTensor(features[:20])
            prediction = self.deployment_predictor(input_tensor.unsqueeze(0))
            success_prob = prediction[0][0].item()
        
        # Select strategy based on risk assessment
        strategies = ['rolling', 'blue_green', 'canary', 'recreate']
        
        if success_prob > 0.9:
            strategy = 'blue_green'  # High confidence, fast switch
        elif success_prob > 0.7:
            strategy = 'rolling'  # Medium confidence, gradual
        elif success_prob > 0.5:
            strategy = 'canary'  # Lower confidence, test first
        else:
            strategy = 'recreate'  # Low confidence, clean slate
        
        # Check if we have enough data to use ML model
        if len(self.training_data) > self.min_training_samples:
            try:
                # Use trained strategy selector
                strategy_features = features[:15].reshape(1, -1)
                strategy_idx = self.strategy_selector.predict(strategy_features)[0]
                strategy = strategies[min(strategy_idx, len(strategies)-1)]
            except:
                pass
        
        decision = {
            'strategy': strategy,
            'confidence': float(success_prob),
            'risk_level': self._calculate_risk(context),
            'estimated_duration': self._estimate_duration(strategy, context),
            'recommendations': self._get_recommendations(strategy, context)
        }
        
        # Record decision for training
        self._record_decision(DecisionType.DEPLOYMENT_STRATEGY, context, decision)
        
        return decision
    
    def _decide_rollback(self, features: np.ndarray, context: Dict) -> Dict:
        """Decide whether to rollback deployment"""
        
        error_rate = context.get('error_rate', 0)
        response_time = context.get('response_time', 0)
        availability = context.get('availability', 100)
        
        # Calculate rollback score
        rollback_score = 0
        
        if error_rate > 5:  # >5% error rate
            rollback_score += 0.4
        if response_time > 1000:  # >1s response time
            rollback_score += 0.3
        if availability < 99:  # <99% availability
            rollback_score += 0.3
        
        # Use anomaly detector
        if self._is_anomaly(features):
            rollback_score += 0.2
        
        should_rollback = rollback_score > 0.6
        
        decision = {
            'rollback': should_rollback,
            'confidence': min(rollback_score, 1.0),
            'reason': self._get_rollback_reason(context),
            'alternative_actions': self._get_alternative_actions(context)
        }
        
        self._record_decision(DecisionType.ROLLBACK_DECISION, context, decision)
        
        return decision
    
    def _decide_scaling(self, features: np.ndarray, context: Dict) -> Dict:
        """Decide scaling requirements"""
        
        cpu_usage = context.get('cpu_usage', 0)
        memory_usage = context.get('memory_usage', 0)
        request_rate = context.get('request_rate', 0)
        queue_length = context.get('queue_length', 0)
        
        # Predict resource needs
        resource_features = np.array([
            cpu_usage, memory_usage, request_rate, queue_length,
            context.get('response_time', 0),
            context.get('error_rate', 0),
            context.get('active_connections', 0),
            context.get('disk_io', 0),
            context.get('network_io', 0),
            context.get('cache_hit_rate', 0),
            context.get('database_connections', 0),
            context.get('thread_count', 0),
            context.get('gc_time', 0),
            context.get('heap_usage', 0),
            context.get('time_of_day', 0)
        ]).reshape(1, -1)
        
        predicted_resources = self.resource_optimizer.predict(resource_features)[0]
        
        current_replicas = context.get('current_replicas', 1)
        
        # Calculate optimal replicas
        cpu_replicas = max(1, int(predicted_resources[0] / 80))  # Target 80% CPU
        mem_replicas = max(1, int(predicted_resources[1] / 70))  # Target 70% memory
        
        target_replicas = max(cpu_replicas, mem_replicas)
        
        # Apply smoothing to avoid flapping
        if abs(target_replicas - current_replicas) <= 1:
            target_replicas = current_replicas
        
        decision = {
            'action': 'scale' if target_replicas != current_replicas else 'maintain',
            'current_replicas': current_replicas,
            'target_replicas': target_replicas,
            'predicted_cpu': float(predicted_resources[0]),
            'predicted_memory': float(predicted_resources[1]),
            'confidence': self._calculate_confidence(features)
        }
        
        self._record_decision(DecisionType.SCALING_DECISION, context, decision)
        
        return decision
    
    def _decide_resources(self, features: np.ndarray, context: Dict) -> Dict:
        """Decide resource allocation"""
        
        workload_type = context.get('workload_type', 'general')
        priority = context.get('priority', 'normal')
        
        # Base resource allocation
        resources = {
            'cpu': 1.0,
            'memory': 2048,
            'disk': 10240,
            'network': 1000
        }
        
        # Adjust based on workload type
        if workload_type == 'compute':
            resources['cpu'] *= 2
        elif workload_type == 'memory':
            resources['memory'] *= 2
        elif workload_type == 'io':
            resources['disk'] *= 2
            resources['network'] *= 1.5
        
        # Adjust based on priority
        if priority == 'high':
            for key in resources:
                resources[key] *= 1.5
        elif priority == 'critical':
            for key in resources:
                resources[key] *= 2
        
        # Use ML model for fine-tuning
        resource_features = features[:15].reshape(1, -1)
        predicted = self.resource_optimizer.predict(resource_features)[0]
        
        # Blend predictions with heuristics
        resources['cpu'] = (resources['cpu'] + predicted[0]) / 2
        resources['memory'] = (resources['memory'] + predicted[1]) / 2
        
        decision = {
            'resources': resources,
            'workload_type': workload_type,
            'priority': priority,
            'optimization_applied': True
        }
        
        self._record_decision(DecisionType.RESOURCE_ALLOCATION, context, decision)
        
        return decision
    
    def _optimize_pipeline(self, features: np.ndarray, context: Dict) -> Dict:
        """Optimize CI/CD pipeline configuration"""
        
        pipeline_history = context.get('history', [])
        current_duration = context.get('current_duration', 0)
        
        optimizations = []
        
        # Analyze historical data
        if pipeline_history:
            avg_duration = np.mean([h['duration'] for h in pipeline_history])
            
            # Identify bottlenecks
            stage_durations = {}
            for run in pipeline_history:
                for stage, duration in run.get('stages', {}).items():
                    if stage not in stage_durations:
                        stage_durations[stage] = []
                    stage_durations[stage].append(duration)
            
            # Find slowest stages
            for stage, durations in stage_durations.items():
                avg = np.mean(durations)
                if avg > avg_duration * 0.3:  # Stage takes >30% of total time
                    optimizations.append({
                        'type': 'parallelize',
                        'stage': stage,
                        'potential_saving': avg * 0.5
                    })
        
        # Cache optimization
        if context.get('cache_hit_rate', 0) < 0.5:
            optimizations.append({
                'type': 'improve_caching',
                'current_hit_rate': context.get('cache_hit_rate', 0),
                'target_hit_rate': 0.8
            })
        
        # Test optimization
        if context.get('test_duration', 0) > current_duration * 0.4:
            optimizations.append({
                'type': 'optimize_tests',
                'suggestion': 'parallel_execution',
                'potential_saving': context.get('test_duration', 0) * 0.6
            })
        
        decision = {
            'optimizations': optimizations,
            'estimated_improvement': sum(o.get('potential_saving', 0) for o in optimizations),
            'priority': self._calculate_optimization_priority(optimizations)
        }
        
        self._record_decision(DecisionType.PIPELINE_OPTIMIZATION, context, decision)
        
        return decision
    
    def _respond_to_security(self, features: np.ndarray, context: Dict) -> Dict:
        """Respond to security threats"""
        
        threat_level = context.get('threat_level', 'low')
        threat_type = context.get('threat_type', 'unknown')
        
        response = {
            'action': 'monitor',
            'isolation': False,
            'rollback': False,
            'alert': False
        }
        
        if threat_level == 'critical':
            response['action'] = 'isolate_and_rollback'
            response['isolation'] = True
            response['rollback'] = True
            response['alert'] = True
        elif threat_level == 'high':
            response['action'] = 'isolate'
            response['isolation'] = True
            response['alert'] = True
        elif threat_level == 'medium':
            response['action'] = 'restrict'
            response['alert'] = True
        
        # Specific responses based on threat type
        if threat_type == 'injection':
            response['additional_actions'] = ['sanitize_inputs', 'update_waf_rules']
        elif threat_type == 'ddos':
            response['additional_actions'] = ['enable_rate_limiting', 'scale_up']
        elif threat_type == 'unauthorized_access':
            response['additional_actions'] = ['revoke_tokens', 'force_reauth']
        
        decision = {
            'response': response,
            'confidence': self._calculate_threat_confidence(context),
            'estimated_mitigation_time': self._estimate_mitigation_time(threat_type)
        }
        
        self._record_decision(DecisionType.SECURITY_RESPONSE, context, decision)
        
        return decision
    
    def _predict_failure(self, features: np.ndarray, context: Dict) -> Dict:
        """Predict potential failures"""
        
        # Use deployment predictor for failure prediction
        with torch.no_grad():
            input_tensor = torch.FloatTensor(features[:20])
            prediction = self.deployment_predictor(input_tensor.unsqueeze(0))
            failure_prob = prediction[0][2].item()  # Failure class
        
        # Identify failure indicators
        indicators = []
        
        if context.get('error_rate', 0) > 1:
            indicators.append('increasing_errors')
        if context.get('response_time', 0) > 500:
            indicators.append('slow_response')
        if context.get('memory_usage', 0) > 90:
            indicators.append('memory_pressure')
        if context.get('disk_usage', 0) > 85:
            indicators.append('disk_space')
        
        # Predict time to failure
        if failure_prob > 0.7:
            time_to_failure = 5  # minutes
        elif failure_prob > 0.5:
            time_to_failure = 30
        elif failure_prob > 0.3:
            time_to_failure = 120
        else:
            time_to_failure = None
        
        decision = {
            'failure_probability': float(failure_prob),
            'indicators': indicators,
            'time_to_failure': time_to_failure,
            'preventive_actions': self._get_preventive_actions(indicators),
            'confidence': float(1 - abs(failure_prob - 0.5) * 2)  # Confidence peaks at 0.5
        }
        
        self._record_decision(DecisionType.FAILURE_PREDICTION, context, decision)
        
        return decision
    
    def train_models(self, force: bool = False):
        """Train or update models with collected data"""
        
        if self.is_training and not force:
            logger.info("Training already in progress")
            return
        
        if len(self.training_data) < self.min_training_samples and not force:
            logger.info(f"Not enough training data: {len(self.training_data)}/{self.min_training_samples}")
            return
        
        self.is_training = True
        
        try:
            # Prepare training data
            X, y_deployment, y_resource, y_strategy = self._prepare_training_data()
            
            if X is not None and len(X) > 0:
                # Train deployment predictor (PyTorch)
                self._train_deployment_predictor(X, y_deployment)
                
                # Train resource optimizer (TensorFlow)
                self._train_resource_optimizer(X, y_resource)
                
                # Train strategy selector (Scikit-learn)
                self._train_strategy_selector(X, y_strategy)
                
                # Save models
                self._save_models()
                
                logger.info("Model training completed successfully")
        
        except Exception as e:
            logger.error(f"Training failed: {e}")
        
        finally:
            self.is_training = False
    
    def _train_deployment_predictor(self, X: np.ndarray, y: np.ndarray):
        """Train PyTorch deployment predictor"""
        
        # Convert to tensors
        X_tensor = torch.FloatTensor(X[:, :20])  # Use first 20 features
        y_tensor = torch.LongTensor(y)
        
        # Create dataset and dataloader
        dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
        
        # Training loop
        criterion = nn.CrossEntropyLoss()
        
        for epoch in range(10):
            total_loss = 0
            for batch_X, batch_y in dataloader:
                self.deployment_optimizer.zero_grad()
                
                outputs = self.deployment_predictor(batch_X)
                loss = criterion(outputs, batch_y)
                
                loss.backward()
                self.deployment_optimizer.step()
                
                total_loss += loss.item()
            
            if epoch % 5 == 0:
                logger.info(f"Deployment predictor - Epoch {epoch}, Loss: {total_loss/len(dataloader):.4f}")
    
    def _train_resource_optimizer(self, X: np.ndarray, y: np.ndarray):
        """Train TensorFlow resource optimizer"""
        
        X_train = X[:, :15]  # Use first 15 features
        
        # Train model
        history = self.resource_optimizer.fit(
            X_train, y,
            epochs=20,
            batch_size=32,
            validation_split=0.2,
            verbose=0
        )
        
        logger.info(f"Resource optimizer - Final loss: {history.history['loss'][-1]:.4f}")
    
    def _train_strategy_selector(self, X: np.ndarray, y: np.ndarray):
        """Train strategy selector"""
        
        X_train = X[:, :15]  # Use first 15 features
        
        # Train model
        self.strategy_selector.fit(X_train, y)
        
        # Calculate accuracy
        accuracy = self.strategy_selector.score(X_train, y)
        logger.info(f"Strategy selector - Accuracy: {accuracy:.4f}")
    
    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for training"""
        
        if not self.training_data:
            return None, None, None, None
        
        # Convert training data to arrays
        X = []
        y_deployment = []
        y_resource = []
        y_strategy = []
        
        for data in self.training_data:
            features = self._extract_features(data.context)
            X.append(features)
            
            # Deployment outcome (0: success, 1: partial, 2: failure)
            outcome = data.outcome.get('deployment_result', 'success')
            if outcome == 'success':
                y_deployment.append(0)
            elif outcome == 'partial':
                y_deployment.append(1)
            else:
                y_deployment.append(2)
            
            # Resource usage
            resources = [
                data.outcome.get('cpu_usage', 50),
                data.outcome.get('memory_usage', 50),
                data.outcome.get('disk_usage', 30),
                data.outcome.get('network_usage', 20)
            ]
            y_resource.append(resources)
            
            # Strategy (0: rolling, 1: blue_green, 2: canary, 3: recreate)
            strategy_map = {'rolling': 0, 'blue_green': 1, 'canary': 2, 'recreate': 3}
            strategy = data.decision.get('strategy', 'rolling')
            y_strategy.append(strategy_map.get(strategy, 0))
        
        return (
            np.array(X),
            np.array(y_deployment),
            np.array(y_resource),
            np.array(y_strategy)
        )
    
    def _extract_features(self, context: Dict) -> np.ndarray:
        """Extract features from context"""
        
        features = [
            context.get('cpu_usage', 0),
            context.get('memory_usage', 0),
            context.get('disk_usage', 0),
            context.get('network_usage', 0),
            context.get('error_rate', 0),
            context.get('response_time', 0),
            context.get('request_rate', 0),
            context.get('queue_length', 0),
            context.get('active_connections', 0),
            context.get('availability', 100),
            context.get('deployment_frequency', 1),
            context.get('rollback_rate', 0),
            context.get('test_coverage', 0),
            context.get('code_complexity', 0),
            context.get('dependencies_count', 0),
            context.get('container_restarts', 0),
            context.get('pod_count', 1),
            context.get('service_count', 1),
            context.get('ingress_count', 0),
            context.get('config_changes', 0),
            context.get('security_score', 100),
            context.get('compliance_score', 100),
            context.get('user_satisfaction', 100),
            context.get('business_impact', 50),
            context.get('time_of_day', datetime.now().hour)
        ]
        
        return np.array(features)
    
    def _record_decision(self, decision_type: DecisionType, context: Dict, decision: Dict):
        """Record decision for future training"""
        
        training_data = TrainingData(
            timestamp=datetime.now(),
            context=context,
            decision=decision,
            outcome={},  # Will be updated when outcome is known
            reward=0.0  # Will be calculated based on outcome
        )
        
        self.training_data.append(training_data)
    
    def update_outcome(self, decision_id: str, outcome: Dict):
        """Update decision outcome for learning"""
        
        # Find the decision in training data
        for data in self.training_data:
            if data.timestamp.isoformat() == decision_id:
                data.outcome = outcome
                data.reward = self._calculate_reward(data.decision, outcome)
                self.reward_history.append(data.reward)
                break
    
    def _calculate_reward(self, decision: Dict, outcome: Dict) -> float:
        """Calculate reward for reinforcement learning"""
        
        reward = 0.0
        
        # Success/failure reward
        if outcome.get('success', False):
            reward += 1.0
        else:
            reward -= 0.5
        
        # Performance reward
        if outcome.get('response_time', float('inf')) < 100:
            reward += 0.2
        
        # Stability reward
        if outcome.get('error_rate', 100) < 1:
            reward += 0.3
        
        # Resource efficiency reward
        if outcome.get('resource_efficiency', 0) > 0.8:
            reward += 0.2
        
        return reward
    
    def _start_continuous_training(self):
        """Start continuous training loop"""
        
        def training_loop():
            while True:
                try:
                    # Wait for training interval
                    asyncio.run(asyncio.sleep(self.auto_train_interval))
                    
                    # Check if we have new data
                    if len(self.training_data) > self.min_training_samples:
                        logger.info("Starting automatic model training...")
                        self.train_models()
                        
                        # Adjust learning rate based on performance
                        self._adjust_learning_rate()
                        
                        # Prune old training data if needed
                        if len(self.training_data) > 5000:
                            # Keep only recent data
                            self.training_data = deque(
                                list(self.training_data)[-3000:],
                                maxlen=10000
                            )
                
                except Exception as e:
                    logger.error(f"Error in continuous training: {e}")
        
        self.training_thread = threading.Thread(target=training_loop, daemon=True)
        self.training_thread.start()
    
    def _adjust_learning_rate(self):
        """Adjust learning rate based on performance"""
        
        if len(self.reward_history) > 100:
            recent_rewards = list(self.reward_history)[-100:]
            avg_reward = np.mean(recent_rewards)
            
            if avg_reward > 0.7:
                # Good performance, reduce learning rate
                self.learning_rate *= 0.95
            elif avg_reward < 0.3:
                # Poor performance, increase learning rate
                self.learning_rate *= 1.05
            
            # Keep learning rate in reasonable bounds
            self.learning_rate = max(0.0001, min(0.01, self.learning_rate))
            
            # Update optimizers
            for param_group in self.deployment_optimizer.param_groups:
                param_group['lr'] = self.learning_rate
            
            self.resource_optimizer.optimizer.learning_rate = self.learning_rate
    
    def _save_models(self):
        """Save trained models"""
        
        # Save PyTorch model
        torch.save({
            'model_state_dict': self.deployment_predictor.state_dict(),
            'optimizer_state_dict': self.deployment_optimizer.state_dict(),
        }, f"{MODELS_DIR}/deployment_predictor.pt")
        
        # Save TensorFlow model
        self.resource_optimizer.save(f"{MODELS_DIR}/resource_optimizer")
        
        # Save Scikit-learn model
        with open(f"{MODELS_DIR}/strategy_selector.pkl", 'wb') as f:
            pickle.dump(self.strategy_selector, f)
        
        # Save training metadata
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'training_samples': len(self.training_data),
            'learning_rate': self.learning_rate,
            'avg_reward': float(np.mean(list(self.reward_history))) if self.reward_history else 0
        }
        
        with open(f"{MODELS_DIR}/metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _load_models(self):
        """Load saved models"""
        
        try:
            # Load PyTorch model
            checkpoint = torch.load(f"{MODELS_DIR}/deployment_predictor.pt")
            self.deployment_predictor.load_state_dict(checkpoint['model_state_dict'])
            self.deployment_optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            
            # Load TensorFlow model
            self.resource_optimizer = keras.models.load_model(f"{MODELS_DIR}/resource_optimizer")
            
            # Load Scikit-learn model
            with open(f"{MODELS_DIR}/strategy_selector.pkl", 'rb') as f:
                self.strategy_selector = pickle.load(f)
            
            logger.info("Models loaded successfully")
        
        except Exception as e:
            logger.info(f"No saved models found or error loading: {e}")
    
    # Helper methods
    def _is_anomaly(self, features: np.ndarray) -> bool:
        """Detect anomalies in features"""
        # Simple threshold-based anomaly detection
        # Can be replaced with more sophisticated methods
        return np.any(np.abs(features) > 3)  # 3 standard deviations
    
    def _calculate_risk(self, context: Dict) -> str:
        """Calculate deployment risk level"""
        risk_score = 0
        
        if context.get('test_coverage', 0) < 60:
            risk_score += 30
        if context.get('rollback_rate', 0) > 10:
            risk_score += 25
        if context.get('code_complexity', 0) > 15:
            risk_score += 20
        if context.get('dependencies_count', 0) > 50:
            risk_score += 15
        if context.get('security_score', 100) < 80:
            risk_score += 10
        
        if risk_score < 30:
            return 'low'
        elif risk_score < 60:
            return 'medium'
        else:
            return 'high'
    
    def _estimate_duration(self, strategy: str, context: Dict) -> int:
        """Estimate deployment duration in minutes"""
        base_duration = {
            'rolling': 15,
            'blue_green': 5,
            'canary': 30,
            'recreate': 10
        }
        
        duration = base_duration.get(strategy, 10)
        
        # Adjust based on context
        if context.get('service_count', 1) > 5:
            duration *= 1.5
        if context.get('database_migration', False):
            duration += 10
        
        return int(duration)
    
    def _get_recommendations(self, strategy: str, context: Dict) -> List[str]:
        """Get deployment recommendations"""
        recommendations = []
        
        if context.get('test_coverage', 0) < 80:
            recommendations.append("Increase test coverage before deployment")
        
        if strategy == 'canary' and context.get('monitoring_setup', False) == False:
            recommendations.append("Set up monitoring for canary deployment")
        
        if context.get('backup_configured', False) == False:
            recommendations.append("Configure backup before deployment")
        
        return recommendations
    
    def _get_rollback_reason(self, context: Dict) -> str:
        """Get reason for rollback decision"""
        reasons = []
        
        if context.get('error_rate', 0) > 5:
            reasons.append(f"High error rate: {context['error_rate']}%")
        if context.get('response_time', 0) > 1000:
            reasons.append(f"Slow response time: {context['response_time']}ms")
        if context.get('availability', 100) < 99:
            reasons.append(f"Low availability: {context['availability']}%")
        
        return "; ".join(reasons) if reasons else "Precautionary rollback"
    
    def _get_alternative_actions(self, context: Dict) -> List[str]:
        """Get alternative actions to rollback"""
        actions = []
        
        if context.get('error_rate', 0) > 5:
            actions.append("Scale up instances")
            actions.append("Enable circuit breaker")
        
        if context.get('response_time', 0) > 1000:
            actions.append("Increase cache TTL")
            actions.append("Optimize database queries")
        
        return actions
    
    def _calculate_confidence(self, features: np.ndarray) -> float:
        """Calculate decision confidence"""
        # Simple confidence based on data availability
        non_zero = np.count_nonzero(features)
        return min(non_zero / len(features), 1.0)
    
    def _calculate_optimization_priority(self, optimizations: List[Dict]) -> str:
        """Calculate optimization priority"""
        total_saving = sum(o.get('potential_saving', 0) for o in optimizations)
        
        if total_saving > 100:
            return 'high'
        elif total_saving > 50:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_threat_confidence(self, context: Dict) -> float:
        """Calculate threat detection confidence"""
        indicators = 0
        
        if context.get('anomaly_score', 0) > 0.7:
            indicators += 1
        if context.get('known_signature', False):
            indicators += 1
        if context.get('multiple_sources', False):
            indicators += 1
        
        return min(indicators / 3, 1.0)
    
    def _estimate_mitigation_time(self, threat_type: str) -> int:
        """Estimate threat mitigation time in minutes"""
        mitigation_times = {
            'injection': 5,
            'ddos': 15,
            'unauthorized_access': 10,
            'malware': 30,
            'data_breach': 60
        }
        
        return mitigation_times.get(threat_type, 20)
    
    def _get_preventive_actions(self, indicators: List[str]) -> List[str]:
        """Get preventive actions based on indicators"""
        actions = []
        
        if 'increasing_errors' in indicators:
            actions.append("Review recent changes")
            actions.append("Increase monitoring")
        
        if 'memory_pressure' in indicators:
            actions.append("Analyze memory leaks")
            actions.append("Scale up memory")
        
        if 'disk_space' in indicators:
            actions.append("Clean up logs")
            actions.append("Archive old data")
        
        return actions

# Global AI engine instance
ai_engine = None

def get_ai_engine():
    """Get or create AI engine instance"""
    global ai_engine
    if ai_engine is None:
        ai_engine = AutonomousAIEngine()
    return ai_engine

if __name__ == '__main__':
    engine = get_ai_engine()
    logger.info("QENEX AI Autonomous Engine started with continuous training")