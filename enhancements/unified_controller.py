#!/usr/bin/env python3
"""
QENEX Unified Controller v5.0
Single process managing all QENEX subsystems
"""

import asyncio
import os
import sys
import signal
import json
import psutil
from pathlib import Path
from datetime import datetime
import subprocess

class QenexUnifiedController:
    def __init__(self):
        self.version = "5.0.0"
        self.modules = {}
        self.running = True
        self.pid_file = Path('/var/run/qenex-unified.pid')
        
    async def start(self):
        """Start unified QENEX OS"""
        print(f"""
╔══════════════════════════════════════════════════════╗
║        QENEX Unified AI OS v{self.version}           ║
║            Enhanced Performance Edition              ║
╚══════════════════════════════════════════════════════╝
        """)
        
        # Check if already running
        if self.pid_file.exists():
            old_pid = int(self.pid_file.read_text())
            try:
                os.kill(old_pid, 0)
                print(f"❌ QENEX already running (PID: {old_pid})")
                return
            except:
                self.pid_file.unlink()
        
        # Write PID
        self.pid_file.write_text(str(os.getpid()))
        
        # Kill any stray QENEX processes
        subprocess.run(['pkill', '-f', 'qenex'], capture_output=True)
        
        # Start all modules in single process
        tasks = [
            self.health_monitor(),
            self.api_server(),
            self.memory_manager(),
            self.performance_tuner(),
            self.ai_engine(),
            self.dashboard_updater()
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n⏹️ Shutting down QENEX...")
            self.running = False
        finally:
            if self.pid_file.exists():
                self.pid_file.unlink()
    
    async def health_monitor(self):
        """Monitor system health"""
        while self.running:
            try:
                health = {
                    'cpu': psutil.cpu_percent(interval=1),
                    'memory': psutil.virtual_memory().percent,
                    'disk': psutil.disk_usage('/').percent,
                    'load': os.getloadavg()[0],
                    'processes': len(psutil.pids()),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Write health status
                health_file = Path('/opt/qenex-os/data/health.json')
                health_file.parent.mkdir(exist_ok=True)
                health_file.write_text(json.dumps(health, indent=2))
                
                # Auto-heal if needed
                if health['memory'] > 90:
                    subprocess.run(['sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'], 
                                 capture_output=True)
                
            except Exception as e:
                print(f"Health monitor error: {e}")
            
            await asyncio.sleep(10)
    
    async def api_server(self):
        """Lightweight API server"""
        from aiohttp import web
        
        async def status_handler(request):
            return web.json_response({
                'status': 'running',
                'version': self.version,
                'modules': list(self.modules.keys()),
                'uptime': str(datetime.now() - self.start_time)
            })
        
        app = web.Application()
        app.router.add_get('/api/status', status_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Try multiple ports
        for port in [8000, 8001, 8002, 8003]:
            try:
                site = web.TCPSite(runner, '0.0.0.0', port)
                await site.start()
                self.modules['api'] = f'port {port}'
                print(f"✓ API Server on port {port}")
                break
            except:
                continue
        
        while self.running:
            await asyncio.sleep(1)
    
    async def memory_manager(self):
        """Intelligent memory management"""
        while self.running:
            mem = psutil.virtual_memory()
            
            if mem.percent > 85:
                # Clear Python garbage
                import gc
                gc.collect()
                
                # Clear system caches
                subprocess.run(['sync'], capture_output=True)
                subprocess.run(['sh', '-c', 'echo 1 > /proc/sys/vm/drop_caches'], 
                             capture_output=True)
            
            await asyncio.sleep(30)
    
    async def performance_tuner(self):
        """Auto-tune performance"""
        while self.running:
            try:
                # Optimize CPU governor
                if psutil.cpu_percent() > 80:
                    subprocess.run(['cpupower', 'frequency-set', '-g', 'performance'], 
                                 capture_output=True)
                else:
                    subprocess.run(['cpupower', 'frequency-set', '-g', 'powersave'], 
                                 capture_output=True)
            except:
                pass
            
            await asyncio.sleep(60)
    
    async def ai_engine(self):
        """AI decision engine"""
        self.modules['ai'] = 'running'
        
        while self.running:
            # Simulate AI processing
            await asyncio.sleep(30)
    
    async def dashboard_updater(self):
        """Update dashboard metrics"""
        while self.running:
            try:
                stats = {
                    'timestamp': datetime.now().isoformat(),
                    'uptime_hours': int((datetime.now() - self.start_time).total_seconds() / 3600),
                    'memory_usage': int(psutil.virtual_memory().percent),
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'load_average': round(os.getloadavg()[0], 2),
                    'disk_usage': int(psutil.disk_usage('/').percent),
                    'services': len(self.modules),
                    'version': self.version
                }
                
                # Write to dashboard API
                api_file = Path('/opt/qenex-os/dashboard/api.json')
                api_file.parent.mkdir(exist_ok=True)
                api_file.write_text(json.dumps(stats, indent=2))
                
            except Exception as e:
                print(f"Dashboard update error: {e}")
            
            await asyncio.sleep(5)
    
    def __init__(self):
        self.version = "5.0.0"
        self.modules = {}
        self.running = True
        self.start_time = datetime.now()
        self.pid_file = Path('/var/run/qenex-unified.pid')

async def main():
    controller = QenexUnifiedController()
    await controller.start()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("❌ Must run as root")
        sys.exit(1)
    
    asyncio.run(main())