#!/usr/bin/env python3
"""
QENEX Memory Optimizer
Aggressive memory management for high-usage scenarios
"""

import os
import gc
import psutil
import subprocess
import asyncio
from datetime import datetime

class MemoryOptimizer:
    def __init__(self):
        self.critical_threshold = 90
        self.warning_threshold = 80
        self.target_usage = 70
        
    async def optimize(self):
        """Main optimization loop"""
        while True:
            mem = psutil.virtual_memory()
            print(f"[{datetime.now()}] Memory: {mem.percent}%")
            
            if mem.percent > self.critical_threshold:
                await self.critical_cleanup()
            elif mem.percent > self.warning_threshold:
                await self.moderate_cleanup()
            
            await asyncio.sleep(30)
    
    async def critical_cleanup(self):
        """Aggressive memory cleanup for critical situations"""
        print("🔴 Critical memory - aggressive cleanup")
        
        # Force Python garbage collection
        gc.collect()
        gc.collect()
        gc.collect()
        
        # Clear all caches
        subprocess.run(['sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'], capture_output=True)
        
        # Kill memory-heavy non-essential processes
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                if proc.info['memory_percent'] > 5:
                    name = proc.info['name']
                    # Skip critical processes
                    if name not in ['systemd', 'nginx', 'haproxy', 'mysql', 'qenex', 'sshd']:
                        print(f"  Killing {name} (using {proc.info['memory_percent']:.1f}% memory)")
                        proc.kill()
            except:
                pass
        
        # Compact memory
        subprocess.run(['sh', '-c', 'echo 1 > /proc/sys/vm/compact_memory'], capture_output=True)
        
        # Clear temp files
        subprocess.run(['find', '/tmp', '-type', 'f', '-atime', '+1', '-delete'], capture_output=True)
        subprocess.run(['find', '/var/tmp', '-type', 'f', '-atime', '+1', '-delete'], capture_output=True)
        
    async def moderate_cleanup(self):
        """Moderate memory cleanup"""
        print("🟡 Warning memory - moderate cleanup")
        
        # Python garbage collection
        gc.collect()
        
        # Clear page cache only
        subprocess.run(['sh', '-c', 'echo 1 > /proc/sys/vm/drop_caches'], capture_output=True)
        
        # Clean old logs
        subprocess.run(['find', '/var/log', '-name', '*.log', '-size', '+100M', '-exec', 'truncate', '-s', '0', '{}', ';'], 
                      capture_output=True)

async def main():
    optimizer = MemoryOptimizer()
    await optimizer.optimize()

if __name__ == "__main__":
    asyncio.run(main())