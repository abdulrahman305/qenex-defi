#!/usr/bin/env python3
"""
Memory Management and Optimization Module for QENEX
Prevents memory leaks and optimizes resource usage
"""

import gc
import sys
import os
import psutil
import weakref
import threading
import time
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, deque
from contextlib import contextmanager
import logging
import tracemalloc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryOptimizer:
    """
    Advanced memory optimization and leak prevention
    """
    
    def __init__(self, threshold_mb: int = 1024, check_interval: int = 60):
        self.threshold_mb = threshold_mb
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread = None
        
        # Memory tracking
        self.peak_memory = 0
        self.memory_history = deque(maxlen=100)
        self.gc_stats = defaultdict(int)
        
        # Object tracking
        self.tracked_objects = weakref.WeakSet()
        self.object_sizes = {}
        
        # Memory leak detection
        self.allocation_tracker = {}
        self.leak_suspects = []
        
        # Start tracemalloc for detailed tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start()
    
    def start_monitoring(self):
        """Start background memory monitoring"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Memory monitoring started")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Memory monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                self.check_memory()
                self.detect_leaks()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in memory monitor: {e}")
    
    def check_memory(self):
        """Check current memory usage and trigger cleanup if needed"""
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # Track memory history
        self.memory_history.append({
            'timestamp': time.time(),
            'memory_mb': memory_mb,
            'percent': process.memory_percent()
        })
        
        # Update peak memory
        if memory_mb > self.peak_memory:
            self.peak_memory = memory_mb
        
        # Trigger cleanup if threshold exceeded
        if memory_mb > self.threshold_mb:
            logger.warning(f"Memory usage high: {memory_mb:.2f} MB")
            self.aggressive_cleanup()
        
        return memory_mb
    
    def aggressive_cleanup(self):
        """Aggressive memory cleanup when threshold exceeded"""
        logger.info("Performing aggressive memory cleanup")
        
        # Force garbage collection
        before_mb = self.get_memory_usage()
        
        # Clear caches
        self.clear_caches()
        
        # Multiple GC passes
        for generation in range(3):
            collected = gc.collect(generation)
            self.gc_stats[f'gen_{generation}'] += collected
        
        # Compact memory (Python 3.4+)
        if hasattr(gc, 'freeze'):
            gc.freeze()
            gc.unfreeze()
        
        after_mb = self.get_memory_usage()
        freed_mb = before_mb - after_mb
        
        logger.info(f"Memory cleanup freed {freed_mb:.2f} MB")
        return freed_mb
    
    def clear_caches(self):
        """Clear various Python caches"""
        # Clear functools caches
        import functools
        functools._lru_cache_clear_all = True
        
        # Clear re cache
        import re
        re.purge()
        
        # Clear linecache
        import linecache
        linecache.clearcache()
        
        # Clear urllib caches
        try:
            import urllib.request
            urllib.request.urlcleanup()
        except:
            pass
    
    def detect_leaks(self):
        """Detect potential memory leaks"""
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')[:10]
        
        self.leak_suspects = []
        for stat in top_stats:
            if stat.size > 10 * 1024 * 1024:  # > 10MB
                self.leak_suspects.append({
                    'file': stat.traceback.format()[0] if stat.traceback else 'unknown',
                    'size_mb': stat.size / 1024 / 1024,
                    'count': stat.count
                })
        
        if self.leak_suspects:
            logger.warning(f"Potential memory leaks detected: {self.leak_suspects}")
    
    def track_object(self, obj: Any, name: str = None):
        """Track an object for memory monitoring"""
        self.tracked_objects.add(obj)
        if name:
            self.object_sizes[name] = sys.getsizeof(obj)
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def get_statistics(self) -> Dict:
        """Get memory statistics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'current_mb': memory_info.rss / 1024 / 1024,
            'peak_mb': self.peak_memory,
            'percent': process.memory_percent(),
            'tracked_objects': len(self.tracked_objects),
            'gc_stats': dict(self.gc_stats),
            'leak_suspects': self.leak_suspects,
            'history': list(self.memory_history)[-10:]  # Last 10 readings
        }
    
    @contextmanager
    def memory_limit(self, limit_mb: int):
        """Context manager to enforce memory limit"""
        initial_mb = self.get_memory_usage()
        
        try:
            yield
        finally:
            current_mb = self.get_memory_usage()
            used_mb = current_mb - initial_mb
            
            if used_mb > limit_mb:
                logger.warning(f"Memory limit exceeded: used {used_mb:.2f} MB, limit was {limit_mb} MB")
                self.aggressive_cleanup()

class ObjectPool:
    """
    Object pooling to reduce memory allocation overhead
    """
    
    def __init__(self, factory, max_size: int = 100):
        self.factory = factory
        self.max_size = max_size
        self.pool = deque(maxlen=max_size)
        self.in_use = weakref.WeakSet()
        self.lock = threading.RLock()
        self.stats = defaultdict(int)
    
    def acquire(self):
        """Get an object from the pool"""
        with self.lock:
            self.stats['acquisitions'] += 1
            
            if self.pool:
                obj = self.pool.popleft()
                self.stats['pool_hits'] += 1
            else:
                obj = self.factory()
                self.stats['new_objects'] += 1
            
            self.in_use.add(obj)
            return obj
    
    def release(self, obj):
        """Return an object to the pool"""
        with self.lock:
            self.stats['releases'] += 1
            
            if obj in self.in_use:
                self.in_use.discard(obj)
                
                if len(self.pool) < self.max_size:
                    # Reset object state if it has a reset method
                    if hasattr(obj, 'reset'):
                        obj.reset()
                    self.pool.append(obj)
                else:
                    # Pool is full, let GC handle it
                    self.stats['discarded'] += 1
    
    def clear(self):
        """Clear the pool"""
        with self.lock:
            self.pool.clear()
            self.in_use.clear()
    
    def get_stats(self) -> Dict:
        """Get pool statistics"""
        with self.lock:
            return {
                'pool_size': len(self.pool),
                'in_use': len(self.in_use),
                'stats': dict(self.stats)
            }

class LazyLoader:
    """
    Lazy loading for large objects
    """
    
    def __init__(self, loader_func, cache: bool = True):
        self.loader_func = loader_func
        self.cache = cache
        self._value = None
        self._loaded = False
        self.lock = threading.RLock()
    
    def get(self):
        """Get the value, loading if necessary"""
        if not self._loaded:
            with self.lock:
                if not self._loaded:  # Double-check pattern
                    self._value = self.loader_func()
                    self._loaded = True
        return self._value
    
    def reset(self):
        """Reset the lazy loader"""
        with self.lock:
            self._value = None
            self._loaded = False
    
    def is_loaded(self) -> bool:
        """Check if value is loaded"""
        return self._loaded

class StreamProcessor:
    """
    Process large data streams without loading everything into memory
    """
    
    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB chunks
        self.chunk_size = chunk_size
        self.processed_bytes = 0
        self.processed_chunks = 0
    
    def process_file(self, file_path: str, processor_func):
        """Process a file in chunks"""
        results = []
        
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                
                result = processor_func(chunk)
                results.append(result)
                
                self.processed_bytes += len(chunk)
                self.processed_chunks += 1
                
                # Periodic GC to keep memory usage low
                if self.processed_chunks % 100 == 0:
                    gc.collect()
        
        return results
    
    def process_iterator(self, iterator, processor_func, batch_size: int = 1000):
        """Process an iterator in batches"""
        batch = []
        results = []
        
        for item in iterator:
            batch.append(item)
            
            if len(batch) >= batch_size:
                result = processor_func(batch)
                results.append(result)
                batch = []
                
                # Periodic GC
                if len(results) % 10 == 0:
                    gc.collect()
        
        # Process remaining items
        if batch:
            result = processor_func(batch)
            results.append(result)
        
        return results

# Global instance
memory_optimizer = MemoryOptimizer()

# Decorators for memory optimization
def memory_optimized(limit_mb: int = 100):
    """Decorator to optimize memory usage of a function"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with memory_optimizer.memory_limit(limit_mb):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def cached_with_limit(maxsize: int = 128, ttl: int = 3600):
    """LRU cache with TTL and memory awareness"""
    from functools import lru_cache
    import time
    
    def decorator(func):
        # Create cache with maxsize
        cached_func = lru_cache(maxsize=maxsize)(func)
        cached_func._cache_time = {}
        
        def wrapper(*args, **kwargs):
            # Check memory before caching
            if memory_optimizer.get_memory_usage() > memory_optimizer.threshold_mb * 0.9:
                # High memory usage, bypass cache
                return func(*args, **kwargs)
            
            # Check TTL
            key = str(args) + str(kwargs)
            if key in cached_func._cache_time:
                if time.time() - cached_func._cache_time[key] > ttl:
                    # Cache expired, clear this entry
                    cached_func.cache_clear()
                    cached_func._cache_time.clear()
            
            result = cached_func(*args, **kwargs)
            cached_func._cache_time[key] = time.time()
            return result
        
        wrapper.cache_info = cached_func.cache_info
        wrapper.cache_clear = cached_func.cache_clear
        return wrapper
    return decorator

# Example usage
if __name__ == "__main__":
    # Start memory monitoring
    memory_optimizer.start_monitoring()
    
    # Create object pool
    connection_pool = ObjectPool(lambda: {"connection": "new"}, max_size=10)
    
    # Use lazy loader
    lazy_data = LazyLoader(lambda: range(1000000))
    
    # Test memory optimization
    @memory_optimized(limit_mb=50)
    def memory_intensive_task():
        data = [i for i in range(1000000)]
        return sum(data)
    
    result = memory_intensive_task()
    print(f"Result: {result}")
    
    # Get statistics
    stats = memory_optimizer.get_statistics()
    print(f"Memory stats: {stats}")
    
    # Stop monitoring
    memory_optimizer.stop_monitoring()