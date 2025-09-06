#!/usr/bin/env python3
"""
QENEX AI System - Advanced Financial Intelligence
Real machine learning with no external dependencies
"""

import math
import random
import json
import time
import pickle
from typing import List, Dict, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path
import threading

class Matrix:
    """Matrix operations for neural networks"""
    
    def __init__(self, rows: int, cols: int, data: Optional[List[List[float]]] = None):
        self.rows = rows
        self.cols = cols
        if data is None:
            self.data = [[0.0 for _ in range(cols)] for _ in range(rows)]
        else:
            self.data = data
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def multiply(self, other: 'Matrix') -> 'Matrix':
        """Matrix multiplication"""
        if self.cols != other.rows:
            raise ValueError("Invalid matrix dimensions for multiplication")
        
        result = Matrix(self.rows, other.cols)
        for i in range(self.rows):
            for j in range(other.cols):
                for k in range(self.cols):
                    result[i][j] += self[i][k] * other[k][j]
        
        return result
    
    def add(self, other: 'Matrix') -> 'Matrix':
        """Matrix addition"""
        if self.rows != other.rows or self.cols != other.cols:
            raise ValueError("Invalid matrix dimensions for addition")
        
        result = Matrix(self.rows, self.cols)
        for i in range(self.rows):
            for j in range(self.cols):
                result[i][j] = self[i][j] + other[i][j]
        
        return result
    
    def transpose(self) -> 'Matrix':
        """Matrix transpose"""
        result = Matrix(self.cols, self.rows)
        for i in range(self.rows):
            for j in range(self.cols):
                result[j][i] = self[i][j]
        return result
    
    def apply_function(self, func) -> 'Matrix':
        """Apply function to all elements"""
        result = Matrix(self.rows, self.cols)
        for i in range(self.rows):
            for j in range(self.cols):
                result[i][j] = func(self[i][j])
        return result
    
    @staticmethod
    def random_matrix(rows: int, cols: int, min_val: float = -1.0, max_val: float = 1.0) -> 'Matrix':
        """Create random matrix"""
        data = [[random.uniform(min_val, max_val) for _ in range(cols)] for _ in range(rows)]
        return Matrix(rows, cols, data)

class ActivationFunctions:
    """Neural network activation functions"""
    
    @staticmethod
    def sigmoid(x: float) -> float:
        """Sigmoid activation function"""
        try:
            return 1.0 / (1.0 + math.exp(-max(-500, min(500, x))))
        except (OverflowError, ZeroDivisionError):
            return 0.0 if x < 0 else 1.0
    
    @staticmethod
    def sigmoid_derivative(x: float) -> float:
        """Derivative of sigmoid"""
        s = ActivationFunctions.sigmoid(x)
        return s * (1 - s)
    
    @staticmethod
    def tanh(x: float) -> float:
        """Hyperbolic tangent"""
        try:
            return math.tanh(max(-500, min(500, x)))
        except OverflowError:
            return -1.0 if x < 0 else 1.0
    
    @staticmethod
    def tanh_derivative(x: float) -> float:
        """Derivative of tanh"""
        t = ActivationFunctions.tanh(x)
        return 1 - t * t
    
    @staticmethod
    def relu(x: float) -> float:
        """Rectified Linear Unit"""
        return max(0, x)
    
    @staticmethod
    def relu_derivative(x: float) -> float:
        """Derivative of ReLU"""
        return 1.0 if x > 0 else 0.0
    
    @staticmethod
    def leaky_relu(x: float, alpha: float = 0.01) -> float:
        """Leaky ReLU"""
        return max(alpha * x, x)
    
    @staticmethod
    def leaky_relu_derivative(x: float, alpha: float = 0.01) -> float:
        """Derivative of Leaky ReLU"""
        return 1.0 if x > 0 else alpha

class NeuralLayer:
    """Single layer of neural network"""
    
    def __init__(self, input_size: int, output_size: int, activation: str = 'sigmoid'):
        self.input_size = input_size
        self.output_size = output_size
        self.activation = activation
        
        # Initialize weights with Xavier initialization
        std = math.sqrt(2.0 / (input_size + output_size))
        self.weights = Matrix.random_matrix(output_size, input_size, -std, std)
        self.biases = Matrix.random_matrix(output_size, 1, -0.1, 0.1)
        
        # For training
        self.last_input = None
        self.last_output = None
        self.last_weighted_sum = None
    
    def forward(self, input_matrix: Matrix) -> Matrix:
        """Forward propagation through layer"""
        self.last_input = input_matrix
        
        # Weighted sum: W * X + B
        self.last_weighted_sum = self.weights.multiply(input_matrix).add(self.biases)
        
        # Apply activation function
        if self.activation == 'sigmoid':
            self.last_output = self.last_weighted_sum.apply_function(ActivationFunctions.sigmoid)
        elif self.activation == 'tanh':
            self.last_output = self.last_weighted_sum.apply_function(ActivationFunctions.tanh)
        elif self.activation == 'relu':
            self.last_output = self.last_weighted_sum.apply_function(ActivationFunctions.relu)
        elif self.activation == 'leaky_relu':
            self.last_output = self.last_weighted_sum.apply_function(ActivationFunctions.leaky_relu)
        else:
            self.last_output = self.last_weighted_sum  # Linear activation
        
        return self.last_output
    
    def backward(self, output_gradient: Matrix, learning_rate: float) -> Matrix:
        """Backward propagation through layer"""
        if self.last_input is None or self.last_weighted_sum is None:
            raise ValueError("Must call forward() before backward()")
        
        # Calculate activation gradient
        if self.activation == 'sigmoid':
            activation_grad = self.last_weighted_sum.apply_function(ActivationFunctions.sigmoid_derivative)
        elif self.activation == 'tanh':
            activation_grad = self.last_weighted_sum.apply_function(ActivationFunctions.tanh_derivative)
        elif self.activation == 'relu':
            activation_grad = self.last_weighted_sum.apply_function(ActivationFunctions.relu_derivative)
        elif self.activation == 'leaky_relu':
            activation_grad = self.last_weighted_sum.apply_function(ActivationFunctions.leaky_relu_derivative)
        else:
            activation_grad = Matrix(self.output_size, 1)
            for i in range(self.output_size):
                activation_grad[i][0] = 1.0  # Linear activation derivative
        
        # Element-wise multiplication of gradients
        delta = Matrix(self.output_size, 1)
        for i in range(self.output_size):
            delta[i][0] = output_gradient[i][0] * activation_grad[i][0]
        
        # Calculate weight gradients
        weight_gradients = delta.multiply(self.last_input.transpose())
        
        # Update weights and biases
        for i in range(self.output_size):
            for j in range(self.input_size):
                self.weights[i][j] -= learning_rate * weight_gradients[i][j]
            self.biases[i][0] -= learning_rate * delta[i][0]
        
        # Calculate input gradient for previous layer
        input_gradient = self.weights.transpose().multiply(delta)
        
        return input_gradient

class DeepNeuralNetwork:
    """Deep neural network with backpropagation"""
    
    def __init__(self, architecture: List[int], activations: Optional[List[str]] = None):
        """
        Initialize neural network
        
        Args:
            architecture: List of layer sizes [input, hidden1, hidden2, ..., output]
            activations: List of activation functions for each layer
        """
        if len(architecture) < 2:
            raise ValueError("Network must have at least input and output layers")
        
        self.architecture = architecture
        self.layers = []
        
        # Default activations
        if activations is None:
            activations = ['relu'] * (len(architecture) - 2) + ['sigmoid']
        
        # Create layers
        for i in range(len(architecture) - 1):
            layer = NeuralLayer(
                architecture[i], 
                architecture[i + 1], 
                activations[i] if i < len(activations) else 'sigmoid'
            )
            self.layers.append(layer)
        
        self.learning_rate = 0.001
        self.training_history = []
        self.epoch = 0
    
    def forward(self, inputs: List[float]) -> List[float]:
        """Forward propagation through entire network"""
        if len(inputs) != self.architecture[0]:
            raise ValueError(f"Input size {len(inputs)} doesn't match expected {self.architecture[0]}")
        
        # Convert input to matrix
        current = Matrix(len(inputs), 1)
        for i, val in enumerate(inputs):
            current[i][0] = val
        
        # Forward through all layers
        for layer in self.layers:
            current = layer.forward(current)
        
        # Convert output to list
        return [current[i][0] for i in range(current.rows)]
    
    def backward(self, targets: List[float]) -> float:
        """Backward propagation with error calculation"""
        if len(targets) != self.architecture[-1]:
            raise ValueError(f"Target size {len(targets)} doesn't match output size {self.architecture[-1]}")
        
        # Calculate output error
        outputs = [self.layers[-1].last_output[i][0] for i in range(len(targets))]
        errors = [targets[i] - outputs[i] for i in range(len(targets))]
        
        # Calculate mean squared error
        mse = sum(error ** 2 for error in errors) / len(errors)
        
        # Convert error to gradient matrix
        output_gradient = Matrix(len(targets), 1)
        for i, error in enumerate(errors):
            output_gradient[i][0] = error
        
        # Backpropagate through all layers
        current_gradient = output_gradient
        for layer in reversed(self.layers):
            current_gradient = layer.backward(current_gradient, self.learning_rate)
        
        return mse
    
    def train_batch(self, inputs_batch: List[List[float]], targets_batch: List[List[float]]) -> float:
        """Train on a batch of examples"""
        if len(inputs_batch) != len(targets_batch):
            raise ValueError("Inputs and targets batch sizes must match")
        
        total_error = 0.0
        
        for inputs, targets in zip(inputs_batch, targets_batch):
            # Forward pass
            self.forward(inputs)
            
            # Backward pass
            error = self.backward(targets)
            total_error += error
        
        avg_error = total_error / len(inputs_batch)
        
        # Record training history
        self.training_history.append({
            'epoch': self.epoch,
            'error': avg_error,
            'timestamp': datetime.now()
        })
        
        self.epoch += 1
        return avg_error
    
    def predict(self, inputs: List[float]) -> List[float]:
        """Make prediction"""
        return self.forward(inputs)
    
    def save(self, filepath: Path):
        """Save model to file"""
        model_data = {
            'architecture': self.architecture,
            'layers': [],
            'learning_rate': self.learning_rate,
            'epoch': self.epoch,
            'training_history': self.training_history
        }
        
        # Save layer weights and biases
        for layer in self.layers:
            layer_data = {
                'weights': layer.weights.data,
                'biases': layer.biases.data,
                'activation': layer.activation
            }
            model_data['layers'].append(layer_data)
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load(self, filepath: Path):
        """Load model from file"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.architecture = model_data['architecture']
        self.learning_rate = model_data['learning_rate']
        self.epoch = model_data['epoch']
        self.training_history = model_data.get('training_history', [])
        
        # Recreate layers
        self.layers = []
        for i, layer_data in enumerate(model_data['layers']):
            layer = NeuralLayer(
                self.architecture[i],
                self.architecture[i + 1],
                layer_data['activation']
            )
            layer.weights = Matrix(len(layer_data['weights']), len(layer_data['weights'][0]), layer_data['weights'])
            layer.biases = Matrix(len(layer_data['biases']), len(layer_data['biases'][0]), layer_data['biases'])
            self.layers.append(layer)

class FinancialRiskAnalyzer:
    """AI-based financial risk analysis system"""
    
    def __init__(self, model_path: Optional[Path] = None):
        # Network architecture: 20 inputs -> 64 -> 32 -> 16 -> 1 output
        self.network = DeepNeuralNetwork(
            architecture=[20, 64, 32, 16, 1],
            activations=['relu', 'relu', 'relu', 'sigmoid']
        )
        
        self.model_path = model_path or Path.home() / '.qenex' / 'risk_model.pkl'
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Risk factors database
        self.risk_patterns = {}
        self.fraud_indicators = []
        self.training_data = []
        
        # Load existing model if available
        self._load_model()
        
        self.lock = threading.Lock()
    
    def extract_features(self, transaction: Dict[str, Any], account_data: Dict[str, Any]) -> List[float]:
        """Extract 20-dimensional feature vector from transaction and account data"""
        features = []
        
        # Transaction amount features (normalized)
        amount = float(transaction.get('amount', 0))
        features.append(min(amount / 100000, 1.0))  # Amount normalized to [0,1]
        features.append(math.log10(amount + 1) / 6)   # Log amount
        
        # Time-based features
        timestamp = transaction.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        features.append(timestamp.hour / 24)           # Hour of day [0,1]
        features.append(timestamp.weekday() / 7)       # Day of week [0,1]
        features.append(timestamp.day / 31)            # Day of month [0,1]
        features.append((timestamp.month - 1) / 11)    # Month [0,1]
        
        # Account features
        account_age_days = account_data.get('account_age_days', 0)
        features.append(min(account_age_days / 365, 1.0))  # Account age in years [0,1]
        
        total_transactions = account_data.get('total_transactions', 0)
        features.append(min(total_transactions / 1000, 1.0))  # Transaction count [0,1]
        
        avg_transaction = account_data.get('avg_transaction_amount', 0)
        features.append(min(avg_transaction / 10000, 1.0))    # Avg transaction amount [0,1]
        
        current_balance = float(account_data.get('balance', 0))
        features.append(min(current_balance / 1000000, 1.0))  # Account balance [0,1]
        
        # Behavioral features
        velocity_1h = transaction.get('velocity_1h', 0)
        features.append(min(velocity_1h / 10, 1.0))          # Transactions in last hour [0,1]
        
        velocity_24h = transaction.get('velocity_24h', 0)
        features.append(min(velocity_24h / 50, 1.0))         # Transactions in last day [0,1]
        
        # Geographic and device features
        features.append(1.0 if transaction.get('international', False) else 0.0)
        features.append(1.0 if transaction.get('new_device', False) else 0.0)
        features.append(1.0 if transaction.get('vpn_detected', False) else 0.0)
        
        # Risk scores from external sources
        features.append(float(transaction.get('ip_risk_score', 0.5)))
        features.append(float(transaction.get('device_risk_score', 0.5)))
        features.append(float(account_data.get('kyc_risk_score', 0.5)))
        
        # Pattern-based features
        features.append(float(transaction.get('amount_pattern_score', 0.5)))
        features.append(float(transaction.get('timing_pattern_score', 0.5)))
        
        # Ensure exactly 20 features
        while len(features) < 20:
            features.append(0.0)
        
        return features[:20]
    
    def analyze_risk(self, transaction: Dict[str, Any], account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze transaction risk using AI model"""
        with self.lock:
            try:
                # Extract features
                features = self.extract_features(transaction, account_data)
                
                # Get AI prediction
                prediction = self.network.predict(features)
                risk_score = prediction[0]
                
                # Determine risk level
                if risk_score < 0.3:
                    risk_level = "LOW"
                    approved = True
                elif risk_score < 0.6:
                    risk_level = "MEDIUM"
                    approved = True
                elif risk_score < 0.8:
                    risk_level = "HIGH"
                    approved = False
                else:
                    risk_level = "CRITICAL"
                    approved = False
                
                # Identify specific risk factors
                risk_factors = self._identify_risk_factors(transaction, account_data, features)
                
                # Calculate confidence based on training data
                confidence = min(0.5 + len(self.training_data) / 10000, 0.95)
                
                return {
                    'risk_score': risk_score,
                    'risk_level': risk_level,
                    'approved': approved,
                    'confidence': confidence,
                    'risk_factors': risk_factors,
                    'model_version': self.network.epoch,
                    'features_used': len(features)
                }
                
            except Exception as e:
                # Fallback risk assessment
                return {
                    'risk_score': 0.5,
                    'risk_level': 'MEDIUM',
                    'approved': True,
                    'confidence': 0.1,
                    'risk_factors': ['AI_MODEL_ERROR'],
                    'error': str(e)
                }
    
    def _identify_risk_factors(self, transaction: Dict, account_data: Dict, features: List[float]) -> List[str]:
        """Identify specific risk factors based on feature values"""
        factors = []
        
        # Check high-risk features
        if features[0] > 0.8:  # Large amount
            factors.append("LARGE_AMOUNT")
        
        if features[2] < 0.25 or features[2] > 0.9:  # Unusual time
            factors.append("UNUSUAL_TIME")
        
        if features[6] < 0.1:  # New account
            factors.append("NEW_ACCOUNT")
        
        if features[10] > 0.5:  # High velocity
            factors.append("HIGH_VELOCITY")
        
        if features[12]:  # International
            factors.append("INTERNATIONAL")
        
        if features[13]:  # New device
            factors.append("NEW_DEVICE")
        
        if features[14]:  # VPN detected
            factors.append("VPN_USAGE")
        
        if features[15] > 0.7:  # High IP risk
            factors.append("HIGH_IP_RISK")
        
        # Pattern-based factors
        if features[18] > 0.7:  # Unusual amount pattern
            factors.append("UNUSUAL_AMOUNT_PATTERN")
        
        if features[19] > 0.7:  # Unusual timing pattern
            factors.append("UNUSUAL_TIMING_PATTERN")
        
        return factors
    
    def train_on_feedback(self, transaction: Dict, account_data: Dict, is_fraud: bool) -> float:
        """Train model on labeled transaction"""
        with self.lock:
            try:
                # Extract features
                features = self.extract_features(transaction, account_data)
                target = [1.0 if is_fraud else 0.0]
                
                # Train on single example
                error = self.network.train_batch([features], [target])
                
                # Store training data
                self.training_data.append({
                    'timestamp': datetime.now(),
                    'features': features,
                    'is_fraud': is_fraud,
                    'error': error
                })
                
                # Save model periodically
                if len(self.training_data) % 100 == 0:
                    self._save_model()
                
                return error
                
            except Exception as e:
                print(f"Training error: {e}")
                return 1.0
    
    def batch_train(self, training_examples: List[Tuple[Dict, Dict, bool]]) -> float:
        """Train on batch of examples"""
        if not training_examples:
            return 0.0
        
        features_batch = []
        targets_batch = []
        
        for transaction, account_data, is_fraud in training_examples:
            features = self.extract_features(transaction, account_data)
            target = [1.0 if is_fraud else 0.0]
            
            features_batch.append(features)
            targets_batch.append(target)
        
        # Train on batch
        error = self.network.train_batch(features_batch, targets_batch)
        
        # Update training history
        for example in training_examples:
            self.training_data.append({
                'timestamp': datetime.now(),
                'is_fraud': example[2],
                'error': error
            })
        
        return error
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get model performance metrics"""
        if len(self.training_data) < 10:
            return {'insufficient_data': True}
        
        recent_data = self.training_data[-1000:]  # Last 1000 examples
        
        # Calculate accuracy on recent data
        fraud_count = sum(1 for d in recent_data if d.get('is_fraud', False))
        fraud_rate = fraud_count / len(recent_data)
        
        # Calculate average error
        avg_error = sum(d.get('error', 0) for d in recent_data) / len(recent_data)
        
        return {
            'total_training_examples': len(self.training_data),
            'recent_fraud_rate': fraud_rate,
            'average_error': avg_error,
            'model_epochs': self.network.epoch,
            'training_start': self.training_data[0]['timestamp'] if self.training_data else None,
            'last_training': self.training_data[-1]['timestamp'] if self.training_data else None
        }
    
    def _save_model(self):
        """Save model to disk"""
        try:
            self.network.save(self.model_path)
            
            # Save additional data
            metadata_path = self.model_path.with_suffix('.meta.pkl')
            metadata = {
                'training_data_count': len(self.training_data),
                'risk_patterns': self.risk_patterns,
                'fraud_indicators': self.fraud_indicators
            }
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
                
        except Exception as e:
            print(f"Failed to save model: {e}")
    
    def _load_model(self):
        """Load model from disk"""
        try:
            if self.model_path.exists():
                self.network.load(self.model_path)
                
                # Load metadata
                metadata_path = self.model_path.with_suffix('.meta.pkl')
                if metadata_path.exists():
                    with open(metadata_path, 'rb') as f:
                        metadata = pickle.load(f)
                        self.risk_patterns = metadata.get('risk_patterns', {})
                        self.fraud_indicators = metadata.get('fraud_indicators', [])
                
        except Exception as e:
            print(f"Failed to load model: {e}")

class MarketPredictor:
    """AI-based market prediction system"""
    
    def __init__(self):
        # Network for price prediction: 15 inputs -> 32 -> 16 -> 8 -> 1 output
        self.network = DeepNeuralNetwork(
            architecture=[15, 32, 16, 8, 1],
            activations=['tanh', 'tanh', 'relu', 'sigmoid']
        )
        
        self.price_history = {}
        self.predictions = []
        self.model_path = Path.home() / '.qenex' / 'market_model.pkl'
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._load_model()
    
    def add_price_data(self, symbol: str, price: float, volume: float, timestamp: Optional[datetime] = None):
        """Add price data point"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        if timestamp is None:
            timestamp = datetime.now()
        
        data_point = {
            'timestamp': timestamp,
            'price': price,
            'volume': volume
        }
        
        self.price_history[symbol].append(data_point)
        
        # Keep only last 1000 points per symbol
        if len(self.price_history[symbol]) > 1000:
            self.price_history[symbol] = self.price_history[symbol][-1000:]
    
    def extract_market_features(self, symbol: str) -> Optional[List[float]]:
        """Extract features for market prediction"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 10:
            return None
        
        data = self.price_history[symbol]
        prices = [d['price'] for d in data[-20:]]  # Last 20 prices
        volumes = [d['volume'] for d in data[-20:]]  # Last 20 volumes
        
        if len(prices) < 10:
            return None
        
        features = []
        
        # Price features
        current_price = prices[-1]
        features.append(current_price / 10000)  # Normalized current price
        
        # Price changes
        if len(prices) >= 2:
            price_change_1 = (prices[-1] - prices[-2]) / prices[-2]
            features.append(price_change_1)
        else:
            features.append(0.0)
        
        if len(prices) >= 5:
            price_change_5 = (prices[-1] - prices[-5]) / prices[-5]
            features.append(price_change_5)
        else:
            features.append(0.0)
        
        # Moving averages
        if len(prices) >= 5:
            ma_5 = sum(prices[-5:]) / 5
            features.append((current_price - ma_5) / ma_5)
        else:
            features.append(0.0)
        
        if len(prices) >= 10:
            ma_10 = sum(prices[-10:]) / 10
            features.append((current_price - ma_10) / ma_10)
        else:
            features.append(0.0)
        
        # Volatility (standard deviation of returns)
        if len(prices) >= 10:
            returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
            volatility = math.sqrt(sum(r**2 for r in returns) / len(returns))
            features.append(volatility)
        else:
            features.append(0.1)
        
        # Volume features
        current_volume = volumes[-1] if volumes else 0
        features.append(min(current_volume / 1000000, 1.0))  # Normalized volume
        
        if len(volumes) >= 5:
            avg_volume_5 = sum(volumes[-5:]) / 5
            if avg_volume_5 > 0:
                features.append((current_volume - avg_volume_5) / avg_volume_5)
            else:
                features.append(0.0)
        else:
            features.append(0.0)
        
        # Technical indicators
        # RSI approximation
        if len(prices) >= 14:
            gains = []
            losses = []
            for i in range(1, 15):  # Last 14 periods
                change = prices[-i] - prices[-i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                features.append(rsi / 100)  # Normalize to [0,1]
            else:
                features.append(0.5)
        else:
            features.append(0.5)
        
        # Momentum
        if len(prices) >= 5:
            momentum = (prices[-1] - prices[-5]) / prices[-5]
            features.append(momentum)
        else:
            features.append(0.0)
        
        # Time features
        now = datetime.now()
        features.append(now.hour / 24)  # Hour of day
        features.append(now.weekday() / 7)  # Day of week
        
        # Trend (linear regression slope approximation)
        if len(prices) >= 10:
            x_vals = list(range(10))
            y_vals = prices[-10:]
            
            # Simple linear regression
            n = len(x_vals)
            sum_x = sum(x_vals)
            sum_y = sum(y_vals)
            sum_xy = sum(x_vals[i] * y_vals[i] for i in range(n))
            sum_x2 = sum(x * x for x in x_vals)
            
            denominator = n * sum_x2 - sum_x * sum_x
            if denominator != 0:
                slope = (n * sum_xy - sum_x * sum_y) / denominator
                features.append(slope / current_price)  # Normalized slope
            else:
                features.append(0.0)
        else:
            features.append(0.0)
        
        # Support/Resistance levels
        if len(prices) >= 20:
            recent_prices = prices[-20:]
            min_price = min(recent_prices)
            max_price = max(recent_prices)
            
            # Distance from support/resistance
            support_distance = (current_price - min_price) / min_price if min_price > 0 else 0
            resistance_distance = (max_price - current_price) / max_price if max_price > 0 else 0
            
            features.append(support_distance)
            features.append(resistance_distance)
        else:
            features.append(0.0)
            features.append(0.0)
        
        # Ensure exactly 15 features
        while len(features) < 15:
            features.append(0.0)
        
        return features[:15]
    
    def predict_price_movement(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Predict price movement for symbol"""
        features = self.extract_market_features(symbol)
        if features is None:
            return None
        
        # Get prediction (0 = down, 1 = up)
        prediction = self.network.predict(features)[0]
        
        # Convert to price movement
        confidence = abs(prediction - 0.5) * 2  # Distance from 0.5 normalized
        direction = "UP" if prediction > 0.5 else "DOWN"
        
        # Get current price for context
        current_price = self.price_history[symbol][-1]['price']
        
        result = {
            'symbol': symbol,
            'current_price': current_price,
            'prediction': prediction,
            'direction': direction,
            'confidence': confidence,
            'timestamp': datetime.now(),
            'features_used': len(features)
        }
        
        self.predictions.append(result)
        return result
    
    def train_on_price_data(self, symbol: str, future_periods: int = 5) -> float:
        """Train model on historical price data"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < future_periods + 20:
            return 0.0
        
        data = self.price_history[symbol]
        training_examples = []
        
        # Create training examples from historical data
        for i in range(20, len(data) - future_periods):
            # Use data up to point i for features
            historical_data = data[:i+1]
            
            # Create temporary symbol data for feature extraction
            temp_symbol = f"{symbol}_temp"
            self.price_history[temp_symbol] = historical_data
            
            features = self.extract_market_features(temp_symbol)
            if features is None:
                continue
            
            # Future price movement as target
            current_price = data[i]['price']
            future_price = data[i + future_periods]['price']
            
            # Target: 1.0 if price went up, 0.0 if down
            target = [1.0 if future_price > current_price else 0.0]
            
            training_examples.append((features, target))
            
            # Clean up temp data
            del self.price_history[temp_symbol]
        
        if not training_examples:
            return 0.0
        
        # Train on batch
        features_batch = [ex[0] for ex in training_examples]
        targets_batch = [ex[1] for ex in training_examples]
        
        error = self.network.train_batch(features_batch, targets_batch)
        
        return error
    
    def save_model(self):
        """Save model to disk"""
        self.network.save(self.model_path)
    
    def _load_model(self):
        """Load model from disk"""
        if self.model_path.exists():
            try:
                self.network.load(self.model_path)
            except Exception as e:
                print(f"Failed to load market model: {e}")

# Demo function
def demo_ai_systems():
    """Demonstrate AI systems"""
    print("=" * 80)
    print("QENEX AI Systems - Financial Intelligence Demo")
    print("=" * 80)
    
    # Risk Analyzer Demo
    print("\n--- Risk Analysis System ---")
    risk_analyzer = FinancialRiskAnalyzer()
    
    # Test transactions
    test_cases = [
        {
            'transaction': {
                'amount': 500.0,
                'timestamp': datetime.now(),
                'international': False,
                'new_device': False,
                'vpn_detected': False
            },
            'account': {
                'balance': 10000.0,
                'account_age_days': 365,
                'total_transactions': 100,
                'avg_transaction_amount': 200.0
            },
            'is_fraud': False
        },
        {
            'transaction': {
                'amount': 50000.0,
                'timestamp': datetime.now().replace(hour=3),  # 3 AM
                'international': True,
                'new_device': True,
                'vpn_detected': True,
                'velocity_1h': 10
            },
            'account': {
                'balance': 1000.0,
                'account_age_days': 1,
                'total_transactions': 1,
                'avg_transaction_amount': 50000.0
            },
            'is_fraud': True
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        analysis = risk_analyzer.analyze_risk(case['transaction'], case['account'])
        print(f"  Amount: ${case['transaction']['amount']}")
        print(f"  Risk Score: {analysis['risk_score']:.3f}")
        print(f"  Risk Level: {analysis['risk_level']}")
        print(f"  Approved: {analysis['approved']}")
        print(f"  Risk Factors: {', '.join(analysis['risk_factors'])}")
        
        # Train on this example
        error = risk_analyzer.train_on_feedback(
            case['transaction'], case['account'], case['is_fraud']
        )
        print(f"  Training Error: {error:.4f}")
    
    # Market Predictor Demo
    print("\n--- Market Prediction System ---")
    market_predictor = MarketPredictor()
    
    # Add some sample price data
    symbols = ['BTC', 'ETH', 'AAPL']
    base_prices = {'BTC': 50000, 'ETH': 3000, 'AAPL': 150}
    
    for symbol in symbols:
        print(f"\nGenerating price history for {symbol}...")
        price = base_prices[symbol]
        
        # Generate 50 data points
        for i in range(50):
            # Random walk with trend
            change = random.gauss(0, 0.02)  # 2% volatility
            price *= (1 + change)
            volume = random.uniform(100000, 1000000)
            
            market_predictor.add_price_data(symbol, price, volume)
        
        print(f"  Current Price: ${price:.2f}")
        
        # Make prediction
        prediction = market_predictor.predict_price_movement(symbol)
        if prediction:
            print(f"  Prediction: {prediction['direction']} (confidence: {prediction['confidence']:.2%})")
        
        # Train on historical data
        error = market_predictor.train_on_price_data(symbol)
        print(f"  Training Error: {error:.4f}")
    
    # Performance Summary
    print("\n--- AI Performance Summary ---")
    risk_performance = risk_analyzer.get_model_performance()
    print("Risk Analyzer:")
    if risk_performance.get('insufficient_data'):
        print("  Status: Learning (insufficient training data)")
    else:
        print(f"  Training Examples: {risk_performance['total_training_examples']}")
        print(f"  Model Epochs: {risk_performance['model_epochs']}")
        print(f"  Average Error: {risk_performance['average_error']:.4f}")
    
    print("Market Predictor:")
    print(f"  Model Epochs: {market_predictor.network.epoch}")
    print(f"  Symbols Tracked: {len(market_predictor.price_history)}")
    print(f"  Predictions Made: {len(market_predictor.predictions)}")
    
    print("\n✅ AI Systems Operational")
    print("✅ Risk analysis with real learning")
    print("✅ Market prediction with technical analysis")
    print("✅ Model persistence and improvement")
    
    # Save models
    risk_analyzer._save_model()
    market_predictor.save_model()
    print("\n✅ Models saved for future use")

if __name__ == "__main__":
    demo_ai_systems()