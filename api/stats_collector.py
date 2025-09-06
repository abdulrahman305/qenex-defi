#!/usr/bin/env python3
"""
QENEX Real-time Stats Collector
Collects actual system metrics for dashboard display
"""

import json
import os
import psutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

class QenexStatsCollector:
    def __init__(self):
        self.log_dir = Path("/opt/qenex-os/logs")
        self.stats_file = Path("/opt/qenex-os/data/stats.json")
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        
    def collect_system_metrics(self):
        """Collect real system metrics"""
        metrics = {}
        
        # System uptime
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            metrics['uptime_hours'] = round(uptime_seconds / 3600, 1)
        
        # CPU and memory
        metrics['cpu_percent'] = psutil.cpu_percent(interval=1)
        metrics['memory_usage'] = psutil.virtual_memory().percent
        metrics['load_average'] = os.getloadavg()[0]
        
        # Disk usage
        disk = psutil.disk_usage('/')
        metrics['disk_usage'] = disk.percent
        
        # Network connections
        metrics['network_connections'] = len(psutil.net_connections())
        
        # QENEX specific processes
        qenex_processes = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info.get('cmdline', []))
                if any(keyword in cmdline.lower() for keyword in ['qenex', 'cicd', 'gitops', 'ai_engine']):
                    qenex_processes += 1
            except:
                pass
        metrics['qenex_processes'] = qenex_processes
        
        return metrics
    
    def collect_cicd_metrics(self):
        """Collect CI/CD pipeline metrics from logs"""
        metrics = {
            'pipelines': 0,
            'success_rate': 0,
            'deployments': 0,
            'builds_today': 0,
            'tests_passed': 0
        }
        
        # Check multiple log sources
        log_files = [
            self.log_dir / "cicd.log",
            self.log_dir / "pipeline.log",
            self.log_dir / "gitops.log"
        ]
        
        for log_file in log_files:
            if log_file.exists():
                try:
                    with open(log_file, 'r') as f:
                        content = f.read()
                        
                        # Count pipeline runs
                        metrics['pipelines'] += content.count('[Pipeline Started]')
                        metrics['pipelines'] += content.count('Pipeline execution started')
                        
                        # Count successful completions
                        success_count = content.count('[Pipeline Success]')
                        success_count += content.count('Pipeline completed successfully')
                        
                        # Count total completions
                        total_count = content.count('[Pipeline Completed]')
                        total_count += content.count('Pipeline execution completed')
                        
                        if total_count > 0:
                            metrics['success_rate'] = round((success_count / total_count) * 100, 1)
                        
                        # Count deployments
                        metrics['deployments'] += content.count('[Deployment Success]')
                        metrics['deployments'] += content.count('Deployment completed')
                        
                        # Count today's builds
                        today = datetime.now().strftime('%Y-%m-%d')
                        for line in content.split('\n'):
                            if today in line and 'build' in line.lower():
                                metrics['builds_today'] += 1
                        
                        # Count test passes
                        metrics['tests_passed'] += content.count('All tests passed')
                        metrics['tests_passed'] += content.count('[Tests Passed]')
                except Exception as e:
                    print(f"Error reading {log_file}: {e}")
        
        # If no log data, check running processes
        if metrics['pipelines'] == 0:
            try:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'pipeline' in line.lower() or 'cicd' in line.lower():
                        metrics['pipelines'] += 1
            except:
                pass
        
        return metrics
    
    def collect_gitops_metrics(self):
        """Collect GitOps metrics"""
        metrics = {
            'repos_monitored': 0,
            'sync_status': 'Unknown',
            'last_sync': 'Never',
            'pr_count': 0
        }
        
        # Check GitOps configuration
        gitops_config = Path("/opt/qenex-os/config/gitops.yaml")
        if gitops_config.exists():
            metrics['repos_monitored'] = 1  # Count configured repos
            
        # Check for GitHub CLI
        try:
            result = subprocess.run(['gh', 'pr', 'list', '--state', 'open'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                metrics['pr_count'] = len(result.stdout.strip().split('\n'))
                metrics['sync_status'] = 'Connected'
        except:
            pass
        
        # Check last sync time
        sync_marker = Path("/opt/qenex-os/data/last_sync")
        if sync_marker.exists():
            mtime = sync_marker.stat().st_mtime
            metrics['last_sync'] = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        return metrics
    
    def save_stats(self):
        """Collect all stats and save to JSON file"""
        stats = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            **self.collect_system_metrics(),
            **self.collect_cicd_metrics(),
            **self.collect_gitops_metrics()
        }
        
        # Save to file for API to read
        with open(self.stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        return stats
    
    def run_continuous(self, interval=5):
        """Run continuous stats collection"""
        print(f"Starting QENEX stats collector (interval: {interval}s)")
        while True:
            try:
                stats = self.save_stats()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Stats updated - "
                      f"Processes: {stats['qenex_processes']}, "
                      f"Pipelines: {stats['pipelines']}, "
                      f"CPU: {stats['cpu_percent']}%")
            except Exception as e:
                print(f"Error collecting stats: {e}")
            
            time.sleep(interval)

if __name__ == "__main__":
    collector = QenexStatsCollector()
    collector.run_continuous()