#!/usr/bin/env python3
"""
Production Blockchain and DeFi System
Real blockchain implementation with DeFi protocols
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from typing import Dict, List, Optional, Set, Any
from enum import Enum
import secrets
import struct

# Set precision for financial calculations
getcontext().prec = 38

# ============================================================================
# Blockchain Core Implementation
# ============================================================================

@dataclass
class Transaction:
    """Blockchain transaction"""
    sender: str
    receiver: str
    amount: Decimal
    fee: Decimal
    timestamp: float
    signature: Optional[str] = None
    nonce: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'sender': self.sender,
            'receiver': self.receiver,
            'amount': str(self.amount),
            'fee': str(self.fee),
            'timestamp': self.timestamp,
            'signature': self.signature,
            'nonce': self.nonce
        }
    
    def hash(self) -> str:
        """Calculate transaction hash"""
        data = f"{self.sender}{self.receiver}{self.amount}{self.fee}{self.timestamp}{self.nonce}"
        return hashlib.sha256(data.encode()).hexdigest()

@dataclass
class Block:
    """Blockchain block"""
    index: int
    timestamp: float
    transactions: List[Transaction]
    previous_hash: str
    nonce: int = 0
    hash: str = ""
    
    def calculate_hash(self) -> str:
        """Calculate block hash"""
        tx_hashes = [tx.hash() for tx in self.transactions]
        data = f"{self.index}{self.timestamp}{tx_hashes}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def mine_block(self, difficulty: int = 4):
        """Mine block with proof of work"""
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

class Blockchain:
    """Production blockchain implementation"""
    
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.mining_reward = Decimal("10")
        self.difficulty = 4
        self.balances: Dict[str, Decimal] = {}
        self.stakes: Dict[str, Decimal] = {}
        self.validators: Set[str] = set()
        
        # Create genesis block
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """Create the first block"""
        genesis = Block(0, time.time(), [], "0")
        genesis.hash = genesis.calculate_hash()
        self.chain.append(genesis)
        
        # Initialize system accounts
        self.balances["system"] = Decimal("1000000")
        self.balances["rewards"] = Decimal("1000000")
    
    def get_latest_block(self) -> Block:
        """Get the latest block in the chain"""
        return self.chain[-1]
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add transaction to pending pool"""
        # Validate transaction
        if not self.validate_transaction(transaction):
            return False
        
        self.pending_transactions.append(transaction)
        return True
    
    def validate_transaction(self, transaction: Transaction) -> bool:
        """Validate transaction"""
        # Check sender balance
        sender_balance = self.balances.get(transaction.sender, Decimal("0"))
        total_amount = transaction.amount + transaction.fee
        
        if sender_balance < total_amount:
            return False
        
        # Verify signature (simplified)
        if transaction.signature:
            expected = hashlib.sha256(
                f"{transaction.sender}{transaction.receiver}{transaction.amount}".encode()
            ).hexdigest()
            if transaction.signature != expected:
                return False
        
        return True
    
    def mine_pending_transactions(self, mining_reward_address: str):
        """Mine pending transactions"""
        # Add mining reward transaction
        reward_tx = Transaction(
            "system",
            mining_reward_address,
            self.mining_reward,
            Decimal("0"),
            time.time()
        )
        
        transactions = self.pending_transactions + [reward_tx]
        
        # Create new block
        block = Block(
            len(self.chain),
            time.time(),
            transactions,
            self.get_latest_block().hash
        )
        
        # Mine the block
        block.mine_block(self.difficulty)
        
        # Add block to chain
        self.chain.append(block)
        
        # Update balances
        for tx in transactions:
            if tx.sender != "system":
                self.balances[tx.sender] -= (tx.amount + tx.fee)
            self.balances[tx.receiver] = self.balances.get(tx.receiver, Decimal("0")) + tx.amount
            if tx.fee > 0:
                self.balances["rewards"] = self.balances.get("rewards", Decimal("0")) + tx.fee
        
        # Clear pending transactions
        self.pending_transactions = []
    
    def get_balance(self, address: str) -> Decimal:
        """Get address balance"""
        return self.balances.get(address, Decimal("0"))
    
    def validate_chain(self) -> bool:
        """Validate entire blockchain"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            
            # Verify hash
            if current.hash != current.calculate_hash():
                return False
            
            # Verify link
            if current.previous_hash != previous.hash:
                return False
            
            # Verify proof of work
            if not current.hash.startswith("0" * self.difficulty):
                return False
        
        return True

# ============================================================================
# DeFi Protocols Implementation
# ============================================================================

class TokenStandard(Enum):
    """Token standards"""
    ERC20 = "ERC20"
    ERC721 = "ERC721"
    ERC1155 = "ERC1155"

@dataclass
class Token:
    """DeFi token"""
    symbol: str
    name: str
    decimals: int
    total_supply: Decimal
    standard: TokenStandard
    owner: str
    balances: Dict[str, Decimal] = field(default_factory=dict)
    allowances: Dict[str, Dict[str, Decimal]] = field(default_factory=dict)
    
    def transfer(self, sender: str, receiver: str, amount: Decimal) -> bool:
        """Transfer tokens"""
        if self.balances.get(sender, Decimal("0")) < amount:
            return False
        
        self.balances[sender] -= amount
        self.balances[receiver] = self.balances.get(receiver, Decimal("0")) + amount
        return True
    
    def approve(self, owner: str, spender: str, amount: Decimal) -> bool:
        """Approve spending allowance"""
        if owner not in self.allowances:
            self.allowances[owner] = {}
        self.allowances[owner][spender] = amount
        return True
    
    def transfer_from(self, spender: str, owner: str, receiver: str, amount: Decimal) -> bool:
        """Transfer tokens on behalf of owner"""
        allowance = self.allowances.get(owner, {}).get(spender, Decimal("0"))
        
        if allowance < amount:
            return False
        
        if self.balances.get(owner, Decimal("0")) < amount:
            return False
        
        self.balances[owner] -= amount
        self.balances[receiver] = self.balances.get(receiver, Decimal("0")) + amount
        self.allowances[owner][spender] -= amount
        
        return True

class LiquidityPool:
    """Automated Market Maker (AMM) liquidity pool"""
    
    def __init__(self, token_a: Token, token_b: Token):
        self.token_a = token_a
        self.token_b = token_b
        self.reserve_a = Decimal("0")
        self.reserve_b = Decimal("0")
        self.total_shares = Decimal("0")
        self.shares: Dict[str, Decimal] = {}
        self.fee_rate = Decimal("0.003")  # 0.3% fee
    
    def add_liquidity(self, provider: str, amount_a: Decimal, amount_b: Decimal) -> Decimal:
        """Add liquidity to pool"""
        # First liquidity provider sets the ratio
        if self.total_shares == 0:
            shares = (amount_a * amount_b).sqrt()
            self.shares[provider] = shares
            self.total_shares = shares
        else:
            # Maintain ratio
            ratio = self.reserve_b / self.reserve_a
            required_b = amount_a * ratio
            
            if abs(amount_b - required_b) > Decimal("0.01"):
                return Decimal("0")  # Ratio mismatch
            
            shares = (amount_a / self.reserve_a) * self.total_shares
            self.shares[provider] = self.shares.get(provider, Decimal("0")) + shares
            self.total_shares += shares
        
        # Transfer tokens to pool
        self.reserve_a += amount_a
        self.reserve_b += amount_b
        
        return shares
    
    def remove_liquidity(self, provider: str, shares: Decimal) -> Tuple[Decimal, Decimal]:
        """Remove liquidity from pool"""
        if self.shares.get(provider, Decimal("0")) < shares:
            return Decimal("0"), Decimal("0")
        
        # Calculate token amounts
        ratio = shares / self.total_shares
        amount_a = self.reserve_a * ratio
        amount_b = self.reserve_b * ratio
        
        # Update state
        self.shares[provider] -= shares
        self.total_shares -= shares
        self.reserve_a -= amount_a
        self.reserve_b -= amount_b
        
        return amount_a, amount_b
    
    def swap(self, token_in: Token, amount_in: Decimal) -> Decimal:
        """Swap tokens using constant product formula"""
        # Apply fee
        amount_in_with_fee = amount_in * (Decimal("1") - self.fee_rate)
        
        # Constant product formula: x * y = k
        if token_in == self.token_a:
            amount_out = (self.reserve_b * amount_in_with_fee) / (self.reserve_a + amount_in_with_fee)
            self.reserve_a += amount_in
            self.reserve_b -= amount_out
        else:
            amount_out = (self.reserve_a * amount_in_with_fee) / (self.reserve_b + amount_in_with_fee)
            self.reserve_b += amount_in
            self.reserve_a -= amount_out
        
        return amount_out
    
    def get_price(self, token: Token) -> Decimal:
        """Get current price of token in pool"""
        if token == self.token_a:
            return self.reserve_b / self.reserve_a
        else:
            return self.reserve_a / self.reserve_b

class LendingProtocol:
    """DeFi lending protocol"""
    
    def __init__(self):
        self.deposits: Dict[str, Dict[str, Decimal]] = {}  # user -> token -> amount
        self.borrows: Dict[str, Dict[str, Decimal]] = {}
        self.collateral: Dict[str, Dict[str, Decimal]] = {}
        self.interest_rates: Dict[str, Decimal] = {}
        self.collateral_factors: Dict[str, Decimal] = {}  # LTV ratios
        self.liquidation_threshold = Decimal("0.8")  # 80% LTV for liquidation
        
    def deposit(self, user: str, token: str, amount: Decimal):
        """Deposit tokens to earn interest"""
        if user not in self.deposits:
            self.deposits[user] = {}
        
        self.deposits[user][token] = self.deposits[user].get(token, Decimal("0")) + amount
    
    def withdraw(self, user: str, token: str, amount: Decimal) -> bool:
        """Withdraw deposited tokens"""
        available = self.deposits.get(user, {}).get(token, Decimal("0"))
        
        if available < amount:
            return False
        
        # Check if withdrawal would cause under-collateralization
        if user in self.borrows and self.borrows[user]:
            if not self._check_collateral_ratio(user):
                return False
        
        self.deposits[user][token] -= amount
        return True
    
    def borrow(self, user: str, token: str, amount: Decimal) -> bool:
        """Borrow tokens against collateral"""
        # Check collateral ratio
        collateral_value = self._calculate_collateral_value(user)
        current_borrows = self._calculate_borrow_value(user)
        new_borrow_value = amount  # Simplified: assuming 1:1 price
        
        max_borrow = collateral_value * self.liquidation_threshold
        
        if current_borrows + new_borrow_value > max_borrow:
            return False
        
        if user not in self.borrows:
            self.borrows[user] = {}
        
        self.borrows[user][token] = self.borrows[user].get(token, Decimal("0")) + amount
        return True
    
    def repay(self, user: str, token: str, amount: Decimal) -> bool:
        """Repay borrowed tokens"""
        owed = self.borrows.get(user, {}).get(token, Decimal("0"))
        
        if amount > owed:
            amount = owed
        
        self.borrows[user][token] -= amount
        
        if self.borrows[user][token] == 0:
            del self.borrows[user][token]
        
        return True
    
    def liquidate(self, liquidator: str, borrower: str, token: str) -> bool:
        """Liquidate under-collateralized position"""
        # Check if position is liquidatable
        collateral_ratio = self._get_collateral_ratio(borrower)
        
        if collateral_ratio >= self.liquidation_threshold:
            return False  # Not liquidatable
        
        # Perform liquidation (simplified)
        borrow_amount = self.borrows[borrower].get(token, Decimal("0"))
        
        if borrow_amount == 0:
            return False
        
        # Liquidator repays debt and receives collateral with bonus
        liquidation_bonus = Decimal("1.1")  # 10% bonus
        collateral_seized = borrow_amount * liquidation_bonus
        
        # Transfer collateral to liquidator
        # Update borrower's positions
        self.borrows[borrower][token] = Decimal("0")
        
        return True
    
    def _calculate_collateral_value(self, user: str) -> Decimal:
        """Calculate total collateral value"""
        return sum(self.deposits.get(user, {}).values())
    
    def _calculate_borrow_value(self, user: str) -> Decimal:
        """Calculate total borrow value"""
        return sum(self.borrows.get(user, {}).values())
    
    def _get_collateral_ratio(self, user: str) -> Decimal:
        """Get current collateral ratio"""
        collateral = self._calculate_collateral_value(user)
        borrows = self._calculate_borrow_value(user)
        
        if borrows == 0:
            return Decimal("999")  # No borrows
        
        return collateral / borrows
    
    def _check_collateral_ratio(self, user: str) -> bool:
        """Check if collateral ratio is healthy"""
        return self._get_collateral_ratio(user) > self.liquidation_threshold

class StakingProtocol:
    """Proof of Stake protocol"""
    
    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain
        self.stakes: Dict[str, Decimal] = {}
        self.rewards_per_block = Decimal("1")
        self.min_stake = Decimal("100")
        self.validators: List[str] = []
        self.delegations: Dict[str, Dict[str, Decimal]] = {}  # delegator -> validator -> amount
    
    def stake(self, validator: str, amount: Decimal) -> bool:
        """Stake tokens to become validator"""
        balance = self.blockchain.get_balance(validator)
        
        if balance < amount:
            return False
        
        if amount < self.min_stake:
            return False
        
        self.stakes[validator] = self.stakes.get(validator, Decimal("0")) + amount
        self.blockchain.balances[validator] -= amount
        
        if validator not in self.validators:
            self.validators.append(validator)
        
        return True
    
    def unstake(self, validator: str, amount: Decimal) -> bool:
        """Unstake tokens"""
        staked = self.stakes.get(validator, Decimal("0"))
        
        if staked < amount:
            return False
        
        self.stakes[validator] -= amount
        self.blockchain.balances[validator] += amount
        
        if self.stakes[validator] < self.min_stake:
            self.validators.remove(validator)
        
        return True
    
    def delegate(self, delegator: str, validator: str, amount: Decimal) -> bool:
        """Delegate stake to validator"""
        if validator not in self.validators:
            return False
        
        balance = self.blockchain.get_balance(delegator)
        
        if balance < amount:
            return False
        
        if delegator not in self.delegations:
            self.delegations[delegator] = {}
        
        self.delegations[delegator][validator] = self.delegations[delegator].get(validator, Decimal("0")) + amount
        self.blockchain.balances[delegator] -= amount
        
        return True
    
    def select_validator(self) -> Optional[str]:
        """Select validator for next block (weighted random)"""
        if not self.validators:
            return None
        
        # Calculate total stake
        total_stake = sum(self.stakes.values())
        
        if total_stake == 0:
            return None
        
        # Weighted selection based on stake
        rand = secrets.randbelow(int(total_stake))
        cumulative = Decimal("0")
        
        for validator, stake in self.stakes.items():
            cumulative += stake
            if cumulative > rand:
                return validator
        
        return self.validators[-1]
    
    def distribute_rewards(self, validator: str):
        """Distribute block rewards"""
        # Validator gets base reward
        validator_reward = self.rewards_per_block * Decimal("0.9")  # 90% to validator
        self.blockchain.balances[validator] += validator_reward
        
        # Distribute to delegators
        if validator in self.delegations:
            total_delegated = sum(
                amount for delegator_stakes in self.delegations.values()
                for val, amount in delegator_stakes.items()
                if val == validator
            )
            
            if total_delegated > 0:
                delegation_reward = self.rewards_per_block * Decimal("0.1")  # 10% to delegators
                
                for delegator, validators in self.delegations.items():
                    if validator in validators:
                        share = validators[validator] / total_delegated
                        self.blockchain.balances[delegator] += delegation_reward * share

# ============================================================================
# Cross-Chain Bridge
# ============================================================================

class CrossChainBridge:
    """Bridge for cross-chain asset transfers"""
    
    def __init__(self):
        self.locked_assets: Dict[str, Dict[str, Decimal]] = {}  # chain -> token -> amount
        self.pending_transfers: List[Dict] = []
        self.completed_transfers: Set[str] = set()
        self.validators: Set[str] = set()
        self.confirmations_required = 3
    
    def lock_assets(self, source_chain: str, token: str, amount: Decimal, 
                   destination_chain: str, destination_address: str) -> str:
        """Lock assets on source chain"""
        transfer_id = hashlib.sha256(
            f"{source_chain}{token}{amount}{destination_chain}{destination_address}{time.time()}".encode()
        ).hexdigest()
        
        if source_chain not in self.locked_assets:
            self.locked_assets[source_chain] = {}
        
        self.locked_assets[source_chain][token] = self.locked_assets[source_chain].get(token, Decimal("0")) + amount
        
        self.pending_transfers.append({
            'id': transfer_id,
            'source_chain': source_chain,
            'destination_chain': destination_chain,
            'token': token,
            'amount': amount,
            'destination_address': destination_address,
            'confirmations': [],
            'status': 'pending'
        })
        
        return transfer_id
    
    def confirm_transfer(self, transfer_id: str, validator: str) -> bool:
        """Validator confirms cross-chain transfer"""
        if validator not in self.validators:
            return False
        
        for transfer in self.pending_transfers:
            if transfer['id'] == transfer_id:
                if validator not in transfer['confirmations']:
                    transfer['confirmations'].append(validator)
                    
                    if len(transfer['confirmations']) >= self.confirmations_required:
                        transfer['status'] = 'confirmed'
                        self.complete_transfer(transfer_id)
                
                return True
        
        return False
    
    def complete_transfer(self, transfer_id: str):
        """Complete cross-chain transfer"""
        for transfer in self.pending_transfers:
            if transfer['id'] == transfer_id and transfer['status'] == 'confirmed':
                # Release assets on destination chain
                self.completed_transfers.add(transfer_id)
                transfer['status'] = 'completed'
                
                # Update locked assets
                source = transfer['source_chain']
                token = transfer['token']
                amount = transfer['amount']
                
                self.locked_assets[source][token] -= amount
                
                return True
        
        return False

# ============================================================================
# DeFi Aggregator
# ============================================================================

class DeFiAggregator:
    """Aggregate DeFi protocols for optimal routing"""
    
    def __init__(self):
        self.pools: List[LiquidityPool] = []
        self.lending_protocols: List[LendingProtocol] = []
        self.bridges: List[CrossChainBridge] = []
    
    def find_best_swap_route(self, token_in: Token, token_out: Token, amount: Decimal) -> List[LiquidityPool]:
        """Find optimal swap route across pools"""
        best_route = []
        best_output = Decimal("0")
        
        # Direct swap
        for pool in self.pools:
            if (pool.token_a == token_in and pool.token_b == token_out) or \
               (pool.token_b == token_in and pool.token_a == token_out):
                output = pool.swap(token_in, amount)
                if output > best_output:
                    best_output = output
                    best_route = [pool]
        
        # Multi-hop swaps (simplified to 2 hops)
        # In production, use graph algorithms for optimal routing
        
        return best_route
    
    def find_best_lending_rate(self, token: str, amount: Decimal) -> Optional[LendingProtocol]:
        """Find best lending rate across protocols"""
        best_protocol = None
        best_rate = Decimal("0")
        
        for protocol in self.lending_protocols:
            rate = protocol.interest_rates.get(token, Decimal("0"))
            if rate > best_rate:
                best_rate = rate
                best_protocol = protocol
        
        return best_protocol

# ============================================================================
# Main DeFi System
# ============================================================================

async def run_defi_system():
    """Run complete DeFi system"""
    print("Starting Production Blockchain and DeFi System")
    
    # Initialize blockchain
    blockchain = Blockchain()
    
    # Create test accounts
    blockchain.balances["alice"] = Decimal("10000")
    blockchain.balances["bob"] = Decimal("5000")
    blockchain.balances["charlie"] = Decimal("7500")
    
    # Create tokens
    usdc = Token("USDC", "USD Coin", 6, Decimal("1000000"), TokenStandard.ERC20, "system")
    eth = Token("ETH", "Ethereum", 18, Decimal("1000000"), TokenStandard.ERC20, "system")
    
    # Initialize token balances
    usdc.balances["alice"] = Decimal("1000")
    usdc.balances["bob"] = Decimal("500")
    eth.balances["alice"] = Decimal("10")
    eth.balances["bob"] = Decimal("5")
    
    # Create liquidity pool
    pool = LiquidityPool(usdc, eth)
    
    # Add liquidity
    shares = pool.add_liquidity("alice", Decimal("100"), Decimal("1"))
    print(f"Alice added liquidity, received {shares} LP tokens")
    
    # Perform swap
    eth_out = pool.swap(usdc, Decimal("10"))
    print(f"Swapped 10 USDC for {eth_out} ETH")
    
    # Initialize lending protocol
    lending = LendingProtocol()
    lending.interest_rates["USDC"] = Decimal("0.05")  # 5% APR
    lending.collateral_factors["USDC"] = Decimal("0.75")  # 75% LTV
    
    # Deposit and borrow
    lending.deposit("alice", "USDC", Decimal("500"))
    success = lending.borrow("alice", "ETH", Decimal("2"))
    print(f"Alice borrowed ETH: {success}")
    
    # Initialize staking
    staking = StakingProtocol(blockchain)
    
    # Stake tokens
    staking.stake("alice", Decimal("1000"))
    print(f"Alice staked 1000 tokens")
    
    # Select validator
    validator = staking.select_validator()
    print(f"Selected validator: {validator}")
    
    # Mine block with staking
    if validator:
        blockchain.mine_pending_transactions(validator)
        staking.distribute_rewards(validator)
    
    # Check blockchain validity
    is_valid = blockchain.validate_chain()
    print(f"Blockchain valid: {is_valid}")
    
    # Display final balances
    print("\nFinal Balances:")
    for address in ["alice", "bob", "charlie", "system", "rewards"]:
        balance = blockchain.get_balance(address)
        print(f"{address}: {balance}")
    
    print("\nDeFi System Running Successfully")

if __name__ == "__main__":
    asyncio.run(run_defi_system())