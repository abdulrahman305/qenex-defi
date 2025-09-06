#!/usr/bin/env python3
"""
QENEX Master System Integration
Orchestrates all QENEX features into a unified AI operating system
"""

import asyncio
import json
import time
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Import all QENEX systems
sys.path.append('/opt/qenex-os')
from autoscaling.autoscaler import QenexAutoScaler
from backup_recovery.backup_system import QenexBackupSystem
from distributed.distributed_system import QenexDistributedSystem
from zero_trust.security_framework import QenexZeroTrustSecurity
from visual_pipeline.pipeline_builder import QenexPipelineBuilder
from voice_control.voice_system import QenexVoiceControl
from quantum_ready.quantum_architecture import QenexQuantumArchitecture

@dataclass
class SystemStatus:
    """Overall system status"""
    component: str
    status: str
    uptime: float
    last_check: float
    details: Dict[str, Any]

class QenexMasterSystem:
    """Master system orchestrating all QENEX components"""
    
    def __init__(self, config_path: str = "/opt/qenex-os/config/master.json"):
        self.config_path = config_path
        self.components = {}
        self.system_status = {}
        self.start_time = time.time()
        self.shutdown_event = asyncio.Event()
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/opt/qenex-os/logs/master_system.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('QenexMasterSystem')
        
        # Load configuration
        self.load_config()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def load_config(self):
        """Load master system configuration"""
        default_config = {
            "enabled_components": {
                "autoscaling": True,
                "backup_recovery": True,
                "distributed": True,
                "zero_trust": True,
                "visual_pipeline": True,
                "voice_control": True,
                "quantum_ready": True
            },
            "startup_order": [
                "zero_trust",
                "backup_recovery",
                "distributed", 
                "autoscaling",
                "visual_pipeline",
                "quantum_ready",
                "voice_control"
            ],
            "health_check_interval": 30,
            "auto_restart": True,
            "system_dashboard": {
                "enabled": True,
                "port": 8080,
                "host": "0.0.0.0"
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
            
    def save_config(self):
        """Save current configuration"""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
            
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()
        
    async def initialize_components(self):
        """Initialize all QENEX components"""
        enabled_components = self.config["enabled_components"]
        
        # Initialize components based on startup order
        for component_name in self.config["startup_order"]:
            if not enabled_components.get(component_name, False):
                self.logger.info(f"Component {component_name} is disabled, skipping")
                continue
                
            try:
                self.logger.info(f"Initializing {component_name}...")
                
                if component_name == "autoscaling":
                    self.components[component_name] = QenexAutoScaler()
                elif component_name == "backup_recovery":
                    self.components[component_name] = QenexBackupSystem()
                elif component_name == "distributed":
                    self.components[component_name] = QenexDistributedSystem()
                elif component_name == "zero_trust":
                    self.components[component_name] = QenexZeroTrustSecurity()
                elif component_name == "visual_pipeline":
                    self.components[component_name] = QenexPipelineBuilder()
                elif component_name == "voice_control":
                    self.components[component_name] = QenexVoiceControl()
                elif component_name == "quantum_ready":
                    self.components[component_name] = QenexQuantumArchitecture()
                    
                self.system_status[component_name] = SystemStatus(
                    component=component_name,
                    status="initialized",
                    uptime=0,
                    last_check=time.time(),
                    details={}
                )
                
                self.logger.info(f"✅ {component_name} initialized successfully")
                
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize {component_name}: {e}")
                self.system_status[component_name] = SystemStatus(
                    component=component_name,
                    status="error",
                    uptime=0,
                    last_check=time.time(),
                    details={"error": str(e)}
                )
                
    async def start_components(self):
        """Start all initialized components"""
        for component_name, component in self.components.items():
            try:
                self.logger.info(f"Starting {component_name}...")
                
                # Start component in background task
                task = asyncio.create_task(component.start())
                
                # Update status
                status = self.system_status[component_name]
                status.status = "running"
                status.uptime = 0
                
                self.logger.info(f"✅ {component_name} started successfully")
                
            except Exception as e:
                self.logger.error(f"❌ Failed to start {component_name}: {e}")
                status = self.system_status[component_name]
                status.status = "error"
                status.details = {"error": str(e)}
                
    async def health_check_loop(self):
        """Continuous health monitoring of all components"""
        while not self.shutdown_event.is_set():
            try:
                for component_name, component in self.components.items():
                    status = self.system_status[component_name]
                    
                    try:
                        # Check component health
                        if hasattr(component, 'get_status'):
                            component_status = component.get_status()
                        elif hasattr(component, 'get_system_status'):
                            component_status = await component.get_system_status()
                        else:
                            component_status = {"status": "unknown"}
                            
                        # Update status
                        status.last_check = time.time()
                        status.uptime = time.time() - self.start_time
                        status.details = component_status
                        
                        if status.status == "error" and self.config.get("auto_restart", False):
                            self.logger.info(f"Auto-restarting failed component: {component_name}")
                            await self.restart_component(component_name)
                            
                    except Exception as e:
                        self.logger.warning(f"Health check failed for {component_name}: {e}")
                        status.status = "unhealthy"
                        status.details = {"health_check_error": str(e)}
                        
                # Save system status
                await self.save_system_status()
                
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                
            await asyncio.sleep(self.config["health_check_interval"])
            
    async def restart_component(self, component_name: str):
        """Restart a specific component"""
        try:
            component = self.components.get(component_name)
            if not component:
                return
                
            # Stop component
            if hasattr(component, 'stop'):
                component.stop()
                
            # Wait a moment
            await asyncio.sleep(2)
            
            # Start component
            await component.start()
            
            # Update status
            status = self.system_status[component_name]
            status.status = "running"
            status.uptime = 0
            
            self.logger.info(f"Successfully restarted {component_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to restart {component_name}: {e}")
            
    async def save_system_status(self):
        """Save system status to file"""
        try:
            status_file = Path("/opt/qenex-os/data/system_status.json")
            status_file.parent.mkdir(parents=True, exist_ok=True)
            
            status_data = {
                "timestamp": time.time(),
                "uptime": time.time() - self.start_time,
                "components": {
                    name: asdict(status) for name, status in self.system_status.items()
                }
            }
            
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save system status: {e}")
            
    def get_master_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        total_components = len(self.components)
        running_components = len([s for s in self.system_status.values() if s.status == "running"])
        error_components = len([s for s in self.system_status.values() if s.status == "error"])
        
        return {
            "qenex_master_system": {
                "version": "3.0.0",
                "uptime": time.time() - self.start_time,
                "status": "healthy" if error_components == 0 else "degraded" if running_components > 0 else "critical"
            },
            "components": {
                "total": total_components,
                "running": running_components,
                "error": error_components,
                "details": {name: asdict(status) for name, status in self.system_status.items()}
            },
            "features": {
                "auto_scaling": "autoscaling" in self.components,
                "backup_recovery": "backup_recovery" in self.components,
                "distributed_processing": "distributed" in self.components,
                "zero_trust_security": "zero_trust" in self.components,
                "visual_pipeline_builder": "visual_pipeline" in self.components,
                "voice_control": "voice_control" in self.components,
                "quantum_ready": "quantum_ready" in self.components
            },
            "timestamp": time.time()
        }
        
    async def shutdown(self):
        """Gracefully shutdown all components"""
        self.logger.info("🔄 Initiating QENEX system shutdown...")
        
        # Stop components in reverse order
        shutdown_order = list(reversed(self.config["startup_order"]))
        
        for component_name in shutdown_order:
            if component_name in self.components:
                try:
                    self.logger.info(f"Stopping {component_name}...")
                    component = self.components[component_name]
                    
                    if hasattr(component, 'stop'):
                        component.stop()
                        
                    self.logger.info(f"✅ {component_name} stopped")
                    
                except Exception as e:
                    self.logger.error(f"❌ Error stopping {component_name}: {e}")
                    
        self.logger.info("🔄 QENEX system shutdown complete")
        
    async def run_system_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive system diagnostics"""
        diagnostics = {
            "system_info": {
                "hostname": open('/proc/sys/kernel/hostname').read().strip(),
                "uptime": time.time() - self.start_time,
                "python_version": sys.version
            },
            "component_diagnostics": {},
            "integration_tests": {}
        }
        
        # Test each component
        for component_name, component in self.components.items():
            component_diag = {
                "status": self.system_status[component_name].status,
                "features_available": []
            }
            
            # Test component-specific features
            if component_name == "autoscaling" and hasattr(component, 'get_scaling_status'):
                try:
                    scaling_status = component.get_scaling_status()
                    component_diag["scaling_enabled"] = scaling_status.get("enabled", False)
                    component_diag["current_instances"] = scaling_status.get("current_instances", 0)
                    component_diag["features_available"].append("auto_scaling")
                except:
                    pass
                    
            elif component_name == "quantum_ready" and hasattr(component, 'get_quantum_status'):
                try:
                    quantum_status = component.get_quantum_status()
                    component_diag["quantum_enabled"] = quantum_status.get("quantum_enabled", False)
                    component_diag["max_qubits"] = quantum_status.get("simulation", {}).get("max_qubits", 0)
                    component_diag["features_available"].append("quantum_simulation")
                except:
                    pass
                    
            diagnostics["component_diagnostics"][component_name] = component_diag
            
        return diagnostics
        
    async def start(self):
        """Start the complete QENEX system"""
        self.logger.info("🚀 Starting QENEX Unified AI Operating System v3.0")
        self.logger.info("=" * 60)
        
        try:
            # Initialize all components
            self.logger.info("📦 Initializing components...")
            await self.initialize_components()
            
            # Start all components
            self.logger.info("🔧 Starting services...")
            await self.start_components()
            
            # Run system diagnostics
            self.logger.info("🔍 Running system diagnostics...")
            diagnostics = await self.run_system_diagnostics()
            
            # Save diagnostics
            with open("/opt/qenex-os/data/system_diagnostics.json", 'w') as f:
                json.dump(diagnostics, f, indent=2)
                
            self.logger.info("✅ QENEX System fully operational!")
            self.logger.info("=" * 60)
            self.logger.info("🎯 Available Features:")
            
            for component_name in self.components.keys():
                status = self.system_status[component_name].status
                icon = "✅" if status == "running" else "❌" if status == "error" else "⚠️"
                self.logger.info(f"   {icon} {component_name.replace('_', ' ').title()}")
                
            self.logger.info("=" * 60)
            
            # Start health monitoring
            health_task = asyncio.create_task(self.health_check_loop())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cancel health monitoring
            health_task.cancel()
            
        except Exception as e:
            self.logger.error(f"💥 Critical error in master system: {e}")
            raise
        finally:
            # Ensure cleanup
            await self.shutdown()

async def main():
    """Main entry point"""
    print("🌟 QENEX AI Operating System - Master Controller")
    print("Advanced AI-powered automation and orchestration platform")
    print()
    
    master_system = QenexMasterSystem()
    
    try:
        await master_system.start()
    except KeyboardInterrupt:
        print("\n🔄 Shutdown requested by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())