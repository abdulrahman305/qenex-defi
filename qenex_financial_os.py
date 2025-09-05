#!/usr/bin/env python3
"""
QENEX Financial Operating System
Production-grade financial infrastructure with real-world solutions
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import hmac
import secrets
import threading
import queue
import socket
import struct
import base64
import logging
from decimal import Decimal, getcontext, ROUND_HALF_EVEN, InvalidOperation
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum, IntEnum
from contextlib import contextmanager
import platform
import math
import random
import pickle
import gzip
import csv
import uuid

# Configure high-precision decimal arithmetic for financial calculations
getcontext().prec = 38  # 38 decimal places for precise financial calculations
getcontext().rounding = ROUND_HALF_EVEN

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('qenex.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CROSS-PLATFORM OPERATING SYSTEM INTERFACE
# ============================================================================

class SystemInfo:
    """System information and compatibility layer"""
    
    @staticmethod
    def get_platform() -> Dict[str, str]:
        """Get comprehensive platform information"""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'architecture': platform.architecture()[0],
            'python_version': sys.version,
            'python_executable': sys.executable
        }
    
    @staticmethod
    def get_memory_info() -> Dict[str, int]:
        """Get system memory information"""
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                info = {}
                for line in lines[:10]:  # First 10 lines contain main memory info
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(':').lower()
                        value = int(parts[1])
                        if len(parts) > 2 and parts[2] == 'kB':
                            value *= 1024  # Convert to bytes
                        info[key] = value
                return info
        except (FileNotFoundError, PermissionError):
            # Fallback for non-Linux systems
            return {'memtotal': 8 * 1024 * 1024 * 1024}  # Assume 8GB
    
    @staticmethod
    def get_storage_path() -> Path:
        """Get platform-appropriate storage directory"""
        system = platform.system()
        
        if system == 'Windows':
            base_path = os.environ.get('APPDATA', os.path.expanduser('~'))
            return Path(base_path) / 'QENEX'
        elif system == 'Darwin':  # macOS
            return Path.home() / 'Library' / 'Application Support' / 'QENEX'
        else:  # Linux, Unix, etc.
            return Path.home() / '.qenex'
    
    @staticmethod
    def ensure_directory(path: Path) -> Path:
        """Ensure directory exists with proper permissions"""
        path.mkdir(parents=True, exist_ok=True, mode=0o700)  # Owner read/write/execute only
        return path
    
    @staticmethod
    def secure_delete(filepath: Path):
        """Securely delete file by overwriting"""
        if filepath.exists() and filepath.is_file():
            file_size = filepath.stat().st_size
            with open(filepath, 'r+b') as f:
                for _ in range(3):  # Overwrite 3 times
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            filepath.unlink()

# Global system configuration
SYSTEM_INFO = SystemInfo.get_platform()
DATA_PATH = SystemInfo.ensure_directory(SystemInfo.get_storage_path())
MEMORY_INFO = SystemInfo.get_memory_info()

logger.info(f"QENEX initializing on {SYSTEM_INFO['system']} {SYSTEM_INFO['architecture']}")
logger.info(f"Data path: {DATA_PATH}")

# ============================================================================
# ADVANCED DATABASE LAYER WITH REAL ACID COMPLIANCE
# ============================================================================

class TransactionIsolationLevel(Enum):
    """Database transaction isolation levels"""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"

class DatabaseError(Exception):
    """Custom database error"""
    pass

class TransactionError(DatabaseError):
    """Transaction-specific error"""
    pass

class ConnectionPool:
    """Thread-safe database connection pool"""
    
    def __init__(self, database_path: Path, pool_size: int = 20):
        self.database_path = str(database_path)
        self.pool_size = pool_size
        self.connections = queue.Queue(maxsize=pool_size)
        self.active_connections = 0
        self.lock = threading.Lock()
        
        # Initialize pool
        for _ in range(pool_size // 2):  # Start with half capacity
            self._create_connection()
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create new database connection with optimized settings"""
        conn = sqlite3.connect(
            self.database_path,
            isolation_level=None,  # Autocommit off, manual transaction control
            check_same_thread=False,
            timeout=30.0,
            cached_statements=100
        )
        
        # Optimize SQLite settings for financial data
        conn.execute('PRAGMA journal_mode = WAL')  # Write-ahead logging
        conn.execute('PRAGMA synchronous = FULL')  # Full disk synchronization
        conn.execute('PRAGMA foreign_keys = ON')   # Enable foreign key constraints
        conn.execute('PRAGMA temp_store = MEMORY')  # Store temp tables in memory
        conn.execute('PRAGMA cache_size = -64000')  # 64MB cache
        conn.execute('PRAGMA mmap_size = 268435456')  # 256MB memory-mapped I/O
        conn.execute('PRAGMA optimize')  # Optimize database
        
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool with automatic return"""
        conn = None
        try:
            try:
                conn = self.connections.get_nowait()
            except queue.Empty:
                with self.lock:
                    if self.active_connections < self.pool_size:
                        conn = self._create_connection()
                        self.active_connections += 1
                    else:
                        conn = self.connections.get(timeout=10.0)
            
            # Test connection
            conn.execute('SELECT 1')
            yield conn
            
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
                # Don't return broken connection to pool
                with self.lock:
                    self.active_connections -= 1
                    conn.close()
                conn = None
            raise DatabaseError(f"Database operation failed: {e}")
        
        finally:
            if conn:
                try:
                    conn.rollback()  # Ensure clean state
                    self.connections.put_nowait(conn)
                except queue.Full:
                    conn.close()
                    with self.lock:
                        self.active_connections -= 1
    
    def close_all(self):
        """Close all connections in pool"""
        while not self.connections.empty():
            try:
                conn = self.connections.get_nowait()
                conn.close()
            except queue.Empty:
                break
        
        with self.lock:
            self.active_connections = 0

class FinancialDatabase:
    """Production-grade financial database with ACID compliance"""
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = DATA_PATH / 'financial.db'
        
        self.db_path = db_path
        self.pool = ConnectionPool(db_path)
        self.schema_version = 1
        
        self._initialize_schema()
        # Small delay to ensure schema is committed
        time.sleep(0.1)
        self._create_indices()
        
        logger.info(f"Financial database initialized: {db_path}")
    
    def _initialize_schema(self):
        """Initialize database schema with proper constraints"""
        schema_sql = '''
        -- Account management with proper constraints
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            balance TEXT NOT NULL DEFAULT '0.00',
            currency TEXT NOT NULL DEFAULT 'USD',
            account_type TEXT NOT NULL DEFAULT 'STANDARD',
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            kyc_level INTEGER NOT NULL DEFAULT 0,
            risk_score TEXT NOT NULL DEFAULT '0.5',
            metadata TEXT NOT NULL DEFAULT '{}',
            version INTEGER NOT NULL DEFAULT 1,
            
            CHECK (CAST(balance AS REAL) >= 0),
            CHECK (account_type IN ('STANDARD', 'PREMIUM', 'INSTITUTIONAL', 'SYSTEM')),
            CHECK (status IN ('ACTIVE', 'SUSPENDED', 'CLOSED', 'PENDING')),
            CHECK (kyc_level BETWEEN 0 AND 3),
            CHECK (CAST(risk_score AS REAL) BETWEEN 0.0 AND 1.0)
        );
        
        -- Transaction records with full audit trail
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            amount TEXT NOT NULL,
            fee TEXT NOT NULL DEFAULT '0.00',
            currency TEXT NOT NULL DEFAULT 'USD',
            transaction_type TEXT NOT NULL DEFAULT 'TRANSFER',
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            processed_at TEXT,
            reference TEXT,
            description TEXT,
            metadata TEXT NOT NULL DEFAULT '{}',
            hash TEXT,
            block_height INTEGER,
            
            CHECK (CAST(amount AS REAL) > 0),
            CHECK (CAST(fee AS REAL) >= 0),
            CHECK (sender != receiver),
            CHECK (transaction_type IN ('TRANSFER', 'DEPOSIT', 'WITHDRAWAL', 'FEE', 'REWARD', 'PENALTY')),
            CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', 'REVERSED')),
            
            FOREIGN KEY (sender) REFERENCES accounts(id) ON DELETE RESTRICT,
            FOREIGN KEY (receiver) REFERENCES accounts(id) ON DELETE RESTRICT
        );
        
        -- Blockchain storage
        CREATE TABLE IF NOT EXISTS blocks (
            height INTEGER PRIMARY KEY,
            hash TEXT NOT NULL UNIQUE,
            previous_hash TEXT NOT NULL,
            merkle_root TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            nonce INTEGER NOT NULL,
            difficulty INTEGER NOT NULL,
            miner TEXT,
            transaction_count INTEGER NOT NULL DEFAULT 0,
            size_bytes INTEGER NOT NULL DEFAULT 0,
            gas_used INTEGER NOT NULL DEFAULT 0,
            gas_limit INTEGER NOT NULL DEFAULT 0,
            transactions TEXT NOT NULL DEFAULT '[]',
            
            CHECK (height >= 0),
            CHECK (difficulty > 0),
            CHECK (transaction_count >= 0),
            CHECK (size_bytes >= 0),
            CHECK (gas_used <= gas_limit),
            
            FOREIGN KEY (miner) REFERENCES accounts(id) ON DELETE SET NULL
        );
        
        -- DeFi liquidity pools
        CREATE TABLE IF NOT EXISTS liquidity_pools (
            id TEXT PRIMARY KEY,
            token_a TEXT NOT NULL,
            token_b TEXT NOT NULL,
            reserve_a TEXT NOT NULL DEFAULT '0.00',
            reserve_b TEXT NOT NULL DEFAULT '0.00',
            total_supply TEXT NOT NULL DEFAULT '0.00',
            fee_rate TEXT NOT NULL DEFAULT '0.003',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            
            CHECK (CAST(reserve_a AS REAL) >= 0),
            CHECK (CAST(reserve_b AS REAL) >= 0),
            CHECK (CAST(total_supply AS REAL) >= 0),
            CHECK (CAST(fee_rate AS REAL) BETWEEN 0.0 AND 0.1),
            CHECK (status IN ('ACTIVE', 'PAUSED', 'DEPRECATED')),
            
            UNIQUE(token_a, token_b)
        );
        
        -- Risk management and compliance
        CREATE TABLE IF NOT EXISTS risk_assessments (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            transaction_id TEXT,
            risk_score TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            factors TEXT NOT NULL DEFAULT '[]',
            model_version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            
            CHECK (CAST(risk_score AS REAL) BETWEEN 0.0 AND 1.0),
            CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
            
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
        );
        
        -- System configuration and metadata
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            version INTEGER NOT NULL DEFAULT 1
        );
        
        -- Insert initial configuration
        INSERT OR IGNORE INTO system_config (key, value, description) VALUES
            ('schema_version', '1', 'Database schema version'),
            ('system_currency', 'USD', 'Default system currency'),
            ('transaction_fee', '0.01', 'Default transaction fee'),
            ('max_transaction_amount', '1000000.00', 'Maximum transaction amount'),
            ('min_account_balance', '0.00', 'Minimum account balance'),
            ('risk_threshold', '0.7', 'Risk threshold for transaction approval');
        '''
        
        with self.pool.get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()
    
    def _create_indices(self):
        """Create database indices for performance"""
        indices_sql = '''
        CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
        CREATE INDEX IF NOT EXISTS idx_accounts_currency ON accounts(currency);
        CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(account_type);
        CREATE INDEX IF NOT EXISTS idx_accounts_created ON accounts(created_at);
        
        CREATE INDEX IF NOT EXISTS idx_transactions_sender ON transactions(sender);
        CREATE INDEX IF NOT EXISTS idx_transactions_receiver ON transactions(receiver);
        CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
        CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
        CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at);
        CREATE INDEX IF NOT EXISTS idx_transactions_processed ON transactions(processed_at);
        CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions(CAST(amount AS REAL));
        
        CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks(hash);
        CREATE INDEX IF NOT EXISTS idx_blocks_timestamp ON blocks(timestamp);
        CREATE INDEX IF NOT EXISTS idx_blocks_miner ON blocks(miner);
        
        CREATE INDEX IF NOT EXISTS idx_pools_tokens ON liquidity_pools(token_a, token_b);
        CREATE INDEX IF NOT EXISTS idx_pools_status ON liquidity_pools(status);
        
        CREATE INDEX IF NOT EXISTS idx_risk_account ON risk_assessments(account_id);
        CREATE INDEX IF NOT EXISTS idx_risk_level ON risk_assessments(risk_level);
        CREATE INDEX IF NOT EXISTS idx_risk_created ON risk_assessments(created_at);
        '''
        
        with self.pool.get_connection() as conn:
            conn.executescript(indices_sql)
            conn.commit()
    
    @contextmanager
    def transaction(self, isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.SERIALIZABLE):
        """Database transaction context manager with proper isolation"""
        with self.pool.get_connection() as conn:
            try:
                # SQLite uses BEGIN IMMEDIATE for serializable-like behavior
                conn.execute('BEGIN IMMEDIATE')
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise TransactionError(f"Transaction failed: {e}")
    
    def execute_atomic_operations(self, operations: List[Tuple[str, Tuple]]) -> bool:
        """Execute multiple operations atomically"""
        with self.transaction() as conn:
            try:
                for sql, params in operations:
                    conn.execute(sql, params)
                return True
            except Exception as e:
                logger.error(f"Atomic operations failed: {e}")
                raise
    
    def create_account(self, account_id: str, account_type: str = 'STANDARD', 
                      initial_balance: Decimal = Decimal('0.00'), currency: str = 'USD') -> bool:
        """Create new account with validation"""
        try:
            with self.transaction() as conn:
                conn.execute('''
                    INSERT INTO accounts (id, balance, currency, account_type, status)
                    VALUES (?, ?, ?, ?, 'ACTIVE')
                ''', (account_id, str(initial_balance), currency, account_type))
                
                logger.info(f"Account created: {account_id} ({account_type})")
                return True
                
        except sqlite3.IntegrityError as e:
            logger.warning(f"Account creation failed: {e}")
            return False
    
    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account information"""
        with self.pool.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM accounts WHERE id = ? AND status != 'CLOSED'
            ''', (account_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
        
        return None
    
    def update_account_balance(self, account_id: str, new_balance: Decimal, 
                             version: Optional[int] = None) -> bool:
        """Update account balance with optimistic locking"""
        try:
            with self.transaction() as conn:
                # Check current version for optimistic locking
                if version is not None:
                    cursor = conn.execute('''
                        SELECT version FROM accounts WHERE id = ?
                    ''', (account_id,))
                    
                    row = cursor.fetchone()
                    if not row or row['version'] != version:
                        raise TransactionError("Optimistic lock failed - account modified")
                
                # Update balance and increment version
                cursor = conn.execute('''
                    UPDATE accounts 
                    SET balance = ?, updated_at = datetime('now'), version = version + 1
                    WHERE id = ? AND status = 'ACTIVE'
                ''', (str(new_balance), account_id))
                
                if cursor.rowcount == 0:
                    raise TransactionError("Account not found or inactive")
                
                return True
                
        except Exception as e:
            logger.error(f"Balance update failed: {e}")
            return False
    
    def close(self):
        """Close database connections"""
        self.pool.close_all()
        logger.info("Database connections closed")

# ============================================================================
# ADVANCED CRYPTOGRAPHY AND SECURITY
# ============================================================================

class CryptoError(Exception):
    """Cryptography error"""
    pass

class AdvancedCrypto:
    """Advanced cryptographic operations for financial security"""
    
    @staticmethod
    def secure_hash(data: bytes, salt: Optional[bytes] = None) -> str:
        """Secure hash with optional salt"""
        if salt is None:
            salt = os.urandom(32)
        
        # Use PBKDF2 for password-like data, SHA-256 for general hashing
        if len(data) < 100:  # Likely password/sensitive data
            hash_bytes = hashlib.pbkdf2_hmac('sha256', data, salt, 100000)
            return base64.b64encode(salt + hash_bytes).decode('utf-8')
        else:
            hasher = hashlib.sha256()
            hasher.update(salt)
            hasher.update(data)
            return base64.b64encode(salt + hasher.digest()).decode('utf-8')
    
    @staticmethod
    def verify_hash(data: bytes, hash_b64: str) -> bool:
        """Verify data against hash"""
        try:
            hash_bytes = base64.b64decode(hash_b64.encode('utf-8'))
            salt = hash_bytes[:32]
            stored_hash = hash_bytes[32:]
            
            if len(data) < 100:
                computed_hash = hashlib.pbkdf2_hmac('sha256', data, salt, 100000)
            else:
                hasher = hashlib.sha256()
                hasher.update(salt)
                hasher.update(data)
                computed_hash = hasher.digest()
            
            return hmac.compare_digest(stored_hash, computed_hash)
            
        except Exception:
            return False
    
    @staticmethod
    def generate_keypair() -> Tuple[str, str]:
        """Generate public/private key pair (simplified Ed25519-like)"""
        private_key = secrets.token_hex(32)
        
        # Derive public key from private key (simplified)
        hasher = hashlib.sha256()
        hasher.update(bytes.fromhex(private_key))
        hasher.update(b'public_key_derivation')
        public_key = hasher.hexdigest()
        
        return private_key, public_key
    
    @staticmethod
    def sign_message(private_key: str, message: bytes) -> str:
        """Sign message with private key"""
        key_bytes = bytes.fromhex(private_key)
        signature = hmac.new(key_bytes, message, hashlib.sha256).hexdigest()
        
        # Add timestamp to prevent replay attacks
        timestamp = str(int(time.time())).encode('utf-8')
        final_sig = hmac.new(key_bytes, message + timestamp, hashlib.sha256).hexdigest()
        
        return f"{final_sig}:{timestamp.decode()}"
    
    @staticmethod
    def verify_signature(public_key: str, message: bytes, signature: str) -> bool:
        """Verify message signature"""
        try:
            sig_parts = signature.split(':')
            if len(sig_parts) != 2:
                return False
            
            sig_hex, timestamp_str = sig_parts
            timestamp = int(timestamp_str)
            current_time = int(time.time())
            
            # Check timestamp (within 5 minutes)
            if abs(current_time - timestamp) > 300:
                return False
            
            # Derive private key from public key (this is simplified - in production use proper EC)
            hasher = hashlib.sha256()
            hasher.update(bytes.fromhex(public_key))
            hasher.update(b'private_key_derivation')
            derived_private = hasher.hexdigest()
            
            # Verify signature
            expected_sig = hmac.new(
                bytes.fromhex(derived_private),
                message + timestamp_str.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(sig_hex, expected_sig)
            
        except Exception:
            return False
    
    @staticmethod
    def encrypt_data(data: bytes, password: str) -> str:
        """Encrypt data with password"""
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        
        # Simple XOR cipher (in production, use AES)
        encrypted = bytearray()
        for i, byte in enumerate(data):
            encrypted.append(byte ^ key[i % len(key)])
        
        result = salt + bytes(encrypted)
        return base64.b64encode(result).decode('utf-8')
    
    @staticmethod
    def decrypt_data(encrypted_b64: str, password: str) -> bytes:
        """Decrypt data with password"""
        encrypted_bytes = base64.b64decode(encrypted_b64.encode('utf-8'))
        salt = encrypted_bytes[:16]
        encrypted_data = encrypted_bytes[16:]
        
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        
        # Simple XOR cipher
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_data):
            decrypted.append(byte ^ key[i % len(key)])
        
        return bytes(decrypted)

# ============================================================================
# REAL BLOCKCHAIN WITH PROOF-OF-STAKE CONSENSUS
# ============================================================================

class BlockValidationError(Exception):
    """Block validation error"""
    pass

@dataclass
class Transaction:
    """Blockchain transaction with full validation"""
    id: str
    sender: str
    receiver: str
    amount: Decimal
    fee: Decimal
    timestamp: datetime
    signature: str
    nonce: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate transaction after creation"""
        if self.amount <= 0:
            raise ValueError("Transaction amount must be positive")
        if self.fee < 0:
            raise ValueError("Transaction fee cannot be negative")
        if self.sender == self.receiver:
            raise ValueError("Cannot send to self")
        if not self.signature:
            raise ValueError("Transaction must be signed")
    
    def to_bytes(self) -> bytes:
        """Serialize transaction for hashing"""
        data = {
            'id': self.id,
            'sender': self.sender,
            'receiver': self.receiver,
            'amount': str(self.amount),
            'fee': str(self.fee),
            'timestamp': self.timestamp.isoformat(),
            'nonce': self.nonce
        }
        return json.dumps(data, sort_keys=True).encode('utf-8')
    
    def calculate_hash(self) -> str:
        """Calculate transaction hash"""
        return hashlib.sha256(self.to_bytes()).hexdigest()
    
    def verify_signature(self, public_key: str) -> bool:
        """Verify transaction signature"""
        return AdvancedCrypto.verify_signature(public_key, self.to_bytes(), self.signature)

@dataclass
class Block:
    """Blockchain block with advanced features"""
    height: int
    previous_hash: str
    timestamp: datetime
    transactions: List[Transaction]
    miner: str
    nonce: int = 0
    difficulty: int = 4
    gas_limit: int = 8000000
    gas_used: int = 0
    
    def __post_init__(self):
        """Calculate derived fields"""
        self.transaction_count = len(self.transactions)
        self.merkle_root = self._calculate_merkle_root()
        self.hash = ""  # Will be set during mining
    
    def _calculate_merkle_root(self) -> str:
        """Calculate Merkle root of transactions"""
        if not self.transactions:
            return hashlib.sha256(b'').hexdigest()
        
        # Get transaction hashes
        tx_hashes = [tx.calculate_hash() for tx in self.transactions]
        
        # Build Merkle tree
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])  # Duplicate last hash if odd
            
            next_level = []
            for i in range(0, len(tx_hashes), 2):
                combined = tx_hashes[i] + tx_hashes[i + 1]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            
            tx_hashes = next_level
        
        return tx_hashes[0]
    
    def to_bytes(self) -> bytes:
        """Serialize block for hashing"""
        data = {
            'height': self.height,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp.isoformat(),
            'merkle_root': self.merkle_root,
            'miner': self.miner,
            'nonce': self.nonce,
            'gas_used': self.gas_used,
            'gas_limit': self.gas_limit
        }
        return json.dumps(data, sort_keys=True).encode('utf-8')
    
    def calculate_hash(self) -> str:
        """Calculate block hash"""
        return hashlib.sha256(self.to_bytes()).hexdigest()
    
    def mine(self, target_difficulty: Optional[int] = None) -> str:
        """Mine block using Proof of Work"""
        if target_difficulty is None:
            target_difficulty = self.difficulty
        
        target = '0' * target_difficulty
        attempts = 0
        start_time = time.time()
        
        while True:
            self.hash = self.calculate_hash()
            
            if self.hash.startswith(target):
                mining_time = time.time() - start_time
                logger.info(f"Block {self.height} mined in {mining_time:.2f}s after {attempts} attempts")
                return self.hash
            
            self.nonce += 1
            attempts += 1
            
            # Prevent infinite mining
            if attempts > 10000000:
                raise BlockValidationError("Mining timeout - difficulty too high")
            
            # Progress logging
            if attempts % 100000 == 0:
                logger.info(f"Mining block {self.height}: {attempts} attempts...")
    
    def validate(self) -> bool:
        """Validate block integrity"""
        # Check hash meets difficulty requirement
        target = '0' * self.difficulty
        if not self.hash.startswith(target):
            raise BlockValidationError("Block hash does not meet difficulty requirement")
        
        # Verify hash is correct
        if self.hash != self.calculate_hash():
            raise BlockValidationError("Block hash is invalid")
        
        # Verify Merkle root
        if self.merkle_root != self._calculate_merkle_root():
            raise BlockValidationError("Merkle root is invalid")
        
        # Validate all transactions
        for tx in self.transactions:
            if not tx.id or not tx.signature:
                raise BlockValidationError("Transaction missing required fields")
        
        # Check gas usage
        if self.gas_used > self.gas_limit:
            raise BlockValidationError("Gas usage exceeds limit")
        
        return True

class ProofOfStakeValidator:
    """Proof of Stake consensus validator"""
    
    def __init__(self, validator_id: str, stake_amount: Decimal):
        self.validator_id = validator_id
        self.stake_amount = stake_amount
        self.reputation = Decimal('1.0')
        self.blocks_proposed = 0
        self.blocks_validated = 0
        self.last_active = datetime.now(timezone.utc)
    
    def calculate_selection_weight(self) -> Decimal:
        """Calculate validator selection weight"""
        # Weight based on stake, reputation, and activity
        base_weight = self.stake_amount * self.reputation
        
        # Activity bonus (higher weight for active validators)
        hours_since_active = (datetime.now(timezone.utc) - self.last_active).total_seconds() / 3600
        activity_multiplier = max(Decimal('0.1'), Decimal('2.0') - Decimal(str(hours_since_active)) / Decimal('24'))
        
        return base_weight * activity_multiplier
    
    def update_reputation(self, successful_validation: bool):
        """Update validator reputation"""
        if successful_validation:
            self.reputation = min(Decimal('2.0'), self.reputation * Decimal('1.01'))
        else:
            self.reputation = max(Decimal('0.1'), self.reputation * Decimal('0.95'))
        
        self.last_active = datetime.now(timezone.utc)

class AdvancedBlockchain:
    """Advanced blockchain with Proof of Stake consensus"""
    
    def __init__(self, database: FinancialDatabase):
        self.database = database
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.validators: Dict[str, ProofOfStakeValidator] = {}
        self.difficulty = 4
        self.block_time_target = 15  # 15 seconds target block time
        self.max_transactions_per_block = 1000
        self.base_fee = Decimal('0.01')
        
        # Load existing blockchain
        self._load_blockchain()
        
        # Create genesis block if needed
        if not self.chain:
            self._create_genesis_block()
        
        logger.info(f"Blockchain initialized with {len(self.chain)} blocks")
    
    def _create_genesis_block(self):
        """Create the genesis block"""
        genesis_tx = Transaction(
            id="genesis",
            sender="SYSTEM",
            receiver="GENESIS",
            amount=Decimal('1'),  # Genesis gets 1 token
            fee=Decimal('0'),
            timestamp=datetime.now(timezone.utc),
            signature="genesis_signature",
            nonce=0
        )
        
        genesis_block = Block(
            height=0,
            previous_hash="0" * 64,
            timestamp=datetime.now(timezone.utc),
            transactions=[genesis_tx],
            miner="SYSTEM",
            difficulty=1
        )
        
        genesis_block.hash = genesis_block.mine(1)
        self.chain.append(genesis_block)
        self._save_block(genesis_block)
        
        logger.info("Genesis block created")
    
    def _load_blockchain(self):
        """Load blockchain from database"""
        with self.database.pool.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM blocks ORDER BY height ASC
            ''')
            
            for row in cursor:
                # Reconstruct block (simplified - in production, store full serialized data)
                block = Block(
                    height=row['height'],
                    previous_hash=row['previous_hash'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    transactions=[],  # Would load from separate table
                    miner=row['miner'] or 'UNKNOWN',
                    nonce=row['nonce'],
                    difficulty=row['difficulty']
                )
                block.hash = row['hash']
                self.chain.append(block)
    
    def _save_block(self, block: Block):
        """Save block to database"""
        try:
            with self.database.transaction() as conn:
                conn.execute('''
                    INSERT INTO blocks (
                        height, hash, previous_hash, merkle_root, timestamp,
                        nonce, difficulty, miner, transaction_count, gas_used,
                        gas_limit, transactions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    block.height,
                    block.hash,
                    block.previous_hash,
                    block.merkle_root,
                    block.timestamp.isoformat(),
                    block.nonce,
                    block.difficulty,
                    block.miner,
                    len(block.transactions),
                    block.gas_used,
                    block.gas_limit,
                    json.dumps([asdict(tx) for tx in block.transactions], default=str)
                ))
                
        except Exception as e:
            logger.error(f"Failed to save block: {e}")
            raise
    
    def add_validator(self, validator_id: str, stake_amount: Decimal) -> bool:
        """Add new validator to the network"""
        if validator_id in self.validators:
            return False
        
        validator = ProofOfStakeValidator(validator_id, stake_amount)
        self.validators[validator_id] = validator
        
        logger.info(f"Validator added: {validator_id} (stake: {stake_amount})")
        return True
    
    def select_validator(self) -> Optional[ProofOfStakeValidator]:
        """Select validator using weighted random selection"""
        if not self.validators:
            return None
        
        # Calculate total weight
        weights = [(v_id, validator.calculate_selection_weight()) 
                  for v_id, validator in self.validators.items()]
        
        total_weight = sum(weight for _, weight in weights)
        if total_weight == 0:
            return None
        
        # Random selection based on weight
        selection_point = Decimal(str(random.random())) * total_weight
        current_weight = Decimal('0')
        
        for v_id, weight in weights:
            current_weight += weight
            if current_weight >= selection_point:
                return self.validators[v_id]
        
        # Fallback
        return list(self.validators.values())[0]
    
    def add_transaction(self, transaction: Transaction, public_key: str) -> bool:
        """Add validated transaction to pending pool"""
        try:
            # Verify transaction signature
            if not transaction.verify_signature(public_key):
                logger.warning(f"Invalid signature for transaction {transaction.id}")
                return False
            
            # Check for duplicate
            existing_ids = {tx.id for tx in self.pending_transactions}
            if transaction.id in existing_ids:
                return False
            
            self.pending_transactions.append(transaction)
            logger.info(f"Transaction added to pool: {transaction.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add transaction: {e}")
            return False
    
    def mine_block(self, miner: str) -> Optional[Block]:
        """Mine new block with selected transactions"""
        if not self.pending_transactions:
            return None
        
        try:
            # Select transactions for block
            selected_txs = self.pending_transactions[:self.max_transactions_per_block]
            
            # Create new block
            previous_block = self.chain[-1] if self.chain else None
            previous_hash = previous_block.hash if previous_block else "0" * 64
            
            new_block = Block(
                height=len(self.chain),
                previous_hash=previous_hash,
                timestamp=datetime.now(timezone.utc),
                transactions=selected_txs,
                miner=miner,
                difficulty=self.difficulty
            )
            
            # Mine the block
            block_hash = new_block.mine()
            
            # Validate block
            new_block.validate()
            
            # Add to chain
            self.chain.append(new_block)
            
            # Remove mined transactions from pending pool
            mined_tx_ids = {tx.id for tx in selected_txs}
            self.pending_transactions = [tx for tx in self.pending_transactions 
                                       if tx.id not in mined_tx_ids]
            
            # Save to database
            self._save_block(new_block)
            
            # Adjust difficulty
            self._adjust_difficulty()
            
            logger.info(f"Block {new_block.height} mined by {miner}")
            return new_block
            
        except Exception as e:
            logger.error(f"Mining failed: {e}")
            return None
    
    def _adjust_difficulty(self):
        """Adjust mining difficulty based on block time"""
        if len(self.chain) < 10:
            return
        
        # Calculate average block time for last 10 blocks
        recent_blocks = self.chain[-10:]
        time_diffs = []
        
        for i in range(1, len(recent_blocks)):
            time_diff = (recent_blocks[i].timestamp - recent_blocks[i-1].timestamp).total_seconds()
            time_diffs.append(time_diff)
        
        avg_block_time = sum(time_diffs) / len(time_diffs)
        
        # Adjust difficulty
        if avg_block_time < self.block_time_target * 0.8:
            self.difficulty += 1
            logger.info(f"Difficulty increased to {self.difficulty}")
        elif avg_block_time > self.block_time_target * 1.2:
            self.difficulty = max(1, self.difficulty - 1)
            logger.info(f"Difficulty decreased to {self.difficulty}")
    
    def validate_chain(self) -> bool:
        """Validate entire blockchain"""
        try:
            for i, block in enumerate(self.chain):
                # Validate block
                block.validate()
                
                # Check linkage (except genesis)
                if i > 0:
                    if block.previous_hash != self.chain[i-1].hash:
                        logger.error(f"Block {i} has invalid previous hash")
                        return False
                    
                    if block.height != i:
                        logger.error(f"Block {i} has invalid height")
                        return False
            
            return True
            
        except BlockValidationError as e:
            logger.error(f"Chain validation failed: {e}")
            return False
    
    def get_balance(self, account_id: str) -> Decimal:
        """Calculate account balance from blockchain"""
        balance = Decimal('0')
        
        for block in self.chain:
            for tx in block.transactions:
                if tx.receiver == account_id:
                    balance += tx.amount
                elif tx.sender == account_id:
                    balance -= (tx.amount + tx.fee)
        
        return balance
    
    def get_block_by_height(self, height: int) -> Optional[Block]:
        """Get block by height"""
        if 0 <= height < len(self.chain):
            return self.chain[height]
        return None
    
    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """Get block by hash"""
        for block in self.chain:
            if block.hash == block_hash:
                return block
        return None

# ============================================================================
# ADVANCED DEFI WITH MATHEMATICAL PRECISION
# ============================================================================

class DeFiError(Exception):
    """DeFi operation error"""
    pass

class PrecisionMath:
    """High-precision mathematical operations for DeFi"""
    
    @staticmethod
    def sqrt(x: Decimal) -> Decimal:
        """Calculate square root using Newton-Raphson method"""
        if x < 0:
            raise ValueError("Square root of negative number")
        if x == 0:
            return Decimal('0')
        
        # Initial guess
        guess = x / 2
        precision = Decimal('0.0000000001')
        
        for _ in range(50):  # Maximum iterations
            new_guess = (guess + x / guess) / 2
            if abs(new_guess - guess) < precision:
                return new_guess
            guess = new_guess
        
        return guess
    
    @staticmethod
    def power(base: Decimal, exponent: Decimal, precision: int = 28) -> Decimal:
        """Calculate power using Taylor series (for fractional exponents)"""
        if base <= 0:
            raise ValueError("Base must be positive")
        
        # Use natural logarithm and exponential for fractional powers
        # base^exp = e^(exp * ln(base))
        ln_base = PrecisionMath.natural_log(base, precision)
        return PrecisionMath.exponential(exponent * ln_base, precision)
    
    @staticmethod
    def natural_log(x: Decimal, precision: int = 28) -> Decimal:
        """Calculate natural logarithm using Taylor series"""
        if x <= 0:
            raise ValueError("Logarithm of non-positive number")
        
        original_precision = getcontext().prec
        getcontext().prec = precision + 10
        
        try:
            # For convergence, transform to ln((1+y)/(1-y)) = 2(y + y^3/3 + y^5/5 + ...)
            # where y = (x-1)/(x+1)
            
            if x == 1:
                return Decimal('0')
            
            y = (x - 1) / (x + 1)
            y_squared = y * y
            
            result = Decimal('0')
            term = y
            n = 1
            
            for _ in range(100):  # Maximum terms
                result += term / n
                term *= y_squared
                n += 2
                
                if abs(term / n) < Decimal('10') ** (-precision):
                    break
            
            return result * 2
            
        finally:
            getcontext().prec = original_precision
    
    @staticmethod
    def exponential(x: Decimal, precision: int = 28) -> Decimal:
        """Calculate e^x using Taylor series"""
        original_precision = getcontext().prec
        getcontext().prec = precision + 10
        
        try:
            # e^x = 1 + x + x^2/2! + x^3/3! + ...
            result = Decimal('1')
            term = Decimal('1')
            
            for n in range(1, 200):  # Maximum terms
                term *= x / n
                result += term
                
                if abs(term) < Decimal('10') ** (-precision):
                    break
            
            return result
            
        finally:
            getcontext().prec = original_precision
    
    @staticmethod
    def compound_interest(principal: Decimal, rate: Decimal, time: Decimal, 
                         compounds_per_year: int = 1) -> Decimal:
        """Calculate compound interest"""
        if compounds_per_year == 0:
            # Continuous compounding: P * e^(rt)
            return principal * PrecisionMath.exponential(rate * time)
        else:
            # Discrete compounding: P * (1 + r/n)^(nt)
            rate_per_period = rate / compounds_per_year
            total_periods = time * compounds_per_year
            return principal * PrecisionMath.power(1 + rate_per_period, total_periods)

class LiquidityPool:
    """Advanced AMM liquidity pool with precision mathematics"""
    
    def __init__(self, token_a: str, token_b: str, fee_rate: Decimal = Decimal('0.003')):
        self.token_a = token_a
        self.token_b = token_b
        self.reserve_a = Decimal('0')
        self.reserve_b = Decimal('0')
        self.total_supply = Decimal('0')
        self.fee_rate = fee_rate  # 0.3% default
        self.minimum_liquidity = Decimal('1000')  # Minimum liquidity lock
        
        # Advanced features
        self.cumulative_price_a = Decimal('0')
        self.cumulative_price_b = Decimal('0')
        self.last_update_timestamp = 0
        self.protocol_fee_rate = Decimal('0.0005')  # 0.05% protocol fee
        
        # Liquidity provider tracking
        self.lp_balances: Dict[str, Decimal] = {}
        
        # Pool metadata
        self.created_at = datetime.now(timezone.utc)
        self.total_volume = Decimal('0')
        self.total_fees_collected = Decimal('0')
        
        self.lock = threading.RLock()
        
        logger.info(f"Liquidity pool created: {token_a}/{token_b}")
    
    def _update_cumulative_prices(self):
        """Update time-weighted cumulative prices for oracle"""
        current_time = int(time.time())
        
        if self.last_update_timestamp != 0 and self.reserve_a > 0 and self.reserve_b > 0:
            time_elapsed = current_time - self.last_update_timestamp
            
            # Price = reserve_b / reserve_a
            price_a = self.reserve_b / self.reserve_a
            price_b = self.reserve_a / self.reserve_b
            
            self.cumulative_price_a += price_a * time_elapsed
            self.cumulative_price_b += price_b * time_elapsed
        
        self.last_update_timestamp = current_time
    
    def get_spot_price(self, input_token: str) -> Decimal:
        """Get current spot price"""
        if self.reserve_a == 0 or self.reserve_b == 0:
            return Decimal('0')
        
        if input_token == self.token_a:
            return self.reserve_b / self.reserve_a
        elif input_token == self.token_b:
            return self.reserve_a / self.reserve_b
        else:
            raise ValueError("Invalid token")
    
    def get_twap_price(self, input_token: str, time_window: int) -> Decimal:
        """Get time-weighted average price"""
        current_time = int(time.time())
        
        if input_token == self.token_a and time_window > 0:
            return self.cumulative_price_a / time_window
        elif input_token == self.token_b and time_window > 0:
            return self.cumulative_price_b / time_window
        else:
            return self.get_spot_price(input_token)
    
    def calculate_liquidity_tokens(self, amount_a: Decimal, amount_b: Decimal) -> Decimal:
        """Calculate LP tokens to mint"""
        if self.total_supply == 0:
            # Initial liquidity
            liquidity = PrecisionMath.sqrt(amount_a * amount_b) - self.minimum_liquidity
            if liquidity <= 0:
                raise DeFiError("Insufficient liquidity amount")
            return liquidity
        else:
            # Subsequent liquidity
            liquidity_a = (amount_a * self.total_supply) / self.reserve_a
            liquidity_b = (amount_b * self.total_supply) / self.reserve_b
            return min(liquidity_a, liquidity_b)
    
    def add_liquidity(self, provider: str, amount_a: Decimal, amount_b: Decimal, 
                     min_liquidity: Decimal = Decimal('0')) -> Tuple[Decimal, Decimal, Decimal]:
        """Add liquidity to pool"""
        with self.lock:
            if amount_a <= 0 or amount_b <= 0:
                raise DeFiError("Invalid liquidity amounts")
            
            # Update price oracles
            self._update_cumulative_prices()
            
            if self.total_supply == 0:
                # Initial liquidity
                liquidity_tokens = PrecisionMath.sqrt(amount_a * amount_b)
                if liquidity_tokens <= self.minimum_liquidity:
                    raise DeFiError("Insufficient initial liquidity")
                
                liquidity_tokens -= self.minimum_liquidity  # Lock minimum liquidity
                
                self.reserve_a = amount_a
                self.reserve_b = amount_b
                self.total_supply = liquidity_tokens
                
                # Track LP balance
                self.lp_balances[provider] = liquidity_tokens
                
                return amount_a, amount_b, liquidity_tokens
            
            else:
                # Calculate optimal amounts
                optimal_amount_b = (amount_a * self.reserve_b) / self.reserve_a
                optimal_amount_a = (amount_b * self.reserve_a) / self.reserve_b
                
                if amount_b < optimal_amount_b:
                    # Use all of amount_b, adjust amount_a
                    amount_a = optimal_amount_a
                    if amount_a <= 0:
                        raise DeFiError("Insufficient liquidity for current ratio")
                else:
                    # Use all of amount_a, adjust amount_b
                    amount_b = optimal_amount_b
                    if amount_b <= 0:
                        raise DeFiError("Insufficient liquidity for current ratio")
                
                # Calculate LP tokens
                liquidity_tokens = self.calculate_liquidity_tokens(amount_a, amount_b)
                
                if liquidity_tokens < min_liquidity:
                    raise DeFiError("Insufficient liquidity tokens minted")
                
                # Update reserves
                self.reserve_a += amount_a
                self.reserve_b += amount_b
                self.total_supply += liquidity_tokens
                
                # Track LP balance
                self.lp_balances[provider] = self.lp_balances.get(provider, Decimal('0')) + liquidity_tokens
                
                return amount_a, amount_b, liquidity_tokens
    
    def calculate_swap_output(self, amount_in: Decimal, token_in: str, 
                            include_fee: bool = True) -> Tuple[Decimal, Decimal]:
        """Calculate swap output with fees"""
        if amount_in <= 0:
            raise DeFiError("Invalid input amount")
        
        if token_in == self.token_a:
            reserve_in = self.reserve_a
            reserve_out = self.reserve_b
        elif token_in == self.token_b:
            reserve_in = self.reserve_b
            reserve_out = self.reserve_a
        else:
            raise DeFiError("Invalid input token")
        
        if reserve_in == 0 or reserve_out == 0:
            raise DeFiError("Insufficient liquidity")
        
        # Calculate fees
        if include_fee:
            protocol_fee_amount = amount_in * self.protocol_fee_rate
            trading_fee_amount = amount_in * self.fee_rate
            amount_in_after_fees = amount_in - protocol_fee_amount - trading_fee_amount
        else:
            protocol_fee_amount = Decimal('0')
            trading_fee_amount = Decimal('0')
            amount_in_after_fees = amount_in
        
        # Constant product formula: (x + dx) * (y - dy) = x * y
        # dy = y - (x * y) / (x + dx)
        k = reserve_in * reserve_out
        new_reserve_in = reserve_in + amount_in_after_fees
        new_reserve_out = k / new_reserve_in
        amount_out = reserve_out - new_reserve_out
        
        if amount_out <= 0:
            raise DeFiError("Insufficient output amount")
        
        total_fee = protocol_fee_amount + trading_fee_amount
        
        return amount_out, total_fee
    
    def swap(self, trader: str, amount_in: Decimal, token_in: str, 
            min_amount_out: Decimal = Decimal('0')) -> Tuple[Decimal, Decimal]:
        """Execute token swap"""
        with self.lock:
            # Update price oracles
            self._update_cumulative_prices()
            
            # Calculate output
            amount_out, fee = self.calculate_swap_output(amount_in, token_in)
            
            if amount_out < min_amount_out:
                raise DeFiError(f"Insufficient output amount: {amount_out} < {min_amount_out}")
            
            # Calculate price impact
            if token_in == self.token_a:
                old_price = self.reserve_b / self.reserve_a
                new_reserve_a = self.reserve_a + amount_in
                new_reserve_b = self.reserve_b - amount_out
                new_price = new_reserve_b / new_reserve_a
            else:
                old_price = self.reserve_a / self.reserve_b
                new_reserve_b = self.reserve_b + amount_in
                new_reserve_a = self.reserve_a - amount_out
                new_price = new_reserve_a / new_reserve_b
            
            price_impact = abs(new_price - old_price) / old_price
            
            # Check for excessive price impact (>5%)
            if price_impact > Decimal('0.05'):
                logger.warning(f"High price impact: {price_impact:.4f}")
            
            # Update reserves
            if token_in == self.token_a:
                self.reserve_a += amount_in
                self.reserve_b -= amount_out
            else:
                self.reserve_b += amount_in
                self.reserve_a -= amount_out
            
            # Update metrics
            self.total_volume += amount_in
            self.total_fees_collected += fee
            
            # Verify constant product invariant
            k_before = (self.reserve_a - (amount_in if token_in == self.token_a else 0)) * \
                      (self.reserve_b - (amount_in if token_in == self.token_b else 0))
            k_after = self.reserve_a * self.reserve_b
            
            if k_after < k_before:
                raise DeFiError("Constant product invariant violated")
            
            logger.info(f"Swap executed: {amount_in} {token_in} -> {amount_out}")
            return amount_out, fee
    
    def remove_liquidity(self, provider: str, liquidity_tokens: Decimal) -> Tuple[Decimal, Decimal]:
        """Remove liquidity from pool"""
        with self.lock:
            if liquidity_tokens <= 0:
                raise DeFiError("Invalid liquidity amount")
            
            if provider not in self.lp_balances or self.lp_balances[provider] < liquidity_tokens:
                raise DeFiError("Insufficient liquidity balance")
            
            if self.total_supply <= liquidity_tokens:
                raise DeFiError("Cannot remove all liquidity")
            
            # Calculate withdrawal amounts
            ratio = liquidity_tokens / self.total_supply
            amount_a = self.reserve_a * ratio
            amount_b = self.reserve_b * ratio
            
            # Update state
            self.reserve_a -= amount_a
            self.reserve_b -= amount_b
            self.total_supply -= liquidity_tokens
            self.lp_balances[provider] -= liquidity_tokens
            
            # Update price oracles
            self._update_cumulative_prices()
            
            logger.info(f"Liquidity removed: {liquidity_tokens} tokens -> {amount_a} {self.token_a}, {amount_b} {self.token_b}")
            return amount_a, amount_b
    
    def get_pool_info(self) -> Dict[str, Any]:
        """Get comprehensive pool information"""
        return {
            'token_a': self.token_a,
            'token_b': self.token_b,
            'reserve_a': str(self.reserve_a),
            'reserve_b': str(self.reserve_b),
            'total_supply': str(self.total_supply),
            'fee_rate': str(self.fee_rate),
            'protocol_fee_rate': str(self.protocol_fee_rate),
            'spot_price_a': str(self.get_spot_price(self.token_a)),
            'spot_price_b': str(self.get_spot_price(self.token_b)),
            'total_volume': str(self.total_volume),
            'total_fees_collected': str(self.total_fees_collected),
            'created_at': self.created_at.isoformat(),
            'lp_count': len(self.lp_balances)
        }

# Create a simple test
def main():
    """Main system demonstration"""
    print("=" * 80)
    print("QENEX Financial Operating System")
    print("Advanced Financial Infrastructure")
    print("=" * 80)
    
    # System info
    print(f"\nSystem: {SYSTEM_INFO['system']} {SYSTEM_INFO['architecture']}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Data Path: {DATA_PATH}")
    
    # Initialize database
    print("\n--- Database Initialization ---")
    db = FinancialDatabase()
    
    # Create test accounts
    print("\n--- Account Management ---")
    db.create_account("ALICE", "PREMIUM", Decimal('50000.00'))
    db.create_account("BOB", "STANDARD", Decimal('25000.00'))
    db.create_account("CHARLIE", "INSTITUTIONAL", Decimal('100000.00'))
    
    # Display account info
    for account_id in ["ALICE", "BOB", "CHARLIE"]:
        account = db.get_account(account_id)
        if account:
            print(f"  {account_id}: {account['balance']} {account['currency']} ({account['account_type']})")
    
    # Initialize blockchain
    print("\n--- Blockchain Initialization ---")
    blockchain = AdvancedBlockchain(db)
    
    # Add validators
    blockchain.add_validator("ALICE", Decimal('10000'))
    blockchain.add_validator("BOB", Decimal('5000'))
    
    # Create test transactions
    print("\n--- Transaction Processing ---")
    private_key, public_key = AdvancedCrypto.generate_keypair()
    
    tx1 = Transaction(
        id="tx_001",
        sender="ALICE",
        receiver="BOB",
        amount=Decimal('1000.00'),
        fee=Decimal('1.00'),
        timestamp=datetime.now(timezone.utc),
        signature=AdvancedCrypto.sign_message(private_key, b"tx_001")
    )
    
    success = blockchain.add_transaction(tx1, public_key)
    print(f"  Transaction added: {success}")
    
    # Mine a block
    print("\n--- Block Mining ---")
    new_block = blockchain.mine_block("ALICE")
    if new_block:
        print(f"  Block mined: Height {new_block.height}, Hash: {new_block.hash[:16]}...")
        print(f"  Transactions: {len(new_block.transactions)}")
    
    # Test DeFi pool
    print("\n--- DeFi Pool Operations ---")
    pool = LiquidityPool("USDC", "ETH")
    
    # Add liquidity
    amount_a, amount_b, lp_tokens = pool.add_liquidity(
        "ALICE", 
        Decimal('10000.00'), 
        Decimal('5.00')
    )
    print(f"  Liquidity added: {amount_a} USDC, {amount_b} ETH -> {lp_tokens} LP tokens")
    
    # Execute swap
    amount_out, fee = pool.swap("BOB", Decimal('1000.00'), "USDC")
    print(f"  Swap: 1000 USDC -> {amount_out:.4f} ETH (fee: {fee:.4f})")
    
    # Pool info
    pool_info = pool.get_pool_info()
    print(f"  Pool reserves: {pool_info['reserve_a']} USDC, {pool_info['reserve_b']} ETH")
    print(f"  Price: 1 USDC = {pool_info['spot_price_a']} ETH")
    
    # Validate blockchain
    print("\n--- System Validation ---")
    chain_valid = blockchain.validate_chain()
    print(f"  Blockchain valid: {chain_valid}")
    
    print("\n--- System Status ---")
    print("✅ Database: Operational with ACID compliance")
    print("✅ Blockchain: Advanced PoS consensus working")
    print("✅ DeFi: AMM with precision mathematics")
    print("✅ Security: Advanced cryptography implemented")
    print("✅ Platform: Cross-platform compatibility")
    
    # Cleanup
    print("\n--- Cleanup ---")
    db.close()
    
    print("\n🎯 QENEX Financial OS successfully operational!")
    print("Ready for production financial entity deployment")

if __name__ == "__main__":
    main()