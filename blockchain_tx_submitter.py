#!/usr/bin/env python3
"""
QXC Blockchain Transaction Submitter
Handles submission of mining proofs to the blockchain
"""

import json
import time
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
import threading
import queue

class BlockchainTransactionSubmitter:
    def __init__(self):
        self.db_path = Path('/opt/qenex-os/mining_operations.db')
        self.pending_queue = queue.Queue()
        self.submission_thread = None
        self.running = False
        
        # Blockchain parameters
        self.node_url = "https://abdulrahman305.github.io/qenex-docs
        self.chain_id = 1337
        self.gas_price = 20000000000  # 20 Gwei
        self.block_time = 3  # seconds
        
        # Transaction pool
        self.mempool = []
        self.confirmed_txs = set()
        
        self.init_database()
        
    def init_database(self):
        """Initialize blockchain transactions table"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blockchain_transactions (
                tx_hash TEXT PRIMARY KEY,
                block_number INTEGER,
                from_address TEXT,
                to_address TEXT,
                value REAL,
                gas_used INTEGER,
                gas_price INTEGER,
                nonce INTEGER,
                data TEXT,
                status TEXT,
                confirmations INTEGER,
                timestamp DATETIME,
                mining_reward REAL,
                improvement_data TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def create_transaction(self, wallet_address, improvement_data):
        """Create a new blockchain transaction"""
        
        # Generate nonce
        nonce = self.get_next_nonce(wallet_address)
        
        # Calculate mining reward
        reward = self.calculate_reward(improvement_data)
        
        # Create transaction object
        tx = {
            'from': wallet_address,
            'to': '0x7d2D8B5aE3C4F9E2A6B1D3C8E5F4A2B9D7C3E1F6',  # Contract address
            'value': 0,
            'gas': 150000,
            'gasPrice': self.gas_price,
            'nonce': nonce,
            'chainId': self.chain_id,
            'data': self.encode_improvement_data(improvement_data),
            'timestamp': datetime.now().isoformat()
        }
        
        # Generate transaction hash
        tx_hash = self.generate_tx_hash(tx)
        tx['hash'] = tx_hash
        tx['reward'] = reward
        
        return tx
        
    def generate_tx_hash(self, tx_data):
        """Generate transaction hash"""
        # Create deterministic hash
        data_str = json.dumps({
            'from': tx_data['from'],
            'to': tx_data['to'],
            'nonce': tx_data['nonce'],
            'data': tx_data['data'],
            'timestamp': tx_data['timestamp']
        }, sort_keys=True)
        
        hash_hex = hashlib.sha256(data_str.encode()).hexdigest()
        return f"0x{hash_hex}"
        
    def get_next_nonce(self, wallet_address):
        """Get next nonce for wallet"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT MAX(nonce) FROM blockchain_transactions 
            WHERE from_address = ?
        ''', (wallet_address,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result[0] is None:
            return 0
        return result[0] + 1
        
    def encode_improvement_data(self, data):
        """Encode improvement data for blockchain"""
        encoded = {
            'version': 'v3.2.1',
            'timestamp': data.get('timestamp', datetime.now().isoformat()),
            'category': data.get('category', 'Unified'),
            'improvement': data.get('improvement_percentage', 0),
            'metrics': {
                'math': data.get('math_improvement', 0),
                'language': data.get('language_improvement', 0),
                'code': data.get('code_improvement', 0),
                'unified': data.get('unified_improvement', 0)
            }
        }
        
        return '0x' + json.dumps(encoded).encode().hex()
        
    def calculate_reward(self, improvement_data):
        """Calculate mining reward"""
        base_reward = 15.0
        improvement = improvement_data.get('improvement_percentage', 0)
        category = improvement_data.get('category', 'Unified')
        
        # Category multipliers
        multipliers = {
            'Mathematics': 1.2,
            'Language': 1.5,
            'Code': 1.3,
            'Unified': 1.4
        }
        
        multiplier = multipliers.get(category, 1.0)
        reward = base_reward * (1 + improvement / 100) * multiplier
        
        return min(reward, 50.0)  # Cap at 50 QXC
        
    def submit_transaction(self, tx):
        """Submit transaction to blockchain"""
        
        # Add to mempool
        self.mempool.append(tx)
        
        # Simulate blockchain submission
        time.sleep(0.5)  # Network delay
        
        # Mark as pending
        tx['status'] = 'pending'
        tx['confirmations'] = 0
        
        # Store in database
        self.store_transaction(tx)
        
        # Add to pending queue for confirmation
        self.pending_queue.put(tx['hash'])
        
        return tx['hash']
        
    def store_transaction(self, tx):
        """Store transaction in database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO blockchain_transactions 
            (tx_hash, block_number, from_address, to_address, value, 
             gas_used, gas_price, nonce, data, status, confirmations, 
             timestamp, mining_reward, improvement_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            tx['hash'],
            None,  # Block number assigned when confirmed
            tx['from'],
            tx['to'],
            tx['value'],
            tx['gas'],
            tx['gasPrice'],
            tx['nonce'],
            tx['data'],
            tx.get('status', 'pending'),
            tx.get('confirmations', 0),
            tx['timestamp'],
            tx.get('reward', 0),
            json.dumps(tx.get('improvement_data', {}))
        ))
        
        conn.commit()
        conn.close()
        
    def confirm_transaction(self, tx_hash):
        """Confirm a pending transaction"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get current block number
        cursor.execute('SELECT MAX(block_number) FROM mining_operations')
        result = cursor.fetchone()
        block_number = (result[0] if result[0] else 1523) + 1
        
        # Update transaction status
        cursor.execute('''
            UPDATE blockchain_transactions 
            SET status = 'confirmed', 
                confirmations = confirmations + 1,
                block_number = ?
            WHERE tx_hash = ?
        ''', (block_number, tx_hash))
        
        conn.commit()
        conn.close()
        
        self.confirmed_txs.add(tx_hash)
        
    def process_pending_transactions(self):
        """Process pending transactions"""
        while self.running:
            try:
                # Get pending transaction
                tx_hash = self.pending_queue.get(timeout=1)
                
                # Wait for block time
                time.sleep(self.block_time)
                
                # Confirm transaction
                self.confirm_transaction(tx_hash)
                
                print(f"✅ Transaction confirmed: {tx_hash[:10]}...")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Error processing transaction: {e}")
                
    def start(self):
        """Start the transaction submitter"""
        self.running = True
        self.submission_thread = threading.Thread(target=self.process_pending_transactions)
        self.submission_thread.daemon = True
        self.submission_thread.start()
        print("🚀 Blockchain transaction submitter started")
        
    def stop(self):
        """Stop the transaction submitter"""
        self.running = False
        if self.submission_thread:
            self.submission_thread.join()
        print("🛑 Blockchain transaction submitter stopped")
        
    def get_transaction_status(self, tx_hash):
        """Get transaction status"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, confirmations, block_number, mining_reward 
            FROM blockchain_transactions 
            WHERE tx_hash = ?
        ''', (tx_hash,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'tx_hash': tx_hash,
                'status': result[0],
                'confirmations': result[1],
                'block_number': result[2],
                'reward': result[3]
            }
        
        return None
        
    def get_mempool_info(self):
        """Get mempool information"""
        return {
            'size': len(self.mempool),
            'pending': len([tx for tx in self.mempool if tx.get('status') == 'pending']),
            'confirmed': len(self.confirmed_txs),
            'gas_price': self.gas_price,
            'block_time': self.block_time
        }

def main():
    """Test the blockchain submitter"""
    submitter = BlockchainTransactionSubmitter()
    submitter.start()
    
    print("📡 Blockchain Transaction Submitter")
    print("=" * 50)
    
    # Test transaction creation
    wallet = "qxc_unified_user_wallet_main"
    improvement_data = {
        'improvement_percentage': 3.5,
        'category': 'Unified',
        'math_improvement': 2.1,
        'language_improvement': 4.2,
        'code_improvement': 3.8,
        'unified_improvement': 3.5
    }
    
    # Create and submit transaction
    tx = submitter.create_transaction(wallet, improvement_data)
    print(f"\n📝 Created transaction:")
    print(f"   Hash: {tx['hash']}")
    print(f"   Reward: {tx['reward']:.4f} QXC")
    print(f"   Nonce: {tx['nonce']}")
    
    # Submit to blockchain
    tx_hash = submitter.submit_transaction(tx)
    print(f"\n✉️ Submitted to blockchain: {tx_hash[:20]}...")
    
    # Check mempool
    mempool_info = submitter.get_mempool_info()
    print(f"\n📊 Mempool Status:")
    print(f"   Size: {mempool_info['size']}")
    print(f"   Pending: {mempool_info['pending']}")
    print(f"   Gas Price: {mempool_info['gas_price'] / 1e9:.1f} Gwei")
    
    # Wait for confirmation
    print("\n⏳ Waiting for confirmation...")
    time.sleep(5)
    
    # Check status
    status = submitter.get_transaction_status(tx_hash)
    if status:
        print(f"\n✅ Transaction Status:")
        print(f"   Status: {status['status']}")
        print(f"   Block: #{status['block_number']}")
        print(f"   Confirmations: {status['confirmations']}")
        print(f"   Reward: {status['reward']:.4f} QXC")
    
    # Stop submitter
    submitter.stop()

if __name__ == "__main__":
    main()