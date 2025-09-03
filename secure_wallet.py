#!/usr/bin/env python3
"""
QENEX Secure Wallet System
Encrypted wallet management with advanced security features
"""

import os
import json
import hashlib
import hmac
import secrets
import time
import sqlite3
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.fernet import Fernet
import base64

@dataclass
class SecureTransaction:
    """Secure transaction with digital signature"""
    tx_id: str
    sender: str
    recipient: str
    amount: float
    timestamp: float
    nonce: int
    signature: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def hash(self) -> str:
        """Calculate transaction hash"""
        data = f"{self.tx_id}{self.sender}{self.recipient}{self.amount}{self.timestamp}{self.nonce}"
        return hashlib.sha256(data.encode()).hexdigest()

class CryptoUtils:
    """Cryptographic utilities for wallet security"""
    
    @staticmethod
    def generate_salt() -> bytes:
        """Generate random salt"""
        return secrets.token_bytes(32)
    
    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """Derive encryption key from password"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    @staticmethod
    def encrypt_data(data: bytes, key: bytes) -> bytes:
        """Encrypt data using Fernet"""
        f = Fernet(key)
        return f.encrypt(data)
    
    @staticmethod
    def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt data using Fernet"""
        f = Fernet(key)
        return f.decrypt(encrypted_data)
    
    @staticmethod
    def generate_keypair() -> Tuple[str, str]:
        """Generate RSA keypair for signing"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem.decode(), public_pem.decode()
    
    @staticmethod
    def sign_data(data: bytes, private_key_pem: str) -> str:
        """Sign data with private key"""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
        
        signature = private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode()
    
    @staticmethod
    def verify_signature(data: bytes, signature: str, public_key_pem: str) -> bool:
        """Verify signature with public key"""
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),
                backend=default_backend()
            )
            
            public_key.verify(
                base64.b64decode(signature),
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except:
            return False

class SecureWallet:
    """Secure wallet with encryption and digital signatures"""
    
    def __init__(self, wallet_id: str, password: str = None):
        self.wallet_id = wallet_id
        self.wallet_dir = f"/opt/qenex-os/secure_wallets/{wallet_id}"
        self.password = password
        
        # Wallet data
        self.private_key = None
        self.public_key = None
        self.address = None
        self.balance = 0.0
        self.transactions = []
        
        # Security
        self.salt = None
        self.encryption_key = None
        self.locked = True
        
        # Create wallet directory
        os.makedirs(self.wallet_dir, exist_ok=True)
        
        # Load or create wallet
        if self.wallet_exists():
            self.load_wallet()
        else:
            self.create_wallet()
    
    def wallet_exists(self) -> bool:
        """Check if wallet files exist"""
        return os.path.exists(f"{self.wallet_dir}/wallet.enc")
    
    def create_wallet(self):
        """Create new wallet with encryption"""
        print(f"Creating new secure wallet: {self.wallet_id}")
        
        # Generate salt for key derivation
        self.salt = CryptoUtils.generate_salt()
        
        # Generate RSA keypair
        self.private_key, self.public_key = CryptoUtils.generate_keypair()
        
        # Generate wallet address from public key
        self.address = self.generate_address()
        
        # Set initial password if provided
        if self.password:
            self.set_password(self.password)
            self.save_wallet()
    
    def generate_address(self) -> str:
        """Generate wallet address from public key"""
        # Create address from public key hash
        pub_key_hash = hashlib.sha256(self.public_key.encode()).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(pub_key_hash)
        
        # Add version byte and checksum
        versioned = b'\x00' + ripemd160.digest()
        checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
        
        # Base58 encode
        address_bytes = versioned + checksum
        address = base64.b58encode(address_bytes).decode()
        
        return f"QXC{address[:32]}"  # QXC prefix for QENEX addresses
    
    def set_password(self, password: str):
        """Set wallet password and derive encryption key"""
        self.password = password
        self.encryption_key = CryptoUtils.derive_key(password, self.salt)
        self.locked = False
    
    def unlock(self, password: str) -> bool:
        """Unlock wallet with password"""
        try:
            # Derive key from password
            key = CryptoUtils.derive_key(password, self.salt)
            
            # Try to decrypt private key to verify password
            encrypted_data = open(f"{self.wallet_dir}/private_key.enc", 'rb').read()
            decrypted = CryptoUtils.decrypt_data(encrypted_data, key)
            
            # If successful, wallet is unlocked
            self.password = password
            self.encryption_key = key
            self.private_key = decrypted.decode()
            self.locked = False
            
            return True
        except:
            return False
    
    def lock(self):
        """Lock wallet"""
        self.password = None
        self.encryption_key = None
        self.locked = True
    
    def save_wallet(self):
        """Save wallet with encryption"""
        if self.locked or not self.encryption_key:
            raise Exception("Wallet is locked")
        
        # Save salt (not encrypted)
        with open(f"{self.wallet_dir}/salt", 'wb') as f:
            f.write(self.salt)
        
        # Save encrypted private key
        encrypted_private = CryptoUtils.encrypt_data(
            self.private_key.encode(),
            self.encryption_key
        )
        with open(f"{self.wallet_dir}/private_key.enc", 'wb') as f:
            f.write(encrypted_private)
        
        # Save public key (not encrypted)
        with open(f"{self.wallet_dir}/public_key.pem", 'w') as f:
            f.write(self.public_key)
        
        # Save wallet metadata (encrypted)
        metadata = {
            "wallet_id": self.wallet_id,
            "address": self.address,
            "created": time.time(),
            "balance": self.balance,
            "transaction_count": len(self.transactions)
        }
        
        encrypted_metadata = CryptoUtils.encrypt_data(
            json.dumps(metadata).encode(),
            self.encryption_key
        )
        with open(f"{self.wallet_dir}/wallet.enc", 'wb') as f:
            f.write(encrypted_metadata)
        
        print(f"Wallet saved securely: {self.address}")
    
    def load_wallet(self):
        """Load wallet from encrypted files"""
        # Load salt
        with open(f"{self.wallet_dir}/salt", 'rb') as f:
            self.salt = f.read()
        
        # Load public key
        with open(f"{self.wallet_dir}/public_key.pem", 'r') as f:
            self.public_key = f.read()
        
        # Generate address from public key
        self.address = self.generate_address()
        
        # Wallet remains locked until password provided
        self.locked = True
    
    def sign_transaction(self, transaction: SecureTransaction) -> str:
        """Sign transaction with private key"""
        if self.locked:
            raise Exception("Wallet is locked")
        
        # Sign transaction hash
        tx_data = transaction.hash().encode()
        signature = CryptoUtils.sign_data(tx_data, self.private_key)
        
        return signature
    
    def verify_transaction(self, transaction: SecureTransaction, signature: str, public_key: str) -> bool:
        """Verify transaction signature"""
        tx_data = transaction.hash().encode()
        return CryptoUtils.verify_signature(tx_data, signature, public_key)
    
    def create_transaction(self, recipient: str, amount: float) -> SecureTransaction:
        """Create and sign a transaction"""
        if self.locked:
            raise Exception("Wallet is locked")
        
        if amount > self.balance:
            raise Exception("Insufficient balance")
        
        # Create transaction
        tx = SecureTransaction(
            tx_id=hashlib.sha256(f"{time.time()}{secrets.token_hex(16)}".encode()).hexdigest(),
            sender=self.address,
            recipient=recipient,
            amount=amount,
            timestamp=time.time(),
            nonce=secrets.randbits(64)
        )
        
        # Sign transaction
        tx.signature = self.sign_transaction(tx)
        
        # Update balance (pending confirmation)
        self.balance -= amount
        self.transactions.append(tx)
        
        return tx
    
    def export_keys(self, password: str) -> Dict:
        """Export encrypted keys for backup"""
        if self.locked:
            raise Exception("Wallet is locked")
        
        if password != self.password:
            raise Exception("Invalid password")
        
        return {
            "wallet_id": self.wallet_id,
            "address": self.address,
            "encrypted_private_key": base64.b64encode(
                CryptoUtils.encrypt_data(self.private_key.encode(), self.encryption_key)
            ).decode(),
            "public_key": self.public_key,
            "salt": base64.b64encode(self.salt).decode()
        }
    
    def import_keys(self, backup: Dict, password: str):
        """Import keys from backup"""
        self.wallet_id = backup["wallet_id"]
        self.address = backup["address"]
        self.public_key = backup["public_key"]
        self.salt = base64.b64decode(backup["salt"])
        
        # Derive key and decrypt private key
        self.encryption_key = CryptoUtils.derive_key(password, self.salt)
        encrypted_private = base64.b64decode(backup["encrypted_private_key"])
        
        try:
            self.private_key = CryptoUtils.decrypt_data(
                encrypted_private,
                self.encryption_key
            ).decode()
            self.password = password
            self.locked = False
            self.save_wallet()
            return True
        except:
            return False
    
    def get_info(self) -> Dict:
        """Get wallet information"""
        return {
            "wallet_id": self.wallet_id,
            "address": self.address,
            "balance": self.balance,
            "locked": self.locked,
            "transaction_count": len(self.transactions)
        }

class WalletManager:
    """Manage multiple secure wallets"""
    
    def __init__(self):
        self.wallets_dir = "/opt/qenex-os/secure_wallets"
        self.db_path = f"{self.wallets_dir}/wallets.db"
        os.makedirs(self.wallets_dir, exist_ok=True)
        self._init_database()
        
        # Active wallets
        self.wallets: Dict[str, SecureWallet] = {}
    
    def _init_database(self):
        """Initialize wallet database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS wallets (
                    wallet_id TEXT PRIMARY KEY,
                    address TEXT UNIQUE,
                    created REAL,
                    last_accessed REAL,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    tx_id TEXT PRIMARY KEY,
                    sender TEXT,
                    recipient TEXT,
                    amount REAL,
                    timestamp REAL,
                    signature TEXT,
                    confirmed INTEGER DEFAULT 0
                )
            ''')
    
    def create_wallet(self, wallet_id: str, password: str) -> SecureWallet:
        """Create new secure wallet"""
        wallet = SecureWallet(wallet_id, password)
        self.wallets[wallet_id] = wallet
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO wallets (wallet_id, address, created, last_accessed, metadata) VALUES (?, ?, ?, ?, ?)',
                (wallet_id, wallet.address, time.time(), time.time(), json.dumps({}))
            )
        
        return wallet
    
    def load_wallet(self, wallet_id: str) -> Optional[SecureWallet]:
        """Load existing wallet"""
        if wallet_id in self.wallets:
            return self.wallets[wallet_id]
        
        wallet = SecureWallet(wallet_id)
        if wallet.wallet_exists():
            self.wallets[wallet_id] = wallet
            
            # Update last accessed
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'UPDATE wallets SET last_accessed = ? WHERE wallet_id = ?',
                    (time.time(), wallet_id)
                )
            
            return wallet
        
        return None
    
    def list_wallets(self) -> List[Dict]:
        """List all wallets"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT wallet_id, address, created, last_accessed FROM wallets')
            return [{
                "wallet_id": row[0],
                "address": row[1],
                "created": row[2],
                "last_accessed": row[3]
            } for row in cursor]
    
    def delete_wallet(self, wallet_id: str, password: str) -> bool:
        """Delete wallet (requires password)"""
        wallet = self.load_wallet(wallet_id)
        if wallet and wallet.unlock(password):
            # Remove from database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM wallets WHERE wallet_id = ?', (wallet_id,))
            
            # Remove files
            import shutil
            shutil.rmtree(wallet.wallet_dir)
            
            # Remove from active wallets
            if wallet_id in self.wallets:
                del self.wallets[wallet_id]
            
            return True
        
        return False
    
    def backup_all_wallets(self, backup_password: str) -> Dict:
        """Backup all wallets"""
        backup = {
            "version": "1.0",
            "timestamp": time.time(),
            "wallets": []
        }
        
        for wallet_info in self.list_wallets():
            wallet = self.load_wallet(wallet_info["wallet_id"])
            if wallet and not wallet.locked:
                backup["wallets"].append(wallet.export_keys(wallet.password))
        
        # Encrypt entire backup
        backup_json = json.dumps(backup).encode()
        salt = CryptoUtils.generate_salt()
        key = CryptoUtils.derive_key(backup_password, salt)
        encrypted = CryptoUtils.encrypt_data(backup_json, key)
        
        return {
            "encrypted_backup": base64.b64encode(encrypted).decode(),
            "salt": base64.b64encode(salt).decode()
        }
    
    def restore_backup(self, backup_data: Dict, backup_password: str) -> bool:
        """Restore wallets from backup"""
        try:
            # Decrypt backup
            encrypted = base64.b64decode(backup_data["encrypted_backup"])
            salt = base64.b64decode(backup_data["salt"])
            key = CryptoUtils.derive_key(backup_password, salt)
            decrypted = CryptoUtils.decrypt_data(encrypted, key)
            
            # Parse backup
            backup = json.loads(decrypted.decode())
            
            # Restore each wallet
            for wallet_data in backup["wallets"]:
                wallet = SecureWallet(wallet_data["wallet_id"])
                if wallet.import_keys(wallet_data, backup_password):
                    self.wallets[wallet_data["wallet_id"]] = wallet
            
            return True
        except:
            return False

# Example usage
def main():
    """Test secure wallet system"""
    manager = WalletManager()
    
    # Create wallets
    print("Creating secure wallets...")
    wallet1 = manager.create_wallet("alice_wallet", "AlicePassword123!")
    wallet2 = manager.create_wallet("bob_wallet", "BobPassword456!")
    
    print(f"\nAlice's address: {wallet1.address}")
    print(f"Bob's address: {wallet2.address}")
    
    # Create and sign transaction
    wallet1.balance = 100.0  # Set balance for testing
    tx = wallet1.create_transaction(wallet2.address, 10.0)
    
    print(f"\nTransaction created:")
    print(f"  From: {tx.sender}")
    print(f"  To: {tx.recipient}")
    print(f"  Amount: {tx.amount} QXC")
    print(f"  Signature: {tx.signature[:32]}...")
    
    # Verify transaction
    is_valid = wallet2.verify_transaction(tx, tx.signature, wallet1.public_key)
    print(f"  Signature valid: {is_valid}")
    
    # Lock and unlock wallet
    wallet1.lock()
    print(f"\nWallet locked: {wallet1.locked}")
    
    if wallet1.unlock("AlicePassword123!"):
        print("Wallet unlocked successfully")
    
    # Backup wallets
    print("\nCreating backup...")
    backup = manager.backup_all_wallets("MasterBackupPassword")
    print(f"Backup size: {len(backup['encrypted_backup'])} bytes")
    
    # List wallets
    print("\nAll wallets:")
    for wallet_info in manager.list_wallets():
        print(f"  - {wallet_info['wallet_id']}: {wallet_info['address']}")

if __name__ == "__main__":
    main()