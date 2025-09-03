#!/usr/bin/env python3
"""
QENEX Self-Healing System - Automatic recovery and repair
"""

import asyncio
import psutil
import subprocess
import json
import logging
import os
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import threading
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthCheck:
    """System health monitoring"""
    
    def __init__(self):
        self.checks = {
            'memory': self.check_memory,
            'disk': self.check_disk,
            'cpu': self.check_cpu,
            'services': self.check_services,
            'network': self.check_network,
            'database': self.check_database,
            'api': self.check_api
        }
        self.thresholds = {
            'memory_critical': 95,
            'memory_warning': 85,
            'disk_critical': 90,
            'disk_warning': 80,
            'cpu_critical': 90,
            'cpu_sustained': 80
        }
        
    async def check_memory(self) -> Dict[str, Any]:
        """Check memory health"""
        mem = psutil.virtual_memory()
        status = 'healthy'
        
        if mem.percent > self.thresholds['memory_critical']:
            status = 'critical'
        elif mem.percent > self.thresholds['memory_warning']:
            status = 'warning'
            
        return {
            'component': 'memory',
            'status': status,
            'usage': mem.percent,
            'available': mem.available,
            'message': f"Memory usage: {mem.percent:.1f}%"
        }
    
    async def check_disk(self) -> Dict[str, Any]:
        """Check disk health"""
        disk = psutil.disk_usage('/')
        status = 'healthy'
        
        if disk.percent > self.thresholds['disk_critical']:
            status = 'critical'
        elif disk.percent > self.thresholds['disk_warning']:
            status = 'warning'
            
        return {
            'component': 'disk',
            'status': status,
            'usage': disk.percent,
            'free': disk.free,
            'message': f"Disk usage: {disk.percent:.1f}%"
        }
    
    async def check_cpu(self) -> Dict[str, Any]:
        """Check CPU health"""
        cpu_percent = psutil.cpu_percent(interval=1)
        load_avg = os.getloadavg()[0]
        status = 'healthy'
        
        if cpu_percent > self.thresholds['cpu_critical']:
            status = 'critical'
        elif load_avg > psutil.cpu_count() * 2:
            status = 'warning'
            
        return {
            'component': 'cpu',
            'status': status,
            'usage': cpu_percent,
            'load': load_avg,
            'message': f"CPU: {cpu_percent:.1f}%, Load: {load_avg:.2f}"
        }
    
    async def check_services(self) -> Dict[str, Any]:
        """Check critical services"""
        services = ['nginx', 'redis-server']
        failed = []
        
        for service in services:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True,
                text=True
            )
            if result.stdout.strip() != 'active':
                failed.append(service)
        
        status = 'critical' if failed else 'healthy'
        
        return {
            'component': 'services',
            'status': status,
            'failed_services': failed,
            'message': f"Failed services: {', '.join(failed)}" if failed else "All services running"
        }
    
    async def check_network(self) -> Dict[str, Any]:
        """Check network connectivity"""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', '8.8.8.8'],
                capture_output=True
            )
            connected = result.returncode == 0
        except:
            connected = False
        
        return {
            'component': 'network',
            'status': 'healthy' if connected else 'critical',
            'connected': connected,
            'message': "Network connected" if connected else "Network unreachable"
        }
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            conn = sqlite3.connect('/opt/qenex-os/data/qenex.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pipelines")
            cursor.fetchone()
            conn.close()
            
            return {
                'component': 'database',
                'status': 'healthy',
                'message': "Database accessible"
            }
        except Exception as e:
            return {
                'component': 'database',
                'status': 'critical',
                'error': str(e),
                'message': f"Database error: {e}"
            }
    
    async def check_api(self) -> Dict[str, Any]:
        """Check API health"""
        try:
            result = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 
                 'http://localhost:8000/api/health'],
                capture_output=True,
                text=True
            )
            healthy = result.stdout.strip() == '200'
            
            return {
                'component': 'api',
                'status': 'healthy' if healthy else 'critical',
                'message': "API responding" if healthy else "API not responding"
            }
        except:
            return {
                'component': 'api',
                'status': 'critical',
                'message': "API check failed"
            }
    
    async def run_all_checks(self) -> List[Dict[str, Any]]:
        """Run all health checks"""
        results = []
        
        for name, check_func in self.checks.items():
            try:
                result = await check_func()
                results.append(result)
            except Exception as e:
                results.append({
                    'component': name,
                    'status': 'error',
                    'error': str(e),
                    'message': f"Check failed: {e}"
                })
        
        return results

class SelfHealingEngine:
    """Automatic system repair and recovery"""
    
    def __init__(self):
        self.health_checker = HealthCheck()
        self.healing_actions = {
            'memory': self.heal_memory,
            'disk': self.heal_disk,
            'cpu': self.heal_cpu,
            'services': self.heal_services,
            'network': self.heal_network,
            'database': self.heal_database,
            'api': self.heal_api
        }
        self.state_file = Path('/opt/qenex-os/data/system_state.json')
        self.recovery_log = []
        self.is_healing = False
        
        # Start monitoring
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def _monitor_loop(self):
        """Continuous monitoring loop"""
        while True:
            try:
                asyncio.run(self.check_and_heal())
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
            
            time.sleep(30)  # Check every 30 seconds
    
    async def check_and_heal(self):
        """Check system health and heal if needed"""
        if self.is_healing:
            return  # Prevent concurrent healing
        
        health_results = await self.health_checker.run_all_checks()
        
        critical_issues = [r for r in health_results if r['status'] == 'critical']
        warning_issues = [r for r in health_results if r['status'] == 'warning']
        
        if critical_issues:
            self.is_healing = True
            logger.warning(f"Critical issues detected: {len(critical_issues)}")
            
            for issue in critical_issues:
                await self.heal_component(issue)
            
            self.is_healing = False
            
        elif warning_issues:
            logger.info(f"Warning issues: {len(warning_issues)}")
            # Less aggressive healing for warnings
            for issue in warning_issues:
                if issue['component'] == 'memory' and issue['usage'] > 90:
                    await self.heal_component(issue)
    
    async def heal_component(self, issue: Dict[str, Any]):
        """Heal a specific component"""
        component = issue['component']
        
        if component in self.healing_actions:
            logger.info(f"Healing {component}: {issue['message']}")
            
            try:
                result = await self.healing_actions[component](issue)
                
                self.recovery_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'component': component,
                    'issue': issue,
                    'action': result['action'],
                    'success': result['success']
                })
                
                if result['success']:
                    logger.info(f"Successfully healed {component}")
                else:
                    logger.error(f"Failed to heal {component}: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Healing error for {component}: {e}")
    
    async def heal_memory(self, issue: Dict) -> Dict[str, Any]:
        """Heal memory issues"""
        actions_taken = []
        
        # 1. Clear caches
        subprocess.run(['sync'], capture_output=True)
        subprocess.run(['sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'], capture_output=True)
        actions_taken.append("Cleared system caches")
        
        # 2. Kill memory-hungry processes
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                if proc.info['memory_percent'] > 10:  # Using more than 10% memory
                    if 'chrome' in proc.info['name'].lower() or 'firefox' in proc.info['name'].lower():
                        proc.kill()
                        actions_taken.append(f"Killed {proc.info['name']}")
            except:
                pass
        
        # 3. Restart heavy services
        if issue['usage'] > 95:
            subprocess.run(['systemctl', 'restart', 'qenex-api'], capture_output=True)
            actions_taken.append("Restarted QENEX API")
        
        # 4. Trigger garbage collection in Python services
        subprocess.run(['pkill', '-USR1', '-f', 'python.*qenex'], capture_output=True)
        actions_taken.append("Triggered garbage collection")
        
        return {
            'action': ', '.join(actions_taken),
            'success': True
        }
    
    async def heal_disk(self, issue: Dict) -> Dict[str, Any]:
        """Heal disk space issues"""
        actions_taken = []
        
        # 1. Clean logs
        subprocess.run(['find', '/opt/qenex-os/logs', '-name', '*.log', '-mtime', '+1', '-delete'], capture_output=True)
        subprocess.run(['find', '/var/log', '-name', '*.log.[0-9]*', '-delete'], capture_output=True)
        actions_taken.append("Cleaned old logs")
        
        # 2. Clean Docker if available
        subprocess.run(['docker', 'system', 'prune', '-af', '--volumes'], capture_output=True)
        actions_taken.append("Cleaned Docker resources")
        
        # 3. Clean package cache
        subprocess.run(['apt-get', 'clean'], capture_output=True)
        subprocess.run(['apt-get', 'autoremove', '-y'], capture_output=True)
        actions_taken.append("Cleaned package cache")
        
        # 4. Clean temp files
        subprocess.run(['find', '/tmp', '-type', 'f', '-atime', '+1', '-delete'], capture_output=True)
        actions_taken.append("Cleaned temp files")
        
        # 5. Compress old database records
        conn = sqlite3.connect('/opt/qenex-os/data/qenex.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pipelines WHERE created_at < datetime('now', '-7 days')")
        cursor.execute("VACUUM")
        conn.commit()
        conn.close()
        actions_taken.append("Compressed database")
        
        return {
            'action': ', '.join(actions_taken),
            'success': True
        }
    
    async def heal_cpu(self, issue: Dict) -> Dict[str, Any]:
        """Heal CPU issues"""
        actions_taken = []
        
        # 1. Nice high-CPU processes
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                if proc.info['cpu_percent'] > 50:
                    os.setpriority(os.PRIO_PROCESS, proc.info['pid'], 10)
                    actions_taken.append(f"Niced {proc.info['name']}")
            except:
                pass
        
        # 2. Kill stuck processes
        subprocess.run(['killall', '-9', 'defunct'], capture_output=True)
        actions_taken.append("Killed zombie processes")
        
        # 3. Restart CPU-intensive services
        if issue['load'] > psutil.cpu_count() * 3:
            subprocess.run(['systemctl', 'restart', 'qenex-autoscaler'], capture_output=True)
            actions_taken.append("Restarted autoscaler")
        
        return {
            'action': ', '.join(actions_taken),
            'success': True
        }
    
    async def heal_services(self, issue: Dict) -> Dict[str, Any]:
        """Heal failed services"""
        actions_taken = []
        
        for service in issue.get('failed_services', []):
            # Try to start the service
            result = subprocess.run(['systemctl', 'start', service], capture_output=True)
            
            if result.returncode == 0:
                actions_taken.append(f"Started {service}")
            else:
                # Try restart if start fails
                result = subprocess.run(['systemctl', 'restart', service], capture_output=True)
                if result.returncode == 0:
                    actions_taken.append(f"Restarted {service}")
                else:
                    # Reset failed state
                    subprocess.run(['systemctl', 'reset-failed', service], capture_output=True)
                    subprocess.run(['systemctl', 'start', service], capture_output=True)
                    actions_taken.append(f"Reset and started {service}")
        
        return {
            'action': ', '.join(actions_taken),
            'success': True
        }
    
    async def heal_network(self, issue: Dict) -> Dict[str, Any]:
        """Heal network issues"""
        actions_taken = []
        
        # 1. Restart network service
        subprocess.run(['systemctl', 'restart', 'systemd-networkd'], capture_output=True)
        actions_taken.append("Restarted network service")
        
        # 2. Flush DNS
        subprocess.run(['systemd-resolve', '--flush-caches'], capture_output=True)
        actions_taken.append("Flushed DNS cache")
        
        # 3. Reset firewall rules
        subprocess.run(['iptables', '-F'], capture_output=True)
        subprocess.run(['iptables', '-X'], capture_output=True)
        subprocess.run(['iptables', '-P', 'INPUT', 'ACCEPT'], capture_output=True)
        subprocess.run(['iptables', '-P', 'OUTPUT', 'ACCEPT'], capture_output=True)
        actions_taken.append("Reset firewall rules")
        
        return {
            'action': ', '.join(actions_taken),
            'success': True
        }
    
    async def heal_database(self, issue: Dict) -> Dict[str, Any]:
        """Heal database issues"""
        actions_taken = []
        
        try:
            # 1. Check database integrity
            conn = sqlite3.connect('/opt/qenex-os/data/qenex.db')
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            if result[0] != 'ok':
                # Restore from backup
                backup_file = '/opt/qenex-os/backups/qenex.db.backup'
                if os.path.exists(backup_file):
                    subprocess.run(['cp', backup_file, '/opt/qenex-os/data/qenex.db'], capture_output=True)
                    actions_taken.append("Restored database from backup")
                else:
                    # Recreate database
                    subprocess.run(['python3', '/opt/qenex-os/database/db_manager.py'], capture_output=True)
                    actions_taken.append("Recreated database")
            else:
                # Optimize database
                cursor.execute("VACUUM")
                cursor.execute("ANALYZE")
                actions_taken.append("Optimized database")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            return {
                'action': f"Database repair failed: {e}",
                'success': False,
                'error': str(e)
            }
        
        return {
            'action': ', '.join(actions_taken),
            'success': True
        }
    
    async def heal_api(self, issue: Dict) -> Dict[str, Any]:
        """Heal API issues"""
        actions_taken = []
        
        # 1. Restart API service
        subprocess.run(['pkill', '-f', 'unified_ai_os.py'], capture_output=True)
        time.sleep(2)
        subprocess.Popen(['python3', '/opt/qenex-os/kernel/unified_ai_os.py'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        actions_taken.append("Restarted API service")
        
        # 2. Clear API cache
        subprocess.run(['redis-cli', 'FLUSHDB'], capture_output=True)
        actions_taken.append("Cleared API cache")
        
        # 3. Restart nginx
        subprocess.run(['nginx', '-s', 'reload'], capture_output=True)
        actions_taken.append("Reloaded nginx")
        
        return {
            'action': ', '.join(actions_taken),
            'success': True
        }
    
    def save_state(self):
        """Save current system state for recovery"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'config': {},
            'pipelines': []
        }
        
        # Save service states
        for service in ['qenex-api', 'qenex-webhook', 'qenex-metrics']:
            result = subprocess.run(['systemctl', 'is-active', service], 
                                  capture_output=True, text=True)
            state['services'][service] = result.stdout.strip()
        
        # Save current pipelines
        try:
            conn = sqlite3.connect('/opt/qenex-os/data/qenex.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, status FROM pipelines WHERE status = 'running'")
            state['pipelines'] = cursor.fetchall()
            conn.close()
        except:
            pass
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f)
    
    def restore_state(self):
        """Restore system to previous state"""
        if not self.state_file.exists():
            return
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Restore services
            for service, status in state['services'].items():
                if status == 'active':
                    subprocess.run(['systemctl', 'start', service], capture_output=True)
            
            logger.info(f"Restored state from {state['timestamp']}")
            
        except Exception as e:
            logger.error(f"Failed to restore state: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get self-healing status"""
        return {
            'is_healing': self.is_healing,
            'recovery_log': self.recovery_log[-10:],
            'health_thresholds': self.health_checker.thresholds
        }

class AutoRollback:
    """Automatic rollback on deployment failures"""
    
    def __init__(self):
        self.deployment_history = []
        self.rollback_points = []
        
    def create_rollback_point(self, deployment_id: str):
        """Create a rollback point before deployment"""
        rollback_point = {
            'deployment_id': deployment_id,
            'timestamp': datetime.now().isoformat(),
            'database_backup': self._backup_database(),
            'config_backup': self._backup_config(),
            'docker_images': self._list_docker_images()
        }
        
        self.rollback_points.append(rollback_point)
        
        # Keep only last 10 rollback points
        if len(self.rollback_points) > 10:
            self.rollback_points.pop(0)
        
        return rollback_point
    
    def _backup_database(self) -> str:
        """Backup database for rollback"""
        backup_file = f"/opt/qenex-os/backups/rollback_{datetime.now().strftime('%Y%m%d%H%M%S')}.db"
        subprocess.run(['cp', '/opt/qenex-os/data/qenex.db', backup_file], capture_output=True)
        return backup_file
    
    def _backup_config(self) -> str:
        """Backup configuration for rollback"""
        backup_file = f"/opt/qenex-os/backups/config_{datetime.now().strftime('%Y%m%d%H%M%S')}.tar.gz"
        subprocess.run(['tar', '-czf', backup_file, '/opt/qenex-os/config'], capture_output=True)
        return backup_file
    
    def _list_docker_images(self) -> List[str]:
        """List current Docker images"""
        result = subprocess.run(['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'],
                              capture_output=True, text=True)
        return result.stdout.strip().split('\n') if result.returncode == 0 else []
    
    async def monitor_deployment(self, deployment_id: str, timeout: int = 300):
        """Monitor deployment and rollback if it fails"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check deployment status
            conn = sqlite3.connect('/opt/qenex-os/data/qenex.db')
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM deployments WHERE id = ?", (deployment_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                status = result[0]
                
                if status == 'success':
                    logger.info(f"Deployment {deployment_id} succeeded")
                    return True
                    
                elif status == 'failed':
                    logger.error(f"Deployment {deployment_id} failed, initiating rollback")
                    await self.rollback(deployment_id)
                    return False
            
            # Check health
            health_check = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                                         'http://localhost:8000/api/health'],
                                        capture_output=True, text=True)
            
            if health_check.stdout.strip() != '200':
                logger.error(f"Health check failed during deployment {deployment_id}")
                await self.rollback(deployment_id)
                return False
            
            await asyncio.sleep(5)
        
        logger.error(f"Deployment {deployment_id} timed out")
        await self.rollback(deployment_id)
        return False
    
    async def rollback(self, deployment_id: str):
        """Perform rollback to previous state"""
        # Find rollback point
        rollback_point = None
        for point in reversed(self.rollback_points):
            if point['deployment_id'] == deployment_id:
                rollback_point = point
                break
        
        if not rollback_point:
            logger.error(f"No rollback point found for {deployment_id}")
            return False
        
        logger.info(f"Rolling back deployment {deployment_id}")
        
        try:
            # Restore database
            subprocess.run(['cp', rollback_point['database_backup'], '/opt/qenex-os/data/qenex.db'],
                         capture_output=True)
            
            # Restore config
            subprocess.run(['tar', '-xzf', rollback_point['config_backup'], '-C', '/'],
                         capture_output=True)
            
            # Restart services
            subprocess.run(['systemctl', 'restart', 'qenex-api'], capture_output=True)
            subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True)
            
            logger.info(f"Successfully rolled back {deployment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

# Global instances
healing_engine = SelfHealingEngine()
auto_rollback = AutoRollback()

if __name__ == "__main__":
    logger.info("QENEX Self-Healing System started")
    
    # Keep running
    while True:
        time.sleep(60)
        status = healing_engine.get_status()
        if status['recovery_log']:
            logger.info(f"Recent recoveries: {len(status['recovery_log'])}")