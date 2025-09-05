#!/usr/bin/env python3
"""
QENEX AI - Self-Improving Financial Intelligence
"""

import json
import math
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class Pattern:
    """Financial pattern recognition"""
    pattern_id: str
    features: List[float]
    outcome: float
    confidence: float
    timestamp: float

class NeuralNetwork:
    """Self-improving neural network"""
    
    def __init__(self, layers: List[int] = None):
        self.layers = layers or [10, 20, 10, 1]
        self.weights = []
        self.biases = []
        self.learning_rate = 0.01
        self.generation = 1
        
        # Initialize network
        for i in range(len(self.layers) - 1):
            w = [[random.gauss(0, 0.5) for _ in range(self.layers[i+1])] 
                 for _ in range(self.layers[i])]
            b = [random.gauss(0, 0.5) for _ in range(self.layers[i+1])]
            self.weights.append(w)
            self.biases.append(b)
    
    def sigmoid(self, x: float) -> float:
        """Activation function"""
        return 1 / (1 + math.exp(-max(-500, min(500, x))))
    
    def forward(self, inputs: List[float]) -> List[float]:
        """Forward propagation"""
        activation = inputs
        
        for w, b in zip(self.weights, self.biases):
            next_activation = []
            for neuron_w, neuron_b in zip(zip(*w), b):
                z = sum(a * weight for a, weight in zip(activation, neuron_w)) + neuron_b
                next_activation.append(self.sigmoid(z))
            activation = next_activation
        
        return activation
    
    def train(self, inputs: List[float], target: float):
        """Train network with backpropagation"""
        output = self.forward(inputs)
        error = target - output[0]
        
        # Simplified weight update
        for i, w in enumerate(self.weights):
            for j in range(len(w)):
                for k in range(len(w[j])):
                    self.weights[i][j][k] += self.learning_rate * error * 0.01
        
        # Evolve
        self.generation += 1
    
    def predict(self, inputs: List[float]) -> float:
        """Make prediction"""
        return self.forward(inputs)[0]

class SelfImprovingAI:
    """Complete self-improving AI system"""
    
    def __init__(self):
        self.network = NeuralNetwork()
        self.patterns = []
        self.performance_history = []
        self.adaptation_rate = 0.1
        
    def extract_features(self, data: Dict) -> List[float]:
        """Extract features from financial data"""
        features = []
        
        # Price features
        features.append(data.get('price', 0) / 100000)
        features.append(data.get('volume', 0) / 1000000)
        features.append(data.get('volatility', 0.5))
        
        # Time features
        features.append(data.get('hour', 12) / 24)
        features.append(data.get('day_of_week', 3) / 7)
        features.append(data.get('month', 6) / 12)
        
        # Market features
        features.append(data.get('market_cap', 0) / 1000000000)
        features.append(data.get('liquidity', 0.5))
        features.append(data.get('correlation', 0))
        features.append(data.get('trend', 0))
        
        return features[:10]  # Ensure 10 features
    
    def learn_pattern(self, data: Dict, outcome: float):
        """Learn from new pattern"""
        features = self.extract_features(data)
        
        # Train network
        self.network.train(features, outcome)
        
        # Store pattern
        pattern = Pattern(
            pattern_id=f"P{len(self.patterns)}",
            features=features,
            outcome=outcome,
            confidence=0.8,
            timestamp=time.time()
        )
        self.patterns.append(pattern)
        
        # Adapt learning rate
        if len(self.patterns) % 10 == 0:
            self._adapt()
    
    def predict_outcome(self, data: Dict) -> Dict:
        """Predict financial outcome"""
        features = self.extract_features(data)
        prediction = self.network.predict(features)
        
        # Find similar patterns
        similar = self._find_similar_patterns(features)
        
        # Calculate confidence
        confidence = 0.5
        if similar:
            outcomes = [p.outcome for p in similar]
            avg_outcome = sum(outcomes) / len(outcomes)
            confidence = 1 - abs(prediction - avg_outcome)
        
        return {
            'prediction': prediction,
            'confidence': confidence,
            'generation': self.network.generation,
            'similar_patterns': len(similar)
        }
    
    def _find_similar_patterns(self, features: List[float], threshold: float = 0.3) -> List[Pattern]:
        """Find similar historical patterns"""
        similar = []
        
        for pattern in self.patterns[-100:]:  # Check last 100 patterns
            distance = sum((a - b) ** 2 for a, b in zip(features, pattern.features)) ** 0.5
            if distance < threshold:
                similar.append(pattern)
        
        return similar
    
    def _adapt(self):
        """Self-adaptation mechanism"""
        if len(self.patterns) < 10:
            return
        
        # Calculate recent performance
        recent = self.patterns[-10:]
        accuracy = sum(1 for p in recent if p.confidence > 0.7) / len(recent)
        
        # Adjust learning rate
        if accuracy < 0.5:
            self.network.learning_rate *= 1.1  # Learn faster
        elif accuracy > 0.8:
            self.network.learning_rate *= 0.9  # Learn slower
        
        # Store performance
        self.performance_history.append({
            'timestamp': time.time(),
            'accuracy': accuracy,
            'generation': self.network.generation
        })
    
    def analyze_risk(self, transaction: Dict) -> Dict:
        """Advanced risk analysis"""
        risk_score = 0.0
        factors = []
        
        # Amount risk
        amount = transaction.get('amount', 0)
        if amount > 100000:
            risk_score += 0.4
            factors.append("Very large transaction")
        elif amount > 10000:
            risk_score += 0.2
            factors.append("Large transaction")
        
        # Pattern-based risk
        prediction = self.predict_outcome(transaction)
        if prediction['prediction'] < 0.3:
            risk_score += 0.3
            factors.append("Negative pattern prediction")
        
        # Behavioral analysis
        if transaction.get('unusual_behavior'):
            risk_score += 0.2
            factors.append("Unusual behavior detected")
        
        # Time-based risk
        hour = transaction.get('hour', 12)
        if hour < 4 or hour > 23:
            risk_score += 0.1
            factors.append("Unusual time")
        
        # Learn from this analysis
        self.learn_pattern(transaction, 1 - risk_score)
        
        return {
            'risk_score': min(risk_score, 1.0),
            'approved': risk_score < 0.6,
            'factors': factors,
            'ai_confidence': prediction['confidence'],
            'ai_generation': self.network.generation
        }

class MarketPredictor:
    """Financial market prediction"""
    
    def __init__(self):
        self.ai = SelfImprovingAI()
        self.market_data = []
        
    def predict_price(self, symbol: str, timeframe: str = '1h') -> Dict:
        """Predict future price"""
        # Get recent market data
        current_data = self._get_market_data(symbol)
        
        # Make prediction
        prediction = self.ai.predict_outcome(current_data)
        
        # Calculate price target
        current_price = current_data.get('price', 0)
        predicted_change = prediction['prediction'] - 0.5  # Center around 0
        price_target = current_price * (1 + predicted_change * 0.1)  # Max 10% change
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'price_target': price_target,
            'confidence': prediction['confidence'],
            'timeframe': timeframe,
            'direction': 'UP' if predicted_change > 0 else 'DOWN'
        }
    
    def _get_market_data(self, symbol: str) -> Dict:
        """Get market data (simulated)"""
        return {
            'symbol': symbol,
            'price': random.uniform(1000, 5000),
            'volume': random.uniform(100000, 10000000),
            'volatility': random.uniform(0.1, 0.9),
            'hour': time.localtime().tm_hour,
            'day_of_week': time.localtime().tm_wday,
            'market_cap': random.uniform(1000000, 1000000000),
            'liquidity': random.uniform(0.3, 0.9)
        }

class TradingBot:
    """Automated trading with AI"""
    
    def __init__(self):
        self.ai = SelfImprovingAI()
        self.predictor = MarketPredictor()
        self.positions = {}
        self.balance = 10000
        self.trades = []
    
    def analyze_opportunity(self, symbol: str) -> Dict:
        """Analyze trading opportunity"""
        # Get prediction
        prediction = self.predictor.predict_price(symbol)
        
        # Risk assessment
        risk = self.ai.analyze_risk({
            'amount': 1000,
            'symbol': symbol,
            'price': prediction['current_price']
        })
        
        # Calculate position size
        if risk['approved'] and prediction['confidence'] > 0.6:
            position_size = self.balance * 0.1 * prediction['confidence']
            action = 'BUY' if prediction['direction'] == 'UP' else 'SELL'
        else:
            position_size = 0
            action = 'HOLD'
        
        return {
            'symbol': symbol,
            'action': action,
            'position_size': position_size,
            'price_target': prediction['price_target'],
            'risk_score': risk['risk_score'],
            'confidence': prediction['confidence']
        }
    
    def execute_trade(self, symbol: str, action: str, size: float, price: float) -> bool:
        """Execute trade"""
        if action == 'BUY' and self.balance >= size:
            self.balance -= size
            self.positions[symbol] = self.positions.get(symbol, 0) + size / price
            
            self.trades.append({
                'symbol': symbol,
                'action': action,
                'size': size,
                'price': price,
                'timestamp': time.time()
            })
            
            # Learn from trade
            self.ai.learn_pattern({'price': price, 'action': 1}, 0.5)
            return True
            
        elif action == 'SELL' and symbol in self.positions:
            amount = self.positions[symbol]
            self.balance += amount * price
            del self.positions[symbol]
            
            self.trades.append({
                'symbol': symbol,
                'action': action,
                'size': amount * price,
                'price': price,
                'timestamp': time.time()
            })
            
            # Learn from trade
            self.ai.learn_pattern({'price': price, 'action': -1}, 0.5)
            return True
        
        return False
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        total = self.balance
        
        for symbol, amount in self.positions.items():
            current_price = self.predictor._get_market_data(symbol)['price']
            total += amount * current_price
        
        return total

# Demo
def demo_ai():
    """Demonstrate AI capabilities"""
    print("=== QENEX AI Demo ===\n")
    
    # Initialize AI
    ai = SelfImprovingAI()
    bot = TradingBot()
    
    # Train AI with sample data
    print("Training AI...")
    for i in range(20):
        sample_data = {
            'price': random.uniform(1000, 5000),
            'volume': random.uniform(100000, 1000000),
            'hour': random.randint(0, 23)
        }
        outcome = random.random()
        ai.learn_pattern(sample_data, outcome)
    
    print(f"AI Generation: {ai.network.generation}")
    
    # Risk analysis
    print("\n--- Risk Analysis ---")
    transactions = [
        {'amount': 500},
        {'amount': 50000, 'unusual_behavior': True},
        {'amount': 10000, 'hour': 3}
    ]
    
    for tx in transactions:
        risk = ai.analyze_risk(tx)
        print(f"Amount: ${tx.get('amount')}, Risk: {risk['risk_score']:.2f}, Approved: {risk['approved']}")
    
    # Market prediction
    print("\n--- Market Prediction ---")
    symbols = ['BTC', 'ETH', 'QENEX']
    
    for symbol in symbols:
        prediction = bot.predictor.predict_price(symbol)
        print(f"{symbol}: ${prediction['current_price']:.2f} → ${prediction['price_target']:.2f} ({prediction['direction']})")
    
    # Trading simulation
    print("\n--- Trading Bot ---")
    initial_value = bot.get_portfolio_value()
    
    for _ in range(5):
        symbol = random.choice(symbols)
        opportunity = bot.analyze_opportunity(symbol)
        
        if opportunity['action'] != 'HOLD':
            success = bot.execute_trade(
                symbol,
                opportunity['action'],
                opportunity['position_size'],
                opportunity['price_target']
            )
            
            if success:
                print(f"Executed {opportunity['action']} {symbol} for ${opportunity['position_size']:.2f}")
    
    final_value = bot.get_portfolio_value()
    print(f"\nPortfolio: ${initial_value:.2f} → ${final_value:.2f}")
    print(f"AI Generation: {ai.network.generation}")

if __name__ == "__main__":
    demo_ai()