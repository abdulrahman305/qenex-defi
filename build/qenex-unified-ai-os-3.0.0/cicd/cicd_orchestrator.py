#!/usr/bin/env python3
"""
QENEX CI/CD Orchestrator
Unified orchestrator that manages all CI/CD components and provides a centralized interface
Version: 1.0.0
"""

import os
import sys
import json
import asyncio
import logging
import threading
import time
import signal
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import subprocess
import tempfile

# Import QENEX components
try:
    from autonomous_cicd import AutonomousCICD, Pipeline, PipelineStatus
    from distributed_executor import DistributedExecutor, ExecutionTask, WorkerNode, TaskStatus
    from secret_manager import SecretManager, SecretType, SecretScope
    from cache_manager import CacheManager, CacheType
    from api_server import QENEXAPIServer
    from dashboard_server import DashboardServer
    from webhook_server import WebhookServer
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    COMPONENTS_AVAILABLE = False
    print(f"Warning: Some components not available: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/opt/qenex-os/cicd/logs/orchestrator.log')
    ]
)
logger = logging.getLogger('QENEX-Orchestrator')

class ServiceStatus(Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class ServiceInfo:
    name: str
    status: ServiceStatus
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    error_message: Optional[str] = None
    restart_count: int = 0
    health_check_url: Optional[str] = None

class QENEXOrchestrator:
    """Main orchestrator for QENEX CI/CD system"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "/opt/qenex-os/cicd/orchestrator_config.json"
        self.config = self._load_config()
        
        # Service instances
        self.services = {}
        self.service_threads = {}
        self.service_processes = {}
        
        # Core components
        self.cicd_engine = None
        self.distributed_executor = None
        self.secret_manager = None
        self.cache_manager = None
        self.api_server = None
        self.dashboard_server = None
        self.webhook_server = None
        
        # Orchestrator state
        self.running = False
        self.start_time = None
        self.shutdown_handlers = []
        
        # Initialize services info
        self._init_service_info()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Create required directories
        self._create_directories()
        
        logger.info("QENEX Orchestrator initialized")
    
    def _load_config(self) -> Dict:
        """Load orchestrator configuration"""
        default_config = {
            "services": {
                "cicd_engine": {
                    "enabled": True,
                    "auto_start": True,
                    "restart_on_failure": True,
                    "max_restarts": 3,
                    "health_check_interval": 30
                },
                "distributed_executor": {
                    "enabled": True,
                    "auto_start": True,
                    "restart_on_failure": True,
                    "max_restarts": 3,
                    "config": {
                        "max_workers": 10,
                        "redis_url": None
                    }
                },
                "secret_manager": {
                    "enabled": True,
                    "auto_start": True,
                    "restart_on_failure": True,
                    "max_restarts": 3
                },
                "cache_manager": {
                    "enabled": True,
                    "auto_start": True,
                    "restart_on_failure": True,
                    "max_restarts": 3,
                    "config": {
                        "max_cache_size_gb": 10,
                        "default_ttl_hours": 24,
                        "compression": "gzip"
                    }
                },
                "api_server": {
                    "enabled": True,
                    "auto_start": True,
                    "restart_on_failure": True,
                    "max_restarts": 3,
                    "host": "0.0.0.0",
                    "port": 8000,
                    "config": {
                        "jwt_secret": "qenex-secret-key",
                        "admin_password": "admin123"
                    }
                },
                "dashboard_server": {
                    "enabled": True,
                    "auto_start": True,
                    "restart_on_failure": True,
                    "max_restarts": 3,
                    "host": "0.0.0.0",
                    "port": 8080
                },
                "webhook_server": {
                    "enabled": True,
                    "auto_start": True,
                    "restart_on_failure": True,
                    "max_restarts": 3,
                    "host": "0.0.0.0",
                    "port": 9000
                }
            },
            "monitoring": {
                "health_check_interval": 30,
                "metrics_collection_interval": 60,
                "log_retention_days": 30,
                "enable_prometheus_metrics": False
            },
            "security": {
                "enable_tls": False,
                "cert_file": None,
                "key_file": None,
                "api_rate_limit": "100/minute"
            },
            "integration": {
                "git_providers": {
                    "github": {
                        "enabled": True,
                        "webhook_secret": None
                    },
                    "gitlab": {
                        "enabled": True,
                        "webhook_secret": None
                    }
                },
                "notification": {
                    "slack_webhook": None,
                    "email_smtp": None
                }
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path) as f:
                    user_config = json.load(f)
                    # Merge with default config
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
        
        return default_config
    
    def _init_service_info(self):
        """Initialize service information"""
        for service_name in self.config["services"].keys():
            self.services[service_name] = ServiceInfo(
                name=service_name,
                status=ServiceStatus.STOPPED
            )
    
    def _create_directories(self):
        """Create required directories"""
        directories = [
            "/opt/qenex-os/cicd",
            "/opt/qenex-os/cicd/logs",
            "/opt/qenex-os/cicd/cache",
            "/opt/qenex-os/cicd/artifacts",
            "/opt/qenex-os/cicd/pipelines",
            "/opt/qenex-os/cicd/workspace",
            "/opt/qenex-os/cicd/secrets"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def start(self):
        """Start the orchestrator and all enabled services"""
        if self.running:
            logger.warning("Orchestrator is already running")
            return
        
        logger.info("Starting QENEX CI/CD Orchestrator")
        self.running = True
        self.start_time = datetime.now()
        
        # Start core services first
        self._start_core_services()
        
        # Start web services
        self._start_web_services()
        
        # Start monitoring and health checks
        self._start_monitoring()
        
        logger.info("All services started successfully")
        
        # Keep orchestrator running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            self.stop()
    
    def stop(self):
        """Stop all services gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping QENEX CI/CD Orchestrator")
        self.running = False
        
        # Execute shutdown handlers
        for handler in self.shutdown_handlers:
            try:
                handler()
            except Exception as e:
                logger.error(f"Error in shutdown handler: {e}")
        
        # Stop services in reverse order
        service_order = list(self.config["services"].keys())
        for service_name in reversed(service_order):
            self._stop_service(service_name)
        
        logger.info("Orchestrator stopped")
    
    def _start_core_services(self):
        """Start core CI/CD services"""
        if COMPONENTS_AVAILABLE:
            # Start Secret Manager
            if self.config["services"]["secret_manager"]["enabled"]:
                self._start_secret_manager()
            
            # Start Cache Manager
            if self.config["services"]["cache_manager"]["enabled"]:
                self._start_cache_manager()
            
            # Start Distributed Executor
            if self.config["services"]["distributed_executor"]["enabled"]:
                self._start_distributed_executor()
            
            # Start CI/CD Engine
            if self.config["services"]["cicd_engine"]["enabled"]:
                self._start_cicd_engine()
        else:
            logger.warning("Core components not available, running in limited mode")
    
    def _start_web_services(self):
        """Start web services"""
        if COMPONENTS_AVAILABLE:
            # Start API Server
            if self.config["services"]["api_server"]["enabled"]:
                self._start_api_server()
            
            # Start Dashboard Server
            if self.config["services"]["dashboard_server"]["enabled"]:
                self._start_dashboard_server()
            
            # Start Webhook Server
            if self.config["services"]["webhook_server"]["enabled"]:
                self._start_webhook_server()
    
    def _start_secret_manager(self):
        """Start Secret Manager service"""
        try:
            self.services["secret_manager"].status = ServiceStatus.STARTING
            self.secret_manager = SecretManager()
            self.services["secret_manager"].status = ServiceStatus.RUNNING
            self.services["secret_manager"].start_time = datetime.now()
            logger.info("Secret Manager started")
        except Exception as e:
            self._handle_service_error("secret_manager", str(e))
    
    def _start_cache_manager(self):
        """Start Cache Manager service"""
        try:
            self.services["cache_manager"].status = ServiceStatus.STARTING
            cache_config = self.config["services"]["cache_manager"].get("config", {})
            self.cache_manager = CacheManager(cache_config)
            self.cache_manager.start()
            self.services["cache_manager"].status = ServiceStatus.RUNNING
            self.services["cache_manager"].start_time = datetime.now()
            logger.info("Cache Manager started")
        except Exception as e:
            self._handle_service_error("cache_manager", str(e))
    
    def _start_distributed_executor(self):
        """Start Distributed Executor service"""
        try:
            self.services["distributed_executor"].status = ServiceStatus.STARTING
            executor_config = self.config["services"]["distributed_executor"].get("config", {})
            self.distributed_executor = DistributedExecutor(executor_config)
            self.distributed_executor.start()
            self.services["distributed_executor"].status = ServiceStatus.RUNNING
            self.services["distributed_executor"].start_time = datetime.now()
            logger.info("Distributed Executor started")
        except Exception as e:
            self._handle_service_error("distributed_executor", str(e))
    
    def _start_cicd_engine(self):
        """Start CI/CD Engine service"""
        try:
            self.services["cicd_engine"].status = ServiceStatus.STARTING
            self.cicd_engine = AutonomousCICD()
            
            # Inject dependencies
            if self.secret_manager:
                self.cicd_engine.set_secret_manager(self.secret_manager)
            if self.cache_manager:
                self.cicd_engine.set_cache_manager(self.cache_manager)
            if self.distributed_executor:
                self.cicd_engine.set_executor(self.distributed_executor)
            
            self.cicd_engine.start()
            self.services["cicd_engine"].status = ServiceStatus.RUNNING
            self.services["cicd_engine"].start_time = datetime.now()
            logger.info("CI/CD Engine started")
        except Exception as e:
            self._handle_service_error("cicd_engine", str(e))
    
    def _start_api_server(self):
        """Start API Server service"""
        try:
            self.services["api_server"].status = ServiceStatus.STARTING
            
            api_config = self.config["services"]["api_server"].get("config", {})
            self.api_server = QENEXAPIServer(api_config)
            
            # Inject dependencies
            if hasattr(self.api_server, 'cicd'):
                self.api_server.cicd = self.cicd_engine
            if hasattr(self.api_server, 'executor'):
                self.api_server.executor = self.distributed_executor
            if hasattr(self.api_server, 'secret_manager'):
                self.api_server.secret_manager = self.secret_manager
            if hasattr(self.api_server, 'cache_manager'):
                self.api_server.cache_manager = self.cache_manager
            
            # Start API server in a separate thread
            api_thread = threading.Thread(
                target=self._run_api_server,
                daemon=True
            )
            api_thread.start()
            self.service_threads["api_server"] = api_thread
            
            self.services["api_server"].status = ServiceStatus.RUNNING
            self.services["api_server"].start_time = datetime.now()
            logger.info("API Server started")
        except Exception as e:
            self._handle_service_error("api_server", str(e))
    
    def _run_api_server(self):
        """Run API server in thread"""
        try:
            host = self.config["services"]["api_server"]["host"]
            port = self.config["services"]["api_server"]["port"]
            self.api_server.run(host=host, port=port, reload=False)
        except Exception as e:
            logger.error(f"API Server error: {e}")
            self._handle_service_error("api_server", str(e))
    
    def _start_dashboard_server(self):
        """Start Dashboard Server service"""
        try:
            self.services["dashboard_server"].status = ServiceStatus.STARTING
            
            # Start dashboard server as separate process
            host = self.config["services"]["dashboard_server"]["host"]
            port = self.config["services"]["dashboard_server"]["port"]
            
            dashboard_cmd = [
                sys.executable,
                "/opt/qenex-os/cicd/dashboard_server.py",
                "--host", host,
                "--port", str(port)
            ]
            
            process = subprocess.Popen(
                dashboard_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.service_processes["dashboard_server"] = process
            self.services["dashboard_server"].status = ServiceStatus.RUNNING
            self.services["dashboard_server"].start_time = datetime.now()
            self.services["dashboard_server"].pid = process.pid
            
            logger.info(f"Dashboard Server started (PID: {process.pid})")
        except Exception as e:
            self._handle_service_error("dashboard_server", str(e))
    
    def _start_webhook_server(self):
        """Start Webhook Server service"""
        try:
            self.services["webhook_server"].status = ServiceStatus.STARTING
            
            # Start webhook server as separate process
            host = self.config["services"]["webhook_server"]["host"]
            port = self.config["services"]["webhook_server"]["port"]
            
            webhook_cmd = [
                sys.executable,
                "/opt/qenex-os/cicd/webhook_server.py",
                "--host", host,
                "--port", str(port)
            ]
            
            process = subprocess.Popen(
                webhook_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.service_processes["webhook_server"] = process
            self.services["webhook_server"].status = ServiceStatus.RUNNING
            self.services["webhook_server"].start_time = datetime.now()
            self.services["webhook_server"].pid = process.pid
            
            logger.info(f"Webhook Server started (PID: {process.pid})")
        except Exception as e:
            self._handle_service_error("webhook_server", str(e))
    
    def _start_monitoring(self):
        """Start monitoring and health check services"""
        # Start health check thread
        health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        health_check_thread.start()
        
        # Start metrics collection thread
        metrics_thread = threading.Thread(
            target=self._metrics_collection_loop,
            daemon=True
        )
        metrics_thread.start()
        
        logger.info("Monitoring services started")
    
    def _stop_service(self, service_name: str):
        """Stop a specific service"""
        if service_name not in self.services:
            return
        
        service = self.services[service_name]
        if service.status == ServiceStatus.STOPPED:
            return
        
        logger.info(f"Stopping {service_name}")
        service.status = ServiceStatus.STOPPING
        
        try:
            # Stop threads
            if service_name in self.service_threads:
                # Threads will stop when orchestrator stops
                pass
            
            # Stop processes
            if service_name in self.service_processes:
                process = self.service_processes[service_name]
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {service_name}")
                    process.kill()
                
                del self.service_processes[service_name]
            
            # Stop service objects
            if service_name == "cache_manager" and self.cache_manager:
                self.cache_manager.stop()
                self.cache_manager = None
            elif service_name == "distributed_executor" and self.distributed_executor:
                self.distributed_executor.stop()
                self.distributed_executor = None
            elif service_name == "cicd_engine" and self.cicd_engine:
                self.cicd_engine.stop()
                self.cicd_engine = None
            
            service.status = ServiceStatus.STOPPED
            logger.info(f"{service_name} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping {service_name}: {e}")
            service.status = ServiceStatus.ERROR
            service.error_message = str(e)
    
    def _handle_service_error(self, service_name: str, error_message: str):
        """Handle service errors"""
        service = self.services[service_name]
        service.status = ServiceStatus.ERROR
        service.error_message = error_message
        service.restart_count += 1
        
        logger.error(f"Service {service_name} error: {error_message}")
        
        # Check if restart is needed and allowed
        service_config = self.config["services"][service_name]
        if (service_config.get("restart_on_failure", False) and
            service.restart_count <= service_config.get("max_restarts", 3)):
            
            logger.info(f"Attempting to restart {service_name} (attempt {service.restart_count})")
            time.sleep(5)  # Wait before restart
            self._restart_service(service_name)
    
    def _restart_service(self, service_name: str):
        """Restart a specific service"""
        logger.info(f"Restarting {service_name}")
        
        # Stop service first
        self._stop_service(service_name)
        
        # Wait a moment
        time.sleep(2)
        
        # Start service again
        if service_name == "secret_manager":
            self._start_secret_manager()
        elif service_name == "cache_manager":
            self._start_cache_manager()
        elif service_name == "distributed_executor":
            self._start_distributed_executor()
        elif service_name == "cicd_engine":
            self._start_cicd_engine()
        elif service_name == "api_server":
            self._start_api_server()
        elif service_name == "dashboard_server":
            self._start_dashboard_server()
        elif service_name == "webhook_server":
            self._start_webhook_server()
    
    def _health_check_loop(self):
        """Periodic health checks"""
        interval = self.config["monitoring"]["health_check_interval"]
        
        while self.running:
            try:
                self._perform_health_checks()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(interval)
    
    def _perform_health_checks(self):
        """Perform health checks on all services"""
        for service_name, service in self.services.items():
            if service.status != ServiceStatus.RUNNING:
                continue
            
            try:
                # Check if service is still healthy
                healthy = self._check_service_health(service_name)
                
                if not healthy:
                    logger.warning(f"Service {service_name} health check failed")
                    self._handle_service_error(service_name, "Health check failed")
                
            except Exception as e:
                logger.error(f"Health check error for {service_name}: {e}")
    
    def _check_service_health(self, service_name: str) -> bool:
        """Check health of a specific service"""
        # Check processes
        if service_name in self.service_processes:
            process = self.service_processes[service_name]
            if process.poll() is not None:
                return False  # Process has terminated
        
        # Service-specific health checks
        if service_name == "secret_manager" and self.secret_manager:
            health = self.secret_manager.health_check()
            return health.get("status") == "healthy"
        
        elif service_name == "cache_manager" and self.cache_manager:
            try:
                stats = self.cache_manager.get_statistics()
                return True  # If we can get stats, it's healthy
            except:
                return False
        
        elif service_name == "distributed_executor" and self.distributed_executor:
            try:
                status = self.distributed_executor.get_cluster_status()
                return True  # If we can get status, it's healthy
            except:
                return False
        
        elif service_name == "cicd_engine" and self.cicd_engine:
            try:
                stats = self.cicd_engine.get_pipeline_stats()
                return True  # If we can get stats, it's healthy
            except:
                return False
        
        return True  # Default to healthy if no specific check
    
    def _metrics_collection_loop(self):
        """Periodic metrics collection"""
        interval = self.config["monitoring"]["metrics_collection_interval"]
        
        while self.running:
            try:
                self._collect_metrics()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                time.sleep(interval)
    
    def _collect_metrics(self):
        """Collect system and service metrics"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "services": {}
        }
        
        # Collect service metrics
        for service_name, service in self.services.items():
            service_metrics = {
                "status": service.status.value,
                "restart_count": service.restart_count,
                "uptime": (datetime.now() - service.start_time).total_seconds() if service.start_time else 0
            }
            
            # Service-specific metrics
            if service_name == "cache_manager" and self.cache_manager:
                try:
                    cache_stats = self.cache_manager.get_statistics()
                    service_metrics["cache"] = cache_stats
                except:
                    pass
            
            elif service_name == "distributed_executor" and self.distributed_executor:
                try:
                    executor_stats = self.distributed_executor.get_cluster_status()
                    service_metrics["executor"] = executor_stats
                except:
                    pass
            
            elif service_name == "cicd_engine" and self.cicd_engine:
                try:
                    pipeline_stats = self.cicd_engine.get_pipeline_stats()
                    service_metrics["pipelines"] = pipeline_stats
                except:
                    pass
            
            metrics["services"][service_name] = service_metrics
        
        # Save metrics to file
        metrics_file = Path("/opt/qenex-os/cicd/logs/metrics.json")
        try:
            with open(metrics_file, "w") as f:
                json.dump(metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        logger.info(f"Received signal {signum}")
        self.stop()
    
    def get_status(self) -> Dict:
        """Get orchestrator status"""
        return {
            "running": self.running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "services": {
                name: {
                    "status": service.status.value,
                    "start_time": service.start_time.isoformat() if service.start_time else None,
                    "restart_count": service.restart_count,
                    "error_message": service.error_message,
                    "pid": service.pid
                }
                for name, service in self.services.items()
            }
        }
    
    def create_default_config(self):
        """Create default configuration file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
        
        logger.info(f"Default configuration created at {self.config_path}")
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Check required sections
        required_sections = ["services", "monitoring", "security", "integration"]
        for section in required_sections:
            if section not in self.config:
                issues.append(f"Missing required section: {section}")
        
        # Validate service configurations
        for service_name, service_config in self.config.get("services", {}).items():
            if not isinstance(service_config.get("enabled"), bool):
                issues.append(f"Service {service_name}: 'enabled' must be boolean")
            
            if "port" in service_config:
                port = service_config["port"]
                if not isinstance(port, int) or port < 1 or port > 65535:
                    issues.append(f"Service {service_name}: invalid port {port}")
        
        return issues

# CLI interface
class OrchestratorCLI:
    """Command-line interface for orchestrator"""
    
    def __init__(self):
        self.orchestrator = None
    
    def start(self, config_file: Optional[str] = None):
        """Start the orchestrator"""
        try:
            self.orchestrator = QENEXOrchestrator(config_file)
            self.orchestrator.start()
        except KeyboardInterrupt:
            if self.orchestrator:
                self.orchestrator.stop()
    
    def stop(self):
        """Stop the orchestrator"""
        if self.orchestrator:
            self.orchestrator.stop()
            print("Orchestrator stopped")
        else:
            print("Orchestrator is not running")
    
    def status(self):
        """Show orchestrator status"""
        if self.orchestrator:
            status = self.orchestrator.get_status()
            print(json.dumps(status, indent=2))
        else:
            print("Orchestrator is not running")
    
    def create_config(self, config_file: str):
        """Create default configuration file"""
        orchestrator = QENEXOrchestrator(config_file)
        orchestrator.create_default_config()
        print(f"Configuration file created: {config_file}")
    
    def validate_config(self, config_file: str):
        """Validate configuration file"""
        orchestrator = QENEXOrchestrator(config_file)
        issues = orchestrator.validate_config()
        
        if issues:
            print("Configuration issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("Configuration is valid")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='QENEX CI/CD Orchestrator')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start orchestrator')
    start_parser.add_argument('--config', help='Configuration file path')
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop orchestrator')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show status')
    
    # Create config command
    create_config_parser = subparsers.add_parser('create-config', help='Create default configuration')
    create_config_parser.add_argument('config_file', help='Configuration file path')
    
    # Validate config command
    validate_parser = subparsers.add_parser('validate-config', help='Validate configuration')
    validate_parser.add_argument('config_file', help='Configuration file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = OrchestratorCLI()
    
    if args.command == 'start':
        cli.start(args.config)
    elif args.command == 'stop':
        cli.stop()
    elif args.command == 'status':
        cli.status()
    elif args.command == 'create-config':
        cli.create_config(args.config_file)
    elif args.command == 'validate-config':
        cli.validate_config(args.config_file)

if __name__ == "__main__":
    main()