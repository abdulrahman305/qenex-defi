#!/usr/bin/env python3
"""
QENEX AI with Resource Limits and Safety Controls
Prevents excessive resource consumption while maintaining performance
"""

import asyncio
import time
import resource
import psutil
import signal
import sys
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ResourceLimits:
    """Resource constraints for AI operation"""
    max_memory_mb: int = 512  # 512MB memory limit
    max_cpu_percent: float = 50.0  # 50% CPU limit
    max_goals_active: int = 100  # Max concurrent goals
    max_nodes: int = 4  # Limited parallel nodes
    check_interval: float = 1.0  # Resource check interval
    
class ResourceMonitor:
    """Monitor and enforce resource limits"""
    
    def __init__(self, limits: ResourceLimits):
        self.limits = limits
        self.process = psutil.Process()
        self.start_time = time.time()
        
    def check_resources(self) -> Dict[str, Any]:
        """Check current resource usage"""
        try:
            memory_mb = self.process.memory_info().rss / (1024 * 1024)
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            return {
                "memory_mb": memory_mb,
                "cpu_percent": cpu_percent,
                "within_limits": (
                    memory_mb <= self.limits.max_memory_mb and
                    cpu_percent <= self.limits.max_cpu_percent
                )
            }
        except Exception as e:
            return {
                "memory_mb": 0,
                "cpu_percent": 0,
                "within_limits": True,
                "error": str(e)
            }
    
    def enforce_limits(self):
        """Enforce resource limits using OS controls"""
        try:
            # Set memory limit
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            resource.setrlimit(
                resource.RLIMIT_AS,
                (self.limits.max_memory_mb * 1024 * 1024, hard)
            )
            
            # Set CPU nice level to reduce priority
            import os
            os.nice(10)  # Lower priority
            
        except Exception:
            pass  # Continue without hard limits if not supported

class ResourceLimitedAI:
    """AI system with enforced resource limits"""
    
    def __init__(self):
        self.limits = ResourceLimits()
        self.monitor = ResourceMonitor(self.limits)
        self.goals_processed = 0
        self.active_goals: List[Dict] = []
        self.should_throttle = False
        self.performance_history: List[float] = []
        
        # Enforce limits on startup
        self.monitor.enforce_limits()
        
        # Setup graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Graceful shutdown handler"""
        print("\n🛑 Shutting down AI with resource cleanup...")
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Clean up resources"""
        self.active_goals.clear()
        self.performance_history.clear()
    
    async def process_goal_limited(self, goal: Dict) -> float:
        """Process goal with resource awareness"""
        # Check if we should throttle
        if self.should_throttle:
            await asyncio.sleep(0.1)  # Throttle processing
        
        # Simulate processing with minimal resource usage
        start = time.time()
        
        # Simple calculation instead of complex operations
        result = sum(ord(c) for c in str(goal)) * 0.001
        
        # Small delay to prevent CPU spinning
        await asyncio.sleep(0.001)
        
        return time.time() - start
    
    async def run_with_limits(self):
        """Main AI loop with resource management"""
        print("🤖 RESOURCE-LIMITED AI SYSTEM")
        print("=" * 50)
        print(f"Memory Limit: {self.limits.max_memory_mb}MB")
        print(f"CPU Limit: {self.limits.max_cpu_percent}%")
        print(f"Max Active Goals: {self.limits.max_goals_active}")
        print(f"Parallel Nodes: {self.limits.max_nodes}")
        print("=" * 50)
        
        resource_check_task = asyncio.create_task(self._monitor_resources())
        processing_task = asyncio.create_task(self._process_goals())
        
        try:
            await asyncio.gather(resource_check_task, processing_task)
        except KeyboardInterrupt:
            self.cleanup()
    
    async def _monitor_resources(self):
        """Continuous resource monitoring"""
        while True:
            status = self.monitor.check_resources()
            
            # Throttle if exceeding limits
            self.should_throttle = not status["within_limits"]
            
            if self.should_throttle:
                print(f"⚠️  Resource limit exceeded: Memory={status['memory_mb']:.1f}MB, CPU={status['cpu_percent']:.1f}%")
                
                # Reduce active goals if needed
                if len(self.active_goals) > 10:
                    self.active_goals = self.active_goals[:10]
            
            await asyncio.sleep(self.limits.check_interval)
    
    async def _process_goals(self):
        """Process goals with resource constraints"""
        while True:
            # Generate limited number of goals
            if len(self.active_goals) < self.limits.max_goals_active:
                new_goal = {
                    "id": self.goals_processed,
                    "type": "optimize",
                    "timestamp": time.time()
                }
                self.active_goals.append(new_goal)
            
            # Process goals in limited batches
            batch_size = min(self.limits.max_nodes, len(self.active_goals))
            if batch_size > 0:
                batch = self.active_goals[:batch_size]
                
                # Process batch with resource awareness
                tasks = [self.process_goal_limited(goal) for goal in batch]
                results = await asyncio.gather(*tasks)
                
                # Update metrics
                self.goals_processed += len(batch)
                self.performance_history.append(sum(results))
                
                # Remove processed goals
                self.active_goals = self.active_goals[batch_size:]
                
                # Keep history bounded
                if len(self.performance_history) > 100:
                    self.performance_history = self.performance_history[-100:]
            
            # Print status periodically
            if self.goals_processed % 50 == 0 and self.goals_processed > 0:
                await self._print_status()
            
            await asyncio.sleep(0)
    
    async def _print_status(self):
        """Print current status with resource info"""
        status = self.monitor.check_resources()
        elapsed = time.time() - self.monitor.start_time
        rate = self.goals_processed / elapsed if elapsed > 0 else 0
        
        print(f"\n📊 STATUS (T={elapsed:.1f}s)")
        print(f"  Goals: {self.goals_processed} | Rate: {rate:.1f}/s | Active: {len(self.active_goals)}")
        print(f"  Memory: {status['memory_mb']:.1f}/{self.limits.max_memory_mb}MB")
        print(f"  CPU: {status['cpu_percent']:.1f}/{self.limits.max_cpu_percent}%")
        print(f"  Throttled: {'Yes' if self.should_throttle else 'No'}")

async def main():
    """Entry point with error handling"""
    ai = ResourceLimitedAI()
    
    try:
        await ai.run_with_limits()
    except Exception as e:
        print(f"❌ Error: {e}")
        ai.cleanup()
    finally:
        print("\n✅ AI system stopped cleanly")

if __name__ == "__main__":
    # Run with resource limits
    asyncio.run(main())