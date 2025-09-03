#!/usr/bin/env python3
"""
QENEX Monitoring & Alert System
Real-time monitoring with intelligent alerting
"""

import asyncio
import json
import smtplib
import subprocess
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import psutil
import aiohttp

class AlertSystem:
    """Advanced monitoring and alerting system"""
    
    def __init__(self):
        self.alerts = []
        self.alert_rules = self.load_alert_rules()
        self.notification_channels = ['console', 'file', 'webhook']
        self.alert_history = []
        self.alert_file = Path('/opt/qenex-os/logs/alerts.log')
        self.webhook_url = None
        
    def load_alert_rules(self) -> List[Dict]:
        """Load alert rules configuration"""
        return [
            {
                'name': 'High CPU Usage',
                'metric': 'cpu',
                'threshold': 85,
                'duration': 60,
                'severity': 'warning',
                'action': 'optimize_cpu'
            },
            {
                'name': 'Critical Memory Usage',
                'metric': 'memory',
                'threshold': 90,
                'duration': 30,
                'severity': 'critical',
                'action': 'free_memory'
            },
            {
                'name': 'Disk Space Low',
                'metric': 'disk',
                'threshold': 85,
                'duration': 0,
                'severity': 'warning',
                'action': 'cleanup_disk'
            },
            {
                'name': 'Service Down',
                'metric': 'service',
                'threshold': 0,
                'duration': 10,
                'severity': 'critical',
                'action': 'restart_service'
            },
            {
                'name': 'Network Latency',
                'metric': 'network_latency',
                'threshold': 100,
                'duration': 30,
                'severity': 'warning',
                'action': 'optimize_network'
            },
            {
                'name': 'Failed Deployments',
                'metric': 'deployment_failures',
                'threshold': 3,
                'duration': 300,
                'severity': 'warning',
                'action': 'review_deployments'
            }
        ]
    
    async def monitor(self):
        """Main monitoring loop"""
        metrics_history = {}
        
        while True:
            try:
                # Collect current metrics
                metrics = await self.collect_metrics()
                
                # Check each alert rule
                for rule in self.alert_rules:
                    metric_name = rule['metric']
                    
                    if metric_name not in metrics:
                        continue
                    
                    current_value = metrics[metric_name]
                    
                    # Initialize history for this metric
                    if metric_name not in metrics_history:
                        metrics_history[metric_name] = []
                    
                    # Add to history
                    metrics_history[metric_name].append({
                        'value': current_value,
                        'timestamp': datetime.now()
                    })
                    
                    # Keep only recent history (last 5 minutes)
                    cutoff_time = datetime.now() - timedelta(minutes=5)
                    metrics_history[metric_name] = [
                        m for m in metrics_history[metric_name]
                        if m['timestamp'] > cutoff_time
                    ]
                    
                    # Check if alert should trigger
                    if await self.should_alert(rule, metrics_history[metric_name]):
                        await self.trigger_alert(rule, current_value)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
            
            await asyncio.sleep(5)
    
    async def collect_metrics(self) -> Dict:
        """Collect system metrics"""
        metrics = {}
        
        try:
            # CPU metrics
            metrics['cpu'] = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            metrics['memory'] = psutil.virtual_memory().percent
            
            # Disk metrics
            metrics['disk'] = psutil.disk_usage('/').percent
            
            # Network latency (ping to 8.8.8.8)
            try:
                result = subprocess.run(['ping', '-c', '1', '-W', '1', '8.8.8.8'],
                                      capture_output=True, text=True)
                if 'time=' in result.stdout:
                    latency = float(result.stdout.split('time=')[1].split(' ')[0])
                    metrics['network_latency'] = latency
            except:
                metrics['network_latency'] = 0
            
            # Service status
            critical_services = ['nginx', 'qenex']
            down_services = 0
            for service in critical_services:
                result = subprocess.run(['pgrep', '-x', service], capture_output=True)
                if result.returncode != 0:
                    down_services += 1
            metrics['service'] = down_services
            
            # Deployment failures (from database/logs)
            try:
                log_file = Path('/opt/qenex-os/logs/deployments.log')
                if log_file.exists():
                    recent_logs = log_file.read_text().split('\n')[-100:]
                    failures = sum(1 for log in recent_logs if 'FAILED' in log)
                    metrics['deployment_failures'] = failures
            except:
                metrics['deployment_failures'] = 0
            
        except Exception as e:
            print(f"Metrics collection error: {e}")
        
        return metrics
    
    async def should_alert(self, rule: Dict, history: List[Dict]) -> bool:
        """Determine if alert should be triggered"""
        if not history:
            return False
        
        threshold = rule['threshold']
        duration = rule['duration']
        
        # Immediate alert (no duration requirement)
        if duration == 0:
            return history[-1]['value'] > threshold
        
        # Check if threshold exceeded for required duration
        cutoff_time = datetime.now() - timedelta(seconds=duration)
        recent_values = [h for h in history if h['timestamp'] > cutoff_time]
        
        if not recent_values:
            return False
        
        # All recent values must exceed threshold
        return all(h['value'] > threshold for h in recent_values)
    
    async def trigger_alert(self, rule: Dict, current_value: float):
        """Trigger an alert"""
        alert = {
            'id': len(self.alerts) + 1,
            'timestamp': datetime.now().isoformat(),
            'rule': rule['name'],
            'severity': rule['severity'],
            'value': current_value,
            'threshold': rule['threshold'],
            'action': rule['action']
        }
        
        # Check if similar alert was recently triggered
        recent_cutoff = datetime.now() - timedelta(minutes=5)
        recent_similar = any(
            a['rule'] == alert['rule'] and 
            datetime.fromisoformat(a['timestamp']) > recent_cutoff
            for a in self.alert_history
        )
        
        if not recent_similar:
            self.alerts.append(alert)
            self.alert_history.append(alert)
            
            # Send notifications
            await self.send_notifications(alert)
            
            # Take automated action
            await self.take_action(alert)
    
    async def send_notifications(self, alert: Dict):
        """Send alert notifications"""
        message = f"""
🚨 QENEX Alert: {alert['rule']}
Severity: {alert['severity'].upper()}
Value: {alert['value']:.2f} (Threshold: {alert['threshold']})
Time: {alert['timestamp']}
Action: {alert['action']}
"""
        
        # Console notification
        if 'console' in self.notification_channels:
            print(message)
        
        # File notification
        if 'file' in self.notification_channels:
            self.alert_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.alert_file, 'a') as f:
                f.write(f"{alert['timestamp']} - {message}\n")
        
        # Webhook notification
        if 'webhook' in self.notification_channels and self.webhook_url:
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(self.webhook_url, json=alert)
            except:
                pass
    
    async def take_action(self, alert: Dict):
        """Take automated action based on alert"""
        action = alert['action']
        
        try:
            if action == 'optimize_cpu':
                # Enable CPU governor
                subprocess.run(['cpupower', 'frequency-set', '-g', 'powersave'],
                             capture_output=True)
                
            elif action == 'free_memory':
                # Clear caches
                subprocess.run(['sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'],
                             capture_output=True)
                
            elif action == 'cleanup_disk':
                # Clean temporary files
                subprocess.run(['find', '/tmp', '-type', 'f', '-mtime', '+1', '-delete'],
                             capture_output=True)
                subprocess.run(['find', '/var/log', '-name', '*.log', '-size', '+100M', '-delete'],
                             capture_output=True)
                
            elif action == 'restart_service':
                # Restart critical services
                subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True)
                
            elif action == 'optimize_network':
                # Optimize network settings
                subprocess.run(['sysctl', '-w', 'net.ipv4.tcp_congestion_control=bbr'],
                             capture_output=True)
                
            elif action == 'review_deployments':
                # Mark for manual review
                print("Deployment failures detected - manual review required")
                
        except Exception as e:
            print(f"Action execution error: {e}")


class AnomalyDetector:
    """Detect anomalies in system behavior"""
    
    def __init__(self):
        self.baseline = {}
        self.anomalies = []
        
    async def learn_baseline(self, duration_hours: int = 24):
        """Learn normal system behavior"""
        print(f"Learning baseline for {duration_hours} hours...")
        
        metrics_history = []
        end_time = datetime.now() + timedelta(hours=duration_hours)
        
        while datetime.now() < end_time:
            metrics = await self.collect_metrics()
            metrics_history.append(metrics)
            
            # Update baseline statistics
            for key, value in metrics.items():
                if key not in self.baseline:
                    self.baseline[key] = {'values': [], 'mean': 0, 'std': 0}
                
                self.baseline[key]['values'].append(value)
            
            await asyncio.sleep(60)  # Collect every minute
        
        # Calculate statistics
        for key in self.baseline:
            values = self.baseline[key]['values']
            if values:
                self.baseline[key]['mean'] = sum(values) / len(values)
                # Simple standard deviation
                mean = self.baseline[key]['mean']
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                self.baseline[key]['std'] = variance ** 0.5
        
        print("Baseline learning complete")
    
    async def detect_anomalies(self, metrics: Dict) -> List[Dict]:
        """Detect anomalies in metrics"""
        anomalies = []
        
        for key, value in metrics.items():
            if key in self.baseline:
                mean = self.baseline[key]['mean']
                std = self.baseline[key]['std']
                
                # Check if value is outside 3 standard deviations
                if std > 0 and abs(value - mean) > 3 * std:
                    anomalies.append({
                        'metric': key,
                        'value': value,
                        'expected': mean,
                        'deviation': abs(value - mean) / std,
                        'timestamp': datetime.now().isoformat()
                    })
        
        return anomalies
    
    async def collect_metrics(self) -> Dict:
        """Collect metrics for anomaly detection"""
        return {
            'cpu': psutil.cpu_percent(interval=1),
            'memory': psutil.virtual_memory().percent,
            'disk_read': psutil.disk_io_counters().read_bytes if psutil.disk_io_counters() else 0,
            'disk_write': psutil.disk_io_counters().write_bytes if psutil.disk_io_counters() else 0,
            'network_sent': psutil.net_io_counters().bytes_sent if psutil.net_io_counters() else 0,
            'network_recv': psutil.net_io_counters().bytes_recv if psutil.net_io_counters() else 0,
            'processes': len(psutil.pids())
        }


async def main():
    """Main monitoring and alerting loop"""
    print("📊 Starting QENEX Monitoring & Alert System...")
    
    alert_system = AlertSystem()
    anomaly_detector = AnomalyDetector()
    
    # Start monitoring
    await alert_system.monitor()


if __name__ == "__main__":
    asyncio.run(main())