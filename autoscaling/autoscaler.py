#!/usr/bin/env python3
"""
QENEX Auto-Scaling System
High-performance load management with intelligent scaling decisions
"""

import asyncio
import json
import time
import psutil
import subprocess
import logging
import docker
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

@dataclass
class ScalingMetrics:
    """System metrics for scaling decisions"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: float
    request_rate: int
    response_time: float
    active_connections: int
    queue_depth: int

@dataclass  
class ScalingRule:
    """Auto-scaling rule configuration"""
    metric: str
    threshold_up: float
    threshold_down: float
    scale_up_count: int
    scale_down_count: int
    cooldown_seconds: int

class QenexAutoScaler:
    """Intelligent auto-scaling system for QENEX"""
    
    def __init__(self, config_path: str = "/opt/qenex-os/config/autoscaling.json"):
        self.config_path = config_path
        self.docker_client = docker.from_env()
        self.scaling_history = []
        self.last_scale_time = {}
        self.active_instances = {}
        self.metrics_history = []
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/opt/qenex-os/logs/autoscaling.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('QenexAutoScaler')
        
        # Load configuration
        self.load_config()
        
    def load_config(self):
        """Load scaling configuration"""
        default_config = {
            "enabled": True,
            "check_interval": 30,
            "min_instances": 1,
            "max_instances": 10,
            "scaling_rules": [
                {
                    "metric": "cpu_usage",
                    "threshold_up": 80.0,
                    "threshold_down": 30.0,
                    "scale_up_count": 2,
                    "scale_down_count": 1,
                    "cooldown_seconds": 300
                },
                {
                    "metric": "memory_usage", 
                    "threshold_up": 85.0,
                    "threshold_down": 40.0,
                    "scale_up_count": 1,
                    "scale_down_count": 1,
                    "cooldown_seconds": 180
                },
                {
                    "metric": "request_rate",
                    "threshold_up": 1000,
                    "threshold_down": 200,
                    "scale_up_count": 3,
                    "scale_down_count": 1,
                    "cooldown_seconds": 120
                }
            ],
            "services": {
                "qenex-api": {
                    "image": "qenex/api:latest",
                    "port": 8000,
                    "env": {"QENEX_MODE": "production"}
                },
                "qenex-worker": {
                    "image": "qenex/worker:latest", 
                    "env": {"WORKER_TYPE": "general"}
                },
                "qenex-pipeline": {
                    "image": "qenex/pipeline:latest",
                    "port": 8001
                }
            }
        }
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = default_config
                self.save_config()
        except Exception as e:
            self.logger.warning(f"Failed to load config: {e}, using defaults")
            self.config = default_config
            
        # Convert scaling rules to objects
        self.scaling_rules = [
            ScalingRule(**rule) for rule in self.config["scaling_rules"]
        ]
        
    def save_config(self):
        """Save current configuration"""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
            
    def collect_metrics(self) -> ScalingMetrics:
        """Collect system metrics for scaling decisions"""
        try:
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # Application metrics (simulated from logs/endpoints)
            request_rate = self.get_request_rate()
            response_time = self.get_avg_response_time()
            active_connections = self.get_active_connections()
            queue_depth = self.get_queue_depth()
            
            metrics = ScalingMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                network_io=network.bytes_sent + network.bytes_recv,
                request_rate=request_rate,
                response_time=response_time,
                active_connections=active_connections,
                queue_depth=queue_depth
            )
            
            # Store metrics history (keep last 100 measurements)
            self.metrics_history.append({
                'timestamp': time.time(),
                'metrics': metrics
            })
            if len(self.metrics_history) > 100:
                self.metrics_history.pop(0)
                
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return ScalingMetrics(0, 0, 0, 0, 0, 0, 0, 0)
            
    def get_request_rate(self) -> int:
        """Get current request rate from nginx/api logs"""
        try:
            # Parse recent access logs for request rate
            result = subprocess.run([
                'tail', '-n', '1000', '/opt/qenex-os/logs/access.log'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                recent_requests = len([l for l in lines if l and 
                                     time.time() - self.parse_log_time(l) < 60])
                return recent_requests
        except:
            pass
        return 0
        
    def get_avg_response_time(self) -> float:
        """Get average response time from application metrics"""
        try:
            # Check application metrics endpoint
            result = subprocess.run([
                'curl', '-s', 'https://abdulrahman305.github.io/qenex-docs
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
        except:
            pass
        return 0.5  # Default response time
        
    def get_active_connections(self) -> int:
        """Get number of active connections"""
        try:
            result = subprocess.run([
                'netstat', '-an', '|', 'grep', ':8000.*ESTABLISHED', '|', 'wc', '-l'
            ], shell=True, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return int(result.stdout.strip())
        except:
            pass
        return 0
        
    def get_queue_depth(self) -> int:
        """Get current processing queue depth"""
        try:
            # Check queue status from Redis/database
            result = subprocess.run([
                'redis-cli', 'LLEN', 'qenex:processing_queue'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return int(result.stdout.strip())
        except:
            pass
        return 0
        
    def parse_log_time(self, log_line: str) -> float:
        """Parse timestamp from log line"""
        try:
            # Basic log timestamp parsing
            return time.time() - 30  # Placeholder
        except:
            return 0
            
    def should_scale_up(self, metrics: ScalingMetrics, rule: ScalingRule) -> bool:
        """Determine if we should scale up based on rule"""
        metric_value = getattr(metrics, rule.metric, 0)
        
        # Check cooldown period
        last_scale = self.last_scale_time.get(rule.metric, 0)
        if time.time() - last_scale < rule.cooldown_seconds:
            return False
            
        # Check threshold
        if metric_value > rule.threshold_up:
            # Ensure we haven't reached max instances
            current_instances = self.get_current_instance_count()
            if current_instances < self.config["max_instances"]:
                return True
                
        return False
        
    def should_scale_down(self, metrics: ScalingMetrics, rule: ScalingRule) -> bool:
        """Determine if we should scale down based on rule"""
        metric_value = getattr(metrics, rule.metric, 0)
        
        # Check cooldown period
        last_scale = self.last_scale_time.get(rule.metric, 0)
        if time.time() - last_scale < rule.cooldown_seconds:
            return False
            
        # Check threshold
        if metric_value < rule.threshold_down:
            # Ensure we don't go below min instances
            current_instances = self.get_current_instance_count()
            if current_instances > self.config["min_instances"]:
                return True
                
        return False
        
    def get_current_instance_count(self) -> int:
        """Get current number of running instances"""
        try:
            containers = self.docker_client.containers.list(
                filters={"label": "qenex.service=true"}
            )
            return len(containers)
        except:
            return 1
            
    def scale_up(self, rule: ScalingRule):
        """Scale up instances"""
        try:
            current_count = self.get_current_instance_count()
            target_count = min(
                current_count + rule.scale_up_count,
                self.config["max_instances"]
            )
            
            self.logger.info(f"Scaling up from {current_count} to {target_count} instances")
            
            # Start new containers for each service
            for service_name, service_config in self.config["services"].items():
                for i in range(rule.scale_up_count):
                    self.start_service_instance(service_name, service_config, i)
                    
            self.last_scale_time[rule.metric] = time.time()
            self.scaling_history.append({
                'timestamp': time.time(),
                'action': 'scale_up',
                'rule': rule.metric,
                'from_count': current_count,
                'to_count': target_count
            })
            
        except Exception as e:
            self.logger.error(f"Error scaling up: {e}")
            
    def scale_down(self, rule: ScalingRule):
        """Scale down instances"""
        try:
            current_count = self.get_current_instance_count()
            target_count = max(
                current_count - rule.scale_down_count,
                self.config["min_instances"]
            )
            
            self.logger.info(f"Scaling down from {current_count} to {target_count} instances")
            
            # Stop excess containers
            containers = self.docker_client.containers.list(
                filters={"label": "qenex.service=true"}
            )
            
            containers_to_stop = containers[:rule.scale_down_count]
            for container in containers_to_stop:
                container.stop(timeout=30)
                container.remove()
                
            self.last_scale_time[rule.metric] = time.time()
            self.scaling_history.append({
                'timestamp': time.time(),
                'action': 'scale_down', 
                'rule': rule.metric,
                'from_count': current_count,
                'to_count': target_count
            })
            
        except Exception as e:
            self.logger.error(f"Error scaling down: {e}")
            
    def start_service_instance(self, service_name: str, service_config: Dict, instance_id: int):
        """Start a new service instance"""
        try:
            container_name = f"qenex-{service_name}-{instance_id}-{int(time.time())}"
            
            # Prepare container configuration
            container_config = {
                'name': container_name,
                'image': service_config['image'],
                'environment': service_config.get('env', {}),
                'labels': {
                    'qenex.service': 'true',
                    'qenex.service_name': service_name,
                    'qenex.instance_id': str(instance_id)
                },
                'network_mode': 'bridge',
                'restart_policy': {'Name': 'unless-stopped'},
                'detach': True
            }
            
            # Add port mapping if specified
            if 'port' in service_config:
                port = service_config['port'] + instance_id
                container_config['ports'] = {f"{service_config['port']}/tcp": port}
                
            # Start container
            container = self.docker_client.containers.run(**container_config)
            
            self.logger.info(f"Started {service_name} instance: {container.name}")
            
            # Register with load balancer
            self.register_with_load_balancer(service_name, container_name, 
                                           service_config.get('port'))
            
        except Exception as e:
            self.logger.error(f"Error starting {service_name} instance: {e}")
            
    def register_with_load_balancer(self, service_name: str, container_name: str, port: Optional[int]):
        """Register new instance with load balancer"""
        try:
            if port:
                # Update nginx upstream configuration
                nginx_config = f"""
upstream {service_name}_backend {{
    server 127.0.0.1:{port};
}}
"""
                
                config_path = f"/etc/nginx/conf.d/{service_name}_{container_name}.conf"
                with open(config_path, 'w') as f:
                    f.write(nginx_config)
                    
                # Reload nginx
                subprocess.run(['nginx', '-s', 'reload'], timeout=10)
                
        except Exception as e:
            self.logger.error(f"Error registering with load balancer: {e}")
            
    def cleanup_stopped_instances(self):
        """Clean up stopped containers and configurations"""
        try:
            # Remove stopped containers
            stopped_containers = self.docker_client.containers.list(
                all=True, 
                filters={"status": "exited", "label": "qenex.service=true"}
            )
            
            for container in stopped_containers:
                container.remove()
                
                # Remove nginx config if exists
                config_path = f"/etc/nginx/conf.d/*{container.name}*.conf"
                subprocess.run(f"rm -f {config_path}", shell=True)
                
            # Reload nginx after cleanup
            subprocess.run(['nginx', '-s', 'reload'], timeout=10)
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            
    def get_scaling_status(self) -> Dict:
        """Get current scaling status and metrics"""
        metrics = self.collect_metrics()
        current_instances = self.get_current_instance_count()
        
        return {
            'enabled': self.config['enabled'],
            'current_instances': current_instances,
            'min_instances': self.config['min_instances'],
            'max_instances': self.config['max_instances'],
            'current_metrics': {
                'cpu_usage': metrics.cpu_usage,
                'memory_usage': metrics.memory_usage,
                'request_rate': metrics.request_rate,
                'response_time': metrics.response_time,
                'active_connections': metrics.active_connections,
                'queue_depth': metrics.queue_depth
            },
            'scaling_history': self.scaling_history[-10:],  # Last 10 events
            'last_check': time.time()
        }
        
    async def monitoring_loop(self):
        """Main monitoring and scaling loop"""
        self.logger.info("Starting auto-scaling monitoring loop")
        
        while self.config.get('enabled', True):
            try:
                # Collect current metrics
                metrics = self.collect_metrics()
                
                # Check each scaling rule
                for rule in self.scaling_rules:
                    if self.should_scale_up(metrics, rule):
                        self.scale_up(rule)
                    elif self.should_scale_down(metrics, rule):
                        self.scale_down(rule)
                
                # Periodic cleanup
                if len(self.scaling_history) % 10 == 0:
                    self.cleanup_stopped_instances()
                
                # Save status
                status = self.get_scaling_status()
                with open('/opt/qenex-os/data/autoscaling_status.json', 'w') as f:
                    json.dump(status, f, indent=2)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                
            await asyncio.sleep(self.config.get('check_interval', 30))
            
    async def start(self):
        """Start the auto-scaling system"""
        self.logger.info("Starting QENEX Auto-Scaling System")
        
        # Ensure data directory exists
        Path('/opt/qenex-os/data').mkdir(parents=True, exist_ok=True)
        
        # Start monitoring loop
        await self.monitoring_loop()
        
    def stop(self):
        """Stop the auto-scaling system"""
        self.logger.info("Stopping QENEX Auto-Scaling System")
        self.config['enabled'] = False

async def main():
    """Main entry point"""
    autoscaler = QenexAutoScaler()
    
    try:
        await autoscaler.start()
    except KeyboardInterrupt:
        autoscaler.stop()
        print("\nAuto-scaler stopped")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())