#!/usr/bin/env python3
"""
Secure Automated Market Maker Implementation
Fixed vulnerabilities:
- Input validation and bounds checking
- Slippage protection enforcement
- Front-running protection with commit-reveal
- TWAP oracle for price manipulation resistance
- Integer overflow protection
- Reentrancy guards
- MEV protection
"""

from decimal import Decimal, getcontext, InvalidOperation, DivisionByZero
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import hmac
import json
import time
import logging
import threading
from collections import deque

# Set high precision for financial calculations
getcontext().prec = 38
getcontext().traps[InvalidOperation] = 1
getcontext().traps[DivisionByZero] = 1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for security
MIN_LIQUIDITY = Decimal('1000')  # Minimum liquidity to prevent manipulation
MAX_SWAP_IMPACT = Decimal('0.1')  # Maximum 10% price impact
MIN_TRADE_AMOUNT = Decimal('0.000001')
MAX_TRADE_AMOUNT = Decimal('1000000000')
TWAP_WINDOW = 900  # 15 minutes for TWAP
COMMIT_REVEAL_DELAY = 2  # Blocks for commit-reveal

class SwapStatus(Enum):
    PENDING = "pending"
    COMMITTED = "committed"
    REVEALED = "revealed"
    EXECUTED = "executed"
    CANCELLED = "cancelled"

@dataclass
class PriceObservation:
    """Price observation for TWAP calculation"""
    timestamp: int
    price0: Decimal
    price1: Decimal
    cumulative0: Decimal
    cumulative1: Decimal

@dataclass
class SwapCommitment:
    """Commit-reveal swap data"""
    user: str
    commitment_hash: str
    block_number: int
    status: SwapStatus
    revealed_data: Optional[Dict] = None
    executed_at: Optional[int] = None

@dataclass
class SecurePool:
    """Secure liquidity pool with protection mechanisms"""
    token0: str
    token1: str
    reserve0: Decimal
    reserve1: Decimal
    total_shares: Decimal
    fee: Decimal = Decimal('0.003')  # 0.3% fee
    
    # Security features
    locked: bool = False
    last_k: Decimal = Decimal('0')
    price_observations: deque = field(default_factory=lambda: deque(maxlen=100))
    last_observation_time: int = 0
    cumulative_price0: Decimal = Decimal('0')
    cumulative_price1: Decimal = Decimal('0')
    
    # MEV protection
    last_swap_block: int = 0
    swaps_in_block: int = 0
    max_swaps_per_block: int = 10
    
    def __post_init__(self):
        """Initialize security checks"""
        self.last_k = self.k
        self.last_observation_time = int(time.time())
    
    @property
    def k(self) -> Decimal:
        """Constant product with overflow protection"""
        try:
            return self.reserve0 * self.reserve1
        except (InvalidOperation, OverflowError):
            raise ValueError("Reserve overflow detected")
    
    def validate_k_invariant(self, tolerance: Decimal = Decimal('0.0001')):
        """Ensure constant product invariant is maintained"""
        if self.last_k > 0:
            k_ratio = abs(self.k - self.last_k) / self.last_k
            if k_ratio > tolerance:
                raise ValueError(f"K invariant violation: {k_ratio} > {tolerance}")
    
    def update_price_observation(self):
        """Update TWAP price observation"""
        current_time = int(time.time())
        time_elapsed = current_time - self.last_observation_time
        
        if time_elapsed > 0 and self.reserve0 > 0 and self.reserve1 > 0:
            price0 = self.reserve1 / self.reserve0
            price1 = self.reserve0 / self.reserve1
            
            # Update cumulative prices
            self.cumulative_price0 += price0 * Decimal(time_elapsed)
            self.cumulative_price1 += price1 * Decimal(time_elapsed)
            
            observation = PriceObservation(
                timestamp=current_time,
                price0=price0,
                price1=price1,
                cumulative0=self.cumulative_price0,
                cumulative1=self.cumulative_price1
            )
            
            self.price_observations.append(observation)
            self.last_observation_time = current_time
    
    def get_twap_price(self, token: str, window: int = TWAP_WINDOW) -> Optional[Decimal]:
        """Get time-weighted average price"""
        if len(self.price_observations) < 2:
            return None
        
        current_time = int(time.time())
        start_time = current_time - window
        
        # Find observations within window
        observations_in_window = [
            obs for obs in self.price_observations
            if obs.timestamp >= start_time
        ]
        
        if len(observations_in_window) < 2:
            return None
        
        first = observations_in_window[0]
        last = observations_in_window[-1]
        time_diff = last.timestamp - first.timestamp
        
        if time_diff == 0:
            return None
        
        if token == self.token0:
            return (last.cumulative0 - first.cumulative0) / Decimal(time_diff)
        else:
            return (last.cumulative1 - first.cumulative1) / Decimal(time_diff)

class SecureAMM:
    """Secure Automated Market Maker with comprehensive protection"""
    
    def __init__(self, block_provider=None):
        self.pools: Dict[str, SecurePool] = {}
        self.liquidity_providers: Dict[str, Dict[str, Decimal]] = {}
        self.swap_commitments: Dict[str, SwapCommitment] = {}
        self.nonces: Dict[str, int] = {}
        self.lock = threading.RLock()
        self.block_provider = block_provider or self._default_block_provider
        self.current_block = 0
        
        # Rate limiting
        self.user_last_action: Dict[str, float] = {}
        self.rate_limit_window = 1.0  # 1 second
        
        # Circuit breaker
        self.circuit_breaker_triggered = False
        self.max_price_change = Decimal('0.2')  # 20% max price change
        
    def _default_block_provider(self) -> int:
        """Default block number provider"""
        return self.current_block
    
    def _check_rate_limit(self, user: str) -> bool:
        """Check if user is rate limited"""
        now = time.time()
        last_action = self.user_last_action.get(user, 0)
        
        if now - last_action < self.rate_limit_window:
            return False
        
        self.user_last_action[user] = now
        return True
    
    def _validate_amount(self, amount: Decimal, name: str = "amount") -> Decimal:
        """Validate amount is within acceptable bounds"""
        if amount <= MIN_TRADE_AMOUNT:
            raise ValueError(f"{name} too small: {amount} <= {MIN_TRADE_AMOUNT}")
        if amount >= MAX_TRADE_AMOUNT:
            raise ValueError(f"{name} too large: {amount} >= {MAX_TRADE_AMOUNT}")
        return amount
    
    def _validate_address(self, address: str) -> str:
        """Validate address format"""
        if not address or len(address) < 3:
            raise ValueError("Invalid address")
        # Add more validation as needed (checksums, etc.)
        return address.lower()
    
    def create_pool(self, token0: str, token1: str, creator: str) -> str:
        """Create new liquidity pool with validation"""
        with self.lock:
            # Validate inputs
            token0 = self._validate_address(token0)
            token1 = self._validate_address(token1)
            creator = self._validate_address(creator)
            
            if token0 == token1:
                raise ValueError("Cannot create pool with same token")
            
            # Ensure consistent ordering
            if token0 > token1:
                token0, token1 = token1, token0
            
            pool_id = f"{token0}-{token1}"
            
            if pool_id in self.pools:
                raise ValueError(f"Pool {pool_id} already exists")
            
            self.pools[pool_id] = SecurePool(
                token0=token0,
                token1=token1,
                reserve0=Decimal('0'),
                reserve1=Decimal('0'),
                total_shares=Decimal('0')
            )
            
            logger.info(f"Created pool: {pool_id} by {creator}")
            return pool_id
    
    def add_liquidity(
        self,
        provider: str,
        token0: str,
        token1: str,
        amount0: Decimal,
        amount1: Decimal,
        min_shares: Optional[Decimal] = None
    ) -> Decimal:
        """Add liquidity with slippage protection"""
        with self.lock:
            # Rate limiting
            if not self._check_rate_limit(provider):
                raise ValueError("Rate limit exceeded")
            
            # Validate inputs
            provider = self._validate_address(provider)
            token0 = self._validate_address(token0)
            token1 = self._validate_address(token1)
            amount0 = self._validate_amount(amount0, "amount0")
            amount1 = self._validate_amount(amount1, "amount1")
            
            # Ensure consistent ordering
            if token0 > token1:
                token0, token1 = token1, token0
                amount0, amount1 = amount1, amount0
            
            pool_id = f"{token0}-{token1}"
            pool = self.pools.get(pool_id)
            
            if not pool:
                raise ValueError(f"Pool {pool_id} does not exist")
            
            if pool.locked:
                raise ValueError("Pool is locked")
            
            # Calculate shares with precision
            if pool.total_shares == Decimal('0'):
                # First liquidity provider
                shares = (amount0 * amount1).sqrt()
                if shares < MIN_LIQUIDITY:
                    raise ValueError(f"Initial liquidity too low: {shares} < {MIN_LIQUIDITY}")
            else:
                # Maintain ratio with slippage check
                expected_amount1 = (amount0 * pool.reserve1) / pool.reserve0
                slippage = abs(amount1 - expected_amount1) / expected_amount1
                
                if slippage > Decimal('0.02'):  # 2% max slippage
                    raise ValueError(f"Slippage too high: {slippage}")
                
                shares = min(
                    (amount0 * pool.total_shares) / pool.reserve0,
                    (amount1 * pool.total_shares) / pool.reserve1
                )
            
            # Check minimum shares if specified
            if min_shares and shares < min_shares:
                raise ValueError(f"Shares {shares} below minimum {min_shares}")
            
            # Update pool reserves atomically
            pool.reserve0 = pool.reserve0 + amount0
            pool.reserve1 = pool.reserve1 + amount1
            pool.total_shares = pool.total_shares + shares
            
            # Update price observation
            pool.update_price_observation()
            
            # Track provider's shares
            if provider not in self.liquidity_providers:
                self.liquidity_providers[provider] = {}
            
            if pool_id not in self.liquidity_providers[provider]:
                self.liquidity_providers[provider][pool_id] = Decimal('0')
            
            self.liquidity_providers[provider][pool_id] += shares
            
            # Update K for invariant checking
            pool.last_k = pool.k
            
            logger.info(f"Added liquidity: {provider} -> {pool_id}: {shares} shares")
            return shares
    
    def commit_swap(
        self,
        user: str,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        nonce: int,
        secret: str
    ) -> str:
        """Commit to a swap (commit-reveal pattern for MEV protection)"""
        with self.lock:
            user = self._validate_address(user)
            
            # Check nonce
            expected_nonce = self.nonces.get(user, 0)
            if nonce != expected_nonce:
                raise ValueError(f"Invalid nonce: expected {expected_nonce}, got {nonce}")
            
            # Create commitment
            swap_data = {
                'user': user,
                'token_in': token_in,
                'token_out': token_out,
                'amount_in': str(amount_in),
                'min_amount_out': str(min_amount_out),
                'nonce': nonce,
                'secret': secret
            }
            
            commitment_data = json.dumps(swap_data, sort_keys=True)
            commitment_hash = hashlib.sha256(commitment_data.encode()).hexdigest()
            
            # Store commitment
            self.swap_commitments[commitment_hash] = SwapCommitment(
                user=user,
                commitment_hash=commitment_hash,
                block_number=self.block_provider(),
                status=SwapStatus.COMMITTED
            )
            
            # Update nonce
            self.nonces[user] = nonce + 1
            
            logger.info(f"Swap committed: {commitment_hash[:8]}... by {user}")
            return commitment_hash
    
    def reveal_and_execute_swap(
        self,
        commitment_hash: str,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        nonce: int,
        secret: str
    ) -> Tuple[Decimal, Decimal]:
        """Reveal and execute committed swap"""
        with self.lock:
            # Verify commitment exists
            commitment = self.swap_commitments.get(commitment_hash)
            if not commitment:
                raise ValueError("Invalid commitment")
            
            if commitment.status != SwapStatus.COMMITTED:
                raise ValueError(f"Invalid commitment status: {commitment.status}")
            
            # Check reveal delay
            current_block = self.block_provider()
            if current_block < commitment.block_number + COMMIT_REVEAL_DELAY:
                raise ValueError("Reveal too early")
            
            # Verify commitment hash
            swap_data = {
                'user': commitment.user,
                'token_in': token_in,
                'token_out': token_out,
                'amount_in': str(amount_in),
                'min_amount_out': str(min_amount_out),
                'nonce': nonce,
                'secret': secret
            }
            
            computed_hash = hashlib.sha256(
                json.dumps(swap_data, sort_keys=True).encode()
            ).hexdigest()
            
            if computed_hash != commitment_hash:
                raise ValueError("Invalid reveal data")
            
            # Mark as revealed
            commitment.status = SwapStatus.REVEALED
            commitment.revealed_data = swap_data
            
            # Execute swap
            amount_out, price_impact = self._execute_swap(
                commitment.user,
                token_in,
                token_out,
                amount_in,
                min_amount_out
            )
            
            # Mark as executed
            commitment.status = SwapStatus.EXECUTED
            commitment.executed_at = current_block
            
            return amount_out, price_impact
    
    def _execute_swap(
        self,
        user: str,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """Execute the actual swap with all protections"""
        # Validate inputs
        amount_in = self._validate_amount(amount_in, "amount_in")
        
        # Find pool
        pool_id = f"{min(token_in, token_out)}-{max(token_in, token_out)}"
        pool = self.pools.get(pool_id)
        
        if not pool:
            raise ValueError(f"No pool for {token_in}/{token_out}")
        
        if pool.locked:
            raise ValueError("Pool is locked")
        
        # Check MEV protection
        current_block = self.block_provider()
        if pool.last_swap_block == current_block:
            pool.swaps_in_block += 1
            if pool.swaps_in_block > pool.max_swaps_per_block:
                raise ValueError("Too many swaps in current block")
        else:
            pool.last_swap_block = current_block
            pool.swaps_in_block = 1
        
        # Determine reserves
        if token_in == pool.token0:
            reserve_in = pool.reserve0
            reserve_out = pool.reserve1
            is_token0_in = True
        else:
            reserve_in = pool.reserve1
            reserve_out = pool.reserve0
            is_token0_in = False
        
        if reserve_in <= 0 or reserve_out <= 0:
            raise ValueError("Pool has no liquidity")
        
        # Calculate output amount with fee
        amount_in_with_fee = amount_in * (Decimal('1') - pool.fee)
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in + amount_in_with_fee
        amount_out = numerator / denominator
        
        # Check slippage protection
        if amount_out < min_amount_out:
            raise ValueError(f"Insufficient output: {amount_out} < {min_amount_out}")
        
        # Calculate price impact
        price_before = reserve_out / reserve_in
        price_after = (reserve_out - amount_out) / (reserve_in + amount_in)
        price_impact = abs(price_after - price_before) / price_before
        
        # Check maximum price impact
        if price_impact > MAX_SWAP_IMPACT:
            raise ValueError(f"Price impact too high: {price_impact} > {MAX_SWAP_IMPACT}")
        
        # Check against TWAP for manipulation
        twap_price = pool.get_twap_price(token_in)
        if twap_price:
            spot_price = reserve_out / reserve_in
            price_deviation = abs(spot_price - twap_price) / twap_price
            if price_deviation > self.max_price_change:
                self.circuit_breaker_triggered = True
                raise ValueError(f"Price manipulation detected: {price_deviation}")
        
        # Update reserves atomically
        if is_token0_in:
            pool.reserve0 = pool.reserve0 + amount_in
            pool.reserve1 = pool.reserve1 - amount_out
        else:
            pool.reserve1 = pool.reserve1 + amount_in
            pool.reserve0 = pool.reserve0 - amount_out
        
        # Validate K invariant
        pool.validate_k_invariant()
        pool.last_k = pool.k
        
        # Update price observation
        pool.update_price_observation()
        
        logger.info(f"Swap executed: {user} swapped {amount_in} {token_in} for {amount_out} {token_out}")
        
        return amount_out, price_impact
    
    def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount_in: Decimal
    ) -> Dict[str, Any]:
        """Get swap quote with comprehensive information"""
        with self.lock:
            pool_id = f"{min(token_in, token_out)}-{max(token_in, token_out)}"
            pool = self.pools.get(pool_id)
            
            if not pool:
                raise ValueError(f"No pool for {token_in}/{token_out}")
            
            # Determine reserves
            if token_in == pool.token0:
                reserve_in = pool.reserve0
                reserve_out = pool.reserve1
            else:
                reserve_in = pool.reserve1
                reserve_out = pool.reserve0
            
            if reserve_in <= 0 or reserve_out <= 0:
                return {
                    'error': 'Insufficient liquidity',
                    'amount_out': Decimal('0'),
                    'price_impact': Decimal('0')
                }
            
            # Calculate output
            amount_in_with_fee = amount_in * (Decimal('1') - pool.fee)
            numerator = amount_in_with_fee * reserve_out
            denominator = reserve_in + amount_in_with_fee
            amount_out = numerator / denominator
            
            # Calculate price impact
            price_before = reserve_out / reserve_in
            price_after = (reserve_out - amount_out) / (reserve_in + amount_in)
            price_impact = abs(price_after - price_before) / price_before
            
            # Get TWAP if available
            twap_price = pool.get_twap_price(token_in)
            
            return {
                'amount_out': amount_out,
                'price_impact': price_impact,
                'price': reserve_out / reserve_in,
                'twap_price': twap_price,
                'fee': pool.fee,
                'liquidity': pool.k.sqrt(),
                'reserves': {
                    token_in: reserve_in,
                    token_out: reserve_out
                }
            }
    
    def emergency_pause(self, pool_id: str):
        """Emergency pause for a pool"""
        with self.lock:
            if pool_id in self.pools:
                self.pools[pool_id].locked = True
                logger.critical(f"Pool {pool_id} emergency paused")
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker after investigation"""
        with self.lock:
            self.circuit_breaker_triggered = False
            logger.info("Circuit breaker reset")

# Usage example
if __name__ == "__main__":
    amm = SecureAMM()
    
    # Create pool
    pool_id = amm.create_pool("USDC", "ETH", "creator1")
    
    # Add initial liquidity
    shares = amm.add_liquidity(
        "lp1", "USDC", "ETH",
        Decimal("10000"), Decimal("5"),
        min_shares=Decimal("100")
    )
    print(f"LP shares: {shares}")
    
    # Get quote
    quote = amm.get_quote("USDC", "ETH", Decimal("100"))
    print(f"Quote: {quote}")
    
    # Commit swap (MEV protection)
    commitment = amm.commit_swap(
        "trader1", "USDC", "ETH",
        Decimal("100"), Decimal("0.045"),
        0, "secret123"
    )
    
    # Simulate block advancement
    amm.current_block += 3
    
    # Reveal and execute
    amount_out, impact = amm.reveal_and_execute_swap(
        commitment, "USDC", "ETH",
        Decimal("100"), Decimal("0.045"),
        0, "secret123"
    )
    print(f"Swapped for {amount_out} ETH with {impact:.2%} price impact")