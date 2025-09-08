#!/usr/bin/env python3
"""
Performance Monitoring and Metrics Collection for QENEX
Real-time performance tracking and bottleneck detection
"""

import time
import psutil
import threading
import asyncio
from typing import Dict, List, Any, Optional, Callable
from collections import deque, defaultdict
from contextlib import contextmanager
from functools import wraps
import logging
import json
from datetime import datetime, timedelta
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """
    Comprehensive performance monitoring system
    """
    
    def __init__(self, sample_interval: int = 1, history_size: int = 1000):
        self.sample_interval = sample_interval
        self.history_size = history_size
        self.running = False
        self.monitor_thread = None
        
        # Metrics storage with bounded size
        self.cpu_metrics = deque(maxlen=history_size)
        self.memory_metrics = deque(maxlen=history_size)
        self.disk_metrics = deque(maxlen=history_size)
        self.network_metrics = deque(maxlen=history_size)
        self.custom_metrics = defaultdict(lambda: deque(maxlen=history_size))
        
        # Performance counters
        self.request_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.transaction_times = deque(maxlen=1000)
        
        # Alerts and thresholds
        self.thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'response_time_ms': 1000,
            'error_rate': 0.05
        }
        self.alerts = deque(maxlen=100)
        
        # Process monitoring
        self.process = psutil.Process()
        self.start_time = time.time()
    
    def start(self):
        """Start performance monitoring"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Performance monitoring started")
    
    def stop(self):
        """Stop performance monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._collect_metrics()
                self._check_thresholds()
                time.sleep(self.sample_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    def _collect_metrics(self):
        """Collect system metrics"""
        timestamp = time.time()
        
        # CPU metrics
        cpu_data = {
            'timestamp': timestamp,
            'percent': psutil.cpu_percent(interval=0.1),
            'per_core': psutil.cpu_percent(percpu=True, interval=0.1),
            'freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            'context_switches': psutil.cpu_stats().ctx_switches,
            'interrupts': psutil.cpu_stats().interrupts
        }
        self.cpu_metrics.append(cpu_data)
        
        # Memory metrics
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        memory_data = {
            'timestamp': timestamp,
            'percent': mem.percent,
            'used_gb': mem.used / (1024**3),
            'available_gb': mem.available / (1024**3),
            'swap_percent': swap.percent,
            'swap_used_gb': swap.used / (1024**3)
        }
        self.memory_metrics.append(memory_data)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        disk_data = {
            'timestamp': timestamp,
            'percent': disk.percent,
            'used_gb': disk.used / (1024**3),
            'read_mb_s': disk_io.read_bytes / (1024**2) if disk_io else 0,
            'write_mb_s': disk_io.write_bytes / (1024**2) if disk_io else 0,
            'read_ops': disk_io.read_count if disk_io else 0,
            'write_ops': disk_io.write_count if disk_io else 0
        }
        self.disk_metrics.append(disk_data)
        
        # Network metrics
        net_io = psutil.net_io_counters()
        network_data = {
            'timestamp': timestamp,
            'bytes_sent_mb': net_io.bytes_sent / (1024**2),
            'bytes_recv_mb': net_io.bytes_recv / (1024**2),
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errors': net_io.errin + net_io.errout,
            'drops': net_io.dropin + net_io.dropout
        }
        self.network_metrics.append(network_data)
    
    def _check_thresholds(self):
        """Check if any metrics exceed thresholds"""
        if self.cpu_metrics:
            latest_cpu = self.cpu_metrics[-1]
            if latest_cpu['percent'] > self.thresholds['cpu_percent']:
                self._create_alert('CPU', f"High CPU usage: {latest_cpu['percent']:.1f}%")
        
        if self.memory_metrics:
            latest_mem = self.memory_metrics[-1]
            if latest_mem['percent'] > self.thresholds['memory_percent']:
                self._create_alert('Memory', f"High memory usage: {latest_mem['percent']:.1f}%")
        
        if self.disk_metrics:
            latest_disk = self.disk_metrics[-1]
            if latest_disk['percent'] > self.thresholds['disk_percent']:
                self._create_alert('Disk', f"High disk usage: {latest_disk['percent']:.1f}%")
        
        # Check response times
        if self.request_times:
            avg_response = statistics.mean(self.request_times)
            if avg_response > self.thresholds['response_time_ms']:
                self._create_alert('Performance', f"High response time: {avg_response:.1f}ms")
        
        # Check error rate
        total_requests = sum(self.error_counts.values())
        if total_requests > 100:
            error_rate = self.error_counts.get('error', 0) / total_requests
            if error_rate > self.thresholds['error_rate']:
                self._create_alert('Errors', f"High error rate: {error_rate:.2%}")
    
    def _create_alert(self, category: str, message: str):
        """Create a performance alert"""
        alert = {
            'timestamp': time.time(),
            'category': category,
            'message': message,
            'datetime': datetime.now().isoformat()
        }
        self.alerts.append(alert)
        logger.warning(f"Performance Alert - {category}: {message}")
    
    def record_request(self, duration_ms: float, success: bool = True):
        """Record a request completion"""
        self.request_times.append(duration_ms)
        if not success:
            self.error_counts['error'] += 1
        else:
            self.error_counts['success'] += 1
    
    def record_transaction(self, duration_ms: float, type: str = 'default'):
        """Record a transaction completion"""
        self.transaction_times.append(duration_ms)
        self.custom_metrics[f'transaction_{type}'].append({
            'timestamp': time.time(),
            'duration_ms': duration_ms
        })
    
    def record_custom_metric(self, name: str, value: float, tags: Dict = None):
        """Record a custom metric"""
        self.custom_metrics[name].append({
            'timestamp': time.time(),
            'value': value,
            'tags': tags or {}
        })
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        stats = {
            'uptime_hours': (time.time() - self.start_time) / 3600,
            'current': {},
            'averages': {},
            'peaks': {},
            'alerts': list(self.alerts)[-10:],  # Last 10 alerts
            'error_counts': dict(self.error_counts)
        }
        
        # Current metrics
        if self.cpu_metrics:
            stats['current']['cpu_percent'] = self.cpu_metrics[-1]['percent']
        if self.memory_metrics:
            stats['current']['memory_percent'] = self.memory_metrics[-1]['percent']
        if self.disk_metrics:
            stats['current']['disk_percent'] = self.disk_metrics[-1]['percent']
        
        # Calculate averages
        if self.cpu_metrics:
            stats['averages']['cpu_percent'] = statistics.mean(
                [m['percent'] for m in self.cpu_metrics]
            )
        
        if self.memory_metrics:
            stats['averages']['memory_percent'] = statistics.mean(
                [m['percent'] for m in self.memory_metrics]
            )
        
        if self.request_times:
            stats['averages']['response_time_ms'] = statistics.mean(self.request_times)
            stats['peaks']['max_response_time_ms'] = max(self.request_times)
            
            # Calculate percentiles
            sorted_times = sorted(self.request_times)
            stats['percentiles'] = {
                'p50': sorted_times[len(sorted_times) // 2],
                'p95': sorted_times[int(len(sorted_times) * 0.95)],
                'p99': sorted_times[int(len(sorted_times) * 0.99)]
            }
        
        return stats
    
    def get_metrics_window(self, window_seconds: int = 300) -> Dict[str, List]:
        """Get metrics for a specific time window"""
        cutoff = time.time() - window_seconds
        
        return {
            'cpu': [m for m in self.cpu_metrics if m['timestamp'] > cutoff],
            'memory': [m for m in self.memory_metrics if m['timestamp'] > cutoff],
            'disk': [m for m in self.disk_metrics if m['timestamp'] > cutoff],
            'network': [m for m in self.network_metrics if m['timestamp'] > cutoff]
        }

class PerformanceProfiler:
    """
    Code profiling and bottleneck detection
    """
    
    def __init__(self):
        self.profiles = {}
        self.call_counts = defaultdict(int)
        self.total_times = defaultdict(float)
        self.lock = threading.RLock()
    
    @contextmanager
    def profile(self, name: str):
        """Context manager for profiling code blocks"""
        start_time = time.perf_counter()
        start_memory = psutil.Process().memory_info().rss
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss
            
            duration = (end_time - start_time) * 1000  # Convert to ms
            memory_delta = (end_memory - start_memory) / 1024 / 1024  # Convert to MB
            
            with self.lock:
                self.call_counts[name] += 1
                self.total_times[name] += duration
                
                if name not in self.profiles:
                    self.profiles[name] = deque(maxlen=1000)
                
                self.profiles[name].append({
                    'timestamp': time.time(),
                    'duration_ms': duration,
                    'memory_delta_mb': memory_delta
                })
    
    def get_profile_stats(self, name: str = None) -> Dict:
        """Get profiling statistics"""
        with self.lock:
            if name:
                if name not in self.profiles:
                    return {}
                
                profile_data = list(self.profiles[name])
                durations = [p['duration_ms'] for p in profile_data]
                
                return {
                    'name': name,
                    'call_count': self.call_counts[name],
                    'total_time_ms': self.total_times[name],
                    'avg_time_ms': statistics.mean(durations) if durations else 0,
                    'min_time_ms': min(durations) if durations else 0,
                    'max_time_ms': max(durations) if durations else 0,
                    'recent_calls': profile_data[-10:]
                }
            else:
                # Return stats for all profiles
                stats = {}
                for profile_name in self.profiles:
                    stats[profile_name] = self.get_profile_stats(profile_name)
                return stats
    
    def get_bottlenecks(self, top_n: int = 10) -> List[Dict]:
        """Identify performance bottlenecks"""
        with self.lock:
            bottlenecks = []
            
            for name, total_time in self.total_times.items():
                bottlenecks.append({
                    'name': name,
                    'total_time_ms': total_time,
                    'call_count': self.call_counts[name],
                    'avg_time_ms': total_time / self.call_counts[name] if self.call_counts[name] > 0 else 0
                })
            
            # Sort by total time descending
            bottlenecks.sort(key=lambda x: x['total_time_ms'], reverse=True)
            return bottlenecks[:top_n]

# Decorators for performance monitoring

def monitor_performance(name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        func_name = name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with profiler.profile(func_name):
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    duration = (time.perf_counter() - start) * 1000
                    monitor.record_request(duration, success=True)
                    return result
                except Exception as e:
                    duration = (time.perf_counter() - start) * 1000
                    monitor.record_request(duration, success=False)
                    raise e
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with profiler.profile(func_name):
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    duration = (time.perf_counter() - start) * 1000
                    monitor.record_request(duration, success=True)
                    return result
                except Exception as e:
                    duration = (time.perf_counter() - start) * 1000
                    monitor.record_request(duration, success=False)
                    raise e
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

def benchmark(iterations: int = 100):
    """Decorator to benchmark function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                times.append((time.perf_counter() - start) * 1000)
            
            logger.info(f"Benchmark {func.__name__}: "
                       f"avg={statistics.mean(times):.2f}ms, "
                       f"min={min(times):.2f}ms, "
                       f"max={max(times):.2f}ms")
            return result
        
        return wrapper
    return decorator

# Global instances
monitor = PerformanceMonitor()
profiler = PerformanceProfiler()

# Auto-start monitoring
monitor.start()

# Example usage
if __name__ == "__main__":
    @monitor_performance("example_function")
    def example_function(n):
        """Example function to monitor"""
        time.sleep(0.1)
        return sum(range(n))
    
    # Run some tests
    for i in range(10):
        example_function(1000000)
    
    # Get statistics
    stats = monitor.get_statistics()
    print(f"Performance stats: {json.dumps(stats, indent=2)}")
    
    # Get bottlenecks
    bottlenecks = profiler.get_bottlenecks()
    print(f"Top bottlenecks: {json.dumps(bottlenecks, indent=2)}")
    
    # Stop monitoring
    monitor.stop()