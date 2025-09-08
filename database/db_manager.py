#!/usr/bin/env python3
"""
QENEX Database Manager - SQLite integration for persistent storage
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="/opt/qenex-os/data/qenex.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.init_database()
        
    def init_database(self):
        """Initialize all database tables"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Pipelines table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pipelines (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    repository TEXT,
                    branch TEXT,
                    commit_sha TEXT,
                    status TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    started_at DATETIME,
                    completed_at DATETIME,
                    duration_seconds REAL,
                    trigger_type TEXT,
                    author TEXT,
                    config JSON
                )
            ''')
            
            # Pipeline stages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pipeline_stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pipeline_id TEXT,
                    stage_name TEXT,
                    status TEXT,
                    started_at DATETIME,
                    completed_at DATETIME,
                    duration_seconds REAL,
                    output TEXT,
                    error TEXT,
                    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
                )
            ''')
            
            # Deployments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deployments (
                    id TEXT PRIMARY KEY,
                    pipeline_id TEXT,
                    environment TEXT,
                    version TEXT,
                    status TEXT,
                    deployed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deployed_by TEXT,
                    rollback_from TEXT,
                    config JSON,
                    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
                )
            ''')
            
            # Build artifacts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pipeline_id TEXT,
                    artifact_name TEXT,
                    artifact_type TEXT,
                    size_bytes INTEGER,
                    path TEXT,
                    checksum TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
                )
            ''')
            
            # Test results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pipeline_id TEXT,
                    test_suite TEXT,
                    total_tests INTEGER,
                    passed INTEGER,
                    failed INTEGER,
                    skipped INTEGER,
                    duration_seconds REAL,
                    coverage_percent REAL,
                    report JSON,
                    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
                )
            ''')
            
            # Metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metric_type TEXT,
                    metric_name TEXT,
                    value REAL,
                    labels JSON,
                    pipeline_id TEXT
                )
            ''')
            
            # Users table (for authentication)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    api_key TEXT UNIQUE,
                    role TEXT DEFAULT 'user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Audit log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    action TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    details JSON,
                    ip_address TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Configuration table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS configuration (
                    key TEXT PRIMARY KEY,
                    value JSON,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pipelines_status ON pipelines(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pipelines_created ON pipelines(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_deployments_env ON deployments(environment)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)')
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    # Pipeline operations
    def create_pipeline(self, pipeline_data: Dict[str, Any]) -> str:
        """Create a new pipeline record"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            pipeline_id = pipeline_data.get('id', f"pipeline_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            
            cursor.execute('''
                INSERT INTO pipelines 
                (id, name, repository, branch, commit_sha, status, trigger_type, author, config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pipeline_id,
                pipeline_data.get('name'),
                pipeline_data.get('repository'),
                pipeline_data.get('branch'),
                pipeline_data.get('commit_sha'),
                'pending',
                pipeline_data.get('trigger_type', 'manual'),
                pipeline_data.get('author'),
                json.dumps(pipeline_data.get('config', {}))
            ))
            
            conn.commit()
            
            logger.info(f"Created pipeline: {pipeline_id}")
            return pipeline_id
    
    def update_pipeline_status(self, pipeline_id: str, status: str, **kwargs):
        """Update pipeline status and optional fields"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = ['status = ?']
            values = [status]
            
            if status == 'running' and 'started_at' not in kwargs:
                updates.append('started_at = CURRENT_TIMESTAMP')
            
            if status in ['success', 'failed', 'cancelled']:
                updates.append('completed_at = CURRENT_TIMESTAMP')
                
                # Calculate duration
                cursor.execute('SELECT started_at FROM pipelines WHERE id = ?', (pipeline_id,))
                result = cursor.fetchone()
                if result and result[0]:
                    started = datetime.fromisoformat(result[0])
                    duration = (datetime.now() - started).total_seconds()
                    updates.append('duration_seconds = ?')
                    values.append(duration)
            
            # SECURITY FIX: Validate column names to prevent SQL injection
            allowed_columns = ['started_at', 'completed_at', 'duration_seconds']
            for key, value in kwargs.items():
                if key in allowed_columns:
                    updates.append(f'{key} = ?')
                    values.append(value)
            
            if updates:  # Only execute if there are valid updates
                values.append(pipeline_id)
                query = f"UPDATE pipelines SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, values)
            
            conn.commit()
    
    def get_pipeline(self, pipeline_id: str) -> Optional[Dict]:
        """Get pipeline details"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM pipelines WHERE id = ?', (pipeline_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def get_recent_pipelines(self, limit: int = 10) -> List[Dict]:
        """Get recent pipelines"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM pipelines 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # Stage operations
    def add_stage(self, pipeline_id: str, stage_name: str, status: str = 'pending'):
        """Add a stage to pipeline"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO pipeline_stages (pipeline_id, stage_name, status)
                VALUES (?, ?, ?)
            ''', (pipeline_id, stage_name, status))
            
            conn.commit()
    
    def update_stage(self, pipeline_id: str, stage_name: str, status: str, **kwargs):
        """Update stage status"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = ['status = ?']
            values = [status]
            
            if status == 'running':
                updates.append('started_at = CURRENT_TIMESTAMP')
            elif status in ['success', 'failed']:
                updates.append('completed_at = CURRENT_TIMESTAMP')
            
            # SECURITY FIX: Validate column names to prevent SQL injection
            allowed_stage_columns = ['output', 'error', 'duration_seconds']
            for key in allowed_stage_columns:
                if key in kwargs:
                    updates.append(f'{key} = ?')
                    values.append(kwargs[key])
            
            if updates:  # Only execute if there are valid updates
                values.extend([pipeline_id, stage_name])
                query = f"UPDATE pipeline_stages SET {', '.join(updates)} WHERE pipeline_id = ? AND stage_name = ?"
                cursor.execute(query, values)
            
            conn.commit()
    
    # Deployment operations
    def create_deployment(self, deployment_data: Dict[str, Any]) -> str:
        """Create deployment record"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            deployment_id = deployment_data.get('id', f"deploy_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            
            cursor.execute('''
                INSERT INTO deployments 
                (id, pipeline_id, environment, version, status, deployed_by, config)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                deployment_id,
                deployment_data.get('pipeline_id'),
                deployment_data.get('environment'),
                deployment_data.get('version'),
                'pending',
                deployment_data.get('deployed_by'),
                json.dumps(deployment_data.get('config', {}))
            ))
            
            conn.commit()
            
            return deployment_id
    
    # Metrics operations
    def record_metric(self, metric_type: str, metric_name: str, value: float, 
                     labels: Dict = None, pipeline_id: str = None):
        """Record a metric"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO metrics (metric_type, metric_name, value, labels, pipeline_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (metric_type, metric_name, value, json.dumps(labels or {}), pipeline_id))
            
            conn.commit()
    
    def get_metrics(self, metric_type: str = None, since: datetime = None) -> List[Dict]:
        """Get metrics with optional filters"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM metrics WHERE 1=1'
        params = []
        
        if metric_type:
            query += ' AND metric_type = ?'
            params.append(metric_type)
        
        if since:
            query += ' AND timestamp > ?'
            params.append(since.isoformat())
        
        query += ' ORDER BY timestamp DESC LIMIT 1000'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Pipeline statistics
        cursor.execute('SELECT COUNT(*) FROM pipelines')
        stats['total_pipelines'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pipelines WHERE status = 'running'")
        stats['running_pipelines'] = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*)
            FROM pipelines
            WHERE completed_at IS NOT NULL
        ''')
        result = cursor.fetchone()[0]
        stats['success_rate'] = round(result, 1) if result else 0
        
        # Deployment statistics
        cursor.execute('SELECT COUNT(*) FROM deployments')
        stats['total_deployments'] = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT environment, COUNT(*) 
            FROM deployments 
            GROUP BY environment
        ''')
        stats['deployments_by_env'] = dict(cursor.fetchall())
        
        # Average pipeline duration
        cursor.execute('''
            SELECT AVG(duration_seconds) 
            FROM pipelines 
            WHERE duration_seconds IS NOT NULL
        ''')
        avg_duration = cursor.fetchone()[0]
        stats['avg_pipeline_duration'] = round(avg_duration, 1) if avg_duration else 0
        
        conn.close()
        return stats
    
    # Audit logging
    def log_audit(self, user_id: int, action: str, resource_type: str, 
                  resource_id: str, details: Dict = None, ip_address: str = None):
        """Log an audit event"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO audit_log 
                (user_id, action, resource_type, resource_id, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, action, resource_type, resource_id, 
                  json.dumps(details or {}), ip_address))
            
            conn.commit()
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old data"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            # Delete old pipelines and related data
            cursor.execute('''
                DELETE FROM pipelines 
                WHERE created_at < ? AND status IN ('success', 'failed', 'cancelled')
            ''', (cutoff_date.isoformat(),))
            
            deleted_pipelines = cursor.rowcount
            
            # Delete orphaned stages
            cursor.execute('''
                DELETE FROM pipeline_stages 
                WHERE pipeline_id NOT IN (SELECT id FROM pipelines)
            ''')
            
            # Delete old metrics
            cursor.execute('DELETE FROM metrics WHERE timestamp < ?', 
                         (cutoff_date.isoformat(),))
            
            deleted_metrics = cursor.rowcount
            
            conn.commit()
            
            logger.info(f"Cleanup: Deleted {deleted_pipelines} old pipelines and {deleted_metrics} old metrics")

# Global instance
db = DatabaseManager()

if __name__ == "__main__":
    # Test database operations
    db = DatabaseManager()
    
    # Create a test pipeline
    pipeline_id = db.create_pipeline({
        'name': 'test-pipeline',
        'repository': 'qenex/test',
        'branch': 'main',
        'commit_sha': 'abc123',
        'author': 'admin'
    })
    
    print(f"Created pipeline: {pipeline_id}")
    
    # Update status
    db.update_pipeline_status(pipeline_id, 'running')
    db.add_stage(pipeline_id, 'build', 'running')
    
    # Get statistics
    stats = db.get_statistics()
    print(f"Statistics: {json.dumps(stats, indent=2)}")
    
    # Get recent pipelines
    recent = db.get_recent_pipelines(5)
    print(f"Recent pipelines: {len(recent)}")