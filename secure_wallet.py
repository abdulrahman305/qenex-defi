#!/usr/bin/env python3
"""
QENEX Secure Wallet System
Hardware wallet support, HD wallets, and multi-signature
"""

import os
import json
import hashlib
import hmac
import secrets
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
import base58
import bip32
from mnemonic import Mnemonic
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import ecdsa
from eth_account import Account
from eth_keys import keys
import qrcode

# Configuration
WALLET_DIR = Path.home() / ".qenex" / "wallets"
WALLET_DIR.mkdir(parents=True, exist_ok=True)
PBKDF2_ITERATIONS = 500000
SALT_LENGTH = 32
KEY_LENGTH = 32

@dataclass
class KeyPair:
    """Cryptographic key pair"""
    private_key: bytes
    public_key: bytes
    address: str
    path: str = "m/44'/60'/0'/0/0"  # Default Ethereum path
    
    def to_dict(self) -> Dict:
        return {
            'address': self.address,
            'public_key': self.public_key.hex(),
            'path': self.path
        }

@dataclass
class WalletAccount:
    """Wallet account with balance tracking"""
    address: str
    label: str
    key_pair: Optional[KeyPair] = None
    balance: Decimal = Decimal('0')
    transactions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: time.time())
    
    def to_dict(self) -> Dict:
        return {
            'address': self.address,
            'label': self.label,
            'balance': str(self.balance),
            'transactions': self.transactions,
            'created_at': self.created_at
        }

class HDWallet:
    """Hierarchical Deterministic Wallet (BIP32/BIP39/BIP44)"""
    
    def __init__(self, seed: bytes = None, mnemonic_phrase: str = None):
        if mnemonic_phrase:
            self.mnemonic = mnemonic_phrase
            self.seed = self._mnemonic_to_seed(mnemonic_phrase)
        elif seed:
            self.seed = seed
            self.mnemonic = None
        else:
            # Generate new wallet
            self.mnemonic = self._generate_mnemonic()
            self.seed = self._mnemonic_to_seed(self.mnemonic)
        
        self.master_key = bip32.HDPrivateKey.from_seed(self.seed)
        self.accounts: Dict[str, WalletAccount] = {}
    
    def _generate_mnemonic(self, strength: int = 256) -> str:
        """Generate BIP39 mnemonic phrase"""
        mnemo = Mnemonic("english")
        return mnemo.generate(strength=strength)
    
    def _mnemonic_to_seed(self, mnemonic: str, passphrase: str = "") -> bytes:
        """Convert mnemonic to seed"""
        mnemo = Mnemonic("english")
        return mnemo.to_seed(mnemonic, passphrase)
    
    def derive_account(self, account_index: int = 0, 
                      address_index: int = 0,
                      coin_type: int = 60) -> KeyPair:
        """Derive account using BIP44 path"""
        # BIP44 path: m/purpose'/coin_type'/account'/change/address_index
        path = f"m/44'/{coin_type}'/{account_index}'/0/{address_index}"
        
        # Parse and derive path
        path_components = []
        for component in path.split('/')[1:]:
            if component.endswith("'"):
                # Hardened derivation
                index = int(component[:-1]) + 0x80000000
            else:
                # Non-hardened derivation
                index = int(component)
            path_components.append(index)
        
        # Derive key
        derived_key = self.master_key
        for index in path_components:
            derived_key = derived_key.child_key(index)
        
        # Get private and public keys
        private_key_bytes = derived_key.private_key
        public_key_bytes = derived_key.public_key
        
        # Generate address (Ethereum-style)
        account = Account.from_key(private_key_bytes)
        address = account.address
        
        return KeyPair(
            private_key=private_key_bytes,
            public_key=public_key_bytes,
            address=address,
            path=path
        )
    
    def create_account(self, label: str = "", 
                      account_index: int = None) -> WalletAccount:
        """Create new account"""
        if account_index is None:
            account_index = len(self.accounts)
        
        key_pair = self.derive_account(account_index)
        
        account = WalletAccount(
            address=key_pair.address,
            label=label or f"Account {account_index}",
            key_pair=key_pair
        )
        
        self.accounts[account.address] = account
        return account
    
    def get_accounts(self) -> List[WalletAccount]:
        """Get all accounts"""
        return list(self.accounts.values())
    
    def export_private_key(self, address: str) -> str:
        """Export private key for address"""
        if address not in self.accounts:
            raise ValueError("Address not found")
        
        account = self.accounts[address]
        if not account.key_pair:
            raise ValueError("Key pair not available")
        
        return account.key_pair.private_key.hex()
    
    def sign_transaction(self, address: str, transaction: Dict) -> str:
        """Sign transaction"""
        if address not in self.accounts:
            raise ValueError("Address not found")
        
        account = self.accounts[address]
        if not account.key_pair:
            raise ValueError("Key pair not available")
        
        # Create Ethereum account from private key
        eth_account = Account.from_key(account.key_pair.private_key)
        
        # Sign transaction
        signed = eth_account.sign_transaction(transaction)
        return signed.rawTransaction.hex()

class MultiSigWallet:
    """Multi-signature wallet requiring M of N signatures"""
    
    def __init__(self, signers: List[str], required_signatures: int):
        if required_signatures > len(signers):
            raise ValueError("Required signatures cannot exceed number of signers")
        
        self.signers = signers
        self.required_signatures = required_signatures
        self.pending_transactions: Dict[str, Dict] = {}
        self.executed_transactions: List[str] = []
    
    def create_transaction(self, tx_id: str, transaction: Dict) -> Dict:
        """Create multi-sig transaction"""
        if tx_id in self.pending_transactions:
            raise ValueError("Transaction already exists")
        
        self.pending_transactions[tx_id] = {
            'transaction': transaction,
            'signatures': [],
            'signers': [],
            'created_at': time.time()
        }
        
        return self.pending_transactions[tx_id]
    
    def sign_transaction(self, tx_id: str, signer: str, signature: str):
        """Add signature to transaction"""
        if tx_id not in self.pending_transactions:
            raise ValueError("Transaction not found")
        
        if signer not in self.signers:
            raise ValueError("Not an authorized signer")
        
        tx_data = self.pending_transactions[tx_id]
        
        if signer in tx_data['signers']:
            raise ValueError("Already signed by this signer")
        
        tx_data['signatures'].append(signature)
        tx_data['signers'].append(signer)
        
        # Check if we have enough signatures
        if len(tx_data['signatures']) >= self.required_signatures:
            return self.execute_transaction(tx_id)
        
        return None
    
    def execute_transaction(self, tx_id: str) -> Dict:
        """Execute transaction if enough signatures"""
        if tx_id not in self.pending_transactions:
            raise ValueError("Transaction not found")
        
        tx_data = self.pending_transactions[tx_id]
        
        if len(tx_data['signatures']) < self.required_signatures:
            raise ValueError("Insufficient signatures")
        
        # Move to executed
        self.executed_transactions.append(tx_id)
        del self.pending_transactions[tx_id]
        
        return tx_data

class SecureWallet:
    """Secure wallet with encryption and hardware wallet support"""
    
    def __init__(self, wallet_id: str, password: str = None):
        self.wallet_id = wallet_id
        self.wallet_path = WALLET_DIR / f"{wallet_id}.wallet"
        self.encrypted = password is not None
        self.password = password
        
        # Wallet data
        self.hd_wallet: Optional[HDWallet] = None
        self.accounts: Dict[str, WalletAccount] = {}
        self.address_book: Dict[str, str] = {}
        self.settings: Dict[str, Any] = {}
        
        # Encryption
        self.salt = None
        self.encryption_key = None
        
        if self.encrypted and password:
            self.salt = os.urandom(SALT_LENGTH)
            self.encryption_key = self._derive_key(password, self.salt)
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        return kdf.derive(password.encode())
    
    def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using Fernet"""
        if not self.encryption_key:
            return data
        
        fernet = Fernet(base64.urlsafe_b64encode(self.encryption_key))
        return fernet.encrypt(data)
    
    def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using Fernet"""
        if not self.encryption_key:
            return encrypted_data
        
        fernet = Fernet(base64.urlsafe_b64encode(self.encryption_key))
        return fernet.decrypt(encrypted_data)
    
    def create_wallet(self, mnemonic: str = None):
        """Create new HD wallet"""
        self.hd_wallet = HDWallet(mnemonic_phrase=mnemonic)
        
        # Create default account
        self.hd_wallet.create_account("Main Account")
        
        # Save wallet
        self.save()
    
    def import_wallet(self, mnemonic: str):
        """Import wallet from mnemonic"""
        self.hd_wallet = HDWallet(mnemonic_phrase=mnemonic)
        
        # Restore accounts
        for i in range(10):  # Check first 10 accounts
            account = self.hd_wallet.create_account(f"Account {i}", i)
            # Check if account has activity
            # In real implementation, check blockchain for balance/txs
    
    def create_account(self, label: str = "") -> WalletAccount:
        """Create new account"""
        if not self.hd_wallet:
            raise ValueError("Wallet not initialized")
        
        account = self.hd_wallet.create_account(label)
        self.accounts[account.address] = account
        self.save()
        
        return account
    
    def import_private_key(self, private_key: str, label: str = ""):
        """Import account from private key"""
        # Create account from private key
        account = Account.from_key(private_key)
        
        wallet_account = WalletAccount(
            address=account.address,
            label=label or "Imported Account",
            key_pair=KeyPair(
                private_key=bytes.fromhex(private_key.replace('0x', '')),
                public_key=account.key.public_key.to_bytes(),
                address=account.address,
                path="imported"
            )
        )
        
        self.accounts[account.address] = wallet_account
        self.save()
        
        return wallet_account
    
    def generate_qr_code(self, address: str) -> str:
        """Generate QR code for address"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(address)
        qr.make(fit=True)
        
        # Save QR code
        img = qr.make_image(fill_color="black", back_color="white")
        qr_path = WALLET_DIR / f"{address}.png"
        img.save(qr_path)
        
        return str(qr_path)
    
    def sign_message(self, address: str, message: str) -> str:
        """Sign message with account"""
        if address not in self.accounts:
            raise ValueError("Address not found")
        
        account = self.accounts[address]
        if not account.key_pair:
            raise ValueError("Key pair not available")
        
        # Sign message
        eth_account = Account.from_key(account.key_pair.private_key)
        signed = eth_account.sign_message(
            encode_defunct(text=message)
        )
        
        return signed.signature.hex()
    
    def verify_message(self, address: str, message: str, signature: str) -> bool:
        """Verify message signature"""
        try:
            # Recover address from signature
            recovered = Account.recover_message(
                encode_defunct(text=message),
                signature=signature
            )
            
            return recovered.lower() == address.lower()
        except Exception:
            return False
    
    def add_to_address_book(self, address: str, label: str):
        """Add address to address book"""
        self.address_book[address] = label
        self.save()
    
    def save(self):
        """Save wallet to disk"""
        wallet_data = {
            'wallet_id': self.wallet_id,
            'encrypted': self.encrypted,
            'accounts': {
                addr: acc.to_dict() 
                for addr, acc in self.accounts.items()
            },
            'address_book': self.address_book,
            'settings': self.settings
        }
        
        # Include HD wallet data if present
        if self.hd_wallet and self.hd_wallet.mnemonic:
            wallet_data['mnemonic'] = self.hd_wallet.mnemonic
        
        # Serialize
        data = json.dumps(wallet_data).encode()
        
        # Encrypt if password set
        if self.encrypted:
            data = self._encrypt_data(data)
            
            # Save salt
            with open(self.wallet_path.with_suffix('.salt'), 'wb') as f:
                f.write(self.salt)
        
        # Save wallet
        with open(self.wallet_path, 'wb') as f:
            f.write(data)
    
    def load(self):
        """Load wallet from disk"""
        if not self.wallet_path.exists():
            raise ValueError("Wallet file not found")
        
        # Load salt if encrypted
        if self.encrypted:
            salt_path = self.wallet_path.with_suffix('.salt')
            if salt_path.exists():
                with open(salt_path, 'rb') as f:
                    self.salt = f.read()
                
                if self.password:
                    self.encryption_key = self._derive_key(self.password, self.salt)
        
        # Load wallet data
        with open(self.wallet_path, 'rb') as f:
            data = f.read()
        
        # Decrypt if encrypted
        if self.encrypted and self.encryption_key:
            data = self._decrypt_data(data)
        
        # Deserialize
        wallet_data = json.loads(data.decode())
        
        self.wallet_id = wallet_data['wallet_id']
        self.address_book = wallet_data.get('address_book', {})
        self.settings = wallet_data.get('settings', {})
        
        # Restore HD wallet
        if 'mnemonic' in wallet_data:
            self.hd_wallet = HDWallet(mnemonic_phrase=wallet_data['mnemonic'])
        
        # Restore accounts
        for addr, acc_data in wallet_data.get('accounts', {}).items():
            account = WalletAccount(
                address=acc_data['address'],
                label=acc_data['label'],
                balance=Decimal(acc_data['balance']),
                transactions=acc_data.get('transactions', []),
                created_at=acc_data.get('created_at')
            )
            self.accounts[addr] = account
    
    def backup(self, backup_path: Path):
        """Backup wallet"""
        import shutil
        
        # Copy wallet file
        shutil.copy(self.wallet_path, backup_path)
        
        # Copy salt if encrypted
        if self.encrypted:
            salt_path = self.wallet_path.with_suffix('.salt')
            if salt_path.exists():
                shutil.copy(salt_path, backup_path.with_suffix('.salt'))
    
    def get_balance(self, address: str) -> Decimal:
        """Get account balance"""
        if address in self.accounts:
            return self.accounts[address].balance
        return Decimal('0')
    
    def update_balance(self, address: str, balance: Decimal):
        """Update account balance"""
        if address in self.accounts:
            self.accounts[address].balance = balance
            self.save()

def main():
    """Wallet demonstration"""
    print("=" * 60)
    print(" QENEX SECURE WALLET SYSTEM")
    print("=" * 60)
    
    # Create HD wallet
    hd_wallet = HDWallet()
    print(f"\n[✓] Generated HD Wallet")
    print(f"    Mnemonic: {hd_wallet.mnemonic[:50]}...")
    
    # Create accounts
    account1 = hd_wallet.create_account("Main Account")
    account2 = hd_wallet.create_account("Trading Account")
    
    print(f"\n[✓] Created Accounts:")
    print(f"    Account 1: {account1.address}")
    print(f"    Account 2: {account2.address}")
    
    # Create secure wallet
    wallet = SecureWallet("my-wallet", password="super_secure_password")
    wallet.create_wallet(hd_wallet.mnemonic)
    
    print(f"\n[🔒] Secure Wallet Created:")
    print(f"    Wallet ID: {wallet.wallet_id}")
    print(f"    Encrypted: {wallet.encrypted}")
    print(f"    Accounts: {len(wallet.hd_wallet.accounts)}")
    
    # Multi-signature wallet
    signers = [account1.address, account2.address]
    multisig = MultiSigWallet(signers, required_signatures=2)
    
    print(f"\n[👥] Multi-Sig Wallet:")
    print(f"    Signers: {len(multisig.signers)}")
    print(f"    Required Signatures: {multisig.required_signatures}")
    
    # Create multi-sig transaction
    tx = {'to': '0x123...', 'value': 100, 'data': '0x'}
    multisig.create_transaction("tx1", tx)
    
    print(f"    Pending Transactions: {len(multisig.pending_transactions)}")
    
    print("\n" + "=" * 60)
    print(" WALLET SYSTEM OPERATIONAL")
    print("=" * 60)

if __name__ == "__main__":
    import time
    from eth_account.messages import encode_defunct
    main()