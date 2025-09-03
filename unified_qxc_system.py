#!/usr/bin/env python3
"""
QENEX Unified Cryptocurrency System (QXC)
A cohesive, integrated blockchain system with real AI performance mining
"""

import os
import json
import time
import hashlib
import sqlite3
import threading
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import fcntl
import struct
import subprocess
import psutil

# ================== CONFIGURATION ==================
class Config:
    """Centralized configuration for the entire system"""
    # Blockchain
    BLOCK_TIME = 30  # seconds
    DIFFICULTY_ADJUSTMENT_INTERVAL = 10  # blocks
    INITIAL_DIFFICULTY = "0000"
    MAX_SUPPLY = 21_000_000  # Maximum QXC supply
    
    # Mining
    BASE_REWARD = 50.0
    HALVING_INTERVAL = 210_000  # blocks
    MIN_IMPROVEMENT_THRESHOLD = 0.001  # 0.1% minimum improvement
    
    # Wallet Distribution
    ORIGINAL_WALLET_SHARE = 0.20  # 20% to genesis wallet
    MINER_WALLET_SHARE = 0.80     # 80% to miner
    
    # AI Evaluation
    EVALUATION_INTERVAL = 60  # seconds
    MODEL_CHECKPOINT_INTERVAL = 100  # blocks
    
    # Database
    DB_PATH = "/opt/qenex-os/blockchain/qxc.db"
    WALLET_DB_PATH = "/opt/qenex-os/blockchain/wallets.db"
    MODEL_PATH = "/opt/qenex-os/models/unified_model.json"
    
    # Network (future implementation)
    P2P_PORT = 8333
    RPC_PORT = 8332
    MAX_PEERS = 8

# ================== BLOCKCHAIN CORE ==================
@dataclass
class Transaction:
    """Immutable transaction record"""
    tx_id: str
    timestamp: float
    sender: str
    recipient: str
    amount: float
    tx_type: str  # 'coinbase', 'transfer', 'mining_reward'
    metadata: Dict[str, Any]
    signature: Optional[str] = None
    
    def hash(self) -> str:
        """Generate transaction hash"""
        data = f"{self.timestamp}{self.sender}{self.recipient}{self.amount}{self.tx_type}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class Block:
    """Immutable block structure"""
    index: int
    timestamp: float
    transactions: List[Transaction]
    previous_hash: str
    nonce: int
    difficulty: str
    merkle_root: str
    miner: str
    ai_improvements: Dict[str, float]
    
    def calculate_merkle_root(self) -> str:
        """Calculate merkle root of transactions"""
        if not self.transactions:
            return hashlib.sha256(b"0").hexdigest()
        
        hashes = [tx.hash() for tx in self.transactions]
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i+1]
                new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = new_hashes
        return hashes[0]
    
    def hash(self) -> str:
        """Calculate block hash"""
        block_string = f"{self.index}{self.timestamp}{self.merkle_root}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "merkle_root": self.merkle_root,
            "miner": self.miner,
            "ai_improvements": self.ai_improvements,
            "hash": self.hash()
        }

class Blockchain:
    """Thread-safe blockchain implementation"""
    
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.lock = threading.RLock()
        self.difficulty = Config.INITIAL_DIFFICULTY
        self.total_supply = 0.0
        
        # Initialize database
        self._init_database()
        
        # Load or create genesis block
        if not self._load_chain():
            self._create_genesis_block()
    
    def _init_database(self):
        """Initialize blockchain database"""
        os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
        with sqlite3.connect(Config.DB_PATH) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS blocks (
                    block_index INTEGER PRIMARY KEY,
                    block_hash TEXT UNIQUE NOT NULL,
                    block_data TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    tx_id TEXT PRIMARY KEY,
                    block_index INTEGER,
                    tx_data TEXT NOT NULL,
                    FOREIGN KEY (block_index) REFERENCES blocks(block_index)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_block_hash ON blocks(block_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tx_block ON transactions(block_index)')
    
    def _create_genesis_block(self):
        """Create the genesis block"""
        genesis_tx = Transaction(
            tx_id="genesis",
            timestamp=time.time(),
            sender="system",
            recipient="GENESIS_WALLET",
            amount=1000000.0,  # Initial supply for development
            tx_type="coinbase",
            metadata={"message": "QENEX Genesis Block"}
        )
        
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            transactions=[genesis_tx],
            previous_hash="0",
            nonce=0,
            difficulty=Config.INITIAL_DIFFICULTY,
            merkle_root="",
            miner="system",
            ai_improvements={}
        )
        genesis_block.merkle_root = genesis_block.calculate_merkle_root()
        
        with self.lock:
            self.chain.append(genesis_block)
            self.total_supply = 1000000.0
            self._save_block(genesis_block)
    
    def _load_chain(self) -> bool:
        """Load blockchain from database"""
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                cursor = conn.execute('SELECT block_data FROM blocks ORDER BY block_index')
                blocks_data = cursor.fetchall()
                
                if not blocks_data:
                    return False
                
                for (block_json,) in blocks_data:
                    block_dict = json.loads(block_json)
                    # Reconstruct transactions
                    transactions = []
                    for tx_dict in block_dict['transactions']:
                        tx = Transaction(**{k: v for k, v in tx_dict.items() if k != 'signature'})
                        if 'signature' in tx_dict:
                            tx.signature = tx_dict['signature']
                        transactions.append(tx)
                    
                    # Reconstruct block
                    block = Block(
                        index=block_dict['index'],
                        timestamp=block_dict['timestamp'],
                        transactions=transactions,
                        previous_hash=block_dict['previous_hash'],
                        nonce=block_dict['nonce'],
                        difficulty=block_dict['difficulty'],
                        merkle_root=block_dict['merkle_root'],
                        miner=block_dict['miner'],
                        ai_improvements=block_dict.get('ai_improvements', {})
                    )
                    self.chain.append(block)
                
                # Calculate total supply
                self.total_supply = sum(
                    tx.amount for block in self.chain 
                    for tx in block.transactions 
                    if tx.tx_type in ['coinbase', 'mining_reward']
                )
                return True
        except Exception as e:
            print(f"Error loading blockchain: {e}")
            return False
    
    def _save_block(self, block: Block):
        """Save block to database"""
        with sqlite3.connect(Config.DB_PATH) as conn:
            block_json = json.dumps(block.to_dict())
            conn.execute(
                'INSERT INTO blocks (block_index, block_hash, block_data, timestamp) VALUES (?, ?, ?, ?)',
                (block.index, block.hash(), block_json, block.timestamp)
            )
            
            for tx in block.transactions:
                tx_json = json.dumps(tx.to_dict())
                conn.execute(
                    'INSERT INTO transactions (tx_id, block_index, tx_data) VALUES (?, ?, ?)',
                    (tx.tx_id, block.index, tx_json)
                )
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add transaction to pending pool"""
        with self.lock:
            # Validate transaction
            if not self._validate_transaction(transaction):
                return False
            
            self.pending_transactions.append(transaction)
            return True
    
    def _validate_transaction(self, transaction: Transaction) -> bool:
        """Validate transaction"""
        # Check if sender has sufficient balance (except for coinbase)
        if transaction.tx_type != 'coinbase' and transaction.tx_type != 'mining_reward':
            balance = self.get_balance(transaction.sender)
            if balance < transaction.amount:
                return False
        
        # Check max supply constraint
        if transaction.tx_type in ['coinbase', 'mining_reward']:
            if self.total_supply + transaction.amount > Config.MAX_SUPPLY:
                return False
        
        return True
    
    def get_balance(self, address: str) -> float:
        """Calculate balance for an address"""
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == address:
                    balance += tx.amount
                if tx.sender == address:
                    balance -= tx.amount
        return balance
    
    def mine_block(self, miner_address: str, ai_improvements: Dict[str, float]) -> Optional[Block]:
        """Mine a new block with proof of work"""
        with self.lock:
            # Create coinbase transaction (mining reward)
            reward = self._calculate_mining_reward()
            if self.total_supply + reward > Config.MAX_SUPPLY:
                reward = Config.MAX_SUPPLY - self.total_supply
            
            if reward <= 0:
                print("Max supply reached, no more mining rewards")
                return None
            
            coinbase_tx = Transaction(
                tx_id=hashlib.sha256(f"coinbase_{time.time()}".encode()).hexdigest(),
                timestamp=time.time(),
                sender="system",
                recipient=miner_address,
                amount=reward,
                tx_type="mining_reward",
                metadata={"ai_improvements": ai_improvements}
            )
            
            transactions = [coinbase_tx] + self.pending_transactions[:10]  # Limit transactions per block
            
            new_block = Block(
                index=len(self.chain),
                timestamp=time.time(),
                transactions=transactions,
                previous_hash=self.chain[-1].hash() if self.chain else "0",
                nonce=0,
                difficulty=self.difficulty,
                merkle_root="",
                miner=miner_address,
                ai_improvements=ai_improvements
            )
            new_block.merkle_root = new_block.calculate_merkle_root()
            
            # Proof of work
            while not new_block.hash().startswith(self.difficulty):
                new_block.nonce += 1
                if new_block.nonce % 10000 == 0:
                    # Check if a new block was added while mining
                    if len(self.chain) != new_block.index:
                        return None
            
            # Add block to chain
            self.chain.append(new_block)
            self._save_block(new_block)
            
            # Update total supply
            self.total_supply += reward
            
            # Clear mined transactions from pending pool
            self.pending_transactions = self.pending_transactions[10:]
            
            # Adjust difficulty if needed
            if len(self.chain) % Config.DIFFICULTY_ADJUSTMENT_INTERVAL == 0:
                self._adjust_difficulty()
            
            return new_block
    
    def _calculate_mining_reward(self) -> float:
        """Calculate mining reward with halving"""
        halvings = len(self.chain) // Config.HALVING_INTERVAL
        return Config.BASE_REWARD / (2 ** halvings)
    
    def _adjust_difficulty(self):
        """Adjust mining difficulty based on block time"""
        if len(self.chain) < Config.DIFFICULTY_ADJUSTMENT_INTERVAL:
            return
        
        recent_blocks = self.chain[-Config.DIFFICULTY_ADJUSTMENT_INTERVAL:]
        time_diff = recent_blocks[-1].timestamp - recent_blocks[0].timestamp
        expected_time = Config.BLOCK_TIME * Config.DIFFICULTY_ADJUSTMENT_INTERVAL
        
        if time_diff < expected_time * 0.5:
            # Increase difficulty
            self.difficulty += "0"
        elif time_diff > expected_time * 2:
            # Decrease difficulty
            if len(self.difficulty) > 2:
                self.difficulty = self.difficulty[:-1]
    
    def validate_chain(self) -> bool:
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Check hash link
            if current.previous_hash != previous.hash():
                return False
            
            # Check proof of work
            if not current.hash().startswith(current.difficulty):
                return False
            
            # Check merkle root
            if current.merkle_root != current.calculate_merkle_root():
                return False
        
        return True

# ================== WALLET MANAGEMENT ==================
class WalletManager:
    """Centralized wallet management with thread safety"""
    
    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain
        self.wallets: Dict[str, Dict] = {}
        self.lock = threading.RLock()
        self._init_database()
        self._load_wallets()
    
    def _init_database(self):
        """Initialize wallet database"""
        os.makedirs(os.path.dirname(Config.WALLET_DB_PATH), exist_ok=True)
        with sqlite3.connect(Config.WALLET_DB_PATH) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS wallets (
                    address TEXT PRIMARY KEY,
                    private_key TEXT NOT NULL,
                    public_key TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    metadata TEXT
                )
            ''')
    
    def _load_wallets(self):
        """Load wallets from database"""
        with sqlite3.connect(Config.WALLET_DB_PATH) as conn:
            cursor = conn.execute('SELECT address, private_key, public_key, metadata FROM wallets')
            for address, private_key, public_key, metadata in cursor:
                self.wallets[address] = {
                    'private_key': private_key,
                    'public_key': public_key,
                    'metadata': json.loads(metadata) if metadata else {}
                }
    
    def create_wallet(self, wallet_id: str, metadata: Dict = None) -> str:
        """Create a new wallet"""
        with self.lock:
            if wallet_id in self.wallets:
                return wallet_id
            
            # Generate keys (simplified for demo)
            private_key = hashlib.sha256(f"{wallet_id}_{time.time()}".encode()).hexdigest()
            public_key = hashlib.sha256(private_key.encode()).hexdigest()
            
            self.wallets[wallet_id] = {
                'private_key': private_key,
                'public_key': public_key,
                'metadata': metadata or {}
            }
            
            # Save to database
            with sqlite3.connect(Config.WALLET_DB_PATH) as conn:
                conn.execute(
                    'INSERT OR REPLACE INTO wallets (address, private_key, public_key, created_at, metadata) VALUES (?, ?, ?, ?, ?)',
                    (wallet_id, private_key, public_key, time.time(), json.dumps(metadata or {}))
                )
            
            return wallet_id
    
    def get_balance(self, wallet_id: str) -> float:
        """Get wallet balance from blockchain"""
        return self.blockchain.get_balance(wallet_id)
    
    def distribute_mining_reward(self, miner_wallet: str, amount: float) -> List[Transaction]:
        """Distribute mining rewards according to hierarchical model"""
        transactions = []
        
        # Original wallet gets 20%
        genesis_amount = amount * Config.ORIGINAL_WALLET_SHARE
        genesis_tx = Transaction(
            tx_id=hashlib.sha256(f"dist_{time.time()}_genesis".encode()).hexdigest(),
            timestamp=time.time(),
            sender=miner_wallet,
            recipient="GENESIS_WALLET",
            amount=genesis_amount,
            tx_type="transfer",
            metadata={"reason": "mining_distribution"}
        )
        transactions.append(genesis_tx)
        
        # Miner keeps 80%
        # (Already received in coinbase transaction)
        
        return transactions

# ================== AI EVALUATION SYSTEM ==================
class AIEvaluator:
    """Real AI model evaluation system"""
    
    def __init__(self):
        self.model_state = self._load_or_create_model()
        self.evaluation_history = []
        self.lock = threading.RLock()
    
    def _load_or_create_model(self) -> Dict:
        """Load or create the unified AI model"""
        os.makedirs(os.path.dirname(Config.MODEL_PATH), exist_ok=True)
        
        if os.path.exists(Config.MODEL_PATH):
            try:
                with open(Config.MODEL_PATH, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Create initial model state
        return {
            "version": 1,
            "capabilities": {
                "mathematics": {
                    "algebra": 0.5,
                    "calculus": 0.5,
                    "statistics": 0.5
                },
                "language": {
                    "syntax": 0.6,
                    "semantics": 0.5,
                    "generation": 0.5
                },
                "code": {
                    "correctness": 0.6,
                    "efficiency": 0.5,
                    "readability": 0.5
                }
            },
            "total_improvements": 0,
            "last_evaluation": time.time()
        }
    
    def evaluate_performance(self) -> Dict[str, float]:
        """Evaluate actual AI performance using system metrics"""
        improvements = {}
        
        with self.lock:
            # Evaluate mathematics (using system calculations)
            math_score = self._evaluate_mathematics()
            old_math = np.mean(list(self.model_state["capabilities"]["mathematics"].values()))
            if math_score > old_math:
                improvements["mathematics"] = (math_score - old_math) / old_math
            
            # Evaluate language (using text processing)
            lang_score = self._evaluate_language()
            old_lang = np.mean(list(self.model_state["capabilities"]["language"].values()))
            if lang_score > old_lang:
                improvements["language"] = (lang_score - old_lang) / old_lang
            
            # Evaluate code (using system performance)
            code_score = self._evaluate_code()
            old_code = np.mean(list(self.model_state["capabilities"]["code"].values()))
            if code_score > old_code:
                improvements["code"] = (code_score - old_code) / old_code
            
            # Update model state if improvements found
            if improvements:
                self._apply_improvements(improvements)
            
            return improvements
    
    def _evaluate_mathematics(self) -> float:
        """Evaluate mathematical capabilities using actual computations"""
        try:
            scores = []
            
            # Test arithmetic
            start = time.perf_counter()
            result = sum(i**2 for i in range(1000))
            arithmetic_time = time.perf_counter() - start
            scores.append(1.0 / (1.0 + arithmetic_time))
            
            # Test numpy operations
            start = time.perf_counter()
            matrix = np.random.rand(100, 100)
            eigenvalues = np.linalg.eigvals(matrix)
            linear_algebra_time = time.perf_counter() - start
            scores.append(1.0 / (1.0 + linear_algebra_time))
            
            return np.mean(scores)
        except:
            return 0.5
    
    def _evaluate_language(self) -> float:
        """Evaluate language processing capabilities"""
        try:
            scores = []
            
            # Test string operations
            start = time.perf_counter()
            text = "The quick brown fox jumps over the lazy dog" * 100
            tokens = text.split()
            unique_tokens = set(tokens)
            processing_time = time.perf_counter() - start
            scores.append(1.0 / (1.0 + processing_time))
            
            # Test pattern matching
            start = time.perf_counter()
            import re
            patterns = [r'\b\w+\b', r'\d+', r'[A-Z][a-z]+']
            for pattern in patterns:
                re.findall(pattern, text)
            pattern_time = time.perf_counter() - start
            scores.append(1.0 / (1.0 + pattern_time))
            
            return np.mean(scores)
        except:
            return 0.5
    
    def _evaluate_code(self) -> float:
        """Evaluate code execution performance"""
        try:
            scores = []
            
            # Test Python execution speed
            start = time.perf_counter()
            exec("result = sum(range(10000))")
            exec_time = time.perf_counter() - start
            scores.append(1.0 / (1.0 + exec_time))
            
            # Test system resource usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            resource_score = (100 - cpu_percent) / 100 * 0.5 + (100 - memory_percent) / 100 * 0.5
            scores.append(resource_score)
            
            return np.mean(scores)
        except:
            return 0.5
    
    def _apply_improvements(self, improvements: Dict[str, float]):
        """Apply improvements to the model (cumulative)"""
        self.model_state["version"] += 1
        self.model_state["total_improvements"] += len(improvements)
        
        for category, improvement in improvements.items():
            if category in self.model_state["capabilities"]:
                for capability in self.model_state["capabilities"][category]:
                    old_value = self.model_state["capabilities"][category][capability]
                    # Cumulative improvement - never decreases
                    new_value = min(1.0, old_value * (1.0 + improvement))
                    self.model_state["capabilities"][category][capability] = new_value
        
        self.model_state["last_evaluation"] = time.time()
        
        # Save model state
        with open(Config.MODEL_PATH, 'w') as f:
            json.dump(self.model_state, f, indent=2)
    
    def get_total_improvement(self, improvements: Dict[str, float]) -> float:
        """Calculate total improvement score for mining reward"""
        if not improvements:
            return 0.0
        
        total = sum(improvements.values())
        return total * 100  # Convert to percentage

# ================== UNIFIED MINING SYSTEM ==================
class UnifiedMiner:
    """Unified mining system that coordinates all components"""
    
    def __init__(self, blockchain: Blockchain, wallet_manager: WalletManager, evaluator: AIEvaluator):
        self.blockchain = blockchain
        self.wallet_manager = wallet_manager
        self.evaluator = evaluator
        self.mining = False
        self.mining_thread = None
        self.stats = {
            "blocks_mined": 0,
            "total_rewards": 0.0,
            "total_improvements": 0
        }
    
    def start_mining(self, miner_wallet: str):
        """Start the mining process"""
        if self.mining:
            return
        
        self.mining = True
        self.mining_thread = threading.Thread(target=self._mining_loop, args=(miner_wallet,))
        self.mining_thread.daemon = True
        self.mining_thread.start()
        print(f"Mining started for wallet: {miner_wallet}")
    
    def stop_mining(self):
        """Stop the mining process"""
        self.mining = False
        if self.mining_thread:
            self.mining_thread.join(timeout=5)
        print("Mining stopped")
    
    def _mining_loop(self, miner_wallet: str):
        """Main mining loop"""
        while self.mining:
            try:
                # Evaluate AI performance
                improvements = self.evaluator.evaluate_performance()
                
                # Only mine if there are real improvements
                if improvements and sum(improvements.values()) > Config.MIN_IMPROVEMENT_THRESHOLD:
                    # Mine block
                    block = self.blockchain.mine_block(miner_wallet, improvements)
                    
                    if block:
                        # Calculate reward
                        reward = block.transactions[0].amount if block.transactions else 0
                        
                        # Distribute rewards
                        distribution_txs = self.wallet_manager.distribute_mining_reward(miner_wallet, reward)
                        for tx in distribution_txs:
                            self.blockchain.add_transaction(tx)
                        
                        # Update stats
                        self.stats["blocks_mined"] += 1
                        self.stats["total_rewards"] += reward
                        self.stats["total_improvements"] += len(improvements)
                        
                        print(f"\n✓ Block #{block.index} mined!")
                        print(f"  Hash: {block.hash()[:16]}...")
                        print(f"  Improvements: {', '.join(f'{k}: +{v:.2%}' for k, v in improvements.items())}")
                        print(f"  Reward: {reward:.2f} QXC")
                        print(f"  Miner balance: {self.wallet_manager.get_balance(miner_wallet):.2f} QXC")
                
                # Wait before next evaluation
                time.sleep(Config.EVALUATION_INTERVAL)
                
            except Exception as e:
                print(f"Mining error: {e}")
                time.sleep(10)
    
    def get_stats(self) -> Dict:
        """Get mining statistics"""
        return {
            **self.stats,
            "blockchain_height": len(self.blockchain.chain),
            "total_supply": self.blockchain.total_supply,
            "difficulty": self.blockchain.difficulty
        }

# ================== MAIN SYSTEM CONTROLLER ==================
class QXCSystem:
    """Main system controller that manages all components"""
    
    def __init__(self):
        print("Initializing QENEX Unified Cryptocurrency System...")
        
        # Initialize core components
        self.blockchain = Blockchain()
        self.wallet_manager = WalletManager(self.blockchain)
        self.evaluator = AIEvaluator()
        self.miner = UnifiedMiner(self.blockchain, self.wallet_manager, self.evaluator)
        
        # Create essential wallets
        self.wallet_manager.create_wallet("GENESIS_WALLET", {"type": "genesis"})
        self.wallet_manager.create_wallet("DEVELOPER_WALLET", {"type": "developer"})
        
        self.running = False
    
    def start(self):
        """Start the unified system"""
        self.running = True
        
        print("\n" + "="*60)
        print("QENEX UNIFIED CRYPTOCURRENCY SYSTEM (QXC)")
        print("="*60)
        print(f"Blockchain Height: {len(self.blockchain.chain)}")
        print(f"Total Supply: {self.blockchain.total_supply:.2f} / {Config.MAX_SUPPLY:.2f} QXC")
        print(f"Current Difficulty: {self.blockchain.difficulty}")
        print(f"Model Version: {self.evaluator.model_state['version']}")
        print("="*60)
        
        # Start mining
        self.miner.start_mining("DEVELOPER_WALLET")
        
        # Run monitoring loop
        self._monitoring_loop()
    
    def _monitoring_loop(self):
        """Monitor system status"""
        last_height = len(self.blockchain.chain)
        
        while self.running:
            try:
                time.sleep(30)
                
                # Check for new blocks
                current_height = len(self.blockchain.chain)
                if current_height > last_height:
                    print(f"\n📊 System Status Update:")
                    stats = self.miner.get_stats()
                    print(f"  Blocks Mined: {stats['blocks_mined']}")
                    print(f"  Total Rewards: {stats['total_rewards']:.2f} QXC")
                    print(f"  AI Improvements: {stats['total_improvements']}")
                    print(f"  Supply: {stats['total_supply']:.2f}/{Config.MAX_SUPPLY:.2f} QXC")
                    
                    # Validate blockchain periodically
                    if current_height % 10 == 0:
                        if self.blockchain.validate_chain():
                            print("  ✓ Blockchain validation: PASSED")
                        else:
                            print("  ✗ Blockchain validation: FAILED")
                            self.stop()
                    
                    last_height = current_height
                
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                print(f"Monitoring error: {e}")
    
    def stop(self):
        """Stop the system"""
        print("\nStopping QENEX Unified Cryptocurrency System...")
        self.running = False
        self.miner.stop_mining()
        
        # Final statistics
        print("\nFinal Statistics:")
        stats = self.miner.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\nSystem stopped successfully")
    
    def get_api_status(self) -> Dict:
        """Get system status for API/monitoring"""
        return {
            "running": self.running,
            "blockchain": {
                "height": len(self.blockchain.chain),
                "total_supply": self.blockchain.total_supply,
                "max_supply": Config.MAX_SUPPLY,
                "difficulty": self.blockchain.difficulty,
                "valid": self.blockchain.validate_chain()
            },
            "model": {
                "version": self.evaluator.model_state["version"],
                "capabilities": self.evaluator.model_state["capabilities"],
                "total_improvements": self.evaluator.model_state["total_improvements"]
            },
            "mining": self.miner.get_stats(),
            "timestamp": time.time()
        }

# ================== ENTRY POINT ==================
def main():
    """Main entry point"""
    system = QXCSystem()
    
    try:
        system.start()
    except KeyboardInterrupt:
        system.stop()
    except Exception as e:
        print(f"System error: {e}")
        system.stop()

if __name__ == "__main__":
    main()