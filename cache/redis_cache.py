#!/usr/bin/env python3
"""
QENEX Redis Cache Manager - High-performance caching layer
"""

import redis
import json
import pickle
import hashlib
import asyncio
import logging
from typing import Any, Optional, Union, Dict, List
from datetime import timedelta
from functools import wraps
import aioredis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisCacheManager:
    def __init__(self, host='localhost', port=6379, db=0, password=None, 
                 default_ttl=3600, key_prefix='qenex:'):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        
        # Sync client
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=False
        )
        
        # Async client
        self.async_client = None
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
    
    async def init_async(self):
        """Initialize async Redis client"""
        self.async_client = await aioredis.create_redis_pool(
            f'redis://{self.host}:{self.port}/{self.db}',
            password=self.password,
            encoding='utf-8'
        )
    
    def _make_key(self, key: str) -> str:
        """Create prefixed cache key"""
        return f"{self.key_prefix}{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first (faster, human-readable)
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if not data:
            return None
        
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    # Synchronous methods
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            full_key = self._make_key(key)
            data = self.redis_client.get(full_key)
            
            if data is None:
                self.stats['misses'] += 1
                return None
            
            self.stats['hits'] += 1
            return self._deserialize(data)
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            full_key = self._make_key(key)
            data = self._serialize(value)
            ttl = ttl or self.default_ttl
            
            result = self.redis_client.setex(full_key, ttl, data)
            self.stats['sets'] += 1
            return result
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            full_key = self._make_key(key)
            result = self.redis_client.delete(full_key)
            self.stats['deletes'] += 1
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        full_key = self._make_key(key)
        return self.redis_client.exists(full_key) > 0
    
    def mget(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values"""
        full_keys = [self._make_key(k) for k in keys]
        values = self.redis_client.mget(full_keys)
        
        result = {}
        for key, value in zip(keys, values):
            if value is not None:
                result[key] = self._deserialize(value)
                self.stats['hits'] += 1
            else:
                self.stats['misses'] += 1
        
        return result
    
    def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values"""
        ttl = ttl or self.default_ttl
        pipe = self.redis_client.pipeline()
        
        for key, value in mapping.items():
            full_key = self._make_key(key)
            data = self._serialize(value)
            pipe.setex(full_key, ttl, data)
            self.stats['sets'] += 1
        
        results = pipe.execute()
        return all(results)
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        full_pattern = self._make_key(pattern)
        keys = self.redis_client.keys(full_pattern)
        
        if keys:
            deleted = self.redis_client.delete(*keys)
            self.stats['deletes'] += deleted
            return deleted
        
        return 0
    
    def flush(self) -> bool:
        """Clear all cache"""
        return self.redis_client.flushdb()
    
    # Async methods
    async def async_get(self, key: str) -> Optional[Any]:
        """Async get value from cache"""
        if not self.async_client:
            await self.init_async()
        
        try:
            full_key = self._make_key(key)
            data = await self.async_client.get(full_key)
            
            if data is None:
                self.stats['misses'] += 1
                return None
            
            self.stats['hits'] += 1
            return self._deserialize(data.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Async cache get error: {e}")
            return None
    
    async def async_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Async set value in cache"""
        if not self.async_client:
            await self.init_async()
        
        try:
            full_key = self._make_key(key)
            data = self._serialize(value)
            ttl = ttl or self.default_ttl
            
            result = await self.async_client.setex(full_key, ttl, data)
            self.stats['sets'] += 1
            return result
            
        except Exception as e:
            logger.error(f"Async cache set error: {e}")
            return False
    
    # Decorator for caching function results
    def cache(self, ttl: Optional[int] = None, key_func: Optional[callable] = None):
        """Decorator to cache function results"""
        def decorator(func):
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default key generation
                    key_parts = [func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = hashlib.md5(':'.join(key_parts).encode()).hexdigest()
                
                # Check cache
                cached = self.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Store in cache
                self.set(cache_key, result, ttl)
                
                return result
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    key_parts = [func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = hashlib.md5(':'.join(key_parts).encode()).hexdigest()
                
                # Check cache
                cached = await self.async_get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                await self.async_set(cache_key, result, ttl)
                
                return result
            
            # Return appropriate wrapper
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    # Cache warming
    def warm_cache(self, data: Dict[str, Any], ttl: Optional[int] = None):
        """Pre-populate cache with data"""
        return self.mset(data, ttl)
    
    # Cache invalidation
    def invalidate_tag(self, tag: str):
        """Invalidate all keys with a specific tag"""
        return self.clear_pattern(f"tag:{tag}:*")
    
    # Statistics
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        info = self.redis_client.info()
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'hit_rate': f"{hit_rate:.2f}%",
            'total_requests': total_requests,
            'memory_used': info.get('used_memory_human', 'N/A'),
            'keys': self.redis_client.dbsize(),
            'connected_clients': info.get('connected_clients', 0),
            'uptime_days': info.get('uptime_in_days', 0)
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }

# Global cache instance
cache = RedisCacheManager()

# Specific cache instances for different purposes
pipeline_cache = RedisCacheManager(db=1, key_prefix='pipeline:')
api_cache = RedisCacheManager(db=2, key_prefix='api:', default_ttl=300)
session_cache = RedisCacheManager(db=3, key_prefix='session:', default_ttl=86400)

# Example usage
if __name__ == "__main__":
    # Test cache operations
    cache = RedisCacheManager()
    
    # Basic operations
    cache.set('test_key', {'data': 'test_value'}, ttl=60)
    value = cache.get('test_key')
    print(f"Retrieved: {value}")
    
    # Multiple operations
    cache.mset({
        'user:1': {'name': 'Alice', 'role': 'admin'},
        'user:2': {'name': 'Bob', 'role': 'user'}
    })
    
    users = cache.mget(['user:1', 'user:2'])
    print(f"Users: {users}")
    
    # Using decorator
    @cache.cache(ttl=300)
    def expensive_operation(x, y):
        print(f"Computing {x} + {y}...")
        return x + y
    
    result1 = expensive_operation(5, 3)  # Computes
    result2 = expensive_operation(5, 3)  # From cache
    
    # Statistics
    print(f"Cache stats: {cache.get_stats()}")