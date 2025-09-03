#!/usr/bin/env python3
"""
QENEX Federated Learning Framework
Advanced federated learning implementation for distributed QENEX instances
"""

import asyncio
import json
import numpy as np
import pickle
import hashlib
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import threading
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import socket
import ssl
import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

# Configuration
FL_ROOT = "/opt/qenex-os/distributed-training/federated"
FL_MODELS = f"{FL_ROOT}/models"
FL_GRADIENTS = f"{FL_ROOT}/gradients"
FL_CRYPTO = f"{FL_ROOT}/crypto"
FL_LOGS = f"{FL_ROOT}/logs"

# Create directories
for directory in [FL_ROOT, FL_MODELS, FL_GRADIENTS, FL_CRYPTO, FL_LOGS]:
    Path(directory).mkdir(parents=True, exist_ok=True)

class AggregationStrategy(Enum):
    FEDERATED_AVERAGING = "federated_averaging"
    WEIGHTED_AVERAGING = "weighted_averaging"
    BYZANTINE_ROBUST = "byzantine_robust"
    DIFFERENTIAL_PRIVATE = "differential_private"
    SECURE_AGGREGATION = "secure_aggregation"

class PrivacyLevel(Enum):
    NONE = "none"
    BASIC = "basic"
    DIFFERENTIAL = "differential"
    HOMOMORPHIC = "homomorphic"
    SECURE_MULTIPARTY = "secure_multiparty"

@dataclass
class FederatedClient:
    client_id: str
    instance_id: str
    ip_address: str
    port: int
    public_key: bytes
    data_samples: int
    model_quality: float
    trust_score: float
    last_contribution: str
    bandwidth_mbps: float
    compute_power: float

@dataclass
class ModelUpdate:
    update_id: str
    client_id: str
    model_name: str
    round_number: int
    gradients: bytes
    weights: bytes
    metadata: Dict[str, Any]
    privacy_budget: float
    signature: bytes
    timestamp: str

@dataclass
class AggregationRound:
    round_id: str
    model_name: str
    round_number: int
    participating_clients: List[str]
    aggregation_strategy: AggregationStrategy
    privacy_level: PrivacyLevel
    target_accuracy: float
    convergence_threshold: float
    max_rounds: int
    start_time: str
    end_time: Optional[str] = None
    final_accuracy: Optional[float] = None

class CryptoManager:
    """Cryptographic operations for secure federated learning"""
    
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.symmetric_key = None
        self.setup_keys()
        
    def setup_keys(self):
        """Setup cryptographic keys"""
        # Generate RSA key pair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        
        # Generate symmetric key for data encryption
        self.symmetric_key = Fernet.generate_key()
        
        # Save keys
        self.save_keys()
    
    def save_keys(self):
        """Save cryptographic keys to secure storage"""
        # Save private key
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(f"{FL_CRYPTO}/private_key.pem", "wb") as f:
            f.write(private_pem)
        
        # Save public key
        public_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        with open(f"{FL_CRYPTO}/public_key.pem", "wb") as f:
            f.write(public_pem)
        
        # Save symmetric key
        with open(f"{FL_CRYPTO}/symmetric_key.key", "wb") as f:
            f.write(self.symmetric_key)
    
    def load_keys(self):
        """Load cryptographic keys from storage"""
        try:
            # Load private key
            with open(f"{FL_CRYPTO}/private_key.pem", "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(), password=None
                )
            
            # Load public key
            with open(f"{FL_CRYPTO}/public_key.pem", "rb") as f:
                self.public_key = serialization.load_pem_public_key(f.read())
            
            # Load symmetric key
            with open(f"{FL_CRYPTO}/symmetric_key.key", "rb") as f:
                self.symmetric_key = f.read()
                
        except FileNotFoundError:
            self.setup_keys()
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using symmetric encryption"""
        fernet = Fernet(self.symmetric_key)
        return fernet.encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using symmetric encryption"""
        fernet = Fernet(self.symmetric_key)
        return fernet.decrypt(encrypted_data)
    
    def sign_data(self, data: bytes) -> bytes:
        """Sign data using private key"""
        signature = self.private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature
    
    def verify_signature(self, data: bytes, signature: bytes, public_key) -> bool:
        """Verify signature using public key"""
        try:
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except:
            return False
    
    def add_differential_privacy_noise(self, gradients: np.ndarray, epsilon: float, delta: float) -> np.ndarray:
        """Add differential privacy noise to gradients"""
        sensitivity = 1.0  # L2 sensitivity
        noise_scale = (2 * sensitivity * np.log(1.25 / delta)) / epsilon
        
        noise = np.random.laplace(0, noise_scale, gradients.shape)
        return gradients + noise

class SecureAggregator:
    """Secure aggregation protocols for federated learning"""
    
    def __init__(self, crypto_manager: CryptoManager):
        self.crypto = crypto_manager
        self.secret_shares = {}
        self.reconstruction_threshold = None
    
    def setup_secret_sharing(self, num_clients: int, threshold: int):
        """Setup Shamir's secret sharing"""
        self.reconstruction_threshold = threshold
        # Implementation would use proper secret sharing library
        # For now, simplified approach
    
    def create_secret_shares(self, secret: bytes, num_shares: int) -> List[bytes]:
        """Create secret shares using Shamir's secret sharing"""
        # Simplified implementation - use proper library in production
        shares = []
        for i in range(num_shares):
            share = hashlib.sha256(secret + str(i).encode()).digest()
            shares.append(share)
        return shares
    
    def reconstruct_secret(self, shares: List[bytes]) -> bytes:
        """Reconstruct secret from shares"""
        # Simplified implementation
        if len(shares) >= self.reconstruction_threshold:
            # In real implementation, use Lagrange interpolation
            return shares[0]  # Placeholder
        else:
            raise ValueError("Insufficient shares for reconstruction")
    
    def secure_aggregate(self, encrypted_updates: List[bytes]) -> bytes:
        """Perform secure aggregation of encrypted updates"""
        # Decrypt updates
        decrypted_updates = []
        for update in encrypted_updates:
            decrypted = self.crypto.decrypt_data(update)
            decrypted_updates.append(pickle.loads(decrypted))
        
        # Aggregate
        aggregated = self.federated_averaging(decrypted_updates)
        
        # Re-encrypt result
        serialized = pickle.dumps(aggregated)
        return self.crypto.encrypt_data(serialized)
    
    def federated_averaging(self, updates: List[np.ndarray]) -> np.ndarray:
        """Perform federated averaging"""
        if not updates:
            return np.array([])
        
        # Simple average
        stacked = np.stack(updates, axis=0)
        return np.mean(stacked, axis=0)

class FederatedLearningFramework:
    """Main federated learning framework"""
    
    def __init__(self, framework_id: str = None):
        self.framework_id = framework_id or f"fl-{uuid.uuid4().hex[:8]}"
        self.crypto = CryptoManager()
        self.secure_aggregator = SecureAggregator(self.crypto)
        
        # Setup logging
        self.logger = self.setup_logging()
        
        # Client management
        self.clients: Dict[str, FederatedClient] = {}
        self.trusted_clients: List[str] = []
        self.blacklisted_clients: List[str] = []
        
        # Round management
        self.current_rounds: Dict[str, AggregationRound] = {}
        self.completed_rounds: List[AggregationRound] = []
        
        # Model updates
        self.pending_updates: Dict[str, List[ModelUpdate]] = {}
        self.aggregated_models: Dict[str, bytes] = {}
        
        # Privacy and security
        self.privacy_budgets: Dict[str, float] = {}
        self.byzantine_detectors = {}
        
        # Performance tracking
        self.convergence_history: Dict[str, List[float]] = {}
        self.communication_costs: Dict[str, int] = {}
        
        self.logger.info(f"Federated Learning Framework initialized: {self.framework_id}")
    
    def setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('FederatedLearning')
        logger.setLevel(logging.DEBUG)
        
        # File handler
        fh = logging.FileHandler(f"{FL_LOGS}/federated_learning.log")
        fh.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    async def register_client(self, client_info: Dict[str, Any]) -> str:
        """Register a new federated learning client"""
        client_id = client_info.get("client_id") or f"client-{uuid.uuid4().hex[:8]}"
        
        # Create client record
        client = FederatedClient(
            client_id=client_id,
            instance_id=client_info.get("instance_id", "unknown"),
            ip_address=client_info.get("ip_address", "unknown"),
            port=client_info.get("port", 8080),
            public_key=client_info.get("public_key", b""),
            data_samples=client_info.get("data_samples", 0),
            model_quality=client_info.get("model_quality", 0.0),
            trust_score=1.0,  # Start with full trust
            last_contribution=datetime.now().isoformat(),
            bandwidth_mbps=client_info.get("bandwidth_mbps", 10.0),
            compute_power=client_info.get("compute_power", 1.0)
        )
        
        self.clients[client_id] = client
        self.privacy_budgets[client_id] = 10.0  # Initial privacy budget
        
        self.logger.info(f"Registered client: {client_id}")
        return client_id
    
    async def start_training_round(self, 
                                 model_name: str, 
                                 strategy: AggregationStrategy = AggregationStrategy.FEDERATED_AVERAGING,
                                 privacy_level: PrivacyLevel = PrivacyLevel.DIFFERENTIAL,
                                 **kwargs) -> str:
        """Start a new federated training round"""
        
        round_id = f"round-{uuid.uuid4().hex[:8]}"
        round_number = kwargs.get("round_number", 1)
        
        # Select participating clients
        participating_clients = await self.select_clients(
            min_clients=kwargs.get("min_clients", 3),
            max_clients=kwargs.get("max_clients", 10),
            quality_threshold=kwargs.get("quality_threshold", 0.5)
        )
        
        if len(participating_clients) < kwargs.get("min_clients", 3):
            raise ValueError("Not enough clients available for training round")
        
        # Create round
        round_info = AggregationRound(
            round_id=round_id,
            model_name=model_name,
            round_number=round_number,
            participating_clients=participating_clients,
            aggregation_strategy=strategy,
            privacy_level=privacy_level,
            target_accuracy=kwargs.get("target_accuracy", 0.95),
            convergence_threshold=kwargs.get("convergence_threshold", 0.001),
            max_rounds=kwargs.get("max_rounds", 100),
            start_time=datetime.now().isoformat()
        )
        
        self.current_rounds[round_id] = round_info
        self.pending_updates[round_id] = []
        
        self.logger.info(f"Started training round {round_id} for model {model_name}")
        self.logger.info(f"Participating clients: {participating_clients}")
        
        # Notify clients about new round
        await self.notify_clients_new_round(round_info)
        
        return round_id
    
    async def select_clients(self, 
                           min_clients: int = 3, 
                           max_clients: int = 10,
                           quality_threshold: float = 0.5) -> List[str]:
        """Select clients for training round"""
        
        # Filter clients based on criteria
        eligible_clients = []
        for client_id, client in self.clients.items():
            if (client_id not in self.blacklisted_clients and
                client.trust_score >= quality_threshold and
                client.data_samples > 0):
                eligible_clients.append((client_id, client.trust_score))
        
        # Sort by trust score
        eligible_clients.sort(key=lambda x: x[1], reverse=True)
        
        # Select up to max_clients
        selected = [client_id for client_id, _ in eligible_clients[:max_clients]]
        
        return selected[:max(min_clients, len(selected))]
    
    async def notify_clients_new_round(self, round_info: AggregationRound):
        """Notify clients about new training round"""
        notification = {
            "type": "training_round_started",
            "round_id": round_info.round_id,
            "model_name": round_info.model_name,
            "round_number": round_info.round_number,
            "aggregation_strategy": round_info.aggregation_strategy.value,
            "privacy_level": round_info.privacy_level.value,
            "target_accuracy": round_info.target_accuracy,
            "max_rounds": round_info.max_rounds
        }
        
        # In production, send via WebSocket/HTTP to each client
        self.logger.info(f"Notifying {len(round_info.participating_clients)} clients")
    
    async def submit_model_update(self, 
                                client_id: str, 
                                round_id: str,
                                gradients: np.ndarray,
                                weights: np.ndarray,
                                metadata: Dict[str, Any]) -> bool:
        """Submit model update from client"""
        
        if round_id not in self.current_rounds:
            self.logger.warning(f"Invalid round ID: {round_id}")
            return False
        
        if client_id not in self.current_rounds[round_id].participating_clients:
            self.logger.warning(f"Client {client_id} not participating in round {round_id}")
            return False
        
        # Apply differential privacy if enabled
        round_info = self.current_rounds[round_id]
        if round_info.privacy_level == PrivacyLevel.DIFFERENTIAL:
            gradients = self.crypto.add_differential_privacy_noise(
                gradients, epsilon=1.0, delta=1e-5
            )
        
        # Serialize and encrypt gradients/weights
        gradients_bytes = self.crypto.encrypt_data(pickle.dumps(gradients))
        weights_bytes = self.crypto.encrypt_data(pickle.dumps(weights))
        
        # Create signature
        data_to_sign = gradients_bytes + weights_bytes
        signature = self.crypto.sign_data(data_to_sign)
        
        # Create model update
        update = ModelUpdate(
            update_id=f"update-{uuid.uuid4().hex[:8]}",
            client_id=client_id,
            model_name=round_info.model_name,
            round_number=round_info.round_number,
            gradients=gradients_bytes,
            weights=weights_bytes,
            metadata=metadata,
            privacy_budget=self.privacy_budgets.get(client_id, 0.0),
            signature=signature,
            timestamp=datetime.now().isoformat()
        )
        
        # Store update
        self.pending_updates[round_id].append(update)
        
        # Update client trust score based on contribution quality
        await self.update_client_trust(client_id, metadata)
        
        self.logger.info(f"Received model update from {client_id} for round {round_id}")
        
        # Check if we have enough updates for aggregation
        min_updates = max(2, len(round_info.participating_clients) // 2)
        if len(self.pending_updates[round_id]) >= min_updates:
            await self.trigger_aggregation(round_id)
        
        return True
    
    async def update_client_trust(self, client_id: str, metadata: Dict[str, Any]):
        """Update client trust score based on contribution"""
        if client_id in self.clients:
            client = self.clients[client_id]
            
            # Simple trust scoring based on accuracy and loss
            accuracy = metadata.get("accuracy", 0.0)
            loss = metadata.get("loss", float('inf'))
            
            # Update trust score (simplified)
            if accuracy > 0.8 and loss < 0.5:
                client.trust_score = min(1.0, client.trust_score + 0.01)
            elif accuracy < 0.5 or loss > 1.0:
                client.trust_score = max(0.0, client.trust_score - 0.05)
            
            # Update model quality
            client.model_quality = accuracy
            client.last_contribution = datetime.now().isoformat()
            
            # Check for blacklisting
            if client.trust_score < 0.3:
                self.blacklisted_clients.append(client_id)
                self.logger.warning(f"Blacklisted client {client_id} due to low trust score")
    
    async def trigger_aggregation(self, round_id: str):
        """Trigger model aggregation for a round"""
        if round_id not in self.current_rounds:
            return
        
        round_info = self.current_rounds[round_id]
        updates = self.pending_updates[round_id]
        
        self.logger.info(f"Starting aggregation for round {round_id} with {len(updates)} updates")
        
        # Verify signatures
        verified_updates = []
        for update in updates:
            if await self.verify_update(update):
                verified_updates.append(update)
            else:
                self.logger.warning(f"Invalid signature for update from {update.client_id}")
        
        if not verified_updates:
            self.logger.error(f"No valid updates for round {round_id}")
            return
        
        # Perform aggregation based on strategy
        aggregated_model = await self.aggregate_models(
            verified_updates, 
            round_info.aggregation_strategy
        )
        
        # Store aggregated model
        self.aggregated_models[f"{round_info.model_name}_{round_info.round_number}"] = aggregated_model
        
        # Evaluate convergence
        convergence_metric = await self.evaluate_convergence(
            round_info.model_name, 
            aggregated_model
        )
        
        # Update convergence history
        if round_info.model_name not in self.convergence_history:
            self.convergence_history[round_info.model_name] = []
        self.convergence_history[round_info.model_name].append(convergence_metric)
        
        # Check if converged
        if convergence_metric < round_info.convergence_threshold:
            await self.complete_round(round_id, True)
        elif round_info.round_number >= round_info.max_rounds:
            await self.complete_round(round_id, False)
        else:
            # Start next round
            await self.start_next_round(round_id)
        
        self.logger.info(f"Aggregation completed for round {round_id}")
    
    async def verify_update(self, update: ModelUpdate) -> bool:
        """Verify model update signature"""
        if update.client_id not in self.clients:
            return False
        
        client = self.clients[update.client_id]
        if not client.public_key:
            return False
        
        # Load client's public key
        try:
            public_key = serialization.load_pem_public_key(client.public_key)
            data_to_verify = update.gradients + update.weights
            return self.crypto.verify_signature(data_to_verify, update.signature, public_key)
        except:
            return False
    
    async def aggregate_models(self, 
                             updates: List[ModelUpdate], 
                             strategy: AggregationStrategy) -> bytes:
        """Aggregate model updates using specified strategy"""
        
        if strategy == AggregationStrategy.FEDERATED_AVERAGING:
            return await self.federated_averaging_aggregation(updates)
        elif strategy == AggregationStrategy.WEIGHTED_AVERAGING:
            return await self.weighted_averaging_aggregation(updates)
        elif strategy == AggregationStrategy.BYZANTINE_ROBUST:
            return await self.byzantine_robust_aggregation(updates)
        elif strategy == AggregationStrategy.DIFFERENTIAL_PRIVATE:
            return await self.differential_private_aggregation(updates)
        elif strategy == AggregationStrategy.SECURE_AGGREGATION:
            return await self.secure_aggregation(updates)
        else:
            return await self.federated_averaging_aggregation(updates)
    
    async def federated_averaging_aggregation(self, updates: List[ModelUpdate]) -> bytes:
        """Standard federated averaging aggregation"""
        weights_list = []
        
        for update in updates:
            # Decrypt weights
            decrypted_weights = self.crypto.decrypt_data(update.weights)
            weights = pickle.loads(decrypted_weights)
            weights_list.append(weights)
        
        # Average the weights
        if weights_list:
            averaged_weights = self.secure_aggregator.federated_averaging(weights_list)
            return pickle.dumps(averaged_weights)
        
        return b""
    
    async def weighted_averaging_aggregation(self, updates: List[ModelUpdate]) -> bytes:
        """Weighted averaging based on client data samples and trust"""
        weights_list = []
        client_weights = []
        
        for update in updates:
            # Decrypt weights
            decrypted_weights = self.crypto.decrypt_data(update.weights)
            weights = pickle.loads(decrypted_weights)
            weights_list.append(weights)
            
            # Calculate client weight
            client = self.clients[update.client_id]
            client_weight = client.data_samples * client.trust_score
            client_weights.append(client_weight)
        
        # Weighted average
        if weights_list and client_weights:
            total_weight = sum(client_weights)
            if total_weight > 0:
                # Normalize weights
                normalized_weights = [w / total_weight for w in client_weights]
                
                # Weighted average
                weighted_avg = np.zeros_like(weights_list[0])
                for weights, norm_weight in zip(weights_list, normalized_weights):
                    weighted_avg += weights * norm_weight
                
                return pickle.dumps(weighted_avg)
        
        return b""
    
    async def byzantine_robust_aggregation(self, updates: List[ModelUpdate]) -> bytes:
        """Byzantine-robust aggregation using geometric median"""
        weights_list = []
        
        for update in updates:
            decrypted_weights = self.crypto.decrypt_data(update.weights)
            weights = pickle.loads(decrypted_weights)
            weights_list.append(weights)
        
        if len(weights_list) < 3:
            # Not enough updates for byzantine robustness
            return await self.federated_averaging_aggregation(updates)
        
        # Remove outliers (simplified approach)
        # In practice, use geometric median or other robust estimators
        median_weights = np.median(weights_list, axis=0)
        
        return pickle.dumps(median_weights)
    
    async def differential_private_aggregation(self, updates: List[ModelUpdate]) -> bytes:
        """Differential privacy aggregation"""
        # Aggregate normally first
        aggregated = await self.federated_averaging_aggregation(updates)
        weights = pickle.loads(aggregated)
        
        # Add global differential privacy noise
        noisy_weights = self.crypto.add_differential_privacy_noise(
            weights, epsilon=1.0, delta=1e-5
        )
        
        return pickle.dumps(noisy_weights)
    
    async def secure_aggregation(self, updates: List[ModelUpdate]) -> bytes:
        """Secure aggregation using cryptographic protocols"""
        encrypted_updates = [update.weights for update in updates]
        return self.secure_aggregator.secure_aggregate(encrypted_updates)
    
    async def evaluate_convergence(self, model_name: str, aggregated_model: bytes) -> float:
        """Evaluate convergence of the model"""
        # Simple convergence metric based on model change
        previous_models = self.convergence_history.get(model_name, [])
        
        if not previous_models:
            return 1.0  # No previous model to compare
        
        # Compare with previous model
        # For now, return a mock convergence metric
        # In practice, evaluate on validation dataset
        
        current_round = len(previous_models)
        convergence = 1.0 / (current_round + 1)  # Decreasing over time
        
        return convergence
    
    async def complete_round(self, round_id: str, converged: bool):
        """Complete a training round"""
        if round_id not in self.current_rounds:
            return
        
        round_info = self.current_rounds[round_id]
        round_info.end_time = datetime.now().isoformat()
        round_info.final_accuracy = 0.95 if converged else 0.8  # Mock accuracy
        
        # Move to completed rounds
        self.completed_rounds.append(round_info)
        del self.current_rounds[round_id]
        del self.pending_updates[round_id]
        
        status = "converged" if converged else "max_rounds_reached"
        self.logger.info(f"Round {round_id} completed: {status}")
        
        # Notify clients about completion
        await self.notify_clients_round_complete(round_info, converged)
    
    async def start_next_round(self, current_round_id: str):
        """Start the next training round"""
        if current_round_id not in self.current_rounds:
            return
        
        current_round = self.current_rounds[current_round_id]
        
        # Start next round
        next_round_id = await self.start_training_round(
            model_name=current_round.model_name,
            strategy=current_round.aggregation_strategy,
            privacy_level=current_round.privacy_level,
            round_number=current_round.round_number + 1,
            target_accuracy=current_round.target_accuracy,
            convergence_threshold=current_round.convergence_threshold,
            max_rounds=current_round.max_rounds
        )
        
        # Complete current round
        await self.complete_round(current_round_id, False)
        
        self.logger.info(f"Started next round {next_round_id} after {current_round_id}")
    
    async def notify_clients_round_complete(self, round_info: AggregationRound, converged: bool):
        """Notify clients about round completion"""
        notification = {
            "type": "training_round_completed",
            "round_id": round_info.round_id,
            "model_name": round_info.model_name,
            "converged": converged,
            "final_accuracy": round_info.final_accuracy,
            "next_round": not converged and round_info.round_number < round_info.max_rounds
        }
        
        self.logger.info(f"Round completion notification sent to clients")
    
    async def get_global_model(self, model_name: str) -> Optional[bytes]:
        """Get the latest global model"""
        # Find the latest version
        latest_key = None
        latest_round = -1
        
        for key in self.aggregated_models.keys():
            if key.startswith(model_name + "_"):
                try:
                    round_num = int(key.split("_")[-1])
                    if round_num > latest_round:
                        latest_round = round_num
                        latest_key = key
                except ValueError:
                    continue
        
        if latest_key:
            return self.aggregated_models[latest_key]
        
        return None
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get federated learning system status"""
        return {
            "framework_id": self.framework_id,
            "clients": {
                "total": len(self.clients),
                "trusted": len(self.trusted_clients),
                "blacklisted": len(self.blacklisted_clients),
                "active": len([c for c in self.clients.values() 
                             if (datetime.now() - datetime.fromisoformat(c.last_contribution)).seconds < 3600])
            },
            "rounds": {
                "active": len(self.current_rounds),
                "completed": len(self.completed_rounds)
            },
            "models": {
                "total": len(self.aggregated_models),
                "available": list(set(key.split("_")[0] for key in self.aggregated_models.keys()))
            },
            "privacy": {
                "total_budget_remaining": sum(self.privacy_budgets.values()),
                "clients_with_budget": len([b for b in self.privacy_budgets.values() if b > 0])
            }
        }
    
    async def save_checkpoint(self) -> str:
        """Save framework checkpoint"""
        checkpoint = {
            "framework_id": self.framework_id,
            "timestamp": datetime.now().isoformat(),
            "clients": {cid: asdict(client) for cid, client in self.clients.items()},
            "current_rounds": {rid: asdict(round_info) for rid, round_info in self.current_rounds.items()},
            "completed_rounds": [asdict(round_info) for round_info in self.completed_rounds],
            "privacy_budgets": self.privacy_budgets,
            "convergence_history": self.convergence_history,
            "communication_costs": self.communication_costs,
            "trusted_clients": self.trusted_clients,
            "blacklisted_clients": self.blacklisted_clients
        }
        
        checkpoint_file = f"{FL_ROOT}/checkpoints/fl_checkpoint_{int(time.time())}.json"
        os.makedirs(os.path.dirname(checkpoint_file), exist_ok=True)
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        self.logger.info(f"Saved checkpoint: {checkpoint_file}")
        return checkpoint_file
    
    async def load_checkpoint(self, checkpoint_file: str):
        """Load framework from checkpoint"""
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
        
        # Restore state
        self.framework_id = checkpoint["framework_id"]
        self.privacy_budgets = checkpoint.get("privacy_budgets", {})
        self.convergence_history = checkpoint.get("convergence_history", {})
        self.communication_costs = checkpoint.get("communication_costs", {})
        self.trusted_clients = checkpoint.get("trusted_clients", [])
        self.blacklisted_clients = checkpoint.get("blacklisted_clients", [])
        
        # Restore clients
        for cid, client_data in checkpoint.get("clients", {}).items():
            self.clients[cid] = FederatedClient(**client_data)
        
        # Restore completed rounds
        for round_data in checkpoint.get("completed_rounds", []):
            self.completed_rounds.append(AggregationRound(**round_data))
        
        self.logger.info(f"Loaded checkpoint from {checkpoint_file}")

async def main():
    """Main entry point for federated learning framework"""
    fl_framework = FederatedLearningFramework()
    
    # Example usage
    try:
        # Register some mock clients
        for i in range(5):
            await fl_framework.register_client({
                "client_id": f"qenex-client-{i}",
                "instance_id": f"instance-{i}",
                "ip_address": f"192.168.1.{100+i}",
                "port": 8080,
                "data_samples": 1000 + i * 100,
                "model_quality": 0.8 + i * 0.02,
                "bandwidth_mbps": 50.0,
                "compute_power": 2.0
            })
        
        # Start a training round
        round_id = await fl_framework.start_training_round(
            model_name="security_detection",
            strategy=AggregationStrategy.FEDERATED_AVERAGING,
            privacy_level=PrivacyLevel.DIFFERENTIAL,
            min_clients=3,
            max_clients=5,
            target_accuracy=0.95,
            convergence_threshold=0.001,
            max_rounds=10
        )
        
        print(f"Started training round: {round_id}")
        
        # Simulate model updates from clients
        import numpy as np
        for i, client_id in enumerate(list(fl_framework.clients.keys())[:3]):
            gradients = np.random.normal(0, 1, (100, 50))
            weights = np.random.normal(0, 1, (50, 10))
            metadata = {"accuracy": 0.85 + i * 0.02, "loss": 0.3 - i * 0.01}
            
            await fl_framework.submit_model_update(
                client_id, round_id, gradients, weights, metadata
            )
        
        # Get status
        status = await fl_framework.get_system_status()
        print("System Status:", json.dumps(status, indent=2))
        
        # Save checkpoint
        checkpoint_file = await fl_framework.save_checkpoint()
        print(f"Saved checkpoint: {checkpoint_file}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║              QENEX Federated Learning Framework           ║
║                   Privacy-Preserving AI Training          ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())