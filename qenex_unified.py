#!/usr/bin/env python3
"""
QENEX Unified AI OS - Single Instance System
"""

import asyncio
import subprocess
import sys
import os
import json
import signal
from pathlib import Path

class QenexSingleOS:
    def __init__(self):
        self.pid_file = Path('/var/run/qenex.pid')
        self.running = False
        
    async def start_all(self):
        """Start single unified QENEX OS instance"""
        # Check if already running
        if self.pid_file.exists():
            try:
                old_pid = int(self.pid_file.read_text())
                os.kill(old_pid, 0)
                print(f"❌ QENEX OS is already running (PID: {old_pid})")
                return
            except:
                self.pid_file.unlink()
        
        print("🚀 Starting QENEX Unified AI OS (Single Instance)...")
        
        # Start the single unified process
        proc = subprocess.Popen(['python3', '/opt/qenex-os/qenex_single_unified.py'])
        print("\n✅ QENEX OS is starting...")
        print("📊 Dashboard: http://91.99.223.180")
        print("📚 API: http://91.99.223.180:8000/api/status")
        print("\nUse 'qenex status' to check status")
    
    async def stop_all(self):
        """Stop QENEX OS"""
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text())
                os.kill(pid, signal.SIGTERM)
                print("✓ QENEX OS stopped")
                self.pid_file.unlink()
            except:
                print("❌ Failed to stop QENEX OS")
        else:
            print("QENEX OS is not running")
    
    def status(self):
        """Show status"""
        try:
            with open('/opt/qenex-os/dashboard/api.json', 'r') as f:
                data = json.load(f)
            
            # Check AI learning status
            ai_status = {}
            try:
                with open('/opt/qenex-os/data/model_status.json', 'r') as f:
                    ai_status = json.load(f)
            except:
                ai_status = {'version': 1.0, 'iterations': 0}
            
            print(f"""
╔══════════════════════════════════════╗
║       QENEX System Status            ║
╠══════════════════════════════════════╣
║ Uptime:     {data['uptime_hours']:>6}h                  ║
║ Pipelines:  {data['pipelines']:>6}                   ║
║ Success:    {data['success_rate']:>6.1f}%                 ║
║ Memory:     {data['memory_usage']:>6.1f}%                 ║
║ Load:       {data['load_average']:>6.2f}                  ║
║ AI Model:   v{ai_status.get('version', 1.0):>5.1f}                  ║
║ Training:   {ai_status.get('iterations', 0):>6} iterations      ║
╚══════════════════════════════════════╝
            """)
        except:
            print("System status unavailable")
    
    def quick_deploy(self, repo, branch='main'):
        """Quick deployment"""
        print(f"🚀 Deploying {repo}#{branch}...")
        
        # Trigger pipeline
        result = subprocess.run([
            'curl', '-X', 'POST',
            'https://abdulrahman305.github.io/qenex-docs
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({'repository': repo, 'branch': branch})
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Pipeline triggered successfully")
        else:
            print("❌ Deployment failed")
    
    def auto_fix(self):
        """Auto-fix common issues"""
        print("🔧 Running auto-fix...")
        
        fixes = [
            ('Optimizing system', '/opt/qenex-os/scripts/optimize_system.sh'),
            ('Cleaning up', '/opt/qenex-os/scripts/cleanup.sh'),
            ('Restarting services', 'systemctl restart nginx'),
        ]
        
        for desc, cmd in fixes:
            print(f"  • {desc}...")
            subprocess.run(cmd.split() if ' ' in cmd else [cmd], 
                         capture_output=True)
        
        print("✅ Auto-fix complete")

async def main():
    qenex = QenexSingleOS()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'start':
            await qenex.start_all()
        elif cmd == 'stop':
            await qenex.stop_all()
        elif cmd == 'status':
            qenex.status()
        elif cmd == 'deploy' and len(sys.argv) > 2:
            repo = sys.argv[2]
            branch = sys.argv[3] if len(sys.argv) > 3 else 'main'
            qenex.quick_deploy(repo, branch)
        elif cmd == 'fix':
            qenex.auto_fix()
        elif cmd == 'nlp' or cmd == 'talk':
            # Launch natural language interface
            subprocess.run(['python3', '/opt/qenex-os/nlp/natural_language_control.py'])
        else:
            print("""
QENEX Unified AI OS - Single Instance

Usage:
  qenex                Show status
  qenex start          Start QENEX OS
  qenex stop           Stop QENEX OS  
  qenex status         Show system status
  qenex deploy <repo>  Deploy repository
  qenex fix            Auto-fix issues
  qenex talk           Natural language control
            """)
    else:
        # Default: show status
        qenex.status()

if __name__ == "__main__":
    asyncio.run(main())