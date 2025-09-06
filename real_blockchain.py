#!/usr/bin/env python3
"""
QENEX Real Blockchain Implementation
Actual blockchain with proof of work and AI training mining
"""

import hashlib
import json
import time
import threading
import sqlite3
from datetime import datetime
from pathlib import Path
import random
import struct
import binascii

class Block:
    """Represents a single block in the blockchain"""
    
    def __init__(self, index, timestamp, data, previous_hash, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()
        
    def calculate_hash(self):
        """Calculate SHA-256 hash of the block"""
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty):
        """Mine the block with proof of work"""
        target = '0' * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        return self.hash

class QXCBlockchain:
    """Real blockchain implementation for QXC tokens"""
    
    def __init__(self):
        self.chain = []
        self.difficulty = 4  # Number of leading zeros required
        self.pending_transactions = []
        self.mining_reward = 15.0
        self.wallets = {}
        self.db_path = Path('/opt/qenex-os/real_blockchain.db')
        
        # Initialize database
        self.init_database()
        
        # Create genesis block
        self.create_genesis_block()
        
    def init_database(self):
        """Initialize blockchain database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Blockchain storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blockchain (
                block_index INTEGER PRIMARY KEY,
                timestamp DATETIME,
                data TEXT,
                previous_hash TEXT,
                nonce INTEGER,
                hash TEXT UNIQUE
            )
        ''')
        
        # Wallet balances
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallets (
                address TEXT PRIMARY KEY,
                balance REAL,
                public_key TEXT,
                created_at DATETIME
            )
        ''')
        
        # Transaction history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                tx_hash TEXT PRIMARY KEY,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                timestamp DATETIME,
                block_index INTEGER,
                ai_improvement REAL,
                category TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def create_genesis_block(self):
        """Create the first block in the chain"""
        genesis_block = Block(0, str(datetime.now()), {
            'message': 'Genesis Block',
            'reward': 0
        }, '0')
        genesis_block.hash = genesis_block.calculate_hash()
        self.chain.append(genesis_block)
        self.save_block(genesis_block)
        
    def get_latest_block(self):
        """Get the most recent block"""
        return self.chain[-1]
    
    def create_wallet(self):
        """Create a new wallet with public/private key pair"""
        # Generate wallet address (simplified - in reality would use ECDSA)
        private_key = hashlib.sha256(str(random.random()).encode()).hexdigest()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        address = 'qxc' + public_key[:40]
        
        # Initialize wallet with 0 balance
        self.wallets[address] = {
            'balance': 0.0,
            'public_key': public_key,
            'private_key': private_key,
            'created_at': datetime.now()
        }
        
        # Save to database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO wallets (address, balance, public_key, created_at)
            VALUES (?, ?, ?, ?)
        ''', (address, 0.0, public_key, datetime.now()))
        conn.commit()
        conn.close()
        
        return {
            'address': address,
            'private_key': private_key,
            'public_key': public_key
        }
    
    def get_balance(self, address):
        """Get wallet balance from blockchain"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Calculate balance from all transactions
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN to_address = ? THEN amount ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN from_address = ? THEN amount ELSE 0 END), 0)
            FROM transactions
        ''', (address, address))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result[0] else 0.0
    
    def create_transaction(self, from_address, to_address, amount, ai_improvement=0, category='transfer'):
        """Create a new transaction"""
        
        # Verify sender has sufficient balance
        if from_address != 'mining_reward':
            balance = self.get_balance(from_address)
            if balance < amount:
                raise ValueError(f"Insufficient balance. Available: {balance}, Required: {amount}")
        
        # Create transaction
        transaction = {
            'from': from_address,
            'to': to_address,
            'amount': amount,
            'timestamp': str(datetime.now()),
            'ai_improvement': ai_improvement,
            'category': category
        }
        
        # Generate transaction hash
        tx_string = json.dumps(transaction, sort_keys=True)
        tx_hash = hashlib.sha256(tx_string.encode()).hexdigest()
        transaction['tx_hash'] = tx_hash
        
        # Add to pending transactions
        self.pending_transactions.append(transaction)
        
        return tx_hash
    
    def mine_pending_transactions(self, mining_address, ai_improvement_data=None):
        """Mine pending transactions and create new block"""
        
        # Calculate mining reward based on AI improvement
        reward = self.calculate_mining_reward(ai_improvement_data)
        
        # Add mining reward transaction
        self.create_transaction(
            'mining_reward',
            mining_address,
            reward,
            ai_improvement_data.get('improvement', 0) if ai_improvement_data else 0,
            ai_improvement_data.get('category', 'mining') if ai_improvement_data else 'mining'
        )
        
        # Create new block with pending transactions
        block = Block(
            len(self.chain),
            str(datetime.now()),
            self.pending_transactions,
            self.get_latest_block().hash
        )
        
        # Mine the block (proof of work)
        print(f"⛏️ Mining block #{block.index}...")
        start_time = time.time()
        block.mine_block(self.difficulty)
        mining_time = time.time() - start_time
        
        # Add block to chain
        self.chain.append(block)
        
        # Save block and transactions to database
        self.save_block(block)
        self.save_transactions(block)
        
        # Clear pending transactions
        self.pending_transactions = []
        
        print(f"✅ Block #{block.index} mined in {mining_time:.2f}s")
        print(f"   Hash: {block.hash}")
        print(f"   Reward: {reward:.4f} QXC")
        
        return {
            'block_index': block.index,
            'hash': block.hash,
            'reward': reward,
            'mining_time': mining_time,
            'nonce': block.nonce
        }
    
    def calculate_mining_reward(self, ai_improvement_data):
        """Calculate mining reward based on actual AI improvement"""
        base_reward = self.mining_reward
        
        if not ai_improvement_data:
            return base_reward
        
        improvement = ai_improvement_data.get('improvement', 0)
        category = ai_improvement_data.get('category', 'general')
        
        # Category multipliers
        multipliers = {
            'mathematics': 1.2,
            'language': 1.5,
            'code': 1.3,
            'unified': 1.4,
            'general': 1.0
        }
        
        multiplier = multipliers.get(category.lower(), 1.0)
        
        # Calculate reward with improvement bonus
        reward = base_reward * (1 + improvement / 100) * multiplier
        
        # Halving schedule (every 1000 blocks)
        halvings = len(self.chain) // 1000
        reward = reward / (2 ** halvings)
        
        return min(reward, 50.0)  # Cap at 50 QXC
    
    def save_block(self, block):
        """Save block to database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO blockchain 
            (block_index, timestamp, data, previous_hash, nonce, hash)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            block.index,
            block.timestamp,
            json.dumps(block.data),
            block.previous_hash,
            block.nonce,
            block.hash
        ))
        
        conn.commit()
        conn.close()
    
    def save_transactions(self, block):
        """Save transactions from block to database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        for tx in block.data:
            cursor.execute('''
                INSERT OR IGNORE INTO transactions 
                (tx_hash, from_address, to_address, amount, timestamp, 
                 block_index, ai_improvement, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tx.get('tx_hash', ''),
                tx.get('from', ''),
                tx.get('to', ''),
                tx.get('amount', 0),
                tx.get('timestamp', ''),
                block.index,
                tx.get('ai_improvement', 0),
                tx.get('category', '')
            ))
        
        conn.commit()
        conn.close()
    
    def validate_chain(self):
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Check current block's hash
            if current.hash != current.calculate_hash():
                return False
            
            # Check link to previous block
            if current.previous_hash != previous.hash:
                return False
            
            # Check proof of work
            if current.hash[:self.difficulty] != '0' * self.difficulty:
                return False
        
        return True
    
    def get_chain_info(self):
        """Get blockchain statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get total mined
        cursor.execute('''
            SELECT SUM(amount) FROM transactions 
            WHERE from_address = 'mining_reward'
        ''')
        total_mined = cursor.fetchone()[0] or 0
        
        # Get transaction count
        cursor.execute('SELECT COUNT(*) FROM transactions')
        tx_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'height': len(self.chain),
            'difficulty': self.difficulty,
            'total_mined': total_mined,
            'transaction_count': tx_count,
            'is_valid': self.validate_chain(),
            'latest_block': {
                'index': self.get_latest_block().index,
                'hash': self.get_latest_block().hash,
                'timestamp': self.get_latest_block().timestamp
            }
        }

def main():
    """Test the real blockchain"""
    print("🔗 QENEX Real Blockchain")
    print("=" * 50)
    
    # Initialize blockchain
    blockchain = QXCBlockchain()
    
    # Create wallets
    print("\n📱 Creating wallets...")
    miner_wallet = blockchain.create_wallet()
    user_wallet = blockchain.create_wallet()
    
    print(f"⛏️ Miner wallet: {miner_wallet['address'][:20]}...")
    print(f"👤 User wallet: {user_wallet['address'][:20]}...")
    
    # Mine some blocks with AI improvement
    print("\n⚡ Starting mining operations...")
    
    for i in range(3):
        # Simulate AI improvement
        ai_data = {
            'improvement': random.uniform(0.5, 5.0),
            'category': random.choice(['mathematics', 'language', 'code', 'unified'])
        }
        
        print(f"\n📊 AI Improvement: {ai_data['improvement']:.2f}% ({ai_data['category']})")
        
        # Mine block
        result = blockchain.mine_pending_transactions(
            miner_wallet['address'],
            ai_data
        )
        
        # Check balance
        balance = blockchain.get_balance(miner_wallet['address'])
        print(f"💰 Miner balance: {balance:.4f} QXC")
    
    # Create a transfer transaction
    print("\n💸 Creating transfer transaction...")
    transfer_amount = 10.0
    
    try:
        tx_hash = blockchain.create_transaction(
            miner_wallet['address'],
            user_wallet['address'],
            transfer_amount
        )
        print(f"📝 Transaction created: {tx_hash[:20]}...")
        
        # Mine the transaction
        blockchain.mine_pending_transactions(miner_wallet['address'])
        
        # Check balances
        miner_balance = blockchain.get_balance(miner_wallet['address'])
        user_balance = blockchain.get_balance(user_wallet['address'])
        
        print(f"\n💳 Final balances:")
        print(f"   Miner: {miner_balance:.4f} QXC")
        print(f"   User: {user_balance:.4f} QXC")
        
    except ValueError as e:
        print(f"❌ Transaction failed: {e}")
    
    # Display chain info
    info = blockchain.get_chain_info()
    print(f"\n📊 Blockchain Statistics:")
    print(f"   Height: {info['height']} blocks")
    print(f"   Difficulty: {info['difficulty']}")
    print(f"   Total mined: {info['total_mined']:.4f} QXC")
    print(f"   Transactions: {info['transaction_count']}")
    print(f"   Valid: {'✅' if info['is_valid'] else '❌'}")
    print(f"   Latest: {info['latest_block']['hash'][:20]}...")

if __name__ == "__main__":
    main()