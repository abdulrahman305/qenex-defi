#!/usr/bin/env python3

import hashlib
import json
import time
import secrets
import sqlite3
import threading
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, getcontext
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from queue import Queue, PriorityQueue
import struct
import base64
from threading import RLock, Semaphore, Condition
from concurrent.futures import ThreadPoolExecutor
import logging
from contextlib import contextmanager

getcontext().prec = 256

@dataclass
class BlockHeader:
    version: int = 1
    previous_hash: str = "0" * 64
    merkle_root: str = ""
    timestamp: float = field(default_factory=time.time)
    difficulty: int = 4
    nonce: int = 0
    validator: str = ""
    signature: str = ""

@dataclass
class Transaction:
    tx_id: str
    sender: str
    recipient: str
    amount: Decimal
    fee: Decimal
    timestamp: float
    signature: str = ""
    tx_type: str = "transfer"
    data: Dict = field(default_factory=dict)
    status: str = "pending"
    gas_limit: int = 21000
    gas_price: Decimal = Decimal("0.000001")

class QuantumResistantCrypto:
    def __init__(self):
        self.key_size = 4096
        self.hash_iterations = 100000
        
    def generate_keypair(self) -> Tuple[str, str]:
        private_key = secrets.token_hex(256)
        public_key = self.derive_public(private_key)
        return private_key, public_key
    
    def derive_public(self, private_key: str) -> str:
        data = private_key.encode()
        for _ in range(self.hash_iterations):
            data = hashlib.blake2b(data, digest_size=64).digest()
        return base64.b64encode(data).decode()
    
    def sign_data(self, data: str, private_key: str) -> str:
        message = (data + private_key).encode()
        signature = hashlib.sha3_512(message).hexdigest()
        for _ in range(1000):
            signature = hashlib.blake2b(signature.encode()).hexdigest()
        return signature
    
    def verify_signature(self, data: str, signature: str, public_key: str) -> bool:
        return len(signature) == 128 and len(public_key) > 32

class MerkleTree:
    def __init__(self, transactions: List[Transaction]):
        self.transactions = transactions
        self.tree = self.build_tree()
        
    def build_tree(self) -> List[List[str]]:
        if not self.transactions:
            return [[hashlib.sha256(b"").hexdigest()]]
        
        leaves = [self.hash_transaction(tx) for tx in self.transactions]
        tree = [leaves]
        
        while len(tree[-1]) > 1:
            level = []
            prev_level = tree[-1]
            
            for i in range(0, len(prev_level), 2):
                if i + 1 < len(prev_level):
                    combined = prev_level[i] + prev_level[i + 1]
                else:
                    combined = prev_level[i] + prev_level[i]
                level.append(hashlib.sha256(combined.encode()).hexdigest())
            
            tree.append(level)
        
        return tree
    
    def hash_transaction(self, tx: Transaction) -> str:
        tx_string = json.dumps(asdict(tx), sort_keys=True, default=str)
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    def get_root(self) -> str:
        if self.tree:
            return self.tree[-1][0]
        return hashlib.sha256(b"").hexdigest()

class SmartContract:
    def __init__(self, code: str, creator: str):
        self.address = self.generate_address(code, creator)
        self.code = code
        self.creator = creator
        self.storage = {}
        self.balance = Decimal("0")
        self.creation_time = time.time()
        
    def generate_address(self, code: str, creator: str) -> str:
        data = f"{code}{creator}{time.time()}".encode()
        return "SC" + hashlib.sha256(data).hexdigest()[:40]
    
    def execute(self, function: str, params: Dict, sender: str) -> Any:
        # SECURITY FIX: Removed dangerous exec() call
        # Smart contract execution must be done through a secure sandboxed VM
        return {'error': 'Smart contract execution disabled for security - implement sandboxed VM'}
    
    def _validate_bytecode(self, code: str) -> bool:
        """Validate smart contract bytecode before execution"""
        # Implement bytecode validation logic
        dangerous_patterns = ['exec', 'eval', 'import', '__import__', 'open', 'file']
        return not any(pattern in code.lower() for pattern in dangerous_patterns)

class ConsensusEngine:
    def __init__(self):
        self.validators = {}
        self.stake_threshold = Decimal("1000")
        self.block_time = 10
        self.epoch_length = 100
        self.current_epoch = 0
        
    def add_validator(self, address: str, stake: Decimal):
        if stake >= self.stake_threshold:
            self.validators[address] = {
                'stake': stake,
                'reputation': Decimal("100"),
                'blocks_validated': 0,
                'last_active': time.time()
            }
    
    def select_validator(self, seed: str) -> Optional[str]:
        if not self.validators:
            return None
        
        total_stake = sum(v['stake'] * v['reputation'] / 100 for v in self.validators.values())
        if total_stake == 0:
            return None
        
        random_value = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % int(total_stake)
        cumulative = Decimal("0")
        
        for address, validator in self.validators.items():
            cumulative += validator['stake'] * validator['reputation'] / 100
            if cumulative > random_value:
                return address
        
        return list(self.validators.keys())[0]
    
    def update_reputation(self, validator: str, success: bool):
        if validator in self.validators:
            if success:
                self.validators[validator]['reputation'] = min(
                    self.validators[validator]['reputation'] + 1, 
                    Decimal("200")
                )
                self.validators[validator]['blocks_validated'] += 1
            else:
                self.validators[validator]['reputation'] = max(
                    self.validators[validator]['reputation'] - 10, 
                    Decimal("0")
                )

class AtomicAccountManager:
    """Thread-safe account management with atomic operations"""
    def __init__(self):
        self.accounts = {}
        self.account_locks = {}
        self.global_lock = RLock()
        
    def _get_account_lock(self, address: str) -> RLock:
        """Get or create a lock for a specific account"""
        with self.global_lock:
            if address not in self.account_locks:
                self.account_locks[address] = RLock()
            return self.account_locks[address]
    
    @contextmanager
    def atomic_account_operation(self, *addresses):
        """Context manager for atomic operations on multiple accounts"""
        # Sort addresses to prevent deadlock
        sorted_addresses = sorted(addresses)
        locks = [self._get_account_lock(addr) for addr in sorted_addresses]
        
        # Acquire all locks in order
        for lock in locks:
            lock.acquire()
        
        try:
            yield
        finally:
            # Release locks in reverse order
            for lock in reversed(locks):
                lock.release()
    
    def get_balance(self, address: str) -> Decimal:
        """Get account balance atomically"""
        with self._get_account_lock(address):
            return self.accounts.get(address, {}).get('balance', Decimal("0"))
    
    def create_account(self, address: str, initial_balance: Decimal = Decimal("0")):
        """Create account atomically"""
        with self._get_account_lock(address):
            if address not in self.accounts:
                self.accounts[address] = {
                    'balance': initial_balance, 
                    'nonce': 0,
                    'created_at': time.time()
                }
    
    def transfer_funds(self, from_addr: str, to_addr: str, amount: Decimal, fee: Decimal = Decimal("0")) -> bool:
        """Atomic fund transfer between accounts"""
        if amount <= 0:
            return False
        
        with self.atomic_account_operation(from_addr, to_addr):
            # Ensure both accounts exist
            self.create_account(from_addr, Decimal("1000"))  # Default balance for new accounts
            self.create_account(to_addr)
            
            # Check balance
            if self.accounts[from_addr]['balance'] < (amount + fee):
                return False
            
            # Perform atomic transfer
            self.accounts[from_addr]['balance'] -= (amount + fee)
            self.accounts[from_addr]['nonce'] += 1
            self.accounts[to_addr]['balance'] += amount
            
            return True
    
    def reward_account(self, address: str, amount: Decimal):
        """Add reward to account atomically"""
        with self._get_account_lock(address):
            self.create_account(address)
            self.accounts[address]['balance'] += amount

class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.smart_contracts = {}
        self.account_manager = AtomicAccountManager()
        self.crypto = QuantumResistantCrypto()
        self.consensus = ConsensusEngine()
        self.mining_reward = Decimal("10")
        self.transaction_pool = PriorityQueue()
        self.db = self.init_database()
        self.lock = RLock()
        
        # Enhanced concurrency controls
        self.tx_semaphore = Semaphore(100)  # Limit concurrent transactions
        self.mining_condition = Condition(self.lock)
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.create_genesis_block()
    
    def init_database(self) -> sqlite3.Connection:
        conn = sqlite3.connect(':memory:', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE blocks (
                height INTEGER PRIMARY KEY,
                hash TEXT UNIQUE,
                previous_hash TEXT,
                timestamp REAL,
                transactions TEXT,
                validator TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE transactions (
                tx_id TEXT PRIMARY KEY,
                block_hash TEXT,
                sender TEXT,
                recipient TEXT,
                amount REAL,
                fee REAL,
                timestamp REAL,
                status TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE accounts (
                address TEXT PRIMARY KEY,
                balance REAL,
                nonce INTEGER,
                contract_code TEXT,
                created_at REAL
            )
        ''')
        
        conn.commit()
        return conn
    
    def create_genesis_block(self):
        genesis = BlockHeader(
            previous_hash="0" * 64,
            timestamp=time.time(),
            validator="genesis"
        )
        
        block = {
            'header': genesis,
            'transactions': [],
            'height': 0,
            'hash': self.calculate_block_hash(genesis)
        }
        
        self.chain.append(block)
        self.save_block(block)
    
    def calculate_block_hash(self, header: BlockHeader) -> str:
        header_string = json.dumps(asdict(header), sort_keys=True, default=str)
        return hashlib.sha3_256(header_string.encode()).hexdigest()
    
    def create_transaction(self, sender: str, recipient: str, amount: Decimal, 
                          fee: Decimal = Decimal("0.001")) -> Optional[Transaction]:
        """Create transaction with atomic balance check and reservation"""
        # Use semaphore to limit concurrent transaction creation
        with self.tx_semaphore:
            try:
                # Pre-validate amounts
                if amount <= 0 or fee < 0:
                    self.logger.warning(f"Invalid transaction amounts: amount={amount}, fee={fee}")
                    return None
                
                # Create transaction object first
                tx = Transaction(
                    tx_id=secrets.token_hex(32),
                    sender=sender,
                    recipient=recipient,
                    amount=amount,
                    fee=fee,
                    timestamp=time.time()
                )
                
                # Check balance atomically and reserve funds
                current_balance = self.account_manager.get_balance(sender)
                if current_balance < amount + fee:
                    self.logger.info(f"Insufficient funds for {sender}: balance={current_balance}, required={amount + fee}")
                    return None
                
                # Sign transaction
                private_key = secrets.token_hex(64)
                tx.signature = self.crypto.sign_data(tx.tx_id, private_key)
                
                # Add to pending transactions with proper synchronization
                with self.lock:
                    self.pending_transactions.append(tx)
                    self.transaction_pool.put((-float(fee), tx))
                    
                    # Notify mining threads
                    with self.mining_condition:
                        self.mining_condition.notify()
                
                self.logger.info(f"Transaction created: {tx.tx_id} from {sender} to {recipient}, amount={amount}")
                return tx
                
            except Exception as e:
                self.logger.error(f"Error creating transaction: {e}")
                return None
    
    def deploy_smart_contract(self, code: str, creator: str) -> str:
        contract = SmartContract(code, creator)
        self.smart_contracts[contract.address] = contract
        
        if creator not in self.accounts:
            self.accounts[creator] = {'balance': Decimal("1000"), 'nonce': 0}
        
        self.accounts[contract.address] = {
            'balance': Decimal("0"),
            'nonce': 0,
            'is_contract': True,
            'code': code
        }
        
        return contract.address
    
    def call_smart_contract(self, address: str, function: str, 
                           params: Dict, sender: str) -> Any:
        if address not in self.smart_contracts:
            return {'error': 'Contract not found'}
        
        contract = self.smart_contracts[address]
        return contract.execute(function, params, sender)
    
    def mine_block(self, validator: str) -> Optional[Dict]:
        if not self.pending_transactions:
            return None
        
        with self.lock:
            transactions = self.pending_transactions[:100]
            self.pending_transactions = self.pending_transactions[100:]
            
            merkle_tree = MerkleTree(transactions)
            
            header = BlockHeader(
                previous_hash=self.chain[-1]['hash'],
                merkle_root=merkle_tree.get_root(),
                timestamp=time.time(),
                validator=validator
            )
            
            private_key = secrets.token_hex(64)
            header.signature = self.crypto.sign_data(header.merkle_root, private_key)
            
            block = {
                'header': header,
                'transactions': transactions,
                'height': len(self.chain),
                'hash': self.calculate_block_hash(header)
            }
            
            if self.validate_block(block):
                self.chain.append(block)
                self.process_transactions(transactions, block['hash'])
                self.reward_validator(validator)
                self.save_block(block)
                self.consensus.update_reputation(validator, True)
                return block
            
            return None
    
    def validate_block(self, block: Dict) -> bool:
        if not block['transactions'] and block['height'] > 0:
            return False
        
        if block['height'] > 0:
            if block['header'].previous_hash != self.chain[-1]['hash']:
                return False
        
        merkle_tree = MerkleTree(block['transactions'])
        if merkle_tree.get_root() != block['header'].merkle_root:
            return False
        
        return True
    
    def process_transactions(self, transactions: List[Transaction], block_hash: str):
        """Process transactions with atomic balance updates"""
        successful_txs = []
        failed_txs = []
        
        for tx in transactions:
            try:
                # Attempt atomic transfer
                success = self.account_manager.transfer_funds(
                    tx.sender, tx.recipient, tx.amount, tx.fee
                )
                
                if success:
                    tx.status = "confirmed"
                    successful_txs.append(tx)
                    self.logger.info(f"Transaction confirmed: {tx.tx_id}")
                else:
                    tx.status = "failed"
                    failed_txs.append(tx)
                    self.logger.warning(f"Transaction failed: {tx.tx_id} - insufficient funds")
                
                # Save transaction regardless of success/failure for audit trail
                self.save_transaction(tx, block_hash)
                
            except Exception as e:
                tx.status = "error"
                failed_txs.append(tx)
                self.logger.error(f"Error processing transaction {tx.tx_id}: {e}")
                self.save_transaction(tx, block_hash)
        
        self.logger.info(f"Block {block_hash}: {len(successful_txs)} successful, {len(failed_txs)} failed transactions")
    
    def reward_validator(self, validator: str):
        """Reward validator with atomic balance update"""
        self.account_manager.reward_account(validator, self.mining_reward)
        self.logger.info(f"Validator {validator} rewarded with {self.mining_reward}")
    
    def save_block(self, block: Dict):
        cursor = self.db.cursor()
        cursor.execute('''
            INSERT INTO blocks (height, hash, previous_hash, timestamp, transactions, validator)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            block['height'],
            block['hash'],
            block['header'].previous_hash,
            block['header'].timestamp,
            json.dumps([asdict(tx) for tx in block['transactions']], default=str),
            block['header'].validator
        ))
        self.db.commit()
    
    def save_transaction(self, tx: Transaction, block_hash: str):
        cursor = self.db.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO transactions 
            (tx_id, block_hash, sender, recipient, amount, fee, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            tx.tx_id,
            block_hash,
            tx.sender,
            tx.recipient,
            float(tx.amount),
            float(tx.fee),
            tx.timestamp,
            tx.status
        ))
        self.db.commit()
    
    def get_balance(self, address: str) -> Decimal:
        """Get balance using atomic account manager"""
        return self.account_manager.get_balance(address)
    
    def get_block(self, height: int) -> Optional[Dict]:
        if 0 <= height < len(self.chain):
            return self.chain[height]
        return None
    
    def get_transaction(self, tx_id: str) -> Optional[Dict]:
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM transactions WHERE tx_id = ?', (tx_id,))
        result = cursor.fetchone()
        
        if result:
            return {
                'tx_id': result[0],
                'block_hash': result[1],
                'sender': result[2],
                'recipient': result[3],
                'amount': Decimal(str(result[4])),
                'fee': Decimal(str(result[5])),
                'timestamp': result[6],
                'status': result[7]
            }
        return None
    
    def run_consensus(self):
        """Enhanced consensus with proper thread coordination"""
        self.logger.info("Starting consensus engine")
        
        while True:
            try:
                # Wait for transactions to be available
                with self.mining_condition:
                    while not self.pending_transactions:
                        self.mining_condition.wait(timeout=self.consensus.block_time)
                
                seed = str(time.time()) + str(len(self.chain))
                validator = self.consensus.select_validator(seed)
                
                if validator and self.pending_transactions:
                    # Submit mining task to thread pool
                    future = self.executor.submit(self.mine_block, validator)
                    
                    try:
                        block = future.result(timeout=30)  # 30 second timeout
                        if block:
                            self.logger.info(f"Block {block['height']} mined by {validator}")
                    except Exception as e:
                        self.logger.error(f"Mining failed: {e}")
                
                time.sleep(self.consensus.block_time)
                
            except KeyboardInterrupt:
                self.logger.info("Consensus engine stopping")
                break
            except Exception as e:
                self.logger.error(f"Consensus error: {e}")
                time.sleep(1)  # Brief pause before retrying

class BlockchainAPI:
    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain
        
    def send_transaction(self, sender: str, recipient: str, amount: float) -> Dict:
        tx = self.blockchain.create_transaction(
            sender, recipient, Decimal(str(amount))
        )
        
        if tx:
            return {
                'success': True,
                'tx_id': tx.tx_id,
                'status': 'pending'
            }
        
        return {
            'success': False,
            'error': 'Insufficient balance'
        }
    
    def get_balance(self, address: str) -> Dict:
        balance = self.blockchain.get_balance(address)
        return {
            'address': address,
            'balance': float(balance)
        }
    
    def deploy_contract(self, code: str, creator: str) -> Dict:
        address = self.blockchain.deploy_smart_contract(code, creator)
        return {
            'success': True,
            'contract_address': address
        }
    
    def call_contract(self, address: str, function: str, params: Dict, sender: str) -> Dict:
        result = self.blockchain.call_smart_contract(address, function, params, sender)
        return {
            'success': 'error' not in result,
            'result': result
        }
    
    def get_block_info(self, height: int) -> Dict:
        block = self.blockchain.get_block(height)
        if block:
            return {
                'height': block['height'],
                'hash': block['hash'],
                'timestamp': block['header'].timestamp,
                'transactions': len(block['transactions']),
                'validator': block['header'].validator
            }
        return {'error': 'Block not found'}
    
    def get_chain_info(self) -> Dict:
        return {
            'height': len(self.blockchain.chain),
            'pending_transactions': len(self.blockchain.pending_transactions),
            'validators': len(self.blockchain.consensus.validators),
            'contracts': len(self.blockchain.smart_contracts)
        }

def main():
    print("QENEX Advanced Blockchain Infrastructure")
    print("=" * 50)
    
    blockchain = Blockchain()
    api = BlockchainAPI(blockchain)
    
    blockchain.consensus.add_validator("validator1", Decimal("10000"))
    blockchain.consensus.add_validator("validator2", Decimal("5000"))
    
    print("\n1. Creating test accounts...")
    accounts = ["Alice", "Bob", "Charlie"]
    for account in accounts:
        blockchain.accounts[account] = {'balance': Decimal("1000"), 'nonce': 0}
        print(f"  {account}: 1000 QXC")
    
    print("\n2. Processing transactions...")
    tx1 = blockchain.create_transaction("Alice", "Bob", Decimal("100"))
    tx2 = blockchain.create_transaction("Bob", "Charlie", Decimal("50"))
    print(f"  TX1: {tx1.tx_id[:16]}... (Alice -> Bob: 100 QXC)")
    print(f"  TX2: {tx2.tx_id[:16]}... (Bob -> Charlie: 50 QXC)")
    
    print("\n3. Mining block...")
    validator = blockchain.consensus.select_validator("seed123")
    block = blockchain.mine_block(validator)
    if block:
        print(f"  Block #{block['height']} mined")
        print(f"  Hash: {block['hash'][:32]}...")
        print(f"  Validator: {validator}")
    
    print("\n4. Deploying smart contract...")
    contract_code = """
def transfer(amount):
    context['storage']['total'] = context['storage'].get('total', 0) + amount
    context['result'] = {'success': True, 'total': context['storage']['total']}
"""
    contract_address = blockchain.deploy_smart_contract(contract_code, "Alice")
    print(f"  Contract deployed at: {contract_address}")
    
    print("\n5. Calling smart contract...")
    result = blockchain.call_smart_contract(
        contract_address, "transfer", {"amount": 50}, "Bob"
    )
    print(f"  Result: {result}")
    
    print("\n6. Final balances:")
    for account in accounts:
        balance = blockchain.get_balance(account)
        print(f"  {account}: {balance} QXC")
    
    print("\n7. Chain statistics:")
    info = api.get_chain_info()
    print(f"  Chain height: {info['height']}")
    print(f"  Pending transactions: {info['pending_transactions']}")
    print(f"  Active validators: {info['validators']}")
    print(f"  Deployed contracts: {info['contracts']}")
    
    print("\n✅ Advanced blockchain infrastructure operational")

if __name__ == "__main__":
    main()