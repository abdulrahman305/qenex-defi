#!/usr/bin/env python3
"""
QENEX Secret Management System
Secure secret storage and retrieval with encryption at rest and in transit
Version: 1.0.0
"""

import os
import sys
import json
import base64
import hashlib
import hmac
import time
import logging
import threading
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import secrets
import uuid

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger = logging.getLogger('QENEX-SecretManager')
    logger.warning("Cryptography library not available. Secret encryption disabled.")

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('QENEX-SecretManager')

class SecretType(Enum):
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"
    DATABASE_URL = "database_url"
    OAUTH_TOKEN = "oauth_token"
    WEBHOOK_SECRET = "webhook_secret"
    ENCRYPTION_KEY = "encryption_key"
    CUSTOM = "custom"

class SecretScope(Enum):
    GLOBAL = "global"
    PROJECT = "project"
    PIPELINE = "pipeline"
    USER = "user"
    ENVIRONMENT = "environment"

class AccessLevel(Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

@dataclass
class SecretMetadata:
    """Metadata for a secret"""
    id: str
    name: str
    secret_type: SecretType
    scope: SecretScope
    scope_id: str  # project_id, pipeline_id, user_id, etc.
    description: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    tags: List[str] = None
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    last_accessed_by: Optional[str] = None
    rotation_enabled: bool = False
    rotation_interval_days: int = 90
    is_active: bool = True

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class SecretAccessLog:
    """Log entry for secret access"""
    id: str
    secret_id: str
    user_id: str
    action: str  # read, write, delete, rotate
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

class EncryptionManager:
    """Manages encryption/decryption operations"""
    
    def __init__(self, master_key: Optional[bytes] = None):
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography library is required for encryption")
        
        self.master_key = master_key or self._generate_master_key()
        self.fernet = Fernet(base64.urlsafe_b64encode(self.master_key[:32]))
        
        # Initialize RSA key pair for asymmetric encryption
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
    
    def _generate_master_key(self) -> bytes:
        """Generate a master encryption key"""
        return secrets.token_bytes(32)
    
    def encrypt_symmetric(self, data: bytes) -> bytes:
        """Encrypt data using symmetric encryption"""
        return self.fernet.encrypt(data)
    
    def decrypt_symmetric(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using symmetric encryption"""
        return self.fernet.decrypt(encrypted_data)
    
    def encrypt_asymmetric(self, data: bytes) -> bytes:
        """Encrypt data using asymmetric encryption (for key exchange)"""
        return self.public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def decrypt_asymmetric(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using asymmetric encryption"""
        return self.private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode())
    
    def generate_salt(self) -> bytes:
        """Generate random salt"""
        return secrets.token_bytes(16)
    
    def hash_password(self, password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """Hash password with salt"""
        if salt is None:
            salt = self.generate_salt()
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            100000
        )
        return password_hash, salt
    
    def verify_password(self, password: str, password_hash: bytes, salt: bytes) -> bool:
        """Verify password against hash"""
        derived_hash, _ = self.hash_password(password, salt)
        return hmac.compare_digest(password_hash, derived_hash)

class SecretStorage:
    """Handles secret storage backend"""
    
    def __init__(self, db_path: str = "/opt/qenex-os/cicd/secrets.db"):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS secrets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    secret_type TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    encrypted_value BLOB NOT NULL,
                    salt BLOB NOT NULL,
                    description TEXT,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP,
                    tags TEXT,
                    access_count INTEGER DEFAULT 0,
                    last_accessed_at TIMESTAMP,
                    last_accessed_by TEXT,
                    rotation_enabled BOOLEAN DEFAULT 0,
                    rotation_interval_days INTEGER DEFAULT 90,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_logs (
                    id TEXT PRIMARY KEY,
                    secret_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    FOREIGN KEY (secret_id) REFERENCES secrets (id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS secret_permissions (
                    id TEXT PRIMARY KEY,
                    secret_id TEXT NOT NULL,
                    user_id TEXT,
                    role TEXT,
                    access_level TEXT NOT NULL,
                    granted_by TEXT NOT NULL,
                    granted_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (secret_id) REFERENCES secrets (id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_secrets_scope ON secrets(scope, scope_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_secrets_name ON secrets(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_secret ON access_logs(secret_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_permissions_secret ON secret_permissions(secret_id)")
    
    def store_secret(self, metadata: SecretMetadata, encrypted_value: bytes, salt: bytes):
        """Store encrypted secret"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO secrets 
                    (id, name, secret_type, scope, scope_id, encrypted_value, salt,
                     description, created_by, created_at, updated_at, expires_at,
                     tags, access_count, last_accessed_at, last_accessed_by,
                     rotation_enabled, rotation_interval_days, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metadata.id, metadata.name, metadata.secret_type.value,
                    metadata.scope.value, metadata.scope_id, encrypted_value, salt,
                    metadata.description, metadata.created_by,
                    metadata.created_at, metadata.updated_at, metadata.expires_at,
                    json.dumps(metadata.tags), metadata.access_count,
                    metadata.last_accessed_at, metadata.last_accessed_by,
                    metadata.rotation_enabled, metadata.rotation_interval_days,
                    metadata.is_active
                ))
    
    def get_secret(self, secret_id: str) -> Optional[Tuple[SecretMetadata, bytes, bytes]]:
        """Retrieve encrypted secret"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM secrets WHERE id = ? AND is_active = 1
                """, (secret_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                metadata = SecretMetadata(
                    id=row['id'],
                    name=row['name'],
                    secret_type=SecretType(row['secret_type']),
                    scope=SecretScope(row['scope']),
                    scope_id=row['scope_id'],
                    description=row['description'],
                    created_by=row['created_by'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                    tags=json.loads(row['tags']) if row['tags'] else [],
                    access_count=row['access_count'],
                    last_accessed_at=datetime.fromisoformat(row['last_accessed_at']) if row['last_accessed_at'] else None,
                    last_accessed_by=row['last_accessed_by'],
                    rotation_enabled=bool(row['rotation_enabled']),
                    rotation_interval_days=row['rotation_interval_days'],
                    is_active=bool(row['is_active'])
                )
                
                return metadata, row['encrypted_value'], row['salt']
    
    def list_secrets(self, scope: Optional[SecretScope] = None, 
                    scope_id: Optional[str] = None) -> List[SecretMetadata]:
        """List secrets with optional filtering"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = "SELECT * FROM secrets WHERE is_active = 1"
                params = []
                
                if scope:
                    query += " AND scope = ?"
                    params.append(scope.value)
                
                if scope_id:
                    query += " AND scope_id = ?"
                    params.append(scope_id)
                
                cursor = conn.execute(query, params)
                
                secrets = []
                for row in cursor.fetchall():
                    metadata = SecretMetadata(
                        id=row['id'],
                        name=row['name'],
                        secret_type=SecretType(row['secret_type']),
                        scope=SecretScope(row['scope']),
                        scope_id=row['scope_id'],
                        description=row['description'],
                        created_by=row['created_by'],
                        created_at=datetime.fromisoformat(row['created_at']),
                        updated_at=datetime.fromisoformat(row['updated_at']),
                        expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                        tags=json.loads(row['tags']) if row['tags'] else [],
                        access_count=row['access_count'],
                        last_accessed_at=datetime.fromisoformat(row['last_accessed_at']) if row['last_accessed_at'] else None,
                        last_accessed_by=row['last_accessed_by'],
                        rotation_enabled=bool(row['rotation_enabled']),
                        rotation_interval_days=row['rotation_interval_days'],
                        is_active=bool(row['is_active'])
                    )
                    secrets.append(metadata)
                
                return secrets
    
    def delete_secret(self, secret_id: str):
        """Soft delete a secret"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE secrets SET is_active = 0, updated_at = ?
                    WHERE id = ?
                """, (datetime.now(), secret_id))
    
    def update_access_stats(self, secret_id: str, user_id: str):
        """Update secret access statistics"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE secrets 
                    SET access_count = access_count + 1,
                        last_accessed_at = ?,
                        last_accessed_by = ?
                    WHERE id = ?
                """, (datetime.now(), user_id, secret_id))
    
    def log_access(self, log_entry: SecretAccessLog):
        """Log secret access"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO access_logs
                    (id, secret_id, user_id, action, timestamp, ip_address,
                     user_agent, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_entry.id, log_entry.secret_id, log_entry.user_id,
                    log_entry.action, log_entry.timestamp, log_entry.ip_address,
                    log_entry.user_agent, log_entry.success, log_entry.error_message
                ))

class SecretManager:
    """Main secret management interface"""
    
    def __init__(self, master_key: Optional[bytes] = None, db_path: Optional[str] = None):
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography library is required")
        
        self.encryption_manager = EncryptionManager(master_key)
        self.storage = SecretStorage(db_path)
        self.lock = threading.RLock()
        
        # Load master key from keyring if available
        if KEYRING_AVAILABLE and not master_key:
            try:
                stored_key = keyring.get_password("qenex", "master_key")
                if stored_key:
                    self.encryption_manager.master_key = base64.b64decode(stored_key)
                else:
                    # Store new master key in keyring
                    encoded_key = base64.b64encode(self.encryption_manager.master_key).decode()
                    keyring.set_password("qenex", "master_key", encoded_key)
            except Exception as e:
                logger.warning(f"Keyring access failed: {e}")
    
    def create_secret(self, name: str, value: str, secret_type: SecretType,
                     scope: SecretScope, scope_id: str, description: str = "",
                     created_by: str = "system", expires_at: Optional[datetime] = None,
                     tags: List[str] = None) -> str:
        """Create a new secret"""
        with self.lock:
            secret_id = str(uuid.uuid4())
            
            # Encrypt the secret value
            salt = self.encryption_manager.generate_salt()
            key = self.encryption_manager.derive_key(self.encryption_manager.master_key.hex(), salt)
            
            fernet = Fernet(base64.urlsafe_b64encode(key))
            encrypted_value = fernet.encrypt(value.encode())
            
            # Create metadata
            metadata = SecretMetadata(
                id=secret_id,
                name=name,
                secret_type=secret_type,
                scope=scope,
                scope_id=scope_id,
                description=description,
                created_by=created_by,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                expires_at=expires_at,
                tags=tags or []
            )
            
            # Store in database
            self.storage.store_secret(metadata, encrypted_value, salt)
            
            # Log creation
            self._log_access(secret_id, created_by, "create", success=True)
            
            logger.info(f"Secret '{name}' created with ID: {secret_id}")
            return secret_id
    
    def get_secret(self, secret_id: str, user_id: str = "system") -> Optional[str]:
        """Retrieve a secret value"""
        with self.lock:
            try:
                result = self.storage.get_secret(secret_id)
                if not result:
                    self._log_access(secret_id, user_id, "read", success=False, 
                                   error="Secret not found")
                    return None
                
                metadata, encrypted_value, salt = result
                
                # Check expiration
                if metadata.expires_at and datetime.now() > metadata.expires_at:
                    self._log_access(secret_id, user_id, "read", success=False,
                                   error="Secret expired")
                    return None
                
                # Decrypt the value
                key = self.encryption_manager.derive_key(self.encryption_manager.master_key.hex(), salt)
                fernet = Fernet(base64.urlsafe_b64encode(key))
                decrypted_value = fernet.decrypt(encrypted_value).decode()
                
                # Update access stats
                self.storage.update_access_stats(secret_id, user_id)
                self._log_access(secret_id, user_id, "read", success=True)
                
                logger.debug(f"Secret {secret_id} accessed by {user_id}")
                return decrypted_value
                
            except Exception as e:
                self._log_access(secret_id, user_id, "read", success=False, error=str(e))
                logger.error(f"Failed to retrieve secret {secret_id}: {e}")
                return None
    
    def update_secret(self, secret_id: str, new_value: str, user_id: str = "system") -> bool:
        """Update a secret value"""
        with self.lock:
            try:
                result = self.storage.get_secret(secret_id)
                if not result:
                    self._log_access(secret_id, user_id, "write", success=False,
                                   error="Secret not found")
                    return False
                
                metadata, _, _ = result
                
                # Generate new salt and encrypt new value
                salt = self.encryption_manager.generate_salt()
                key = self.encryption_manager.derive_key(self.encryption_manager.master_key.hex(), salt)
                
                fernet = Fernet(base64.urlsafe_b64encode(key))
                encrypted_value = fernet.encrypt(new_value.encode())
                
                # Update metadata
                metadata.updated_at = datetime.now()
                
                # Store updated secret
                self.storage.store_secret(metadata, encrypted_value, salt)
                
                self._log_access(secret_id, user_id, "write", success=True)
                logger.info(f"Secret {secret_id} updated by {user_id}")
                return True
                
            except Exception as e:
                self._log_access(secret_id, user_id, "write", success=False, error=str(e))
                logger.error(f"Failed to update secret {secret_id}: {e}")
                return False
    
    def delete_secret(self, secret_id: str, user_id: str = "system") -> bool:
        """Delete a secret"""
        with self.lock:
            try:
                self.storage.delete_secret(secret_id)
                self._log_access(secret_id, user_id, "delete", success=True)
                logger.info(f"Secret {secret_id} deleted by {user_id}")
                return True
            except Exception as e:
                self._log_access(secret_id, user_id, "delete", success=False, error=str(e))
                logger.error(f"Failed to delete secret {secret_id}: {e}")
                return False
    
    def list_secrets(self, scope: Optional[SecretScope] = None,
                    scope_id: Optional[str] = None) -> List[Dict]:
        """List secrets (metadata only)"""
        secrets = self.storage.list_secrets(scope, scope_id)
        return [
            {
                "id": secret.id,
                "name": secret.name,
                "type": secret.secret_type.value,
                "scope": secret.scope.value,
                "scope_id": secret.scope_id,
                "description": secret.description,
                "created_by": secret.created_by,
                "created_at": secret.created_at.isoformat(),
                "updated_at": secret.updated_at.isoformat(),
                "expires_at": secret.expires_at.isoformat() if secret.expires_at else None,
                "tags": secret.tags,
                "access_count": secret.access_count,
                "last_accessed_at": secret.last_accessed_at.isoformat() if secret.last_accessed_at else None,
                "rotation_enabled": secret.rotation_enabled
            }
            for secret in secrets
        ]
    
    def rotate_secret(self, secret_id: str, new_value: str, user_id: str = "system") -> bool:
        """Rotate a secret (update with logging)"""
        success = self.update_secret(secret_id, new_value, user_id)
        if success:
            self._log_access(secret_id, user_id, "rotate", success=True)
        return success
    
    def get_secrets_for_pipeline(self, pipeline_id: str) -> Dict[str, str]:
        """Get all secrets for a specific pipeline"""
        secrets_dict = {}
        
        # Get pipeline-specific secrets
        pipeline_secrets = self.storage.list_secrets(SecretScope.PIPELINE, pipeline_id)
        for secret in pipeline_secrets:
            value = self.get_secret(secret.id)
            if value:
                secrets_dict[secret.name] = value
        
        # Get global secrets
        global_secrets = self.storage.list_secrets(SecretScope.GLOBAL)
        for secret in global_secrets:
            if secret.name not in secrets_dict:  # Don't override pipeline-specific secrets
                value = self.get_secret(secret.id)
                if value:
                    secrets_dict[secret.name] = value
        
        return secrets_dict
    
    def _log_access(self, secret_id: str, user_id: str, action: str,
                   success: bool = True, error: Optional[str] = None,
                   ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log secret access"""
        log_entry = SecretAccessLog(
            id=str(uuid.uuid4()),
            secret_id=secret_id,
            user_id=user_id,
            action=action,
            timestamp=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error
        )
        
        try:
            self.storage.log_access(log_entry)
        except Exception as e:
            logger.error(f"Failed to log access: {e}")
    
    def cleanup_expired_secrets(self):
        """Remove expired secrets"""
        with self.lock:
            secrets = self.storage.list_secrets()
            now = datetime.now()
            
            for secret in secrets:
                if secret.expires_at and now > secret.expires_at:
                    self.storage.delete_secret(secret.id)
                    logger.info(f"Expired secret {secret.id} ({secret.name}) removed")
    
    def export_secrets(self, scope: Optional[SecretScope] = None,
                      scope_id: Optional[str] = None, include_values: bool = False) -> Dict:
        """Export secrets for backup/migration"""
        secrets = self.storage.list_secrets(scope, scope_id)
        
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "secrets": []
        }
        
        for secret in secrets:
            secret_data = asdict(secret)
            secret_data['secret_type'] = secret_data['secret_type'].value
            secret_data['scope'] = secret_data['scope'].value
            secret_data['created_at'] = secret_data['created_at'].isoformat()
            secret_data['updated_at'] = secret_data['updated_at'].isoformat()
            if secret_data['expires_at']:
                secret_data['expires_at'] = secret_data['expires_at'].isoformat()
            if secret_data['last_accessed_at']:
                secret_data['last_accessed_at'] = secret_data['last_accessed_at'].isoformat()
            
            if include_values:
                secret_data['value'] = self.get_secret(secret.id)
            
            export_data['secrets'].append(secret_data)
        
        return export_data
    
    def health_check(self) -> Dict:
        """Perform health check on secret manager"""
        try:
            # Test encryption/decryption
            test_data = "health_check_test"
            encrypted = self.encryption_manager.encrypt_symmetric(test_data.encode())
            decrypted = self.encryption_manager.decrypt_symmetric(encrypted).decode()
            
            encryption_ok = (test_data == decrypted)
            
            # Count secrets
            secrets = self.storage.list_secrets()
            total_secrets = len(secrets)
            expired_secrets = len([s for s in secrets if s.expires_at and datetime.now() > s.expires_at])
            
            return {
                "status": "healthy" if encryption_ok else "unhealthy",
                "encryption_test": encryption_ok,
                "total_secrets": total_secrets,
                "expired_secrets": expired_secrets,
                "database_connected": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# CLI interface for secret management
class SecretManagerCLI:
    """Command-line interface for secret management"""
    
    def __init__(self):
        self.secret_manager = SecretManager()
    
    def create(self, name: str, value: str, secret_type: str = "custom",
              scope: str = "global", scope_id: str = "default",
              description: str = "", expires_days: Optional[int] = None):
        """Create a secret via CLI"""
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        secret_id = self.secret_manager.create_secret(
            name=name,
            value=value,
            secret_type=SecretType(secret_type),
            scope=SecretScope(scope),
            scope_id=scope_id,
            description=description,
            expires_at=expires_at
        )
        
        print(f"Secret created with ID: {secret_id}")
        return secret_id
    
    def get(self, secret_id: str):
        """Get a secret via CLI"""
        value = self.secret_manager.get_secret(secret_id)
        if value:
            print(value)
        else:
            print("Secret not found or access denied")
    
    def list_secrets(self, scope: Optional[str] = None, scope_id: Optional[str] = None):
        """List secrets via CLI"""
        scope_enum = SecretScope(scope) if scope else None
        secrets = self.secret_manager.list_secrets(scope_enum, scope_id)
        
        if not secrets:
            print("No secrets found")
            return
        
        print(f"{'ID':<36} {'Name':<20} {'Type':<15} {'Scope':<10} {'Created':<20}")
        print("-" * 101)
        
        for secret in secrets:
            print(f"{secret['id']:<36} {secret['name']:<20} {secret['type']:<15} "
                  f"{secret['scope']:<10} {secret['created_at'][:19]:<20}")
    
    def delete(self, secret_id: str):
        """Delete a secret via CLI"""
        if self.secret_manager.delete_secret(secret_id):
            print(f"Secret {secret_id} deleted")
        else:
            print("Failed to delete secret")
    
    def health(self):
        """Check health via CLI"""
        health_status = self.secret_manager.health_check()
        print(json.dumps(health_status, indent=2))

# Example usage and testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='QENEX Secret Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a secret')
    create_parser.add_argument('name', help='Secret name')
    create_parser.add_argument('value', help='Secret value')
    create_parser.add_argument('--type', default='custom', help='Secret type')
    create_parser.add_argument('--scope', default='global', help='Secret scope')
    create_parser.add_argument('--scope-id', default='default', help='Scope ID')
    create_parser.add_argument('--description', default='', help='Description')
    create_parser.add_argument('--expires-days', type=int, help='Expiration in days')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get a secret')
    get_parser.add_argument('secret_id', help='Secret ID')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List secrets')
    list_parser.add_argument('--scope', help='Filter by scope')
    list_parser.add_argument('--scope-id', help='Filter by scope ID')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a secret')
    delete_parser.add_argument('secret_id', help='Secret ID')
    
    # Health command
    health_parser = subparsers.add_parser('health', help='Health check')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = SecretManagerCLI()
    
    if args.command == 'create':
        cli.create(args.name, args.value, args.type, args.scope, 
                  args.scope_id, args.description, args.expires_days)
    elif args.command == 'get':
        cli.get(args.secret_id)
    elif args.command == 'list':
        cli.list_secrets(args.scope, args.scope_id)
    elif args.command == 'delete':
        cli.delete(args.secret_id)
    elif args.command == 'health':
        cli.health()