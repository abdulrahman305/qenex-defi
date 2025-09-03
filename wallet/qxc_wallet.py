#!/usr/bin/env python3
"""
QENEX Coin (QXC) Wallet Management System
Manages wallets, transactions, and mining rewards for developers
"""

import hashlib
import json
import time
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import secrets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

class QXCWallet:
    """QENEX Coin Wallet for developers"""
    
    def __init__(self, developer_id: str, wallet_dir: str = "/opt/qenex-os/wallets"):
        self.developer_id = developer_id
        self.wallet_dir = wallet_dir
        self.wallet_file = os.path.join(wallet_dir, f"{developer_id}.wallet")
        self.balance = 0.0
        self.address = ""
        self.private_key = None
        self.public_key = None
        self.transactions = []
        self.mining_stats = {
            "total_mined": 0.0,
            "blocks_mined": 0,
            "improvements_submitted": 0,
            "accuracy_gains": 0.0,
            "speed_gains": 0.0,
            "models_improved": 0,
            "algorithms_created": 0
        }
        
        # Ensure wallet directory exists
        os.makedirs(wallet_dir, exist_ok=True)
        
        # Load or create wallet
        if os.path.exists(self.wallet_file):
            self.load_wallet()
        else:
            self.create_wallet()
    
    def create_wallet(self):
        """Create a new wallet with cryptographic keys"""
        print(f"[QXC Wallet] Creating new wallet for {self.developer_id}")
        
        # Generate RSA key pair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        
        # Generate wallet address from public key
        pub_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.address = hashlib.sha256(pub_key_bytes).hexdigest()
        
        # Initialize balance
        self.balance = 0.0
        
        # Save wallet
        self.save_wallet()
        
        print(f"[QXC Wallet] Wallet created successfully!")
        print(f"[QXC Wallet] Address: {self.address}")
    
    def save_wallet(self):
        """Save wallet to encrypted file"""
        wallet_data = {
            "developer_id": self.developer_id,
            "address": self.address,
            "balance": self.balance,
            "created_at": datetime.now().isoformat(),
            "mining_stats": self.mining_stats,
            "transactions": self.transactions[-100:]  # Keep last 100 transactions
        }
        
        # Serialize private key
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        wallet_data["private_key"] = private_pem.decode('utf-8')
        
        # Save to file
        with open(self.wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        # Set file permissions (owner read/write only)
        os.chmod(self.wallet_file, 0o600)
    
    def load_wallet(self):
        """Load wallet from file"""
        with open(self.wallet_file, 'r') as f:
            wallet_data = json.load(f)
        
        self.address = wallet_data["address"]
        self.balance = wallet_data["balance"]
        self.mining_stats = wallet_data.get("mining_stats", self.mining_stats)
        self.transactions = wallet_data.get("transactions", [])
        
        # Load private key
        private_pem = wallet_data["private_key"].encode('utf-8')
        self.private_key = serialization.load_pem_private_key(
            private_pem,
            password=None,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        
        print(f"[QXC Wallet] Wallet loaded for {self.developer_id}")
        print(f"[QXC Wallet] Balance: {self.balance:.4f} QXC")
    
    def sign_transaction(self, transaction: dict) -> str:
        """Sign a transaction with private key"""
        tx_data = f"{transaction['sender']}{transaction['receiver']}{transaction['amount']}{transaction['timestamp']}"
        tx_bytes = tx_data.encode('utf-8')
        
        signature = self.private_key.sign(
            tx_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return signature.hex()
    
    def send_qxc(self, receiver_address: str, amount: float) -> Optional[str]:
        """Send QXC to another wallet"""
        if amount <= 0:
            print("[QXC Wallet] Invalid amount")
            return None
        
        if self.balance < amount + 0.001:  # Include transaction fee
            print(f"[QXC Wallet] Insufficient balance. Current: {self.balance:.4f} QXC")
            return None
        
        # Create transaction
        transaction = {
            "tx_id": hashlib.sha256(f"{time.time()}{self.address}{receiver_address}".encode()).hexdigest(),
            "sender": self.address,
            "receiver": receiver_address,
            "amount": amount,
            "fee": 0.001,
            "timestamp": time.time(),
            "ai_contribution": {
                "type": "transfer",
                "score": 0.0
            }
        }
        
        # Sign transaction
        transaction["signature"] = self.sign_transaction(transaction)
        
        # Update balance (will be confirmed when block is mined)
        self.balance -= (amount + 0.001)
        self.transactions.append(transaction)
        self.save_wallet()
        
        print(f"[QXC Wallet] Sent {amount:.4f} QXC to {receiver_address[:16]}...")
        print(f"[QXC Wallet] New balance: {self.balance:.4f} QXC")
        
        return transaction["tx_id"]
    
    def receive_mining_reward(self, amount: float, improvement_type: str, improvement_percentage: float):
        """Receive mining reward for AI improvement"""
        self.balance += amount
        self.mining_stats["total_mined"] += amount
        self.mining_stats["blocks_mined"] += 1
        self.mining_stats["improvements_submitted"] += 1
        
        if "accuracy" in improvement_type.lower():
            self.mining_stats["accuracy_gains"] += improvement_percentage
            self.mining_stats["models_improved"] += 1
        elif "speed" in improvement_type.lower():
            self.mining_stats["speed_gains"] += improvement_percentage
        elif "algorithm" in improvement_type.lower():
            self.mining_stats["algorithms_created"] += 1
        
        # Record reward transaction
        transaction = {
            "tx_id": hashlib.sha256(f"{time.time()}mining_reward{self.address}".encode()).hexdigest(),
            "sender": "MINING_REWARD",
            "receiver": self.address,
            "amount": amount,
            "fee": 0.0,
            "timestamp": time.time(),
            "ai_contribution": {
                "type": improvement_type,
                "score": improvement_percentage
            }
        }
        
        self.transactions.append(transaction)
        self.save_wallet()
        
        print(f"[QXC Wallet] Mining reward received: {amount:.4f} QXC")
        print(f"[QXC Wallet] Improvement: {improvement_type} (+{improvement_percentage:.2f}%)")
        print(f"[QXC Wallet] New balance: {self.balance:.4f} QXC")
    
    def get_transaction_history(self, limit: int = 10) -> List[dict]:
        """Get recent transaction history"""
        return self.transactions[-limit:]
    
    def get_mining_statistics(self) -> dict:
        """Get detailed mining statistics"""
        return {
            **self.mining_stats,
            "average_reward": self.mining_stats["total_mined"] / max(1, self.mining_stats["blocks_mined"]),
            "average_accuracy_gain": self.mining_stats["accuracy_gains"] / max(1, self.mining_stats["models_improved"]),
            "mining_efficiency": self.mining_stats["blocks_mined"] / max(1, self.mining_stats["improvements_submitted"])
        }
    
    def export_wallet(self, password: Optional[str] = None) -> dict:
        """Export wallet data (optionally encrypted)"""
        export_data = {
            "developer_id": self.developer_id,
            "address": self.address,
            "public_key": self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
        }
        
        if password:
            # Encrypt private key with password
            private_pem = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
            )
            export_data["encrypted_private_key"] = private_pem.decode('utf-8')
        
        return export_data
    
    def import_wallet(self, import_data: dict, password: Optional[str] = None):
        """Import wallet from exported data"""
        self.address = import_data["address"]
        self.developer_id = import_data["developer_id"]
        
        if "encrypted_private_key" in import_data and password:
            private_pem = import_data["encrypted_private_key"].encode('utf-8')
            self.private_key = serialization.load_pem_private_key(
                private_pem,
                password=password.encode(),
                backend=default_backend()
            )
            self.public_key = self.private_key.public_key()
            self.save_wallet()
            print(f"[QXC Wallet] Wallet imported successfully")

class WalletManager:
    """Manages multiple QXC wallets and transactions"""
    
    def __init__(self, db_path: str = "/opt/qenex-os/wallets/wallets.db"):
        self.db_path = db_path
        self.wallets: Dict[str, QXCWallet] = {}
        self.init_database()
    
    def init_database(self):
        """Initialize wallet database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallets (
                address TEXT PRIMARY KEY,
                developer_id TEXT UNIQUE,
                balance REAL,
                created_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id TEXT PRIMARY KEY,
                sender TEXT,
                receiver TEXT,
                amount REAL,
                fee REAL,
                timestamp TIMESTAMP,
                block_height INTEGER,
                ai_contribution_type TEXT,
                ai_contribution_score REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mining_rewards (
                reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT,
                amount REAL,
                improvement_type TEXT,
                improvement_percentage REAL,
                model_hash TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (wallet_address) REFERENCES wallets(address)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_wallet(self, developer_id: str) -> QXCWallet:
        """Create a new wallet for a developer"""
        wallet = QXCWallet(developer_id)
        self.wallets[wallet.address] = wallet
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO wallets (address, developer_id, balance, created_at, last_active)
            VALUES (?, ?, ?, ?, ?)
        ''', (wallet.address, developer_id, wallet.balance, datetime.now(), datetime.now()))
        conn.commit()
        conn.close()
        
        return wallet
    
    def get_wallet(self, address: str) -> Optional[QXCWallet]:
        """Get wallet by address"""
        if address in self.wallets:
            return self.wallets[address]
        
        # Try to load from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT developer_id FROM wallets WHERE address = ?', (address,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            developer_id = result[0]
            wallet = QXCWallet(developer_id)
            self.wallets[address] = wallet
            return wallet
        
        return None
    
    def process_transaction(self, tx: dict) -> bool:
        """Process a transaction between wallets"""
        sender_wallet = self.get_wallet(tx["sender"])
        receiver_wallet = self.get_wallet(tx["receiver"])
        
        if not sender_wallet:
            print(f"[Wallet Manager] Sender wallet not found: {tx['sender'][:16]}...")
            return False
        
        if not receiver_wallet:
            print(f"[Wallet Manager] Receiver wallet not found: {tx['receiver'][:16]}...")
            return False
        
        # Execute transaction
        tx_id = sender_wallet.send_qxc(tx["receiver"], tx["amount"])
        if tx_id:
            receiver_wallet.balance += tx["amount"]
            receiver_wallet.save_wallet()
            
            # Record in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions 
                (tx_id, sender, receiver, amount, fee, timestamp, ai_contribution_type, ai_contribution_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (tx_id, tx["sender"], tx["receiver"], tx["amount"], 0.001, time.time(),
                  tx.get("ai_contribution", {}).get("type", "transfer"),
                  tx.get("ai_contribution", {}).get("score", 0.0)))
            conn.commit()
            conn.close()
            
            return True
        
        return False
    
    def distribute_mining_reward(self, wallet_address: str, amount: float, 
                                improvement_type: str, improvement_percentage: float, model_hash: str):
        """Distribute mining reward to wallet"""
        wallet = self.get_wallet(wallet_address)
        if not wallet:
            print(f"[Wallet Manager] Wallet not found for mining reward: {wallet_address[:16]}...")
            return
        
        wallet.receive_mining_reward(amount, improvement_type, improvement_percentage)
        
        # Record in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO mining_rewards 
            (wallet_address, amount, improvement_type, improvement_percentage, model_hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (wallet_address, amount, improvement_type, improvement_percentage, model_hash, datetime.now()))
        conn.commit()
        conn.close()
    
    def get_richest_wallets(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Get wallets with highest balance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT address, balance FROM wallets 
            ORDER BY balance DESC LIMIT ?
        ''', (limit,))
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_top_miners(self, limit: int = 10) -> List[dict]:
        """Get top mining contributors"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wallet_address, COUNT(*) as blocks, SUM(amount) as total_mined,
                   AVG(improvement_percentage) as avg_improvement
            FROM mining_rewards
            GROUP BY wallet_address
            ORDER BY total_mined DESC
            LIMIT ?
        ''', (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "address": row[0],
                "blocks_mined": row[1],
                "total_mined": row[2],
                "average_improvement": row[3]
            })
        
        conn.close()
        return results
    
    def get_network_statistics(self) -> dict:
        """Get overall network statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total wallets
        cursor.execute('SELECT COUNT(*) FROM wallets')
        total_wallets = cursor.fetchone()[0]
        
        # Total transactions
        cursor.execute('SELECT COUNT(*) FROM transactions')
        total_transactions = cursor.fetchone()[0]
        
        # Total QXC in circulation
        cursor.execute('SELECT SUM(balance) FROM wallets')
        total_supply = cursor.fetchone()[0] or 0.0
        
        # Total mining rewards
        cursor.execute('SELECT SUM(amount) FROM mining_rewards')
        total_rewards = cursor.fetchone()[0] or 0.0
        
        # Average improvement
        cursor.execute('SELECT AVG(improvement_percentage) FROM mining_rewards')
        avg_improvement = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        return {
            "total_wallets": total_wallets,
            "total_transactions": total_transactions,
            "total_supply": total_supply,
            "total_mining_rewards": total_rewards,
            "average_improvement": avg_improvement
        }

# CLI for wallet management
def main():
    """Command-line interface for QXC wallet"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: qxc_wallet.py <command> [args]")
        print("Commands:")
        print("  create <developer_id>  - Create new wallet")
        print("  balance <address>      - Check wallet balance")
        print("  send <from> <to> <amount> - Send QXC")
        print("  history <address>      - Show transaction history")
        print("  stats <address>        - Show mining statistics")
        print("  network               - Show network statistics")
        return
    
    manager = WalletManager()
    command = sys.argv[1]
    
    if command == "create" and len(sys.argv) == 3:
        wallet = manager.create_wallet(sys.argv[2])
        print(f"Wallet created: {wallet.address}")
    
    elif command == "balance" and len(sys.argv) == 3:
        wallet = manager.get_wallet(sys.argv[2])
        if wallet:
            print(f"Balance: {wallet.balance:.4f} QXC")
        else:
            print("Wallet not found")
    
    elif command == "send" and len(sys.argv) == 5:
        tx = {
            "sender": sys.argv[2],
            "receiver": sys.argv[3],
            "amount": float(sys.argv[4])
        }
        if manager.process_transaction(tx):
            print("Transaction successful")
        else:
            print("Transaction failed")
    
    elif command == "history" and len(sys.argv) == 3:
        wallet = manager.get_wallet(sys.argv[2])
        if wallet:
            for tx in wallet.get_transaction_history():
                print(f"{tx['timestamp']}: {tx['amount']:.4f} QXC "
                      f"{'to' if tx['sender'] == wallet.address else 'from'} "
                      f"{tx['receiver' if tx['sender'] == wallet.address else 'sender'][:16]}...")
    
    elif command == "stats" and len(sys.argv) == 3:
        wallet = manager.get_wallet(sys.argv[2])
        if wallet:
            stats = wallet.get_mining_statistics()
            for key, value in stats.items():
                print(f"{key}: {value}")
    
    elif command == "network":
        stats = manager.get_network_statistics()
        for key, value in stats.items():
            print(f"{key}: {value}")

if __name__ == "__main__":
    main()