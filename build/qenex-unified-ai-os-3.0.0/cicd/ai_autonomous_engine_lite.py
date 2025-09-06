#!/usr/bin/env python3
"""
QENEX AI Autonomous CI/CD Engine - Lightweight Version
Self-learning deployment system (fallback implementation)
Version: 1.0.0-lite
"""

import os
import sys
import json
import random
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('QENEX-AI-CICD-Lite')

# AI Configuration
AI_ROOT = "/opt/qenex-os/cicd/ai"
MODELS_DIR = f"{AI_ROOT}/models"
TRAINING_DATA_DIR = f"{AI_ROOT}/training_data"
METRICS_DIR = f"{AI_ROOT}/metrics"

for directory in [AI_ROOT, MODELS_DIR, TRAINING_DATA_DIR, METRICS_DIR]:
    Path(directory).mkdir(parents=True, exist_ok=True)

class DecisionType(Enum):
    DEPLOYMENT_STRATEGY = "deployment_strategy"
    RESOURCE_ALLOCATION = "resource_allocation"
    ROLLBACK_DECISION = "rollback_decision"
    SCALING_DECISION = "scaling_decision"
    SECURITY_ACTION = "security_action"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"

@dataclass
class TrainingData:
    context: Dict
    action: str
    reward: float
    timestamp: datetime

class AIAutonomousEngineLite:
    """Lightweight AI autonomous engine without ML dependencies"""
    
    def __init__(self):
        self.training_data = []
        self.reward_history = []
        self.is_training = False
        self.learning_rate = 0.001
        self.auto_train_interval = 3600  # 1 hour
        self.decision_cache = {}
        self.performance_metrics = {
            'total_decisions': 0,
            'successful_decisions': 0,
            'average_confidence': 0.75
        }
        
        self._load_training_data()
        self._start_auto_training()
        logger.info("AI Autonomous Engine (Lite) initialized")
    
    def make_decision(self, decision_type: DecisionType, context: Dict) -> Dict:
        """Make an AI-powered decision"""
        self.performance_metrics['total_decisions'] += 1
        
        # Use rule-based logic for decisions since ML isn't available
        decision = self._rule_based_decision(decision_type, context)
        
        # Cache decision for consistency
        cache_key = f"{decision_type.value}_{hash(str(sorted(context.items())))}"
        self.decision_cache[cache_key] = decision
        
        # Record decision for learning
        training_sample = TrainingData(
            context=context,
            action=decision.get('action', 'unknown'),
            reward=0.0,  # Will be updated based on outcome
            timestamp=datetime.now()
        )
        self.training_data.append(training_sample)
        
        logger.info(f"AI decision made: {decision_type.value} -> {decision.get('action')}")
        return decision
    
    def _rule_based_decision(self, decision_type: DecisionType, context: Dict) -> Dict:
        """Rule-based decision making (fallback for ML)"""
        cpu_usage = context.get('cpu_usage', 50)
        memory_usage = context.get('memory_usage', 50)
        error_rate = context.get('error_rate', 0.1)
        response_time = context.get('response_time', 100)
        
        if decision_type == DecisionType.DEPLOYMENT_STRATEGY:
            if error_rate > 5.0:
                return {
                    'action': 'canary_deployment',
                    'confidence': 0.9,
                    'parameters': {'canary_percentage': 10, 'monitor_duration': 300},
                    'reasoning': 'High error rate detected, using cautious canary deployment'
                }
            elif cpu_usage > 80 or memory_usage > 80:
                return {
                    'action': 'blue_green_deployment',
                    'confidence': 0.8,
                    'parameters': {'pre_deploy_checks': True, 'rollback_threshold': 5},
                    'reasoning': 'High resource usage, using blue-green for safety'
                }
            else:
                return {
                    'action': 'rolling_deployment',
                    'confidence': 0.85,
                    'parameters': {'max_unavailable': '25%', 'max_surge': '25%'},
                    'reasoning': 'Normal conditions, using efficient rolling deployment'
                }
        
        elif decision_type == DecisionType.RESOURCE_ALLOCATION:
            if cpu_usage > 70:
                return {
                    'action': 'scale_up_cpu',
                    'confidence': 0.8,
                    'parameters': {'cpu_request': '200m', 'cpu_limit': '500m'},
                    'reasoning': 'High CPU usage detected'
                }
            elif memory_usage > 70:
                return {
                    'action': 'scale_up_memory',
                    'confidence': 0.8,
                    'parameters': {'memory_request': '256Mi', 'memory_limit': '512Mi'},
                    'reasoning': 'High memory usage detected'
                }
            else:
                return {
                    'action': 'maintain_current',
                    'confidence': 0.7,
                    'parameters': {},
                    'reasoning': 'Resource usage within normal range'
                }
        
        elif decision_type == DecisionType.ROLLBACK_DECISION:
            if error_rate > 10.0:
                return {
                    'action': 'immediate_rollback',
                    'confidence': 0.95,
                    'parameters': {'rollback_method': 'instant'},
                    'reasoning': 'Critical error rate, immediate rollback required'
                }
            elif error_rate > 2.0 or response_time > 500:
                return {
                    'action': 'gradual_rollback',
                    'confidence': 0.8,
                    'parameters': {'rollback_percentage': 50},
                    'reasoning': 'Elevated issues detected, gradual rollback'
                }
            else:
                return {
                    'action': 'continue_deployment',
                    'confidence': 0.75,
                    'parameters': {},
                    'reasoning': 'Metrics within acceptable range'
                }
        
        elif decision_type == DecisionType.SCALING_DECISION:
            if cpu_usage > 80 or memory_usage > 80:
                scale_factor = max(2, int((max(cpu_usage, memory_usage) / 50)))
                return {
                    'action': 'scale_out',
                    'confidence': 0.85,
                    'parameters': {'replicas': min(scale_factor, 10), 'scale_up_cooldown': 300},
                    'reasoning': f'High resource usage ({max(cpu_usage, memory_usage)}%), scaling out'
                }
            elif cpu_usage < 30 and memory_usage < 30:
                return {
                    'action': 'scale_in',
                    'confidence': 0.7,
                    'parameters': {'min_replicas': 2, 'scale_down_cooldown': 600},
                    'reasoning': 'Low resource usage, scaling in to optimize costs'
                }
            else:
                return {
                    'action': 'maintain_scale',
                    'confidence': 0.8,
                    'parameters': {},
                    'reasoning': 'Resource usage optimal, maintaining current scale'
                }
        
        elif decision_type == DecisionType.SECURITY_ACTION:
            if error_rate > 15.0:
                return {
                    'action': 'security_lockdown',
                    'confidence': 0.9,
                    'parameters': {'block_duration': 300, 'alert_level': 'critical'},
                    'reasoning': 'Anomalously high error rate may indicate attack'
                }
            else:
                return {
                    'action': 'continue_monitoring',
                    'confidence': 0.6,
                    'parameters': {'alert_threshold': 5.0},
                    'reasoning': 'No immediate security concerns detected'
                }
        
        elif decision_type == DecisionType.PERFORMANCE_OPTIMIZATION:
            optimizations = []
            if response_time > 200:
                optimizations.append('enable_caching')
            if cpu_usage > 60:
                optimizations.append('optimize_cpu_usage')
            if memory_usage > 60:
                optimizations.append('optimize_memory_usage')
            
            if optimizations:
                return {
                    'action': 'apply_optimizations',
                    'confidence': 0.75,
                    'parameters': {'optimizations': optimizations},
                    'reasoning': f'Performance issues detected: {", ".join(optimizations)}'
                }
            else:
                return {
                    'action': 'performance_optimal',
                    'confidence': 0.8,
                    'parameters': {},
                    'reasoning': 'Performance metrics within optimal range'
                }
        
        # Default fallback
        return {
            'action': 'no_action',
            'confidence': 0.5,
            'parameters': {},
            'reasoning': 'Unknown decision type or insufficient context'
        }
    
    def update_reward(self, decision_id: str, reward: float):
        """Update reward for a previous decision"""
        self.reward_history.append(reward)
        if len(self.reward_history) > 100:
            self.reward_history.pop(0)
        
        # Update performance metrics
        if reward > 0:
            self.performance_metrics['successful_decisions'] += 1
        
        # Simple learning: adjust confidence based on reward
        if reward > 0:
            self.performance_metrics['average_confidence'] = min(0.95, 
                self.performance_metrics['average_confidence'] * 1.01)
        else:
            self.performance_metrics['average_confidence'] = max(0.3, 
                self.performance_metrics['average_confidence'] * 0.99)
        
        logger.info(f"Reward updated: {reward}, avg confidence: {self.performance_metrics['average_confidence']:.3f}")
    
    def train_models(self, force: bool = False):
        """Train AI models (simulated)"""
        if self.is_training and not force:
            logger.info("Training already in progress")
            return
        
        self.is_training = True
        logger.info("Starting AI model training (simulated)")
        
        try:
            # Simulate training process
            training_samples = len(self.training_data)
            if training_samples < 10:
                logger.info("Insufficient training data, using synthetic samples")
                self._generate_synthetic_data()
            
            # Simulate training time based on data size
            training_time = min(10, max(1, training_samples / 100))
            time.sleep(training_time)
            
            # Update metrics
            success_rate = len([r for r in self.reward_history if r > 0]) / max(1, len(self.reward_history))
            self.performance_metrics['average_confidence'] = min(0.95, 0.5 + success_rate * 0.4)
            
            logger.info(f"Training completed: {training_samples} samples, confidence: {self.performance_metrics['average_confidence']:.3f}")
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
        finally:
            self.is_training = False
    
    def _generate_synthetic_data(self):
        """Generate synthetic training data"""
        scenarios = [
            ({'cpu_usage': 30, 'memory_usage': 40, 'error_rate': 0.1}, 'rolling_deployment', 0.8),
            ({'cpu_usage': 85, 'memory_usage': 70, 'error_rate': 1.5}, 'blue_green_deployment', 0.9),
            ({'cpu_usage': 60, 'memory_usage': 90, 'error_rate': 8.0}, 'canary_deployment', 0.7),
            ({'cpu_usage': 95, 'memory_usage': 95, 'error_rate': 0.2}, 'scale_out', 0.9),
        ]
        
        for context, action, reward in scenarios:
            sample = TrainingData(
                context=context,
                action=action,
                reward=reward,
                timestamp=datetime.now() - timedelta(hours=random.randint(1, 24))
            )
            self.training_data.append(sample)
            self.reward_history.append(reward)
    
    def _start_auto_training(self):
        """Start automatic training thread"""
        def auto_train():
            while True:
                try:
                    time.sleep(self.auto_train_interval)
                    if len(self.training_data) > 5:  # Minimum samples for training
                        self.train_models()
                except Exception as e:
                    logger.error(f"Auto-training error: {e}")
        
        training_thread = threading.Thread(target=auto_train, daemon=True)
        training_thread.start()
        logger.info(f"Auto-training started (interval: {self.auto_train_interval}s)")
    
    def _load_training_data(self):
        """Load saved training data"""
        data_file = f"{TRAINING_DATA_DIR}/training_data.json"
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                
                for item in data.get('samples', []):
                    sample = TrainingData(
                        context=item['context'],
                        action=item['action'],
                        reward=item['reward'],
                        timestamp=datetime.fromisoformat(item['timestamp'])
                    )
                    self.training_data.append(sample)
                    self.reward_history.append(sample.reward)
                
                logger.info(f"Loaded {len(self.training_data)} training samples")
            except Exception as e:
                logger.error(f"Failed to load training data: {e}")
    
    def _save_training_data(self):
        """Save training data"""
        data_file = f"{TRAINING_DATA_DIR}/training_data.json"
        try:
            data = {
                'samples': [],
                'metrics': self.performance_metrics
            }
            
            # Save recent training data (last 1000 samples)
            recent_samples = self.training_data[-1000:] if len(self.training_data) > 1000 else self.training_data
            for sample in recent_samples:
                data['samples'].append({
                    'context': sample.context,
                    'action': sample.action,
                    'reward': sample.reward,
                    'timestamp': sample.timestamp.isoformat()
                })
            
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save training data: {e}")

# Global instance
ai_engine = None

def get_ai_engine():
    """Get or create AI engine instance"""
    global ai_engine
    if ai_engine is None:
        ai_engine = AIAutonomousEngineLite()
    return ai_engine