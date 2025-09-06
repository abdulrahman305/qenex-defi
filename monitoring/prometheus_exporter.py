#!/usr/bin/env python3
"""
QENEX Prometheus Metrics Exporter
"""

import time
import psutil
import sqlite3
import json
from prometheus_client import start_http_server, Gauge, Counter, Histogram, Summary
from prometheus_client.core import CollectorRegistry
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create metrics registry
registry = CollectorRegistry()

# System metrics
system_uptime = Gauge('qenex_system_uptime_seconds', 'System uptime in seconds', registry=registry)
system_load = Gauge('qenex_system_load_average', 'System load average', ['period'], registry=registry)
system_cpu_percent = Gauge('qenex_cpu_usage_percent', 'CPU usage percentage', registry=registry)
system_memory_percent = Gauge('qenex_memory_usage_percent', 'Memory usage percentage', registry=registry)
system_disk_percent = Gauge('qenex_disk_usage_percent', 'Disk usage percentage', ['mount'], registry=registry)
system_network_bytes = Counter('qenex_network_bytes_total', 'Network bytes transferred', ['direction'], registry=registry)

# Process metrics
qenex_processes = Gauge('qenex_active_processes', 'Number of QENEX processes', registry=registry)
process_cpu_seconds = Counter('qenex_process_cpu_seconds_total', 'Total CPU seconds', ['process'], registry=registry)
process_memory_bytes = Gauge('qenex_process_memory_bytes', 'Process memory usage', ['process'], registry=registry)

# Pipeline metrics
pipeline_total = Counter('qenex_pipeline_runs_total', 'Total pipeline runs', ['status'], registry=registry)
pipeline_duration = Histogram('qenex_pipeline_duration_seconds', 'Pipeline duration', ['pipeline'], registry=registry)
pipeline_queue_size = Gauge('qenex_pipeline_queue_size', 'Pipeline queue size', registry=registry)
pipeline_success_rate = Gauge('qenex_pipeline_success_rate', 'Pipeline success rate', registry=registry)

# Deployment metrics
deployment_total = Counter('qenex_deployments_total', 'Total deployments', ['environment', 'status'], registry=registry)
deployment_duration = Summary('qenex_deployment_duration_seconds', 'Deployment duration', registry=registry)
deployment_rollback = Counter('qenex_deployment_rollbacks_total', 'Deployment rollbacks', registry=registry)

# Webhook metrics
webhook_received = Counter('qenex_webhooks_received_total', 'Webhooks received', ['source', 'event'], registry=registry)
webhook_processed = Counter('qenex_webhooks_processed_total', 'Webhooks processed', ['source', 'status'], registry=registry)

# Database metrics
db_connections = Gauge('qenex_database_connections', 'Database connections', registry=registry)
db_queries = Counter('qenex_database_queries_total', 'Database queries', ['type'], registry=registry)

# Alert metrics
alerts_triggered = Counter('qenex_alerts_triggered_total', 'Alerts triggered', ['severity', 'type'], registry=registry)

class MetricsCollector:
    def __init__(self):
        self.db_path = "/opt/qenex-os/data/metrics.db"
        self.init_database()
        self.last_network = psutil.net_io_counters()
        
    def init_database(self):
        """Initialize metrics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create metrics tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pipeline_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_id TEXT,
                start_time DATETIME,
                end_time DATETIME,
                status TEXT,
                duration_seconds REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deployment_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT,
                environment TEXT,
                start_time DATETIME,
                end_time DATETIME,
                status TEXT,
                rollback BOOLEAN
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                severity TEXT,
                type TEXT,
                message TEXT,
                resolved BOOLEAN
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def collect_system_metrics(self):
        """Collect system-level metrics"""
        # Uptime
        with open('/proc/uptime', 'r') as f:
            uptime = float(f.readline().split()[0])
            system_uptime.set(uptime)
        
        # Load average
        load = os.getloadavg()
        system_load.labels(period='1m').set(load[0])
        system_load.labels(period='5m').set(load[1])
        system_load.labels(period='15m').set(load[2])
        
        # CPU and Memory
        system_cpu_percent.set(psutil.cpu_percent(interval=1))
        system_memory_percent.set(psutil.virtual_memory().percent)
        
        # Disk usage
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                system_disk_percent.labels(mount=partition.mountpoint).set(usage.percent)
            except:
                pass
        
        # Network
        current_network = psutil.net_io_counters()
        bytes_sent = current_network.bytes_sent - self.last_network.bytes_sent
        bytes_recv = current_network.bytes_recv - self.last_network.bytes_recv
        
        if bytes_sent > 0:
            system_network_bytes.labels(direction='sent').inc(bytes_sent)
        if bytes_recv > 0:
            system_network_bytes.labels(direction='received').inc(bytes_recv)
        
        self.last_network = current_network
    
    def collect_process_metrics(self):
        """Collect process-level metrics"""
        qenex_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_times', 'memory_info', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info.get('cmdline', []))
                if any(keyword in cmdline.lower() for keyword in ['qenex', 'cicd', 'gitops']):
                    qenex_count += 1
                    
                    # CPU time
                    cpu_times = proc.info['cpu_times']
                    if cpu_times:
                        process_cpu_seconds.labels(process=proc.info['name']).inc(
                            cpu_times.user + cpu_times.system
                        )
                    
                    # Memory
                    mem_info = proc.info['memory_info']
                    if mem_info:
                        process_memory_bytes.labels(process=proc.info['name']).set(mem_info.rss)
            except:
                pass
        
        qenex_processes.set(qenex_count)
    
    def collect_pipeline_metrics(self):
        """Collect pipeline metrics from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get pipeline statistics
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM pipeline_metrics 
            WHERE datetime(start_time) > datetime('now', '-1 hour')
            GROUP BY status
        ''')
        
        for status, count in cursor.fetchall():
            pipeline_total.labels(status=status).inc(count)
        
        # Success rate
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*)
            FROM pipeline_metrics
            WHERE datetime(start_time) > datetime('now', '-24 hours')
        ''')
        
        success_rate = cursor.fetchone()[0]
        if success_rate:
            pipeline_success_rate.set(success_rate)
        
        # Check queue from JSON file
        try:
            api_data = json.loads(Path('/opt/qenex-os/dashboard/api.json').read_text())
            pipeline_queue_size.set(api_data.get('pipelines', 0))
        except:
            pass
        
        conn.close()
    
    def collect_deployment_metrics(self):
        """Collect deployment metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Deployment counts
        cursor.execute('''
            SELECT environment, status, COUNT(*)
            FROM deployment_metrics
            WHERE datetime(start_time) > datetime('now', '-24 hours')
            GROUP BY environment, status
        ''')
        
        for env, status, count in cursor.fetchall():
            deployment_total.labels(environment=env, status=status).inc(count)
        
        # Rollback count
        cursor.execute('''
            SELECT COUNT(*)
            FROM deployment_metrics
            WHERE rollback = 1 AND datetime(start_time) > datetime('now', '-24 hours')
        ''')
        
        rollback_count = cursor.fetchone()[0]
        if rollback_count:
            deployment_rollback.inc(rollback_count)
        
        conn.close()
    
    def check_alerts(self):
        """Check and trigger alerts based on thresholds"""
        alerts = []
        
        # High load alert
        if os.getloadavg()[0] > 10:
            alerts.append(('critical', 'high_load', f'Load average: {os.getloadavg()[0]:.2f}'))
        
        # High memory alert
        mem_percent = psutil.virtual_memory().percent
        if mem_percent > 90:
            alerts.append(('critical', 'high_memory', f'Memory usage: {mem_percent:.1f}%'))
        elif mem_percent > 80:
            alerts.append(('warning', 'high_memory', f'Memory usage: {mem_percent:.1f}%'))
        
        # Disk space alert
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                if usage.percent > 90:
                    alerts.append(('critical', 'low_disk', f'Disk {partition.mountpoint}: {usage.percent:.1f}%'))
            except:
                pass
        
        # Store and count alerts
        if alerts:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for severity, alert_type, message in alerts:
                alerts_triggered.labels(severity=severity, type=alert_type).inc()
                
                cursor.execute('''
                    INSERT INTO alert_history (timestamp, severity, type, message, resolved)
                    VALUES (datetime('now'), ?, ?, ?, 0)
                ''', (severity, alert_type, message))
                
                logger.warning(f"Alert: [{severity}] {alert_type} - {message}")
            
            conn.commit()
            conn.close()
    
    def collect_all_metrics(self):
        """Collect all metrics"""
        try:
            self.collect_system_metrics()
            self.collect_process_metrics()
            self.collect_pipeline_metrics()
            self.collect_deployment_metrics()
            self.check_alerts()
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")

import os

def main():
    """Main metrics collection loop"""
    collector = MetricsCollector()
    
    # Start Prometheus HTTP server
    start_http_server(9090, registry=registry)
    logger.info("Prometheus metrics exporter started on port 9090")
    logger.info("Access metrics at http://localhost:9090/metrics")
    
    # Collect metrics every 15 seconds
    while True:
        collector.collect_all_metrics()
        time.sleep(15)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Metrics exporter stopped")