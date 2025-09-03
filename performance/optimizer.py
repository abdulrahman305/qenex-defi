#!/usr/bin/env python3
"""
QENEX Performance Optimizer
Intelligent CPU load balancing and memory optimization
"""

import os
import psutil
import asyncio
import multiprocessing
from typing import Dict, List
import subprocess
import json
from datetime import datetime
from pathlib import Path

class PerformanceOptimizer:
    def __init__(self):
        self.cpu_threshold = 80
        self.memory_threshold = 85
        self.optimization_interval = 10
        self.process_priorities = {}
        self.cache_dir = Path('/opt/qenex-os/cache')
        self.cache_dir.mkdir(exist_ok=True)
        
    async def optimize_cpu(self):
        """Intelligent CPU load balancing"""
        while True:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                
                if cpu_percent > self.cpu_threshold:
                    # Get top CPU consuming processes
                    processes = []
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                        try:
                            processes.append(proc.info)
                        except:
                            pass
                    
                    # Sort by CPU usage
                    processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
                    
                    # Renice heavy processes
                    for proc in processes[:5]:
                        if proc['cpu_percent'] > 20:
                            try:
                                os.nice(5)  # Lower priority
                                subprocess.run(['renice', '10', str(proc['pid'])], 
                                             capture_output=True)
                            except:
                                pass
                    
                    # Enable CPU frequency scaling
                    subprocess.run(['cpupower', 'frequency-set', '-g', 'powersave'],
                                 capture_output=True)
                
            except Exception as e:
                print(f"CPU optimization error: {e}")
            
            await asyncio.sleep(self.optimization_interval)
    
    async def optimize_memory(self):
        """Memory optimization with intelligent caching"""
        while True:
            try:
                mem = psutil.virtual_memory()
                
                if mem.percent > self.memory_threshold:
                    # Clear page cache
                    subprocess.run(['sh', '-c', 'echo 1 > /proc/sys/vm/drop_caches'],
                                 capture_output=True)
                    
                    # Compact memory
                    subprocess.run(['sh', '-c', 'echo 1 > /proc/sys/vm/compact_memory'],
                                 capture_output=True)
                    
                    # Kill memory-heavy processes if critical
                    if mem.percent > 95:
                        processes = []
                        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                            try:
                                if proc.info['memory_percent'] > 10:
                                    processes.append(proc.info)
                            except:
                                pass
                        
                        # Sort by memory usage
                        processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
                        
                        # Terminate lowest priority high-memory process
                        if processes:
                            try:
                                os.kill(processes[0]['pid'], 15)  # SIGTERM
                            except:
                                pass
                
            except Exception as e:
                print(f"Memory optimization error: {e}")
            
            await asyncio.sleep(self.optimization_interval)
    
    async def intelligent_caching(self):
        """Implement intelligent caching for frequently accessed data"""
        cache = {}
        cache_hits = {}
        max_cache_size = 100  # MB
        
        while True:
            try:
                # Monitor file access patterns
                accessed_files = self.get_frequently_accessed_files()
                
                for file_path in accessed_files:
                    if file_path not in cache:
                        # Add to cache if frequently accessed
                        if self.should_cache(file_path, cache_hits):
                            try:
                                with open(file_path, 'rb') as f:
                                    content = f.read()
                                    if len(content) < 10 * 1024 * 1024:  # < 10MB
                                        cache[file_path] = content
                                        cache_hits[file_path] = 1
                            except:
                                pass
                    else:
                        cache_hits[file_path] += 1
                
                # Evict least recently used if cache too large
                if self.get_cache_size(cache) > max_cache_size * 1024 * 1024:
                    # Remove least accessed items
                    sorted_items = sorted(cache_hits.items(), key=lambda x: x[1])
                    for file_path, _ in sorted_items[:len(sorted_items)//4]:
                        if file_path in cache:
                            del cache[file_path]
                            del cache_hits[file_path]
                
            except Exception as e:
                print(f"Caching error: {e}")
            
            await asyncio.sleep(30)
    
    def get_frequently_accessed_files(self) -> List[str]:
        """Get list of frequently accessed files"""
        try:
            # Use lsof to find open files
            result = subprocess.run(['lsof', '-Fn'], capture_output=True, text=True)
            files = []
            for line in result.stdout.split('\n'):
                if line.startswith('n/'):
                    files.append(line[1:])
            return files[:20]  # Top 20 files
        except:
            return []
    
    def should_cache(self, file_path: str, cache_hits: Dict) -> bool:
        """Determine if file should be cached"""
        # Don't cache system files
        if file_path.startswith('/proc') or file_path.startswith('/sys'):
            return False
        # Don't cache large files
        try:
            if os.path.getsize(file_path) > 10 * 1024 * 1024:
                return False
        except:
            return False
        return True
    
    def get_cache_size(self, cache: Dict) -> int:
        """Calculate total cache size"""
        return sum(len(v) for v in cache.values())
    
    async def process_prioritization(self):
        """Intelligent process prioritization"""
        critical_processes = ['qenex', 'nginx', 'systemd']
        
        while True:
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        name = proc.info['name']
                        pid = proc.info['pid']
                        
                        # Boost critical processes
                        if any(crit in name for crit in critical_processes):
                            subprocess.run(['renice', '-5', str(pid)], capture_output=True)
                        # Lower priority for batch jobs
                        elif 'batch' in name or 'backup' in name:
                            subprocess.run(['renice', '15', str(pid)], capture_output=True)
                    except:
                        pass
                
            except Exception as e:
                print(f"Process prioritization error: {e}")
            
            await asyncio.sleep(60)


class PredictiveAnalytics:
    """Predictive failure detection and performance forecasting"""
    
    def __init__(self):
        self.metrics_history = []
        self.max_history = 1000
        self.prediction_threshold = 0.8
        
    async def collect_metrics(self):
        """Collect system metrics for analysis"""
        while True:
            try:
                metric = {
                    'timestamp': datetime.now().isoformat(),
                    'cpu': psutil.cpu_percent(interval=1),
                    'memory': psutil.virtual_memory().percent,
                    'disk': psutil.disk_usage('/').percent,
                    'network': self.get_network_usage(),
                    'processes': len(psutil.pids())
                }
                
                self.metrics_history.append(metric)
                
                # Keep history limited
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history = self.metrics_history[-self.max_history:]
                
                # Analyze for anomalies
                anomalies = self.detect_anomalies()
                if anomalies:
                    await self.handle_anomalies(anomalies)
                
            except Exception as e:
                print(f"Metrics collection error: {e}")
            
            await asyncio.sleep(5)
    
    def get_network_usage(self) -> float:
        """Get network usage percentage"""
        try:
            stats = psutil.net_io_counters()
            # Simple calculation - bytes sent + received
            total = stats.bytes_sent + stats.bytes_recv
            return min(100, total / (1024 * 1024 * 100))  # Normalize to percentage
        except:
            return 0
    
    def detect_anomalies(self) -> List[str]:
        """Detect anomalies in system behavior"""
        anomalies = []
        
        if len(self.metrics_history) < 10:
            return anomalies
        
        # Get recent metrics
        recent = self.metrics_history[-10:]
        
        # Calculate averages
        avg_cpu = sum(m['cpu'] for m in recent) / len(recent)
        avg_memory = sum(m['memory'] for m in recent) / len(recent)
        
        # Check for sudden spikes
        current = self.metrics_history[-1]
        
        if current['cpu'] > avg_cpu * 1.5 and current['cpu'] > 80:
            anomalies.append('cpu_spike')
        
        if current['memory'] > avg_memory * 1.2 and current['memory'] > 85:
            anomalies.append('memory_spike')
        
        if current['disk'] > 90:
            anomalies.append('disk_critical')
        
        # Check for sustained high usage
        if all(m['cpu'] > 75 for m in recent):
            anomalies.append('sustained_high_cpu')
        
        return anomalies
    
    async def handle_anomalies(self, anomalies: List[str]):
        """Handle detected anomalies"""
        for anomaly in anomalies:
            if anomaly == 'cpu_spike':
                # Trigger CPU optimization
                subprocess.run(['nice', '-n', '10', 'echo', 'CPU spike detected'])
            elif anomaly == 'memory_spike':
                # Clear caches
                subprocess.run(['sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'])
            elif anomaly == 'disk_critical':
                # Clean up disk
                subprocess.run(['find', '/tmp', '-type', 'f', '-mtime', '+1', '-delete'])
            elif anomaly == 'sustained_high_cpu':
                # Enable power saving
                subprocess.run(['cpupower', 'frequency-set', '-g', 'powersave'])
    
    def predict_failure(self) -> Dict:
        """Predict potential system failures"""
        if len(self.metrics_history) < 100:
            return {'risk': 'low', 'confidence': 0.1}
        
        # Simple prediction based on trends
        recent = self.metrics_history[-20:]
        
        # Calculate trend
        cpu_trend = self.calculate_trend([m['cpu'] for m in recent])
        memory_trend = self.calculate_trend([m['memory'] for m in recent])
        
        risk_score = 0
        
        # High CPU trend
        if cpu_trend > 2 and recent[-1]['cpu'] > 70:
            risk_score += 0.4
        
        # High memory trend
        if memory_trend > 2 and recent[-1]['memory'] > 80:
            risk_score += 0.4
        
        # Disk usage
        if recent[-1]['disk'] > 85:
            risk_score += 0.2
        
        if risk_score > 0.7:
            return {'risk': 'high', 'confidence': risk_score}
        elif risk_score > 0.4:
            return {'risk': 'medium', 'confidence': risk_score}
        else:
            return {'risk': 'low', 'confidence': risk_score}
    
    def calculate_trend(self, values: List[float]) -> float:
        """Calculate trend in values (positive = increasing)"""
        if len(values) < 2:
            return 0
        
        # Simple linear regression
        n = len(values)
        x_mean = n / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0
        
        return numerator / denominator


async def main():
    """Main performance optimization loop"""
    print("🚀 Starting QENEX Performance Optimizer...")
    
    optimizer = PerformanceOptimizer()
    analytics = PredictiveAnalytics()
    
    tasks = [
        optimizer.optimize_cpu(),
        optimizer.optimize_memory(),
        optimizer.intelligent_caching(),
        optimizer.process_prioritization(),
        analytics.collect_metrics()
    ]
    
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())