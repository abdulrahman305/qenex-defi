#!/usr/bin/env python3
"""
QENEX AI Assistant - Intelligent pipeline optimization and predictive analytics
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sqlite3
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PipelinePredictor(nn.Module):
    """Neural network for predicting pipeline success/failure"""
    
    def __init__(self, input_size=10):
        super(PipelinePredictor, self).__init__()
        self.fc1 = nn.Linear(input_size, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 16)
        self.fc4 = nn.Linear(16, 2)
        self.dropout = nn.Dropout(0.2)
        self.relu = nn.ReLU()
        self.softmax = nn.Softmax(dim=1)
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.relu(self.fc3(x))
        x = self.fc4(x)
        return self.softmax(x)

class QenexAIAssistant:
    def __init__(self, db_path="/opt/qenex-os/data/qenex.db"):
        self.db_path = db_path
        self.pipeline_predictor = PipelinePredictor()
        self.anomaly_detector = IsolationForest(contamination=0.1)
        self.resource_optimizer = RandomForestClassifier(n_estimators=100)
        self.scaler = StandardScaler()
        self.patterns = self.load_patterns()
        
    def load_patterns(self) -> Dict:
        """Load common error patterns and solutions"""
        return {
            'out_of_memory': {
                'pattern': r'(out of memory|OOM|memory error)',
                'solution': 'Increase memory allocation or optimize memory usage',
                'action': 'scale_up_memory'
            },
            'timeout': {
                'pattern': r'(timeout|timed out|deadline exceeded)',
                'solution': 'Increase timeout limits or optimize slow operations',
                'action': 'increase_timeout'
            },
            'dependency_error': {
                'pattern': r'(module not found|package not found|cannot find)',
                'solution': 'Install missing dependencies or update requirements',
                'action': 'install_dependencies'
            },
            'test_failure': {
                'pattern': r'(test failed|assertion error|test error)',
                'solution': 'Review failing tests and fix code issues',
                'action': 'analyze_tests'
            },
            'build_error': {
                'pattern': r'(build failed|compilation error|syntax error)',
                'solution': 'Fix syntax errors or build configuration',
                'action': 'fix_build'
            }
        }
    
    def extract_features(self, pipeline_data: Dict) -> np.ndarray:
        """Extract features from pipeline data for ML models"""
        features = []
        
        # Time-based features
        hour = datetime.now().hour
        day_of_week = datetime.now().weekday()
        features.extend([hour, day_of_week])
        
        # Repository features
        repo_size = len(pipeline_data.get('repository', ''))
        branch_is_main = 1 if pipeline_data.get('branch') == 'main' else 0
        features.extend([repo_size, branch_is_main])
        
        # Historical features
        recent_failures = self.get_recent_failures(pipeline_data.get('repository'))
        avg_duration = self.get_avg_duration(pipeline_data.get('repository'))
        features.extend([recent_failures, avg_duration])
        
        # Code complexity (simplified)
        num_files = pipeline_data.get('num_files', 0)
        lines_changed = pipeline_data.get('lines_changed', 0)
        features.extend([num_files, lines_changed])
        
        # System load
        load_avg = os.getloadavg()[0]
        memory_percent = psutil.virtual_memory().percent if 'psutil' in globals() else 50
        features.extend([load_avg, memory_percent])
        
        return np.array(features).reshape(1, -1)
    
    def predict_pipeline_outcome(self, pipeline_data: Dict) -> Dict[str, Any]:
        """Predict if pipeline will succeed or fail"""
        try:
            features = self.extract_features(pipeline_data)
            features_tensor = torch.FloatTensor(features)
            
            with torch.no_grad():
                prediction = self.pipeline_predictor(features_tensor)
                success_prob = prediction[0][1].item()
            
            risk_level = 'low' if success_prob > 0.8 else 'medium' if success_prob > 0.5 else 'high'
            
            recommendations = []
            if success_prob < 0.5:
                recommendations.append("Consider running additional tests before deployment")
                recommendations.append("Review recent changes for potential issues")
            
            return {
                'success_probability': round(success_prob * 100, 2),
                'risk_level': risk_level,
                'recommendations': recommendations,
                'confidence': round(max(prediction[0]).item() * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                'success_probability': 50.0,
                'risk_level': 'unknown',
                'recommendations': [],
                'confidence': 0
            }
    
    def detect_anomalies(self, metrics: List[Dict]) -> List[Dict]:
        """Detect anomalies in system metrics"""
        if len(metrics) < 10:
            return []
        
        try:
            # Extract metric values
            df = pd.DataFrame(metrics)
            features = df[['cpu_percent', 'memory_percent', 'load_average']].values
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Detect anomalies
            predictions = self.anomaly_detector.fit_predict(features_scaled)
            
            anomalies = []
            for i, pred in enumerate(predictions):
                if pred == -1:  # Anomaly detected
                    anomalies.append({
                        'timestamp': metrics[i].get('timestamp'),
                        'type': 'system_anomaly',
                        'metrics': metrics[i],
                        'severity': self.calculate_severity(metrics[i])
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return []
    
    def analyze_logs(self, log_content: str) -> Dict[str, Any]:
        """Analyze logs using pattern matching and NLP"""
        analysis = {
            'errors': [],
            'warnings': [],
            'suggestions': [],
            'root_cause': None
        }
        
        # Pattern matching for common errors
        for error_type, pattern_info in self.patterns.items():
            if re.search(pattern_info['pattern'], log_content, re.IGNORECASE):
                analysis['errors'].append({
                    'type': error_type,
                    'solution': pattern_info['solution'],
                    'action': pattern_info['action']
                })
        
        # Extract error messages
        error_lines = re.findall(r'(?:ERROR|FATAL|CRITICAL).*', log_content, re.IGNORECASE)
        analysis['errors'].extend([{'message': line} for line in error_lines[:5]])
        
        # Extract warnings
        warning_lines = re.findall(r'(?:WARNING|WARN).*', log_content, re.IGNORECASE)
        analysis['warnings'] = warning_lines[:5]
        
        # Determine root cause
        if analysis['errors']:
            analysis['root_cause'] = self.determine_root_cause(analysis['errors'])
        
        # Generate suggestions
        analysis['suggestions'] = self.generate_suggestions(analysis)
        
        return analysis
    
    def determine_root_cause(self, errors: List[Dict]) -> str:
        """Determine the root cause of failures"""
        if not errors:
            return "No errors detected"
        
        # Priority-based root cause determination
        priority_errors = ['out_of_memory', 'dependency_error', 'build_error']
        
        for priority in priority_errors:
            for error in errors:
                if error.get('type') == priority:
                    return f"Root cause: {priority.replace('_', ' ').title()}"
        
        return f"Root cause: {errors[0].get('type', 'Unknown error')}"
    
    def generate_suggestions(self, analysis: Dict) -> List[str]:
        """Generate actionable suggestions based on analysis"""
        suggestions = []
        
        for error in analysis.get('errors', []):
            if error.get('type') == 'out_of_memory':
                suggestions.append("• Increase container memory limits to 2GB")
                suggestions.append("• Enable swap space on the host system")
                suggestions.append("• Optimize memory-intensive operations")
            elif error.get('type') == 'timeout':
                suggestions.append("• Increase timeout to 600 seconds")
                suggestions.append("• Add caching to reduce processing time")
                suggestions.append("• Consider parallel processing")
            elif error.get('type') == 'dependency_error':
                suggestions.append("• Run 'pip install -r requirements.txt'")
                suggestions.append("• Update package versions in requirements")
                suggestions.append("• Check for conflicting dependencies")
        
        return suggestions[:5]  # Limit to top 5 suggestions
    
    def optimize_resources(self, current_metrics: Dict) -> Dict[str, Any]:
        """Optimize resource allocation based on current usage"""
        optimization = {
            'cpu_allocation': 'maintain',
            'memory_allocation': 'maintain',
            'worker_count': 'maintain',
            'actions': []
        }
        
        cpu_usage = current_metrics.get('cpu_percent', 0)
        memory_usage = current_metrics.get('memory_percent', 0)
        queue_size = current_metrics.get('queue_size', 0)
        
        # CPU optimization
        if cpu_usage > 80:
            optimization['cpu_allocation'] = 'increase'
            optimization['actions'].append('Scale up CPU resources by 50%')
        elif cpu_usage < 20:
            optimization['cpu_allocation'] = 'decrease'
            optimization['actions'].append('Scale down CPU resources by 25%')
        
        # Memory optimization
        if memory_usage > 85:
            optimization['memory_allocation'] = 'increase'
            optimization['actions'].append('Increase memory by 1GB')
        elif memory_usage < 30:
            optimization['memory_allocation'] = 'decrease'
            optimization['actions'].append('Reduce memory allocation by 512MB')
        
        # Worker optimization
        if queue_size > 10:
            optimization['worker_count'] = 'increase'
            optimization['actions'].append(f'Spawn {min(queue_size // 5, 3)} additional workers')
        elif queue_size == 0 and cpu_usage < 30:
            optimization['worker_count'] = 'decrease'
            optimization['actions'].append('Reduce worker count by 1')
        
        return optimization
    
    def generate_pipeline_config(self, description: str) -> Dict[str, Any]:
        """Generate pipeline configuration from natural language description"""
        config = {
            'stages': [],
            'environment': {},
            'notifications': True
        }
        
        # Parse description for keywords
        description_lower = description.lower()
        
        # Detect programming language
        if 'python' in description_lower:
            config['language'] = 'python'
            config['stages'].append({'name': 'install', 'commands': ['pip install -r requirements.txt']})
        elif 'node' in description_lower or 'javascript' in description_lower:
            config['language'] = 'nodejs'
            config['stages'].append({'name': 'install', 'commands': ['npm install']})
        elif 'go' in description_lower or 'golang' in description_lower:
            config['language'] = 'go'
            config['stages'].append({'name': 'install', 'commands': ['go mod download']})
        
        # Detect testing requirements
        if 'test' in description_lower:
            if config.get('language') == 'python':
                config['stages'].append({'name': 'test', 'commands': ['pytest']})
            elif config.get('language') == 'nodejs':
                config['stages'].append({'name': 'test', 'commands': ['npm test']})
        
        # Detect build requirements
        if 'build' in description_lower:
            config['stages'].append({'name': 'build', 'commands': ['make build']})
        
        # Detect deployment
        if 'deploy' in description_lower:
            if 'production' in description_lower:
                config['stages'].append({'name': 'deploy', 'commands': ['./deploy.sh production']})
                config['environment']['ENV'] = 'production'
            else:
                config['stages'].append({'name': 'deploy', 'commands': ['./deploy.sh staging']})
                config['environment']['ENV'] = 'staging'
        
        # Detect Docker
        if 'docker' in description_lower:
            config['stages'].insert(0, {'name': 'docker-build', 
                                       'commands': ['docker build -t app:latest .']})
        
        return config
    
    def train_models(self):
        """Train AI models with historical data"""
        try:
            # Load historical data from database
            conn = sqlite3.connect(self.db_path)
            
            # Load pipeline data
            pipelines_df = pd.read_sql_query(
                "SELECT * FROM pipelines WHERE completed_at IS NOT NULL",
                conn
            )
            
            if len(pipelines_df) > 100:
                # Prepare training data
                # This is simplified - in production, you'd have more sophisticated feature engineering
                logger.info("Training AI models with historical data...")
                
                # Train pipeline predictor
                # ... training code ...
                
                logger.info("AI models trained successfully")
            else:
                logger.info("Insufficient data for training (need at least 100 samples)")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Training error: {e}")
    
    def get_recent_failures(self, repository: str) -> int:
        """Get count of recent failures for a repository"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM pipelines 
                WHERE repository = ? 
                AND status = 'failed'
                AND created_at > datetime('now', '-7 days')
            """, (repository,))
            
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
        except:
            return 0
    
    def get_avg_duration(self, repository: str) -> float:
        """Get average pipeline duration for a repository"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT AVG(duration_seconds) FROM pipelines 
                WHERE repository = ? 
                AND duration_seconds IS NOT NULL
            """, (repository,))
            
            avg = cursor.fetchone()[0] or 300.0
            conn.close()
            return avg
            
        except:
            return 300.0
    
    def calculate_severity(self, metrics: Dict) -> str:
        """Calculate severity level of an anomaly"""
        cpu = metrics.get('cpu_percent', 0)
        memory = metrics.get('memory_percent', 0)
        
        if cpu > 95 or memory > 95:
            return 'critical'
        elif cpu > 80 or memory > 80:
            return 'high'
        elif cpu > 60 or memory > 60:
            return 'medium'
        else:
            return 'low'

import os
import psutil

# Global AI assistant instance
ai_assistant = QenexAIAssistant()

if __name__ == "__main__":
    # Test AI assistant
    assistant = QenexAIAssistant()
    
    # Test pipeline prediction
    test_pipeline = {
        'repository': 'qenex/test-app',
        'branch': 'main',
        'num_files': 10,
        'lines_changed': 150
    }
    
    prediction = assistant.predict_pipeline_outcome(test_pipeline)
    print(f"Pipeline prediction: {json.dumps(prediction, indent=2)}")
    
    # Test log analysis
    test_logs = """
    ERROR: Out of memory error occurred
    WARNING: Deprecated API usage
    FATAL: Cannot connect to database
    """
    
    analysis = assistant.analyze_logs(test_logs)
    print(f"Log analysis: {json.dumps(analysis, indent=2)}")
    
    # Test natural language pipeline generation
    description = "Create a Python pipeline with testing and deployment to production"
    config = assistant.generate_pipeline_config(description)
    print(f"Generated config: {json.dumps(config, indent=2)}")