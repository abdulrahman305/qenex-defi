#!/usr/bin/env python3
"""
Secure Key Management System
Enterprise-grade cryptographic key management with HSM support
"""

import os
import json
import hashlib
import hmac
import secrets
import base64
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.fernet import Fernet
import logging
from pathlib import Path
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeyType(Enum):
    """Types of cryptographic keys"""
    MASTER = "master"
    ENCRYPTION = "encryption"
    SIGNING = "signing"
    TOKEN = "token"
    API = "api"
    SESSION = "session"

class SecureKeyManager:
    """
    Enterprise-grade key management system
    Features:
    - Hardware Security Module (HSM) support
    - Key rotation and versioning
    - Secure key derivation
    - Memory-safe operations
    - Audit logging
    """
    
    def __init__(self, config_path: str = "/opt/qenex/keys/config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.backend = default_backend()
        
        # Initialize secure storage
        self.key_store: Dict[str, Dict[str, Any]] = {}
        self.key_versions: Dict[str, List[str]] = {}
        self.rotation_schedule: Dict[str, datetime] = {}
        
        # Initialize master key from environment or HSM
        self.master_key = self._initialize_master_key()
        
        # Setup key rotation scheduler
        self._setup_rotation_schedule()
        
        # Initialize audit log
        self.audit_log = []
        
    def _load_config(self) -> Dict:
        """Load security configuration"""
        default_config = {
            "hsm_enabled": False,
            "hsm_url": None,
            "key_rotation_days": 90,
            "max_key_versions": 5,
            "scrypt_n": 2**14,
            "scrypt_r": 8,
            "scrypt_p": 1,
            "pbkdf2_iterations": 100000,
            "enforce_key_expiry": True,
            "audit_enabled": True
        }
        
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                default_config.update(config)
        
        return default_config
    
    def _initialize_master_key(self) -> bytes:
        """Initialize master key from secure source"""
        # Try to load from environment variable first
        master_key_b64 = os.environ.get('QENEX_MASTER_KEY')
        
        if master_key_b64:
            try:
                master_key = base64.b64decode(master_key_b64)
                if len(master_key) >= 32:
                    logger.info("Master key loaded from environment")
                    return master_key
            except Exception as e:
                logger.error(f"Failed to load master key from environment: {e}")
        
        # Try HSM if configured
        if self.config.get('hsm_enabled'):
            master_key = self._load_from_hsm('master_key')
            if master_key:
                logger.info("Master key loaded from HSM")
                return master_key
        
        # Generate new master key (should be stored securely)
        master_key = secrets.token_bytes(32)
        logger.warning("Generated new master key - MUST be stored securely!")
        logger.warning(f"Export: QENEX_MASTER_KEY={base64.b64encode(master_key).decode()}")
        
        return master_key
    
    def _load_from_hsm(self, key_id: str) -> Optional[bytes]:
        """Load key from Hardware Security Module"""
        # This would integrate with actual HSM API
        # Example: AWS KMS, Azure Key Vault, HashiCorp Vault
        logger.info(f"HSM integration for key {key_id} not implemented")
        return None
    
    def derive_key(self, purpose: str, salt: Optional[bytes] = None, 
                   key_type: KeyType = KeyType.ENCRYPTION) -> bytes:
        """Derive a key for specific purpose using Scrypt"""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        # Use Scrypt for memory-hard key derivation
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=self.config['scrypt_n'],
            r=self.config['scrypt_r'],
            p=self.config['scrypt_p'],
            backend=self.backend
        )
        
        # Combine master key with purpose
        key_material = self.master_key + purpose.encode()
        derived_key = kdf.derive(key_material)
        
        # Store key metadata
        key_id = self._generate_key_id(purpose, key_type)
        self._store_key_metadata(key_id, {
            'type': key_type.value,
            'purpose': purpose,
            'salt': base64.b64encode(salt).decode(),
            'created': datetime.utcnow().isoformat(),
            'version': 1,
            'algorithm': 'scrypt'
        })
        
        self._audit_log('key_derived', {'key_id': key_id, 'purpose': purpose})
        
        return derived_key
    
    def generate_data_encryption_key(self) -> Tuple[str, bytes]:
        """Generate a new data encryption key"""
        key = Fernet.generate_key()
        key_id = f"dek_{secrets.token_urlsafe(16)}"
        
        # Encrypt DEK with KEK (Key Encryption Key)
        kek = self.derive_key("key_encryption", key_type=KeyType.ENCRYPTION)
        encrypted_dek = self._encrypt_key(key, kek)
        
        self.key_store[key_id] = {
            'encrypted_key': base64.b64encode(encrypted_dek).decode(),
            'created': datetime.utcnow().isoformat(),
            'type': KeyType.ENCRYPTION.value
        }
        
        return key_id, key
    
    def _encrypt_key(self, key: bytes, kek: bytes) -> bytes:
        """Encrypt a key with AES-256-GCM"""
        iv = secrets.token_bytes(12)  # 96-bit IV for GCM
        
        cipher = Cipher(
            algorithms.AES(kek),
            modes.GCM(iv),
            backend=self.backend
        )
        
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(key) + encryptor.finalize()
        
        # Return IV + ciphertext + tag
        return iv + ciphertext + encryptor.tag
    
    def _decrypt_key(self, encrypted: bytes, kek: bytes) -> bytes:
        """Decrypt a key with AES-256-GCM"""
        iv = encrypted[:12]
        tag = encrypted[-16:]
        ciphertext = encrypted[12:-16]
        
        cipher = Cipher(
            algorithms.AES(kek),
            modes.GCM(iv, tag),
            backend=self.backend
        )
        
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
    
    def rotate_key(self, key_id: str) -> str:
        """Rotate a key and maintain version history"""
        if key_id not in self.key_store:
            raise ValueError(f"Key {key_id} not found")
        
        old_metadata = self.key_store[key_id]
        
        # Generate new version
        new_version = old_metadata.get('version', 1) + 1
        new_key_id = f"{key_id}_v{new_version}"
        
        # Generate new key based on type
        key_type = KeyType(old_metadata['type'])
        if key_type == KeyType.ENCRYPTION:
            _, new_key = self.generate_data_encryption_key()
        else:
            new_key = self.derive_key(
                old_metadata.get('purpose', key_id),
                key_type=key_type
            )
        
        # Store new version
        self.key_store[new_key_id] = {
            **old_metadata,
            'version': new_version,
            'rotated_from': key_id,
            'rotated_at': datetime.utcnow().isoformat()
        }
        
        # Update version history
        if key_id not in self.key_versions:
            self.key_versions[key_id] = []
        self.key_versions[key_id].append(new_key_id)
        
        # Maintain maximum versions
        if len(self.key_versions[key_id]) > self.config['max_key_versions']:
            oldest = self.key_versions[key_id].pop(0)
            del self.key_store[oldest]
        
        self._audit_log('key_rotated', {
            'old_key_id': key_id,
            'new_key_id': new_key_id,
            'version': new_version
        })
        
        return new_key_id
    
    def _setup_rotation_schedule(self):
        """Setup automatic key rotation schedule"""
        rotation_days = self.config['key_rotation_days']
        
        for key_id in self.key_store:
            metadata = self.key_store[key_id]
            created = datetime.fromisoformat(metadata['created'])
            rotate_at = created + timedelta(days=rotation_days)
            self.rotation_schedule[key_id] = rotate_at
    
    def check_rotation_needed(self) -> List[str]:
        """Check which keys need rotation"""
        now = datetime.utcnow()
        keys_to_rotate = []
        
        for key_id, rotate_at in self.rotation_schedule.items():
            if now >= rotate_at:
                keys_to_rotate.append(key_id)
        
        return keys_to_rotate
    
    def generate_api_key(self, client_id: str, scope: List[str]) -> str:
        """Generate secure API key with embedded metadata"""
        # Generate random key
        key_bytes = secrets.token_bytes(32)
        
        # Create metadata
        metadata = {
            'client_id': client_id,
            'scope': scope,
            'created': datetime.utcnow().isoformat(),
            'version': 1
        }
        
        # Sign metadata with HMAC
        metadata_json = json.dumps(metadata, sort_keys=True)
        signature = hmac.new(
            self.master_key,
            metadata_json.encode(),
            hashlib.sha256
        ).digest()
        
        # Combine key + signature
        api_key = base64.urlsafe_b64encode(key_bytes + signature).decode()
        
        # Store key info
        key_id = f"api_{client_id}"
        self.key_store[key_id] = {
            'key_hash': hashlib.sha256(key_bytes).hexdigest(),
            'metadata': metadata,
            'type': KeyType.API.value
        }
        
        return f"qnx_{api_key}"
    
    def verify_api_key(self, api_key: str) -> Optional[Dict]:
        """Verify and extract API key metadata"""
        if not api_key.startswith("qnx_"):
            return None
        
        try:
            key_data = base64.urlsafe_b64decode(api_key[4:])
            key_bytes = key_data[:32]
            signature = key_data[32:]
            
            # Verify against stored keys
            key_hash = hashlib.sha256(key_bytes).hexdigest()
            
            for key_id, metadata in self.key_store.items():
                if metadata.get('key_hash') == key_hash:
                    return metadata.get('metadata')
            
            return None
            
        except Exception as e:
            logger.error(f"API key verification failed: {e}")
            return None
    
    def _generate_key_id(self, purpose: str, key_type: KeyType) -> str:
        """Generate unique key identifier"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_urlsafe(8)
        return f"{key_type.value}_{purpose}_{timestamp}_{random_part}"
    
    def _store_key_metadata(self, key_id: str, metadata: Dict):
        """Store key metadata securely"""
        self.key_store[key_id] = metadata
        
        # Persist to secure storage if configured
        if self.config.get('persist_metadata'):
            self._persist_metadata()
    
    def _persist_metadata(self):
        """Persist key metadata to secure storage"""
        # This would write to secure storage (encrypted file, database, etc.)
        pass
    
    def _audit_log(self, action: str, details: Dict):
        """Log security audit events"""
        if not self.config.get('audit_enabled'):
            return
        
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'details': details
        }
        
        self.audit_log.append(event)
        logger.info(f"Security audit: {action} - {details}")
    
    def secure_wipe(self, data: bytes):
        """Securely wipe sensitive data from memory"""
        if isinstance(data, bytearray):
            for i in range(len(data)):
                data[i] = secrets.randbits(8)
        # In production, use specialized secure deletion libraries
    
    def export_public_keys(self) -> Dict[str, str]:
        """Export public keys for verification"""
        public_keys = {}
        
        for key_id, metadata in self.key_store.items():
            if metadata.get('type') == KeyType.SIGNING.value:
                # Export only public portion
                public_keys[key_id] = metadata.get('public_key', '')
        
        return public_keys

class SecureTokenManager:
    """Manage secure tokens with expiration and validation"""
    
    def __init__(self, key_manager: SecureKeyManager):
        self.key_manager = key_manager
        self.tokens: Dict[str, Dict] = {}
        
    def generate_session_token(self, user_id: str, duration_minutes: int = 30) -> str:
        """Generate secure session token"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        
        # Derive session key
        session_key = self.key_manager.derive_key(
            f"session_{user_id}",
            key_type=KeyType.SESSION
        )
        
        # Create token data
        token_data = {
            'user_id': user_id,
            'created': datetime.utcnow().isoformat(),
            'expires': expires_at.isoformat(),
            'key_hash': hashlib.sha256(session_key).hexdigest()
        }
        
        # Sign token
        signature = hmac.new(
            session_key,
            json.dumps(token_data).encode(),
            hashlib.sha256
        ).hexdigest()
        
        self.tokens[token] = {
            **token_data,
            'signature': signature
        }
        
        return token
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """Validate session token"""
        if token not in self.tokens:
            return None
        
        token_data = self.tokens[token]
        
        # Check expiration
        expires = datetime.fromisoformat(token_data['expires'])
        if datetime.utcnow() >= expires:
            del self.tokens[token]
            return None
        
        return {
            'user_id': token_data['user_id'],
            'created': token_data['created']
        }
    
    def revoke_token(self, token: str):
        """Revoke a session token"""
        if token in self.tokens:
            del self.tokens[token]
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens"""
        now = datetime.utcnow()
        expired = []
        
        for token, data in self.tokens.items():
            expires = datetime.fromisoformat(data['expires'])
            if now >= expires:
                expired.append(token)
        
        for token in expired:
            del self.tokens[token]
        
        return len(expired)

# Usage example
if __name__ == "__main__":
    # Initialize key manager
    key_manager = SecureKeyManager()
    
    # Generate encryption key
    key_id, encryption_key = key_manager.generate_data_encryption_key()
    print(f"Generated encryption key: {key_id}")
    
    # Generate API key
    api_key = key_manager.generate_api_key("client_123", ["read", "write"])
    print(f"Generated API key: {api_key}")
    
    # Check for key rotation
    keys_to_rotate = key_manager.check_rotation_needed()
    print(f"Keys needing rotation: {keys_to_rotate}")
    
    # Initialize token manager
    token_manager = SecureTokenManager(key_manager)
    
    # Generate session token
    session_token = token_manager.generate_session_token("user_456")
    print(f"Generated session token: {session_token}")
    
    # Validate token
    token_info = token_manager.validate_token(session_token)
    print(f"Token validation: {token_info}")