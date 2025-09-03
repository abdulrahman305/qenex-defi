#!/usr/bin/env python3
"""
QENEX Continuous AI Learning System - Core OS Component
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import numpy as np
import sqlite3
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import hashlib
from typing import Dict, List, Any, Tuple
import threading
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExperienceBuffer(Dataset):
    """Stores system experiences for continuous learning"""
    
    def __init__(self, capacity=100000):
        self.capacity = capacity
        self.buffer = []
        self.position = 0
        self.lock = threading.Lock()
        
    def push(self, state, action, reward, next_state):
        """Add experience to buffer"""
        with self.lock:
            if len(self.buffer) < self.capacity:
                self.buffer.append(None)
            self.buffer[self.position] = (state, action, reward, next_state)
            self.position = (self.position + 1) % self.capacity
    
    def sample(self, batch_size):
        """Sample batch for training"""
        with self.lock:
            indices = np.random.choice(len(self.buffer), batch_size, replace=False)
            return [self.buffer[i] for i in indices]
    
    def __len__(self):
        return len(self.buffer)
    
    def __getitem__(self, idx):
        return self.buffer[idx]

class AdaptiveModel(nn.Module):
    """Self-improving neural network that learns continuously"""
    
    def __init__(self, input_dim=128, hidden_dim=256, output_dim=64):
        super(AdaptiveModel, self).__init__()
        
        # Main network
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        
        # Task-specific heads
        self.pipeline_head = nn.Linear(hidden_dim, 3)  # success/fail/timeout
        self.resource_head = nn.Linear(hidden_dim, 4)  # cpu/mem/disk/network
        self.anomaly_head = nn.Linear(hidden_dim, 2)  # normal/anomaly
        self.optimization_head = nn.Linear(hidden_dim, output_dim)
        
        # Attention mechanism for feature importance
        self.attention = nn.MultiheadAttention(hidden_dim, num_heads=8)
        
        # Meta-learning parameters
        self.meta_learner = nn.LSTM(hidden_dim, hidden_dim, batch_first=True)
        
        self.version = 1.0
        self.training_iterations = 0
        
    def forward(self, x, task='pipeline'):
        """Forward pass with task-specific output"""
        # Encode features
        features = self.encoder(x)
        
        # Apply attention for feature selection
        attn_output, _ = self.attention(features.unsqueeze(0), 
                                        features.unsqueeze(0), 
                                        features.unsqueeze(0))
        features = features + attn_output.squeeze(0)
        
        # Task-specific outputs
        if task == 'pipeline':
            return self.pipeline_head(features)
        elif task == 'resource':
            return self.resource_head(features)
        elif task == 'anomaly':
            return self.anomaly_head(features)
        else:
            return self.optimization_head(features)
    
    def adapt(self, loss_gradient):
        """Adapt model parameters based on recent performance"""
        with torch.no_grad():
            for param in self.parameters():
                if param.grad is not None:
                    # Meta-learning update
                    param.data -= 0.001 * loss_gradient * param.grad

class ContinuousLearningEngine:
    """Core continuous learning system for QENEX OS"""
    
    def __init__(self):
        self.model = AdaptiveModel()
        self.optimizer = optim.AdamW(self.model.parameters(), lr=0.001)
        self.scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            self.optimizer, T_0=1000, T_mult=2
        )
        
        self.experience_buffer = ExperienceBuffer()
        self.model_checkpoint_dir = Path("/opt/qenex-os/ai/checkpoints")
        self.model_checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.training_queue = queue.Queue()
        self.is_training = False
        self.performance_history = []
        
        # Load existing model if available
        self.load_latest_model()
        
        # Start continuous training thread
        self.training_thread = threading.Thread(target=self._training_loop, daemon=True)
        self.training_thread.start()
        
        # Start experience collection
        self.collection_thread = threading.Thread(target=self._collect_experiences, daemon=True)
        self.collection_thread.start()
    
    def _collect_experiences(self):
        """Continuously collect system experiences"""
        while True:
            try:
                # Collect from database
                conn = sqlite3.connect('/opt/qenex-os/data/qenex.db')
                cursor = conn.cursor()
                
                # Get recent pipeline executions
                cursor.execute("""
                    SELECT p.*, 
                           COUNT(ps.id) as stage_count,
                           AVG(ps.duration_seconds) as avg_stage_duration
                    FROM pipelines p
                    LEFT JOIN pipeline_stages ps ON p.id = ps.pipeline_id
                    WHERE p.completed_at > datetime('now', '-1 hour')
                    GROUP BY p.id
                    ORDER BY p.completed_at DESC
                    LIMIT 100
                """)
                
                pipelines = cursor.fetchall()
                
                for pipeline in pipelines:
                    # Extract features
                    state = self._extract_pipeline_features(pipeline)
                    
                    # Determine reward
                    reward = self._calculate_reward(pipeline)
                    
                    # Store experience
                    self.experience_buffer.push(
                        state=state,
                        action=np.zeros(64),  # Placeholder for action
                        reward=reward,
                        next_state=state  # Simplified for now
                    )
                
                # Get system metrics
                cursor.execute("""
                    SELECT * FROM metrics 
                    WHERE timestamp > datetime('now', '-10 minutes')
                    ORDER BY timestamp DESC
                """)
                
                metrics = cursor.fetchall()
                for metric in metrics:
                    state = self._extract_metric_features(metric)
                    self.training_queue.put(('metric', state))
                
                conn.close()
                
            except Exception as e:
                logger.error(f"Experience collection error: {e}")
            
            # Collect every 30 seconds
            asyncio.run(asyncio.sleep(30))
    
    def _training_loop(self):
        """Continuous training loop"""
        while True:
            try:
                if len(self.experience_buffer) > 1000:
                    self.is_training = True
                    
                    # Sample batch
                    batch = self.experience_buffer.sample(min(64, len(self.experience_buffer)))
                    
                    # Prepare data
                    states = torch.FloatTensor([e[0] for e in batch])
                    rewards = torch.FloatTensor([e[2] for e in batch])
                    
                    # Training step
                    self.model.train()
                    
                    # Multi-task learning
                    tasks = ['pipeline', 'resource', 'anomaly', 'optimization']
                    total_loss = 0
                    
                    for task in tasks:
                        outputs = self.model(states, task=task)
                        
                        # Task-specific loss
                        if task == 'pipeline':
                            targets = (rewards > 0).long()
                            if len(targets.shape) == 1:
                                targets = targets.unsqueeze(1).expand(-1, 3)
                            loss = nn.CrossEntropyLoss()(outputs, targets[:, 0])
                        elif task == 'resource':
                            targets = torch.randn_like(outputs)  # Placeholder
                            loss = nn.MSELoss()(outputs, targets)
                        elif task == 'anomaly':
                            targets = (rewards < -0.5).long()
                            loss = nn.CrossEntropyLoss()(outputs, targets)
                        else:
                            targets = torch.randn_like(outputs)  # Placeholder
                            loss = nn.MSELoss()(outputs, targets)
                        
                        total_loss += loss
                    
                    # Backpropagation
                    self.optimizer.zero_grad()
                    total_loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    self.optimizer.step()
                    self.scheduler.step()
                    
                    # Meta-learning adaptation
                    self.model.adapt(total_loss.detach())
                    
                    # Update metrics
                    self.model.training_iterations += 1
                    self.performance_history.append({
                        'iteration': self.model.training_iterations,
                        'loss': total_loss.item(),
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Periodic checkpoint
                    if self.model.training_iterations % 100 == 0:
                        self.save_checkpoint()
                        logger.info(f"Training iteration {self.model.training_iterations}, Loss: {total_loss.item():.4f}")
                    
                    # Evaluate and potentially update production model
                    if self.model.training_iterations % 500 == 0:
                        self.evaluate_and_deploy()
                    
                    self.is_training = False
                
            except Exception as e:
                logger.error(f"Training error: {e}")
                self.is_training = False
            
            # Small delay between training iterations
            asyncio.run(asyncio.sleep(5))
    
    def _extract_pipeline_features(self, pipeline) -> np.ndarray:
        """Extract features from pipeline data"""
        features = []
        
        # Basic features
        features.append(1.0 if pipeline[5] == 'success' else 0.0)  # status
        features.append(pipeline[9] if pipeline[9] else 0.0)  # duration
        features.append(len(pipeline[2]) if pipeline[2] else 0)  # repo name length
        features.append(1.0 if pipeline[3] == 'main' else 0.0)  # is main branch
        
        # Time features
        if pipeline[7]:  # started_at
            hour = datetime.fromisoformat(pipeline[7]).hour
            features.append(hour / 24.0)
            features.append(1.0 if hour >= 9 and hour <= 17 else 0.0)  # business hours
        else:
            features.extend([0.0, 0.0])
        
        # Pad to 128 dimensions
        while len(features) < 128:
            features.append(0.0)
        
        return np.array(features[:128], dtype=np.float32)
    
    def _extract_metric_features(self, metric) -> np.ndarray:
        """Extract features from metric data"""
        features = []
        
        # Parse metric value
        features.append(metric[4] if metric[4] else 0.0)  # value
        
        # Parse labels if JSON
        try:
            labels = json.loads(metric[5]) if metric[5] else {}
            for key in ['cpu', 'memory', 'disk', 'network']:
                features.append(labels.get(key, 0.0))
        except:
            features.extend([0.0] * 4)
        
        # Pad to 128 dimensions
        while len(features) < 128:
            features.append(0.0)
        
        return np.array(features[:128], dtype=np.float32)
    
    def _calculate_reward(self, pipeline) -> float:
        """Calculate reward for reinforcement learning"""
        reward = 0.0
        
        # Success/failure reward
        if pipeline[5] == 'success':
            reward += 1.0
        elif pipeline[5] == 'failed':
            reward -= 1.0
        
        # Duration reward (faster is better)
        if pipeline[9]:  # duration_seconds
            if pipeline[9] < 60:
                reward += 0.5
            elif pipeline[9] > 300:
                reward -= 0.5
        
        return reward
    
    def predict(self, features: np.ndarray, task: str = 'pipeline') -> Dict[str, Any]:
        """Make prediction using current model"""
        self.model.eval()
        
        with torch.no_grad():
            input_tensor = torch.FloatTensor(features).unsqueeze(0)
            output = self.model(input_tensor, task=task)
            
            if task == 'pipeline':
                probs = torch.softmax(output, dim=1).squeeze().numpy()
                prediction = {
                    'success_probability': float(probs[0]),
                    'failure_probability': float(probs[1]),
                    'timeout_probability': float(probs[2]),
                    'recommendation': self._generate_recommendation(probs)
                }
            elif task == 'anomaly':
                probs = torch.softmax(output, dim=1).squeeze().numpy()
                prediction = {
                    'is_anomaly': bool(probs[1] > 0.5),
                    'anomaly_score': float(probs[1]),
                    'confidence': float(max(probs))
                }
            else:
                prediction = {
                    'values': output.squeeze().numpy().tolist()
                }
        
        return prediction
    
    def _generate_recommendation(self, probs: np.ndarray) -> str:
        """Generate recommendation based on predictions"""
        if probs[0] > 0.8:
            return "High success probability - proceed with deployment"
        elif probs[1] > 0.5:
            return "High failure risk - review code and add more tests"
        elif probs[2] > 0.3:
            return "Timeout risk - consider optimizing or increasing limits"
        else:
            return "Moderate risk - monitor closely during execution"
    
    def save_checkpoint(self):
        """Save model checkpoint with versioning"""
        checkpoint = {
            'model_state': self.model.state_dict(),
            'optimizer_state': self.optimizer.state_dict(),
            'scheduler_state': self.scheduler.state_dict(),
            'version': self.model.version,
            'iterations': self.model.training_iterations,
            'timestamp': datetime.now().isoformat(),
            'performance': self.performance_history[-100:] if self.performance_history else []
        }
        
        # Version-based filename
        filename = f"model_v{self.model.version:.1f}_{self.model.training_iterations}.pt"
        path = self.model_checkpoint_dir / filename
        
        torch.save(checkpoint, path)
        
        # Keep only last 10 checkpoints
        checkpoints = sorted(self.model_checkpoint_dir.glob("model_*.pt"))
        if len(checkpoints) > 10:
            for old_checkpoint in checkpoints[:-10]:
                old_checkpoint.unlink()
        
        logger.info(f"Checkpoint saved: {filename}")
    
    def load_latest_model(self):
        """Load the most recent model checkpoint"""
        checkpoints = sorted(self.model_checkpoint_dir.glob("model_*.pt"))
        
        if checkpoints:
            latest = checkpoints[-1]
            checkpoint = torch.load(latest, map_location='cpu')
            
            self.model.load_state_dict(checkpoint['model_state'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state'])
            self.scheduler.load_state_dict(checkpoint['scheduler_state'])
            self.model.version = checkpoint.get('version', 1.0)
            self.model.training_iterations = checkpoint.get('iterations', 0)
            self.performance_history = checkpoint.get('performance', [])
            
            logger.info(f"Loaded model v{self.model.version} with {self.model.training_iterations} iterations")
    
    def evaluate_and_deploy(self):
        """Evaluate model and deploy if performance improved"""
        try:
            # Simple evaluation metric
            recent_loss = np.mean([h['loss'] for h in self.performance_history[-10:]])
            previous_loss = np.mean([h['loss'] for h in self.performance_history[-20:-10]]) if len(self.performance_history) > 20 else float('inf')
            
            if recent_loss < previous_loss * 0.95:  # 5% improvement threshold
                self.model.version += 0.1
                self.save_checkpoint()
                
                # Deploy to production
                production_path = self.model_checkpoint_dir / "production_model.pt"
                torch.save(self.model.state_dict(), production_path)
                
                logger.info(f"Deployed new model v{self.model.version} with {recent_loss:.4f} loss (improved from {previous_loss:.4f})")
                
                # Notify system
                self._notify_model_update()
        
        except Exception as e:
            logger.error(f"Evaluation error: {e}")
    
    def _notify_model_update(self):
        """Notify system about model update"""
        try:
            with open('/opt/qenex-os/data/model_status.json', 'w') as f:
                json.dump({
                    'version': self.model.version,
                    'iterations': self.model.training_iterations,
                    'updated_at': datetime.now().isoformat(),
                    'status': 'active',
                    'performance': {
                        'recent_loss': np.mean([h['loss'] for h in self.performance_history[-10:]]) if self.performance_history else None,
                        'improvement': True
                    }
                }, f)
        except Exception as e:
            logger.error(f"Failed to update model status: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current learning system status"""
        return {
            'model_version': self.model.version,
            'training_iterations': self.model.training_iterations,
            'is_training': self.is_training,
            'buffer_size': len(self.experience_buffer),
            'learning_rate': self.optimizer.param_groups[0]['lr'],
            'recent_performance': self.performance_history[-10:] if self.performance_history else [],
            'status': 'training' if self.is_training else 'idle'
        }

# Global learning engine instance
learning_engine = ContinuousLearningEngine()

class FederatedLearning:
    """Enable learning from multiple QENEX instances"""
    
    def __init__(self):
        self.local_model = learning_engine.model
        self.aggregated_weights = {}
        
    async def share_knowledge(self, peer_urls: List[str]):
        """Share and aggregate knowledge with peer QENEX instances"""
        import aiohttp
        
        peer_weights = []
        
        async with aiohttp.ClientSession() as session:
            for url in peer_urls:
                try:
                    async with session.get(f"{url}/api/ai/model_weights") as response:
                        if response.status == 200:
                            weights = await response.json()
                            peer_weights.append(weights)
                except:
                    continue
        
        if peer_weights:
            # Federated averaging
            self._aggregate_models(peer_weights)
    
    def _aggregate_models(self, peer_weights: List[Dict]):
        """Aggregate model weights from peers"""
        with torch.no_grad():
            for name, param in self.local_model.named_parameters():
                if name in peer_weights[0]:
                    # Average weights
                    avg_weight = torch.zeros_like(param)
                    for weights in peer_weights:
                        avg_weight += torch.tensor(weights[name])
                    avg_weight /= len(peer_weights)
                    
                    # Update local model (weighted average with local)
                    param.data = 0.7 * param.data + 0.3 * avg_weight

# Auto-start continuous learning
if __name__ == "__main__":
    logger.info("QENEX Continuous Learning Engine started")
    logger.info(f"Model version: {learning_engine.model.version}")
    logger.info(f"Training iterations: {learning_engine.model.training_iterations}")
    
    # Keep running
    while True:
        asyncio.run(asyncio.sleep(60))
        status = learning_engine.get_status()
        logger.info(f"Status: {status['status']}, Buffer: {status['buffer_size']}, Iterations: {status['training_iterations']}")