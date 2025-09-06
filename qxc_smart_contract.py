#!/usr/bin/env python3
"""
QXC Token Smart Contract Interface
Provides Web3 connectivity for QXC mining operations
"""

import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
import sqlite3

class QXCSmartContract:
    def __init__(self):
        # Contract configuration
        self.contract_address = "0x7d2D8B5aE3C4F9E2A6B1D3C8E5F4A2B9D7C3E1F6"
        self.chain_id = 1337  # Local development chain
        self.max_supply = 21000000
        self.current_supply = 384.8744
        
        # Initialize Web3 (local node simulation)
        self.w3 = self.init_web3()
        
        # Contract ABI
        self.abi = self.load_contract_abi()
        
        # Mining parameters
        self.base_reward = 15.0
        self.difficulty_adjustment = 0.95
        
    def init_web3(self):
        """Initialize Web3 connection"""
        # For production, this would connect to a real node
        # Currently simulating with local provider
        return {
            'connected': True,
            'chain_id': self.chain_id,
            'latest_block': 1523,
            'gas_price': 20000000000  # 20 Gwei
        }
    
    def load_contract_abi(self):
        """Load QXC token contract ABI"""
        return [
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_wallet", "type": "address"},
                    {"name": "_improvement", "type": "uint256"},
                    {"name": "_category", "type": "string"}
                ],
                "name": "minedWithImprovement",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]
    
    def calculate_mining_reward(self, improvement_percentage, category):
        """Calculate mining reward based on improvement"""
        base = self.base_reward
        
        # Category multipliers
        multipliers = {
            'Mathematics': 1.2,
            'Language': 1.5,
            'Code': 1.3,
            'Unified': 1.4
        }
        
        category_multiplier = multipliers.get(category, 1.0)
        
        # Calculate reward
        reward = base * (1 + improvement_percentage / 100) * category_multiplier
        
        # Apply difficulty adjustment
        reward *= self.difficulty_adjustment
        
        return min(reward, 50.0)  # Cap at 50 QXC per mine
    
    def submit_mining_proof(self, wallet_address, improvement_data):
        """Submit proof of improvement to blockchain"""
        
        # Generate transaction data
        tx_data = {
            'from': wallet_address,
            'to': self.contract_address,
            'value': 0,
            'gas': 150000,
            'gasPrice': self.w3['gas_price'],
            'nonce': int(time.time()),
            'data': self.encode_mining_data(improvement_data)
        }
        
        # Generate transaction hash
        tx_hash = self.generate_tx_hash(tx_data)
        
        # Simulate blockchain submission
        result = {
            'transactionHash': tx_hash,
            'blockNumber': self.w3['latest_block'] + 1,
            'gasUsed': 120000,
            'status': 1,  # Success
            'reward': self.calculate_mining_reward(
                improvement_data['improvement_percentage'],
                improvement_data['category']
            )
        }
        
        return result
    
    def encode_mining_data(self, data):
        """Encode mining data for blockchain"""
        encoded = json.dumps(data, sort_keys=True)
        return '0x' + encoded.encode().hex()
    
    def generate_tx_hash(self, tx_data):
        """Generate transaction hash"""
        data_str = json.dumps(tx_data, sort_keys=True)
        hash_hex = hashlib.sha256(data_str.encode()).hexdigest()
        return f"0x{hash_hex}"
    
    def get_token_info(self):
        """Get QXC token information"""
        return {
            'name': 'QENEX Coin',
            'symbol': 'QXC',
            'decimals': 18,
            'totalSupply': self.max_supply,
            'currentSupply': self.current_supply,
            'contractAddress': self.contract_address,
            'network': 'QENEX Network',
            'consensus': 'Proof of Improvement'
        }
    
    def get_wallet_balance(self, wallet_address):
        """Get wallet balance from blockchain"""
        # In production, this would query the actual blockchain
        # Currently reading from local database
        db_path = Path('/opt/qenex-os/mining_operations.db')
        
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT SUM(amount) FROM mining_operations 
                WHERE wallet_address = ? AND status = 'success'
            ''', (wallet_address,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result[0] else 0.0
        
        return 0.0
    
    def get_mining_history(self, wallet_address, limit=50):
        """Get mining history for wallet"""
        db_path = Path('/opt/qenex-os/mining_operations.db')
        
        if not db_path.exists():
            return []
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT transaction_hash, block_number, amount, 
                   improvement_percentage, category, timestamp, gas_used
            FROM mining_operations 
            WHERE wallet_address = ? AND status = 'success'
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (wallet_address, limit))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'transactionHash': row[0],
                'blockNumber': row[1],
                'amount': row[2],
                'improvement': row[3],
                'category': row[4],
                'timestamp': row[5],
                'gasUsed': row[6]
            })
        
        conn.close()
        return history
    
    def verify_transaction(self, tx_hash):
        """Verify a transaction on the blockchain"""
        # Simulate transaction verification
        return {
            'verified': True,
            'confirmations': 12,
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        }

def main():
    """Test the smart contract interface"""
    contract = QXCSmartContract()
    
    print("🔗 QXC Smart Contract Interface")
    print("=" * 50)
    
    # Display token info
    token_info = contract.get_token_info()
    print(f"📊 Token: {token_info['name']} ({token_info['symbol']})")
    print(f"💰 Max Supply: {token_info['totalSupply']:,} QXC")
    print(f"⛏️ Current Supply: {token_info['currentSupply']:.4f} QXC")
    print(f"📍 Contract: {token_info['contractAddress']}")
    
    # Test wallet balance
    wallet = "qxc_unified_user_wallet_main"
    balance = contract.get_wallet_balance(wallet)
    print(f"\n💳 Wallet Balance: {balance:.4f} QXC")
    
    # Test mining submission
    improvement_data = {
        'improvement_percentage': 2.5,
        'category': 'Unified',
        'model_version': 'v3.2.1',
        'timestamp': datetime.now().isoformat()
    }
    
    result = contract.submit_mining_proof(wallet, improvement_data)
    print(f"\n✅ Mining Submitted!")
    print(f"   TX Hash: {result['transactionHash']}")
    print(f"   Block: #{result['blockNumber']}")
    print(f"   Reward: {result['reward']:.4f} QXC")
    
    # Get recent history
    history = contract.get_mining_history(wallet, 5)
    if history:
        print(f"\n📜 Recent Mining History:")
        for tx in history:
            print(f"   {tx['transactionHash'][:10]}... | {tx['amount']:.2f} QXC | {tx['category']}")

if __name__ == "__main__":
    main()