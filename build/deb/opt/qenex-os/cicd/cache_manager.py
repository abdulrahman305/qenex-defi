#!/usr/bin/env python3
"""
QENEX Pipeline Caching System
Intelligent caching system for CI/CD pipelines to accelerate builds
Version: 1.0.0
"""

import os
import sys
import json
import hashlib
import pickle
import sqlite3
import time
import shutil
import tarfile
import tempfile
import threading
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import fnmatch

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import lz4.frame
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('QENEX-CacheManager')

class CacheType(Enum):
    DEPENDENCY = "dependency"      # Package dependencies (npm_modules, pip cache, etc.)
    BUILD_ARTIFACT = "build_artifact"  # Compiled binaries, built assets
    TEST_RESULT = "test_result"    # Test results and coverage
    DOCKER_LAYER = "docker_layer"  # Docker image layers
    SOURCE_CODE = "source_code"    # Git repository snapshots
    INTERMEDIATE = "intermediate"   # Intermediate build steps
    CUSTOM = "custom"              # Custom cache entries

class CacheStrategy(Enum):
    LRU = "lru"                    # Least Recently Used
    LFU = "lfu"                    # Least Frequently Used
    TTL = "ttl"                    # Time To Live
    SIZE_BASED = "size_based"      # Based on cache size limits
    HYBRID = "hybrid"              # Combination of strategies

class CompressionType(Enum):
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    BROTLI = "brotli"

@dataclass
class CacheKey:
    """Represents a cache key with all necessary information"""
    key: str
    pipeline_id: str
    stage_name: str
    content_hash: str
    dependencies: List[str]
    cache_type: CacheType
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_string(self) -> str:
        """Convert to string representation"""
        return f"{self.pipeline_id}:{self.stage_name}:{self.content_hash}:{self.key}"

@dataclass
class CacheEntry:
    """Represents a cache entry with metadata"""
    id: str
    cache_key: CacheKey
    file_path: str
    size_bytes: int
    compression_type: CompressionType
    created_at: datetime
    last_accessed_at: datetime
    access_count: int
    ttl_seconds: Optional[int] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        if self.ttl_seconds and not self.expires_at:
            self.expires_at = self.created_at + timedelta(seconds=self.ttl_seconds)
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return self.expires_at and datetime.now() > self.expires_at
    
    @property
    def age_seconds(self) -> int:
        """Get age of cache entry in seconds"""
        return int((datetime.now() - self.created_at).total_seconds())

class HashCalculator:
    """Calculates content hashes for cache keys"""
    
    @staticmethod
    def hash_file(file_path: str) -> str:
        """Calculate SHA-256 hash of a file"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except FileNotFoundError:
            return ""
    
    @staticmethod
    def hash_directory(directory: str, patterns: List[str] = None) -> str:
        """Calculate hash of directory contents"""
        if not os.path.exists(directory):
            return ""
        
        sha256_hash = hashlib.sha256()
        patterns = patterns or ["*"]
        
        # Get all files matching patterns
        files = []
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, directory)
                
                # Check if file matches any pattern
                if any(fnmatch.fnmatch(rel_path, pattern) for pattern in patterns):
                    files.append(file_path)
        
        # Sort files for consistent hashing
        files.sort()
        
        for file_path in files:
            # Include relative path in hash
            rel_path = os.path.relpath(file_path, directory)
            sha256_hash.update(rel_path.encode())
            
            # Include file content hash
            file_hash = HashCalculator.hash_file(file_path)
            sha256_hash.update(file_hash.encode())
        
        return sha256_hash.hexdigest()
    
    @staticmethod
    def hash_string(content: str) -> str:
        """Calculate hash of string content"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    @staticmethod
    def hash_dependencies(dependencies: List[str]) -> str:
        """Calculate hash of dependency list"""
        # Sort dependencies for consistent hashing
        sorted_deps = sorted(dependencies)
        content = "\n".join(sorted_deps)
        return HashCalculator.hash_string(content)

class CompressionManager:
    """Handles compression and decompression of cache entries"""
    
    @staticmethod
    def compress_file(source_path: str, target_path: str, 
                     compression_type: CompressionType) -> int:
        """Compress a file and return compressed size"""
        if compression_type == CompressionType.NONE:
            shutil.copy2(source_path, target_path)
            return os.path.getsize(target_path)
        
        elif compression_type == CompressionType.GZIP:
            import gzip
            with open(source_path, 'rb') as src:
                with gzip.open(target_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
            return os.path.getsize(target_path)
        
        elif compression_type == CompressionType.LZ4 and LZ4_AVAILABLE:
            import lz4.frame
            with open(source_path, 'rb') as src:
                with lz4.frame.open(target_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
            return os.path.getsize(target_path)
        
        else:
            # Fallback to no compression
            shutil.copy2(source_path, target_path)
            return os.path.getsize(target_path)
    
    @staticmethod
    def decompress_file(source_path: str, target_path: str,
                       compression_type: CompressionType):
        """Decompress a file"""
        if compression_type == CompressionType.NONE:
            shutil.copy2(source_path, target_path)
        
        elif compression_type == CompressionType.GZIP:
            import gzip
            with gzip.open(source_path, 'rb') as src:
                with open(target_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
        
        elif compression_type == CompressionType.LZ4 and LZ4_AVAILABLE:
            import lz4.frame
            with lz4.frame.open(source_path, 'rb') as src:
                with open(target_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
        
        else:
            shutil.copy2(source_path, target_path)
    
    @staticmethod
    def compress_directory(source_dir: str, target_file: str,
                          compression_type: CompressionType) -> int:
        """Compress an entire directory"""
        if compression_type == CompressionType.GZIP:
            with tarfile.open(target_file, 'w:gz') as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))
        elif compression_type == CompressionType.LZ4 and LZ4_AVAILABLE:
            # Create uncompressed tar first, then compress
            temp_tar = target_file + ".tmp"
            with tarfile.open(temp_tar, 'w') as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))
            
            CompressionManager.compress_file(temp_tar, target_file, compression_type)
            os.remove(temp_tar)
        else:
            # Uncompressed tar
            with tarfile.open(target_file, 'w') as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))
        
        return os.path.getsize(target_file)
    
    @staticmethod
    def decompress_directory(source_file: str, target_dir: str,
                           compression_type: CompressionType):
        """Decompress to directory"""
        os.makedirs(target_dir, exist_ok=True)
        
        if compression_type == CompressionType.GZIP:
            with tarfile.open(source_file, 'r:gz') as tar:
                tar.extractall(target_dir)
        elif compression_type == CompressionType.LZ4 and LZ4_AVAILABLE:
            # Decompress first, then extract tar
            temp_tar = source_file + ".tmp"
            CompressionManager.decompress_file(source_file, temp_tar, compression_type)
            
            with tarfile.open(temp_tar, 'r') as tar:
                tar.extractall(target_dir)
            os.remove(temp_tar)
        else:
            with tarfile.open(source_file, 'r') as tar:
                tar.extractall(target_dir)

class CacheStorage:
    """Handles cache storage backend"""
    
    def __init__(self, cache_dir: str = "/opt/qenex-os/cicd/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.cache_dir / "cache.db"
        self.data_dir = self.cache_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.lock = threading.RLock()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    id TEXT PRIMARY KEY,
                    cache_key TEXT NOT NULL,
                    pipeline_id TEXT NOT NULL,
                    stage_name TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    dependencies TEXT NOT NULL,
                    cache_type TEXT NOT NULL,
                    tags TEXT,
                    file_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    compression_type TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_accessed_at TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    ttl_seconds INTEGER,
                    expires_at TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Create indexes for efficient queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON cache_entries(cache_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pipeline ON cache_entries(pipeline_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON cache_entries(content_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_type ON cache_entries(cache_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)")
    
    def store_entry(self, entry: CacheEntry):
        """Store cache entry in database"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries
                    (id, cache_key, pipeline_id, stage_name, content_hash, dependencies,
                     cache_type, tags, file_path, size_bytes, compression_type,
                     created_at, last_accessed_at, access_count, ttl_seconds,
                     expires_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.id,
                    entry.cache_key.to_string(),
                    entry.cache_key.pipeline_id,
                    entry.cache_key.stage_name,
                    entry.cache_key.content_hash,
                    json.dumps(entry.cache_key.dependencies),
                    entry.cache_key.cache_type.value,
                    json.dumps(entry.cache_key.tags),
                    entry.file_path,
                    entry.size_bytes,
                    entry.compression_type.value,
                    entry.created_at,
                    entry.last_accessed_at,
                    entry.access_count,
                    entry.ttl_seconds,
                    entry.expires_at,
                    json.dumps(entry.metadata)
                ))
    
    def get_entry(self, cache_key: str) -> Optional[CacheEntry]:
        """Retrieve cache entry by key"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM cache_entries WHERE cache_key = ?
                """, (cache_key,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Reconstruct CacheKey
                cache_key_obj = CacheKey(
                    key=row['cache_key'].split(':')[-1],
                    pipeline_id=row['pipeline_id'],
                    stage_name=row['stage_name'],
                    content_hash=row['content_hash'],
                    dependencies=json.loads(row['dependencies']),
                    cache_type=CacheType(row['cache_type']),
                    tags=json.loads(row['tags']) if row['tags'] else []
                )
                
                # Reconstruct CacheEntry
                entry = CacheEntry(
                    id=row['id'],
                    cache_key=cache_key_obj,
                    file_path=row['file_path'],
                    size_bytes=row['size_bytes'],
                    compression_type=CompressionType(row['compression_type']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    last_accessed_at=datetime.fromisoformat(row['last_accessed_at']),
                    access_count=row['access_count'],
                    ttl_seconds=row['ttl_seconds'],
                    expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                
                return entry
    
    def find_entries(self, pipeline_id: Optional[str] = None,
                    cache_type: Optional[CacheType] = None,
                    content_hash: Optional[str] = None) -> List[CacheEntry]:
        """Find cache entries by criteria"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = "SELECT * FROM cache_entries WHERE 1=1"
                params = []
                
                if pipeline_id:
                    query += " AND pipeline_id = ?"
                    params.append(pipeline_id)
                
                if cache_type:
                    query += " AND cache_type = ?"
                    params.append(cache_type.value)
                
                if content_hash:
                    query += " AND content_hash = ?"
                    params.append(content_hash)
                
                cursor = conn.execute(query, params)
                return [self._row_to_entry(row) for row in cursor.fetchall()]
    
    def update_access(self, entry_id: str):
        """Update access statistics"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE cache_entries 
                    SET last_accessed_at = ?, access_count = access_count + 1
                    WHERE id = ?
                """, (datetime.now(), entry_id))
    
    def delete_entry(self, entry_id: str):
        """Delete cache entry"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                # Get file path before deletion
                cursor = conn.execute("SELECT file_path FROM cache_entries WHERE id = ?", (entry_id,))
                row = cursor.fetchone()
                
                if row and os.path.exists(row[0]):
                    try:
                        os.remove(row[0])
                    except OSError as e:
                        logger.warning(f"Failed to delete cache file {row[0]}: {e}")
                
                conn.execute("DELETE FROM cache_entries WHERE id = ?", (entry_id,))
    
    def get_expired_entries(self) -> List[CacheEntry]:
        """Get all expired cache entries"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM cache_entries 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                """, (datetime.now(),))
                
                return [self._row_to_entry(row) for row in cursor.fetchall()]
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_entries,
                        SUM(size_bytes) as total_size,
                        AVG(size_bytes) as avg_size,
                        MAX(size_bytes) as max_size,
                        MIN(size_bytes) as min_size,
                        SUM(access_count) as total_accesses
                    FROM cache_entries
                """)
                
                stats = cursor.fetchone()
                
                # Get type distribution
                cursor = conn.execute("""
                    SELECT cache_type, COUNT(*) as count, SUM(size_bytes) as size
                    FROM cache_entries GROUP BY cache_type
                """)
                
                type_stats = {row[0]: {"count": row[1], "size": row[2]} 
                             for row in cursor.fetchall()}
                
                return {
                    "total_entries": stats[0] or 0,
                    "total_size_bytes": stats[1] or 0,
                    "average_size_bytes": stats[2] or 0,
                    "max_size_bytes": stats[3] or 0,
                    "min_size_bytes": stats[4] or 0,
                    "total_accesses": stats[5] or 0,
                    "type_distribution": type_stats
                }
    
    def _row_to_entry(self, row) -> CacheEntry:
        """Convert database row to CacheEntry"""
        cache_key_obj = CacheKey(
            key=row['cache_key'].split(':')[-1],
            pipeline_id=row['pipeline_id'],
            stage_name=row['stage_name'],
            content_hash=row['content_hash'],
            dependencies=json.loads(row['dependencies']),
            cache_type=CacheType(row['cache_type']),
            tags=json.loads(row['tags']) if row['tags'] else []
        )
        
        return CacheEntry(
            id=row['id'],
            cache_key=cache_key_obj,
            file_path=row['file_path'],
            size_bytes=row['size_bytes'],
            compression_type=CompressionType(row['compression_type']),
            created_at=datetime.fromisoformat(row['created_at']),
            last_accessed_at=datetime.fromisoformat(row['last_accessed_at']),
            access_count=row['access_count'],
            ttl_seconds=row['ttl_seconds'],
            expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )

class CacheManager:
    """Main cache management interface"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.storage = CacheStorage(self.config.get('cache_dir'))
        
        # Cache configuration
        self.max_cache_size_gb = self.config.get('max_cache_size_gb', 10)
        self.default_ttl_hours = self.config.get('default_ttl_hours', 24)
        self.cleanup_interval_minutes = self.config.get('cleanup_interval_minutes', 30)
        self.compression_type = CompressionType(self.config.get('compression', 'gzip'))
        
        # Cache strategy
        self.strategy = CacheStrategy(self.config.get('strategy', 'hybrid'))
        
        self.lock = threading.RLock()
        self.cleanup_thread = None
        self.running = False
        
        # Redis integration for distributed caching
        self.redis_client = None
        if REDIS_AVAILABLE and self.config.get('redis_url'):
            try:
                import redis
                self.redis_client = redis.from_url(self.config['redis_url'])
                logger.info("Connected to Redis for distributed cache coordination")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
    
    def start(self):
        """Start cache manager services"""
        if self.running:
            return
        
        self.running = True
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("Cache manager started")
    
    def stop(self):
        """Stop cache manager services"""
        self.running = False
        
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        
        logger.info("Cache manager stopped")
    
    def store(self, key: str, source_path: str, pipeline_id: str, stage_name: str,
              cache_type: CacheType = CacheType.CUSTOM,
              dependencies: List[str] = None, ttl_hours: Optional[int] = None,
              tags: List[str] = None, metadata: Dict = None) -> bool:
        """Store content in cache"""
        try:
            with self.lock:
                # Calculate content hash
                if os.path.isfile(source_path):
                    content_hash = HashCalculator.hash_file(source_path)
                else:
                    content_hash = HashCalculator.hash_directory(source_path)
                
                # Create cache key
                cache_key = CacheKey(
                    key=key,
                    pipeline_id=pipeline_id,
                    stage_name=stage_name,
                    content_hash=content_hash,
                    dependencies=dependencies or [],
                    cache_type=cache_type,
                    tags=tags or []
                )
                
                # Check if already cached
                existing_entry = self.storage.get_entry(cache_key.to_string())
                if existing_entry and not existing_entry.is_expired:
                    logger.debug(f"Cache entry already exists: {cache_key.to_string()}")
                    return True
                
                # Generate unique filename
                cache_id = str(uuid.uuid4())
                cache_filename = f"{cache_id}.cache"
                cache_file_path = self.storage.data_dir / cache_filename
                
                # Compress and store
                if os.path.isfile(source_path):
                    size = CompressionManager.compress_file(
                        source_path, str(cache_file_path), self.compression_type
                    )
                else:
                    size = CompressionManager.compress_directory(
                        source_path, str(cache_file_path), self.compression_type
                    )
                
                # Create cache entry
                now = datetime.now()
                ttl_seconds = (ttl_hours or self.default_ttl_hours) * 3600
                
                entry = CacheEntry(
                    id=cache_id,
                    cache_key=cache_key,
                    file_path=str(cache_file_path),
                    size_bytes=size,
                    compression_type=self.compression_type,
                    created_at=now,
                    last_accessed_at=now,
                    access_count=0,
                    ttl_seconds=ttl_seconds,
                    metadata=metadata or {}
                )
                
                # Store in database
                self.storage.store_entry(entry)
                
                # Notify distributed cache
                if self.redis_client:
                    self._notify_cache_update(cache_key.to_string())
                
                logger.info(f"Stored cache entry: {cache_key.to_string()} ({size} bytes)")
                
                # Trigger cleanup if needed
                self._check_cache_size()
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to store cache entry: {e}")
            return False
    
    def retrieve(self, key: str, target_path: str, pipeline_id: str, stage_name: str,
                content_hash: Optional[str] = None, dependencies: List[str] = None) -> bool:
        """Retrieve content from cache"""
        try:
            with self.lock:
                # Create cache key for lookup
                lookup_hash = content_hash or "any"
                cache_key = CacheKey(
                    key=key,
                    pipeline_id=pipeline_id,
                    stage_name=stage_name,
                    content_hash=lookup_hash,
                    dependencies=dependencies or [],
                    cache_type=CacheType.CUSTOM
                )
                
                # Try exact match first
                entry = self.storage.get_entry(cache_key.to_string())
                
                # If not found and no specific hash provided, try content-based lookup
                if not entry and not content_hash:
                    # Find entries with matching dependencies
                    entries = self.storage.find_entries(pipeline_id=pipeline_id)
                    for candidate in entries:
                        if (candidate.cache_key.key == key and 
                            candidate.cache_key.stage_name == stage_name and
                            not candidate.is_expired):
                            # Check dependency compatibility
                            if self._dependencies_compatible(candidate.cache_key.dependencies, dependencies or []):
                                entry = candidate
                                break
                
                if not entry:
                    logger.debug(f"Cache miss for key: {key}")
                    return False
                
                if entry.is_expired:
                    logger.debug(f"Cache entry expired: {key}")
                    self.storage.delete_entry(entry.id)
                    return False
                
                # Check if cached file exists
                if not os.path.exists(entry.file_path):
                    logger.warning(f"Cache file missing: {entry.file_path}")
                    self.storage.delete_entry(entry.id)
                    return False
                
                # Decompress and restore
                if os.path.isdir(target_path) or target_path.endswith('/'):
                    # Directory target
                    os.makedirs(target_path, exist_ok=True)
                    CompressionManager.decompress_directory(
                        entry.file_path, target_path, entry.compression_type
                    )
                else:
                    # File target
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    CompressionManager.decompress_file(
                        entry.file_path, target_path, entry.compression_type
                    )
                
                # Update access statistics
                self.storage.update_access(entry.id)
                
                logger.info(f"Cache hit for key: {key} (age: {entry.age_seconds}s)")
                return True
                
        except Exception as e:
            logger.error(f"Failed to retrieve cache entry: {e}")
            return False
    
    def invalidate(self, key: Optional[str] = None, pipeline_id: Optional[str] = None,
                  cache_type: Optional[CacheType] = None, tags: List[str] = None) -> int:
        """Invalidate cache entries"""
        try:
            with self.lock:
                entries = self.storage.find_entries(pipeline_id=pipeline_id, cache_type=cache_type)
                
                count = 0
                for entry in entries:
                    should_delete = False
                    
                    if key and entry.cache_key.key == key:
                        should_delete = True
                    elif tags and any(tag in entry.cache_key.tags for tag in tags):
                        should_delete = True
                    elif not key and not tags:
                        should_delete = True
                    
                    if should_delete:
                        self.storage.delete_entry(entry.id)
                        count += 1
                
                logger.info(f"Invalidated {count} cache entries")
                return count
                
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return 0
    
    def get_cache_key(self, key: str, pipeline_id: str, stage_name: str,
                     source_path: str, dependencies: List[str] = None) -> str:
        """Generate cache key for given parameters"""
        # Calculate content hash
        if os.path.isfile(source_path):
            content_hash = HashCalculator.hash_file(source_path)
        else:
            content_hash = HashCalculator.hash_directory(source_path)
        
        cache_key = CacheKey(
            key=key,
            pipeline_id=pipeline_id,
            stage_name=stage_name,
            content_hash=content_hash,
            dependencies=dependencies or [],
            cache_type=CacheType.CUSTOM
        )
        
        return cache_key.to_string()
    
    def get_statistics(self) -> Dict:
        """Get cache statistics"""
        stats = self.storage.get_cache_stats()
        
        # Add additional metrics
        stats.update({
            "cache_hit_rate": self._calculate_hit_rate(),
            "cache_size_gb": stats["total_size_bytes"] / (1024**3),
            "max_cache_size_gb": self.max_cache_size_gb,
            "cleanup_interval_minutes": self.cleanup_interval_minutes,
            "compression_type": self.compression_type.value,
            "strategy": self.strategy.value
        })
        
        return stats
    
    def cleanup_expired(self) -> int:
        """Clean up expired cache entries"""
        try:
            expired_entries = self.storage.get_expired_entries()
            count = 0
            
            for entry in expired_entries:
                self.storage.delete_entry(entry.id)
                count += 1
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired cache entries")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired entries: {e}")
            return 0
    
    def _dependencies_compatible(self, cached_deps: List[str], 
                               current_deps: List[str]) -> bool:
        """Check if dependencies are compatible for cache reuse"""
        # Simple exact match for now
        return set(cached_deps) == set(current_deps)
    
    def _check_cache_size(self):
        """Check cache size and cleanup if needed"""
        stats = self.storage.get_cache_stats()
        current_size_gb = stats["total_size_bytes"] / (1024**3)
        
        if current_size_gb > self.max_cache_size_gb:
            logger.info(f"Cache size ({current_size_gb:.2f} GB) exceeds limit ({self.max_cache_size_gb} GB)")
            self._cleanup_by_strategy()
    
    def _cleanup_by_strategy(self):
        """Cleanup cache entries based on strategy"""
        if self.strategy == CacheStrategy.LRU:
            self._cleanup_lru()
        elif self.strategy == CacheStrategy.LFU:
            self._cleanup_lfu()
        elif self.strategy == CacheStrategy.SIZE_BASED:
            self._cleanup_by_size()
        else:
            # Hybrid strategy
            self._cleanup_hybrid()
    
    def _cleanup_lru(self):
        """Cleanup least recently used entries"""
        # Implementation would sort by last_accessed_at and remove oldest
        pass
    
    def _cleanup_lfu(self):
        """Cleanup least frequently used entries"""
        # Implementation would sort by access_count and remove least used
        pass
    
    def _cleanup_by_size(self):
        """Cleanup largest entries first"""
        # Implementation would sort by size_bytes and remove largest
        pass
    
    def _cleanup_hybrid(self):
        """Hybrid cleanup strategy"""
        # Combine multiple factors: age, frequency, size
        pass
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        # This would require additional tracking
        return 0.0
    
    def _notify_cache_update(self, cache_key: str):
        """Notify distributed cache of update"""
        if self.redis_client:
            try:
                self.redis_client.publish("qenex_cache_updates", cache_key)
            except Exception as e:
                logger.warning(f"Failed to notify cache update: {e}")
    
    def _cleanup_loop(self):
        """Background cleanup loop"""
        while self.running:
            try:
                self.cleanup_expired()
                time.sleep(self.cleanup_interval_minutes * 60)
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                time.sleep(60)

# High-level cache decorators and utilities
class CacheDecorator:
    """Decorators for automatic caching"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def cache_result(self, key: str, pipeline_id: str, stage_name: str,
                    ttl_hours: int = 24, cache_type: CacheType = CacheType.CUSTOM):
        """Decorator to cache function results"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Generate cache key based on function arguments
                args_hash = HashCalculator.hash_string(str(args) + str(kwargs))
                cache_key = f"{key}:{args_hash}"
                
                # Try to retrieve from cache
                temp_dir = tempfile.mkdtemp()
                cache_file = os.path.join(temp_dir, "result.pkl")
                
                if self.cache_manager.retrieve(cache_key, cache_file, pipeline_id, stage_name):
                    try:
                        with open(cache_file, 'rb') as f:
                            result = pickle.load(f)
                        shutil.rmtree(temp_dir)
                        logger.debug(f"Function result retrieved from cache: {cache_key}")
                        return result
                    except Exception as e:
                        logger.warning(f"Failed to load cached result: {e}")
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                
                try:
                    with open(cache_file, 'wb') as f:
                        pickle.dump(result, f)
                    
                    self.cache_manager.store(
                        cache_key, cache_file, pipeline_id, stage_name,
                        cache_type=cache_type, ttl_hours=ttl_hours
                    )
                    logger.debug(f"Function result cached: {cache_key}")
                except Exception as e:
                    logger.warning(f"Failed to cache result: {e}")
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                
                return result
            return wrapper
        return decorator

# CLI interface
class CacheManagerCLI:
    """Command-line interface for cache management"""
    
    def __init__(self):
        self.cache_manager = CacheManager()
    
    def store(self, key: str, source: str, pipeline_id: str, stage_name: str,
             cache_type: str = "custom", ttl_hours: int = 24):
        """Store content in cache"""
        success = self.cache_manager.store(
            key, source, pipeline_id, stage_name,
            CacheType(cache_type), ttl_hours=ttl_hours
        )
        
        if success:
            print(f"Successfully cached: {key}")
        else:
            print(f"Failed to cache: {key}")
    
    def retrieve(self, key: str, target: str, pipeline_id: str, stage_name: str):
        """Retrieve content from cache"""
        success = self.cache_manager.retrieve(key, target, pipeline_id, stage_name)
        
        if success:
            print(f"Successfully retrieved: {key}")
        else:
            print(f"Cache miss: {key}")
    
    def stats(self):
        """Show cache statistics"""
        stats = self.cache_manager.get_statistics()
        print(json.dumps(stats, indent=2))
    
    def cleanup(self):
        """Clean up expired entries"""
        count = self.cache_manager.cleanup_expired()
        print(f"Cleaned up {count} expired entries")
    
    def invalidate(self, key: Optional[str] = None, pipeline_id: Optional[str] = None):
        """Invalidate cache entries"""
        count = self.cache_manager.invalidate(key=key, pipeline_id=pipeline_id)
        print(f"Invalidated {count} cache entries")

# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='QENEX Cache Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Store command
    store_parser = subparsers.add_parser('store', help='Store in cache')
    store_parser.add_argument('key', help='Cache key')
    store_parser.add_argument('source', help='Source path')
    store_parser.add_argument('pipeline_id', help='Pipeline ID')
    store_parser.add_argument('stage_name', help='Stage name')
    store_parser.add_argument('--type', default='custom', help='Cache type')
    store_parser.add_argument('--ttl', type=int, default=24, help='TTL in hours')
    
    # Retrieve command
    retrieve_parser = subparsers.add_parser('retrieve', help='Retrieve from cache')
    retrieve_parser.add_argument('key', help='Cache key')
    retrieve_parser.add_argument('target', help='Target path')
    retrieve_parser.add_argument('pipeline_id', help='Pipeline ID')
    retrieve_parser.add_argument('stage_name', help='Stage name')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean expired entries')
    
    # Invalidate command
    invalidate_parser = subparsers.add_parser('invalidate', help='Invalidate entries')
    invalidate_parser.add_argument('--key', help='Cache key to invalidate')
    invalidate_parser.add_argument('--pipeline-id', help='Pipeline ID to invalidate')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = CacheManagerCLI()
    
    if args.command == 'store':
        cli.store(args.key, args.source, args.pipeline_id, args.stage_name,
                 args.type, args.ttl)
    elif args.command == 'retrieve':
        cli.retrieve(args.key, args.target, args.pipeline_id, args.stage_name)
    elif args.command == 'stats':
        cli.stats()
    elif args.command == 'cleanup':
        cli.cleanup()
    elif args.command == 'invalidate':
        cli.invalidate(args.key, args.pipeline_id)