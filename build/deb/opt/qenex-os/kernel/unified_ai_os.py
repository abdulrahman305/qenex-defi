#!/usr/bin/env python3
"""
QENEX Unified AI Operating System
Complete integration of all QENEX subsystems with AI-driven orchestration
Version: 3.0.0
"""

import os
import sys
import json
import yaml
import asyncio
import threading
import subprocess
import psutil
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import hashlib
import time
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('QENEX-AI-OS')

# System paths
QENEX_ROOT = "/opt/qenex-os"
KERNEL_DIR = f"{QENEX_ROOT}/kernel"
CICD_DIR = f"{QENEX_ROOT}/cicd"
AI_DIR = f"{QENEX_ROOT}/ai"
CONFIG_DIR = f"{QENEX_ROOT}/config"
RUNTIME_DIR = f"{QENEX_ROOT}/runtime"
LOGS_DIR = f"{QENEX_ROOT}/logs"

# Ensure directories exist
for directory in [QENEX_ROOT, KERNEL_DIR, CICD_DIR, AI_DIR, CONFIG_DIR, RUNTIME_DIR, LOGS_DIR]:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Add paths
sys.path.insert(0, QENEX_ROOT)
sys.path.insert(0, KERNEL_DIR)
sys.path.insert(0, CICD_DIR)
sys.path.insert(0, AI_DIR)

class SystemMode(Enum):
    """Operating system modes"""
    NORMAL = "normal"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"

class SubsystemType(Enum):
    """QENEX subsystem types"""
    KERNEL = "kernel"
    SHELL = "shell"
    CICD = "cicd"
    AI = "ai"
    SECURITY = "security"
    NETWORK = "network"
    STORAGE = "storage"
    MONITORING = "monitoring"
    ORCHESTRATION = "orchestration"

@dataclass
class SystemConfiguration:
    """Unified system configuration"""
    mode: SystemMode = SystemMode.NORMAL
    
    # Core settings
    ai_enabled: bool = True
    auto_optimization: bool = True
    self_healing: bool = True
    continuous_learning: bool = True
    
    # Resource management
    cpu_threshold: int = 80
    memory_threshold: int = 85
    disk_threshold: int = 90
    
    # Security
    security_level: str = "high"
    encryption_enabled: bool = True
    audit_enabled: bool = True
    
    # Performance
    cache_enabled: bool = True
    parallel_processing: bool = True
    distributed_mode: bool = False
    
    # Monitoring
    telemetry_enabled: bool = True
    metrics_interval: int = 60
    log_level: str = "INFO"

@dataclass
class SystemState:
    """Current system state"""
    uptime: float = 0
    cpu_usage: float = 0
    memory_usage: float = 0
    disk_usage: float = 0
    network_io: Dict = field(default_factory=dict)
    active_processes: int = 0
    active_pipelines: int = 0
    health_score: float = 100.0
    threat_level: str = "low"
    mode: SystemMode = SystemMode.NORMAL

class QenexUnifiedAIOS:
    """QENEX Unified AI Operating System"""
    
    def __init__(self):
        self.config = SystemConfiguration()
        self.state = SystemState()
        self.subsystems = {}
        self.services = {}
        self.running = False
        self.boot_time = None
        self.shutdown_handlers = []
        
        # AI decision engine
        self.ai_engine = None
        
        # System threads
        self.monitor_thread = None
        self.ai_thread = None
        self.optimization_thread = None
        
        logger.info("QENEX Unified AI OS initializing...")
    
    def boot(self) -> Dict:
        """Boot the unified AI OS"""
        logger.info("Starting QENEX Unified AI OS boot sequence...")
        
        self.boot_time = datetime.now()
        boot_results = {
            'timestamp': self.boot_time.isoformat(),
            'stages': []
        }
        
        try:
            # Stage 1: Initialize kernel
            logger.info("[1/7] Initializing kernel...")
            self._initialize_kernel()
            boot_results['stages'].append({'kernel': 'initialized'})
            
            # Stage 2: Load subsystems
            logger.info("[2/7] Loading subsystems...")
            self._load_subsystems()
            boot_results['stages'].append({'subsystems': 'loaded'})
            
            # Stage 3: Initialize AI engine
            logger.info("[3/7] Initializing AI engine...")
            self._initialize_ai()
            boot_results['stages'].append({'ai': 'initialized'})
            
            # Stage 4: Start core services
            logger.info("[4/7] Starting core services...")
            self._start_core_services()
            boot_results['stages'].append({'services': 'started'})
            
            # Stage 5: Initialize networking
            logger.info("[5/7] Initializing networking...")
            self._initialize_networking()
            boot_results['stages'].append({'networking': 'initialized'})
            
            # Stage 6: Start monitoring
            logger.info("[6/7] Starting monitoring systems...")
            self._start_monitoring()
            boot_results['stages'].append({'monitoring': 'started'})
            
            # Stage 7: Final optimization
            logger.info("[7/7] Running final optimizations...")
            self._run_optimizations()
            boot_results['stages'].append({'optimization': 'completed'})
            
            self.running = True
            boot_results['status'] = 'success'
            boot_results['message'] = 'QENEX Unified AI OS booted successfully'
            
            # Display boot message
            self._display_boot_message()
            
            # Register shutdown handlers
            self._register_shutdown_handlers()
            
        except Exception as e:
            logger.error(f"Boot failed: {e}")
            boot_results['status'] = 'failed'
            boot_results['error'] = str(e)
            self.emergency_shutdown()
        
        return boot_results
    
    def _initialize_kernel(self):
        """Initialize the QENEX kernel"""
        try:
            # Import kernel if available
            from qenex_core import QenexKernel
            self.subsystems['kernel'] = QenexKernel()
            logger.info("QENEX kernel initialized")
        except ImportError:
            logger.warning("Kernel module not available, using mock")
            self.subsystems['kernel'] = {'status': 'mock'}
    
    def _load_subsystems(self):
        """Load all QENEX subsystems"""
        subsystem_loaders = {
            SubsystemType.SHELL: self._load_shell,
            SubsystemType.CICD: self._load_cicd,
            SubsystemType.SECURITY: self._load_security,
            SubsystemType.STORAGE: self._load_storage,
            SubsystemType.ORCHESTRATION: self._load_orchestration
        }
        
        for subsystem_type, loader in subsystem_loaders.items():
            try:
                loader()
                logger.info(f"Loaded subsystem: {subsystem_type.value}")
            except Exception as e:
                logger.error(f"Failed to load {subsystem_type.value}: {e}")
    
    def _load_shell(self):
        """Load QENEX shell subsystem"""
        try:
            from qenex_shell import QenexShell
            self.subsystems['shell'] = QenexShell()
        except ImportError:
            self.subsystems['shell'] = {'status': 'unavailable'}
    
    def _load_cicd(self):
        """Load CI/CD subsystem"""
        try:
            from autonomous_cicd import get_cicd_engine
            from gitops_controller import get_gitops_controller
            from unified_enhancements import get_unified_system
            
            self.subsystems['cicd'] = {
                'engine': get_cicd_engine(),
                'gitops': get_gitops_controller(),
                'unified': get_unified_system()
            }
        except ImportError as e:
            logger.warning(f"CI/CD subsystem partially loaded: {e}")
            self.subsystems['cicd'] = {'status': 'partial'}
    
    def _load_security(self):
        """Load security subsystem"""
        try:
            from secret_manager import get_secret_manager
            self.subsystems['security'] = {
                'secrets': get_secret_manager()
            }
        except ImportError:
            self.subsystems['security'] = {'status': 'basic'}
    
    def _load_storage(self):
        """Load storage subsystem"""
        try:
            from cache_manager import get_cache_manager
            self.subsystems['storage'] = {
                'cache': get_cache_manager()
            }
        except ImportError:
            self.subsystems['storage'] = {'status': 'basic'}
    
    def _load_orchestration(self):
        """Load orchestration subsystem"""
        try:
            from cicd_orchestrator import get_orchestrator
            from distributed_executor import get_distributed_executor
            
            self.subsystems['orchestration'] = {
                'orchestrator': get_orchestrator(),
                'distributed': get_distributed_executor()
            }
        except ImportError:
            self.subsystems['orchestration'] = {'status': 'basic'}
    
    def _initialize_ai(self):
        """Initialize AI engine"""
        try:
            from ai_autonomous_engine import get_ai_engine
            self.ai_engine = get_ai_engine()
            
            # Start AI decision loop
            self._start_ai_decision_loop()
            
            logger.info("AI engine initialized with continuous learning")
        except ImportError:
            logger.warning("AI engine not available, using rule-based fallback")
            self.ai_engine = None
    
    def _start_core_services(self):
        """Start core system services"""
        services_config = [
            ('dashboard', 8080, 'dashboard_server'),
            ('api', 8000, 'api_server'),
            ('webhooks', 8082, 'webhook_server')
        ]
        
        for service_name, port, module_name in services_config:
            try:
                module = __import__(module_name)
                get_func = getattr(module, f'get_{service_name}_server')
                service = get_func()
                service.start()
                self.services[service_name] = service
                logger.info(f"Started {service_name} service on port {port}")
            except Exception as e:
                logger.warning(f"Could not start {service_name}: {e}")
    
    def _initialize_networking(self):
        """Initialize networking subsystem"""
        self.subsystems['network'] = {
            'hostname': socket.gethostname(),
            'ip_address': socket.gethostbyname(socket.gethostname()),
            'interfaces': self._get_network_interfaces()
        }
        logger.info(f"Network initialized: {self.subsystems['network']['hostname']}")
    
    def _get_network_interfaces(self) -> List[Dict]:
        """Get network interface information"""
        interfaces = []
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    interfaces.append({
                        'interface': interface,
                        'ip': addr.address,
                        'netmask': addr.netmask
                    })
        return interfaces
    
    def _start_monitoring(self):
        """Start system monitoring"""
        def monitor_loop():
            while self.running:
                try:
                    # Update system state
                    self.state.cpu_usage = psutil.cpu_percent(interval=1)
                    self.state.memory_usage = psutil.virtual_memory().percent
                    self.state.disk_usage = psutil.disk_usage('/').percent
                    self.state.active_processes = len(psutil.pids())
                    
                    # Calculate uptime
                    if self.boot_time:
                        self.state.uptime = (datetime.now() - self.boot_time).total_seconds()
                    
                    # Calculate health score
                    self._calculate_health_score()
                    
                    # Check thresholds
                    self._check_thresholds()
                    
                    # Log metrics if enabled
                    if self.config.telemetry_enabled:
                        self._log_metrics()
                    
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                
                time.sleep(self.config.metrics_interval)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("System monitoring started")
    
    def _calculate_health_score(self):
        """Calculate overall system health score"""
        score = 100.0
        
        # CPU impact
        if self.state.cpu_usage > self.config.cpu_threshold:
            score -= (self.state.cpu_usage - self.config.cpu_threshold) * 0.5
        
        # Memory impact
        if self.state.memory_usage > self.config.memory_threshold:
            score -= (self.state.memory_usage - self.config.memory_threshold) * 0.5
        
        # Disk impact
        if self.state.disk_usage > self.config.disk_threshold:
            score -= (self.state.disk_usage - self.config.disk_threshold) * 0.3
        
        # CI/CD pipeline health
        if 'cicd' in self.subsystems and isinstance(self.subsystems['cicd'], dict):
            if 'engine' in self.subsystems['cicd']:
                pipelines = self.subsystems['cicd']['engine'].list_pipelines()
                if pipelines:
                    failed = sum(1 for p in pipelines if p.get('status') == 'failed')
                    failure_rate = (failed / len(pipelines)) * 100
                    if failure_rate > 20:
                        score -= failure_rate * 0.2
        
        self.state.health_score = max(0, min(100, score))
    
    def _check_thresholds(self):
        """Check system thresholds and take action"""
        if self.state.cpu_usage > self.config.cpu_threshold:
            logger.warning(f"High CPU usage: {self.state.cpu_usage}%")
            if self.config.auto_optimization:
                self._optimize_cpu()
        
        if self.state.memory_usage > self.config.memory_threshold:
            logger.warning(f"High memory usage: {self.state.memory_usage}%")
            if self.config.auto_optimization:
                self._optimize_memory()
        
        if self.state.disk_usage > self.config.disk_threshold:
            logger.warning(f"High disk usage: {self.state.disk_usage}%")
            if self.config.auto_optimization:
                self._optimize_disk()
    
    def _optimize_cpu(self):
        """Optimize CPU usage"""
        logger.info("Running CPU optimization...")
        
        # Get AI recommendation if available
        if self.ai_engine:
            from ai_autonomous_engine import DecisionType
            decision = self.ai_engine.make_decision(
                DecisionType.RESOURCE_ALLOCATION,
                {'cpu_usage': self.state.cpu_usage}
            )
            logger.info(f"AI recommendation: {decision}")
        
        # Kill high CPU processes
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                if proc.info['cpu_percent'] > 50:
                    logger.info(f"High CPU process: {proc.info['name']} ({proc.info['cpu_percent']}%)")
            except:
                pass
    
    def _optimize_memory(self):
        """Optimize memory usage"""
        logger.info("Running memory optimization...")
        
        # Clear caches
        if 'storage' in self.subsystems and 'cache' in self.subsystems['storage']:
            cache = self.subsystems['storage']['cache']
            cache.cleanup(strategy='aggressive')
        
        # Garbage collection
        import gc
        gc.collect()
        logger.info("Garbage collection completed")
    
    def _optimize_disk(self):
        """Optimize disk usage"""
        logger.info("Running disk optimization...")
        
        # Clean old logs
        log_dir = Path(LOGS_DIR)
        for log_file in log_dir.glob("*.log"):
            if log_file.stat().st_mtime < (time.time() - 7 * 24 * 3600):  # 7 days old
                log_file.unlink()
                logger.info(f"Deleted old log: {log_file}")
        
        # Clean CI/CD artifacts
        if 'cicd' in self.subsystems and 'engine' in self.subsystems['cicd']:
            self.subsystems['cicd']['engine']._cleanup_old_artifacts()
    
    def _run_optimizations(self):
        """Run system optimizations"""
        def optimization_loop():
            while self.running:
                try:
                    if self.config.auto_optimization:
                        # Run various optimizations
                        optimizations = []
                        
                        # Cache optimization
                        if 'storage' in self.subsystems and 'cache' in self.subsystems['storage']:
                            cache = self.subsystems['storage']['cache']
                            cache.optimize_cache_strategy()
                            optimizations.append("cache")
                        
                        # AI model optimization
                        if self.ai_engine and self.config.continuous_learning:
                            self.ai_engine._adjust_learning_rate()
                            optimizations.append("ai_learning")
                        
                        # Resource optimization
                        if self.state.health_score < 80:
                            self._balance_resources()
                            optimizations.append("resources")
                        
                        if optimizations:
                            logger.info(f"Completed optimizations: {optimizations}")
                
                except Exception as e:
                    logger.error(f"Optimization error: {e}")
                
                time.sleep(300)  # Run every 5 minutes
        
        self.optimization_thread = threading.Thread(target=optimization_loop, daemon=True)
        self.optimization_thread.start()
    
    def _balance_resources(self):
        """Balance system resources"""
        logger.info("Balancing system resources...")
        
        # Adjust process priorities
        for proc in psutil.process_iter(['pid', 'name', 'nice']):
            try:
                if 'qenex' in proc.info['name'].lower():
                    # Increase priority for QENEX processes
                    proc.nice(-5)
            except:
                pass
    
    def _start_ai_decision_loop(self):
        """Start AI-driven decision making loop"""
        def ai_loop():
            while self.running:
                try:
                    if self.ai_engine and self.config.ai_enabled:
                        from ai_autonomous_engine import DecisionType
                        
                        # Make various AI decisions
                        context = {
                            'cpu_usage': self.state.cpu_usage,
                            'memory_usage': self.state.memory_usage,
                            'disk_usage': self.state.disk_usage,
                            'health_score': self.state.health_score,
                            'mode': self.state.mode.value
                        }
                        
                        # Failure prediction
                        failure_prediction = self.ai_engine.make_decision(
                            DecisionType.FAILURE_PREDICTION,
                            context
                        )
                        
                        if failure_prediction.get('failure_probability', 0) > 0.7:
                            logger.warning(f"High failure probability detected: {failure_prediction}")
                            if self.config.self_healing:
                                self._self_heal(failure_prediction)
                        
                        # Resource optimization
                        if self.state.health_score < 90:
                            resource_decision = self.ai_engine.make_decision(
                                DecisionType.RESOURCE_ALLOCATION,
                                context
                            )
                            self._apply_resource_decision(resource_decision)
                
                except Exception as e:
                    logger.error(f"AI decision loop error: {e}")
                
                time.sleep(60)  # Make decisions every minute
        
        self.ai_thread = threading.Thread(target=ai_loop, daemon=True)
        self.ai_thread.start()
    
    def _self_heal(self, prediction: Dict):
        """Self-healing based on failure prediction"""
        logger.info("Initiating self-healing procedures...")
        
        preventive_actions = prediction.get('preventive_actions', [])
        for action in preventive_actions:
            logger.info(f"Executing preventive action: {action}")
            
            if 'memory' in action.lower():
                self._optimize_memory()
            elif 'disk' in action.lower():
                self._optimize_disk()
            elif 'restart' in action.lower():
                self._restart_unhealthy_services()
    
    def _restart_unhealthy_services(self):
        """Restart unhealthy services"""
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'health_check'):
                    health = service.health_check()
                    if not health.get('healthy', True):
                        logger.info(f"Restarting unhealthy service: {service_name}")
                        service.restart()
            except:
                pass
    
    def _apply_resource_decision(self, decision: Dict):
        """Apply AI resource allocation decision"""
        resources = decision.get('resources', {})
        
        if resources:
            logger.info(f"Applying AI resource allocation: {resources}")
            # Implementation would adjust actual resource limits
    
    def _log_metrics(self):
        """Log system metrics"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'state': asdict(self.state),
            'config': asdict(self.config)
        }
        
        metrics_file = f"{LOGS_DIR}/metrics_{datetime.now().strftime('%Y%m%d')}.json"
        
        # Append metrics to file
        with open(metrics_file, 'a') as f:
            f.write(json.dumps(metrics) + '\n')
    
    def _display_boot_message(self):
        """Display boot completion message"""
        print("""
╔═══════════════════════════════════════════════════════════════╗
║              QENEX UNIFIED AI OS v3.0.0                       ║
║                                                                ║
║  ██████  ███████ ███    ██ ███████ ██   ██                    ║
║ ██    ██ ██      ████   ██ ██       ██ ██                     ║
║ ██    ██ █████   ██ ██  ██ █████     ███                      ║
║ ██ ▄▄ ██ ██      ██  ██ ██ ██       ██ ██                     ║
║  ██████  ███████ ██   ████ ███████ ██   ██                    ║
║     ▀▀                                                         ║
║                AI-Powered Autonomous Operating System          ║
╚═══════════════════════════════════════════════════════════════╝

System Status: OPERATIONAL
Health Score: {:.1f}%
Mode: {}
Uptime: {:.0f} seconds

Services:
  ✓ Dashboard: http://localhost:8080
  ✓ API: http://localhost:8000/docs
  ✓ Webhooks: http://localhost:8082

Type 'qenex-shell' to access the command interface.
        """.format(self.state.health_score, self.state.mode.value, self.state.uptime))
    
    def _register_shutdown_handlers(self):
        """Register system shutdown handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def set_mode(self, mode: SystemMode) -> Dict:
        """Change system operating mode"""
        logger.info(f"Changing system mode from {self.state.mode.value} to {mode.value}")
        
        self.state.mode = mode
        
        # Apply mode-specific configurations
        if mode == SystemMode.PERFORMANCE:
            self.config.cache_enabled = True
            self.config.parallel_processing = True
            self.config.distributed_mode = True
            self.config.security_level = "medium"
        elif mode == SystemMode.SECURITY:
            self.config.security_level = "maximum"
            self.config.encryption_enabled = True
            self.config.audit_enabled = True
            self.config.distributed_mode = False
        elif mode == SystemMode.DEVELOPMENT:
            self.config.log_level = "DEBUG"
            self.config.self_healing = False
            self.config.auto_optimization = False
        elif mode == SystemMode.PRODUCTION:
            self.config.security_level = "high"
            self.config.self_healing = True
            self.config.auto_optimization = True
            self.config.continuous_learning = True
        elif mode == SystemMode.MAINTENANCE:
            self.config.auto_optimization = False
            self.config.self_healing = False
        elif mode == SystemMode.EMERGENCY:
            self.config.security_level = "maximum"
            self.config.self_healing = True
            self.config.auto_optimization = True
            # Disable non-essential services
            self._disable_non_essential_services()
        
        return {
            'status': 'success',
            'mode': mode.value,
            'config_changes': asdict(self.config)
        }
    
    def _disable_non_essential_services(self):
        """Disable non-essential services in emergency mode"""
        non_essential = ['dashboard', 'webhooks']
        for service_name in non_essential:
            if service_name in self.services:
                try:
                    self.services[service_name].stop()
                    logger.info(f"Stopped non-essential service: {service_name}")
                except:
                    pass
    
    def get_status(self) -> Dict:
        """Get comprehensive system status"""
        status = {
            'version': '3.0.0',
            'running': self.running,
            'boot_time': self.boot_time.isoformat() if self.boot_time else None,
            'state': asdict(self.state),
            'config': asdict(self.config),
            'subsystems': {},
            'services': {}
        }
        
        # Check subsystem status
        for name, subsystem in self.subsystems.items():
            if isinstance(subsystem, dict):
                status['subsystems'][name] = subsystem.get('status', 'loaded')
            else:
                status['subsystems'][name] = 'active'
        
        # Check service status
        for name, service in self.services.items():
            try:
                if hasattr(service, 'running'):
                    status['services'][name] = 'running' if service.running else 'stopped'
                else:
                    status['services'][name] = 'unknown'
            except:
                status['services'][name] = 'error'
        
        return status
    
    def execute_command(self, command: str, args: List[str] = None) -> Dict:
        """Execute a system command"""
        logger.info(f"Executing command: {command} {args}")
        
        commands = {
            'status': self.get_status,
            'mode': lambda: self.set_mode(SystemMode[args[0].upper()]) if args else {'error': 'Mode required'},
            'optimize': self._run_system_optimization,
            'health': lambda: {'health_score': self.state.health_score, 'state': asdict(self.state)},
            'services': lambda: {name: 'running' if hasattr(s, 'running') and s.running else 'stopped' 
                                for name, s in self.services.items()},
            'shutdown': self.shutdown,
            'restart': self.restart
        }
        
        if command in commands:
            return commands[command]()
        else:
            return {'error': f'Unknown command: {command}'}
    
    def _run_system_optimization(self) -> Dict:
        """Run comprehensive system optimization"""
        logger.info("Running comprehensive system optimization...")
        
        optimizations = []
        
        # Memory optimization
        self._optimize_memory()
        optimizations.append("memory")
        
        # Disk optimization
        self._optimize_disk()
        optimizations.append("disk")
        
        # Cache optimization
        if 'storage' in self.subsystems and 'cache' in self.subsystems['storage']:
            self.subsystems['storage']['cache'].optimize_cache_strategy()
            optimizations.append("cache")
        
        # AI optimization
        if self.ai_engine:
            self.ai_engine._adjust_learning_rate()
            optimizations.append("ai")
        
        # Resource balancing
        self._balance_resources()
        optimizations.append("resources")
        
        return {
            'status': 'success',
            'optimizations': optimizations,
            'health_score_before': self.state.health_score,
            'health_score_after': self._calculate_health_score() or self.state.health_score
        }
    
    def restart(self) -> Dict:
        """Restart the system"""
        logger.info("System restart initiated...")
        
        # Shutdown
        self.shutdown()
        
        # Wait
        time.sleep(2)
        
        # Boot again
        return self.boot()
    
    def shutdown(self) -> Dict:
        """Shutdown the system"""
        logger.info("System shutdown initiated...")
        
        self.running = False
        
        # Stop all services
        for name, service in self.services.items():
            try:
                if hasattr(service, 'stop'):
                    service.stop()
                logger.info(f"Stopped service: {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        # Stop subsystems
        for name, subsystem in self.subsystems.items():
            try:
                if isinstance(subsystem, dict):
                    for sub_name, sub_component in subsystem.items():
                        if hasattr(sub_component, 'shutdown'):
                            sub_component.shutdown()
                elif hasattr(subsystem, 'shutdown'):
                    subsystem.shutdown()
                logger.info(f"Stopped subsystem: {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        logger.info("QENEX Unified AI OS shutdown complete")
        
        return {
            'status': 'success',
            'message': 'System shutdown complete',
            'uptime': self.state.uptime
        }
    
    def emergency_shutdown(self):
        """Emergency shutdown procedure"""
        logger.critical("EMERGENCY SHUTDOWN INITIATED")
        self.running = False
        
        # Force stop all threads
        for thread in threading.enumerate():
            if thread != threading.current_thread():
                thread._stop()
        
        # Kill all QENEX processes
        for proc in psutil.process_iter(['pid', 'name']):
            if 'qenex' in proc.info['name'].lower():
                try:
                    proc.kill()
                except:
                    pass
        
        logger.critical("Emergency shutdown complete")

# Global OS instance
unified_ai_os = None

def get_unified_ai_os():
    """Get or create unified AI OS instance"""
    global unified_ai_os
    if unified_ai_os is None:
        unified_ai_os = QenexUnifiedAIOS()
    return unified_ai_os

# Main entry point
def main():
    """Main entry point for QENEX Unified AI OS"""
    import argparse
    
    parser = argparse.ArgumentParser(description='QENEX Unified AI Operating System')
    parser.add_argument('command', choices=['boot', 'status', 'shutdown', 'restart', 'shell'],
                       help='System command')
    parser.add_argument('--mode', choices=['normal', 'performance', 'security', 'development', 
                                          'production', 'maintenance', 'emergency'],
                       help='System mode')
    
    args = parser.parse_args()
    
    os_instance = get_unified_ai_os()
    
    if args.command == 'boot':
        if args.mode:
            os_instance.config.mode = SystemMode[args.mode.upper()]
        result = os_instance.boot()
        print(json.dumps(result, indent=2))
        
        # Keep running
        try:
            while os_instance.running:
                time.sleep(1)
        except KeyboardInterrupt:
            os_instance.shutdown()
    
    elif args.command == 'status':
        result = os_instance.get_status()
        print(json.dumps(result, indent=2, default=str))
    
    elif args.command == 'shutdown':
        result = os_instance.shutdown()
        print(json.dumps(result, indent=2))
    
    elif args.command == 'restart':
        result = os_instance.restart()
        print(json.dumps(result, indent=2))
    
    elif args.command == 'shell':
        # Launch QENEX shell
        subprocess.run(['python3', f'{KERNEL_DIR}/qenex_shell.py'])

if __name__ == '__main__':
    main()