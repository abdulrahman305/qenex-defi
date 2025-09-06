#!/usr/bin/env python3
"""
QENEX Optimized AMM - High-Performance DeFi Platform
Production-ready implementation with advanced features
"""

import math
import time
import hashlib
import secrets
import threading
from decimal import Decimal, getcontext
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import heapq

# Set decimal precision
getcontext().prec = 28

# Constants
MIN_LIQUIDITY = Decimal('0.000001')
MAX_SLIPPAGE = Decimal('0.5')
BASE_FEE = Decimal('0.003')  # 0.3%
PROTOCOL_FEE_SHARE = Decimal('0.0005')  # 0.05% to protocol
LP_FEE_SHARE = Decimal('0.0025')  # 0.25% to LPs

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

@dataclass
class Order:
    """Order structure for limit order book"""
    id: str
    user: str
    order_type: OrderType
    token_in: str
    token_out: str
    amount_in: Decimal
    min_amount_out: Decimal
    max_amount_out: Optional[Decimal] = None
    price: Optional[Decimal] = None
    expiry: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    
    def __lt__(self, other):
        """For heap operations - better price is lower"""
        if self.price and other.price:
            return self.price < other.price
        return self.created_at < other.created_at

class PriceOracle:
    """Time-weighted average price oracle"""
    
    def __init__(self, window_size: int = 3600):  # 1 hour default
        self.window_size = window_size
        self.price_history = defaultdict(list)
        self.lock = threading.RLock()
    
    def update_price(self, pair: str, price: Decimal):
        """Update price for a pair"""
        with self.lock:
            timestamp = time.time()
            history = self.price_history[pair]
            
            # Add new price point
            history.append((timestamp, price))
            
            # Remove old price points outside window
            cutoff = timestamp - self.window_size
            self.price_history[pair] = [
                (t, p) for t, p in history if t > cutoff
            ]
    
    def get_twap(self, pair: str) -> Optional[Decimal]:
        """Get time-weighted average price"""
        with self.lock:
            history = self.price_history.get(pair, [])
            if not history:
                return None
            
            if len(history) == 1:
                return history[0][1]
            
            # Calculate TWAP
            total_weighted_price = Decimal('0')
            total_time = Decimal('0')
            
            for i in range(1, len(history)):
                time_delta = Decimal(str(history[i][0] - history[i-1][0]))
                avg_price = (history[i][1] + history[i-1][1]) / 2
                total_weighted_price += avg_price * time_delta
                total_time += time_delta
            
            return total_weighted_price / total_time if total_time > 0 else history[-1][1]

class LiquidityPool:
    """Optimized liquidity pool with advanced features"""
    
    def __init__(self, token0: str, token1: str):
        self.token0 = min(token0, token1)
        self.token1 = max(token0, token1)
        self.reserve0 = Decimal('0')
        self.reserve1 = Decimal('0')
        self.total_shares = Decimal('0')
        self.k_last = Decimal('0')  # Last invariant for fee calculation
        self.price_cumulative0 = Decimal('0')
        self.price_cumulative1 = Decimal('0')
        self.last_update = time.time()
        self.lock = threading.RLock()
        
        # Fee tracking
        self.accumulated_fees0 = Decimal('0')
        self.accumulated_fees1 = Decimal('0')
        self.protocol_fees0 = Decimal('0')
        self.protocol_fees1 = Decimal('0')
        
        # Liquidity providers
        self.lp_shares = defaultdict(Decimal)
        self.lp_fees = defaultdict(lambda: {'token0': Decimal('0'), 'token1': Decimal('0')})
    
    def update_price_cumulative(self):
        """Update cumulative prices for TWAP"""
        current_time = time.time()
        time_elapsed = Decimal(str(current_time - self.last_update))
        
        if time_elapsed > 0 and self.reserve0 > 0 and self.reserve1 > 0:
            self.price_cumulative0 += (self.reserve1 / self.reserve0) * time_elapsed
            self.price_cumulative1 += (self.reserve0 / self.reserve1) * time_elapsed
        
        self.last_update = current_time
    
    def get_spot_price(self, token: str) -> Decimal:
        """Get current spot price"""
        with self.lock:
            if self.reserve0 == 0 or self.reserve1 == 0:
                return Decimal('0')
            
            if token == self.token0:
                return self.reserve1 / self.reserve0
            else:
                return self.reserve0 / self.reserve1
    
    def calculate_output(self, amount_in: Decimal, reserve_in: Decimal, 
                        reserve_out: Decimal) -> Tuple[Decimal, Decimal]:
        """Calculate output amount with price impact"""
        if amount_in <= 0 or reserve_in <= 0 or reserve_out <= 0:
            return Decimal('0'), Decimal('0')
        
        # Apply fee
        amount_in_with_fee = amount_in * (Decimal('1') - BASE_FEE)
        
        # Calculate output
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in + amount_in_with_fee
        amount_out = numerator / denominator
        
        # Calculate price impact
        spot_price = reserve_out / reserve_in
        execution_price = amount_out / amount_in
        price_impact = abs(spot_price - execution_price) / spot_price
        
        return amount_out, price_impact
    
    def swap(self, token_in: str, amount_in: Decimal, 
             min_amount_out: Decimal) -> Tuple[Decimal, Decimal, str]:
        """Execute swap with optimizations"""
        with self.lock:
            # Update price cumulative before swap
            self.update_price_cumulative()
            
            # Determine reserves
            if token_in == self.token0:
                reserve_in, reserve_out = self.reserve0, self.reserve1
                token_out = self.token1
            else:
                reserve_in, reserve_out = self.reserve1, self.reserve0
                token_out = self.token0
            
            # Calculate output and price impact
            amount_out, price_impact = self.calculate_output(
                amount_in, reserve_in, reserve_out
            )
            
            # Check slippage
            if amount_out < min_amount_out:
                raise ValueError(f"Slippage too high: {amount_out} < {min_amount_out}")
            
            if price_impact > MAX_SLIPPAGE:
                raise ValueError(f"Price impact too high: {price_impact * 100:.2f}%")
            
            # Calculate fees
            fee_amount = amount_in * BASE_FEE
            protocol_fee = fee_amount * (PROTOCOL_FEE_SHARE / BASE_FEE)
            lp_fee = fee_amount - protocol_fee
            
            # Update reserves
            if token_in == self.token0:
                self.reserve0 += amount_in
                self.reserve1 -= amount_out
                self.accumulated_fees0 += lp_fee
                self.protocol_fees0 += protocol_fee
            else:
                self.reserve1 += amount_in
                self.reserve0 -= amount_out
                self.accumulated_fees1 += lp_fee
                self.protocol_fees1 += protocol_fee
            
            # Verify constant product (with fees)
            k_after = self.reserve0 * self.reserve1
            if k_after < self.k_last:
                raise ValueError("K invariant violated")
            
            self.k_last = k_after
            
            # Generate transaction hash
            tx_data = f"swap{token_in}{token_out}{amount_in}{amount_out}{time.time()}{secrets.token_hex(8)}"
            tx_hash = '0x' + hashlib.sha256(tx_data.encode()).hexdigest()
            
            return amount_out, price_impact, tx_hash
    
    def add_liquidity(self, provider: str, amount0: Decimal, 
                     amount1: Decimal) -> Tuple[Decimal, str]:
        """Add liquidity with optimal ratios"""
        with self.lock:
            # Update price cumulative
            self.update_price_cumulative()
            
            # Calculate shares
            if self.total_shares == 0:
                # Initial liquidity
                shares = self._sqrt(amount0 * amount1)
                if shares <= MIN_LIQUIDITY:
                    raise ValueError("Insufficient initial liquidity")
                
                # Lock minimum liquidity
                locked_shares = MIN_LIQUIDITY
                shares -= locked_shares
                self.total_shares = shares + locked_shares
                
            else:
                # Calculate optimal amounts
                optimal_amount1 = (amount0 * self.reserve1) / self.reserve0
                
                if amount1 > optimal_amount1:
                    # Adjust amount1
                    amount1 = optimal_amount1
                else:
                    # Adjust amount0
                    amount0 = (amount1 * self.reserve0) / self.reserve1
                
                # Calculate shares proportionally
                shares = min(
                    (amount0 * self.total_shares) / self.reserve0,
                    (amount1 * self.total_shares) / self.reserve1
                )
            
            # Distribute accumulated fees to existing LPs
            if self.total_shares > 0:
                self._distribute_fees()
            
            # Update reserves
            self.reserve0 += amount0
            self.reserve1 += amount1
            self.k_last = self.reserve0 * self.reserve1
            
            # Update LP shares
            self.lp_shares[provider] += shares
            self.total_shares += shares
            
            # Generate transaction hash
            tx_data = f"addliq{provider}{amount0}{amount1}{shares}{time.time()}{secrets.token_hex(8)}"
            tx_hash = '0x' + hashlib.sha256(tx_data.encode()).hexdigest()
            
            return shares, tx_hash
    
    def remove_liquidity(self, provider: str, shares: Decimal) -> Tuple[Decimal, Decimal, str]:
        """Remove liquidity with fee distribution"""
        with self.lock:
            if shares > self.lp_shares[provider]:
                raise ValueError("Insufficient shares")
            
            # Update price cumulative
            self.update_price_cumulative()
            
            # Distribute fees before removal
            self._distribute_fees()
            
            # Calculate amounts to return
            amount0 = (shares * self.reserve0) / self.total_shares
            amount1 = (shares * self.reserve1) / self.total_shares
            
            # Add accumulated fees for this provider
            fee_share = shares / self.total_shares
            amount0 += self.lp_fees[provider]['token0']
            amount1 += self.lp_fees[provider]['token1']
            
            # Update reserves
            self.reserve0 -= amount0
            self.reserve1 -= amount1
            self.k_last = self.reserve0 * self.reserve1
            
            # Update shares
            self.lp_shares[provider] -= shares
            self.total_shares -= shares
            
            # Clear fees for removed shares
            self.lp_fees[provider]['token0'] = Decimal('0')
            self.lp_fees[provider]['token1'] = Decimal('0')
            
            # Generate transaction hash
            tx_data = f"remliq{provider}{shares}{amount0}{amount1}{time.time()}{secrets.token_hex(8)}"
            tx_hash = '0x' + hashlib.sha256(tx_data.encode()).hexdigest()
            
            return amount0, amount1, tx_hash
    
    def _distribute_fees(self):
        """Distribute accumulated fees to LPs"""
        if self.total_shares == 0:
            return
        
        for provider, shares in self.lp_shares.items():
            if shares > 0:
                share_ratio = shares / self.total_shares
                self.lp_fees[provider]['token0'] += self.accumulated_fees0 * share_ratio
                self.lp_fees[provider]['token1'] += self.accumulated_fees1 * share_ratio
        
        # Reset accumulated fees
        self.accumulated_fees0 = Decimal('0')
        self.accumulated_fees1 = Decimal('0')
    
    def _sqrt(self, n: Decimal) -> Decimal:
        """Calculate square root using Newton's method"""
        if n == 0:
            return Decimal('0')
        
        x = n
        y = (x + 1) / 2
        
        while y < x:
            x = y
            y = (x + n / x) / 2
        
        return x

class OptimizedAMM:
    """High-performance AMM with advanced features"""
    
    def __init__(self):
        self.pools: Dict[str, LiquidityPool] = {}
        self.oracle = PriceOracle()
        self.order_book: Dict[str, List[Order]] = defaultdict(list)
        self.lock = threading.RLock()
        
        # Performance metrics
        self.total_volume = Decimal('0')
        self.total_fees_collected = Decimal('0')
        self.swap_count = 0
    
    def create_pool(self, token0: str, token1: str) -> LiquidityPool:
        """Create a new liquidity pool"""
        with self.lock:
            pool_key = self._get_pool_key(token0, token1)
            
            if pool_key in self.pools:
                raise ValueError(f"Pool already exists: {pool_key}")
            
            pool = LiquidityPool(token0, token1)
            self.pools[pool_key] = pool
            return pool
    
    def get_pool(self, token0: str, token1: str) -> Optional[LiquidityPool]:
        """Get existing pool"""
        pool_key = self._get_pool_key(token0, token1)
        return self.pools.get(pool_key)
    
    def swap(self, user: str, token_in: str, token_out: str, 
             amount_in: Decimal, min_amount_out: Decimal = Decimal('0'),
             deadline: Optional[int] = None) -> Dict[str, Any]:
        """Execute swap with routing and optimization"""
        
        # Check deadline
        if deadline and time.time() > deadline:
            raise ValueError("Transaction deadline exceeded")
        
        with self.lock:
            # Find best route (for now, direct pool only)
            pool = self.get_pool(token_in, token_out)
            if not pool:
                raise ValueError(f"No pool found for {token_in}/{token_out}")
            
            # Execute swap
            amount_out, price_impact, tx_hash = pool.swap(
                token_in, amount_in, min_amount_out
            )
            
            # Update oracle
            price = amount_out / amount_in
            self.oracle.update_price(f"{token_in}/{token_out}", price)
            
            # Update metrics
            self.total_volume += amount_in
            self.total_fees_collected += amount_in * BASE_FEE
            self.swap_count += 1
            
            return {
                'user': user,
                'token_in': token_in,
                'token_out': token_out,
                'amount_in': amount_in,
                'amount_out': amount_out,
                'price': price,
                'price_impact': price_impact,
                'tx_hash': tx_hash,
                'timestamp': time.time()
            }
    
    def add_liquidity(self, provider: str, token0: str, token1: str,
                     amount0: Decimal, amount1: Decimal) -> Dict[str, Any]:
        """Add liquidity to pool"""
        with self.lock:
            pool = self.get_pool(token0, token1)
            if not pool:
                pool = self.create_pool(token0, token1)
            
            shares, tx_hash = pool.add_liquidity(provider, amount0, amount1)
            
            return {
                'provider': provider,
                'token0': token0,
                'token1': token1,
                'amount0': amount0,
                'amount1': amount1,
                'shares': shares,
                'tx_hash': tx_hash,
                'timestamp': time.time()
            }
    
    def remove_liquidity(self, provider: str, token0: str, token1: str,
                        shares: Decimal) -> Dict[str, Any]:
        """Remove liquidity from pool"""
        with self.lock:
            pool = self.get_pool(token0, token1)
            if not pool:
                raise ValueError(f"No pool found for {token0}/{token1}")
            
            amount0, amount1, tx_hash = pool.remove_liquidity(provider, shares)
            
            return {
                'provider': provider,
                'token0': token0,
                'token1': token1,
                'shares': shares,
                'amount0': amount0,
                'amount1': amount1,
                'tx_hash': tx_hash,
                'timestamp': time.time()
            }
    
    def place_limit_order(self, user: str, token_in: str, token_out: str,
                         amount_in: Decimal, price: Decimal, 
                         expiry: Optional[int] = None) -> str:
        """Place a limit order"""
        order_id = '0x' + secrets.token_hex(16)
        
        order = Order(
            id=order_id,
            user=user,
            order_type=OrderType.LIMIT,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            min_amount_out=amount_in * price,
            price=price,
            expiry=expiry
        )
        
        with self.lock:
            pool_key = self._get_pool_key(token_in, token_out)
            heapq.heappush(self.order_book[pool_key], order)
        
        return order_id
    
    def match_orders(self, token0: str, token1: str) -> List[Dict[str, Any]]:
        """Match limit orders against current pool price"""
        matches = []
        pool = self.get_pool(token0, token1)
        
        if not pool:
            return matches
        
        with self.lock:
            pool_key = self._get_pool_key(token0, token1)
            orders = self.order_book.get(pool_key, [])
            
            if not orders:
                return matches
            
            current_price = pool.get_spot_price(token0)
            matched_orders = []
            
            # Process orders that can be matched
            temp_orders = []
            while orders:
                order = heapq.heappop(orders)
                
                # Check expiry
                if order.expiry and time.time() > order.expiry:
                    continue
                
                # Check if order can be matched
                if order.order_type == OrderType.LIMIT:
                    if order.price and order.price >= current_price:
                        # Execute order
                        try:
                            result = self.swap(
                                order.user,
                                order.token_in,
                                order.token_out,
                                order.amount_in,
                                order.min_amount_out
                            )
                            result['order_id'] = order.id
                            matches.append(result)
                        except Exception as e:
                            # Order couldn't be executed, keep it
                            temp_orders.append(order)
                    else:
                        temp_orders.append(order)
            
            # Restore unmatched orders
            for order in temp_orders:
                heapq.heappush(orders, order)
            
            self.order_book[pool_key] = orders
        
        return matches
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        return {
            'total_volume': str(self.total_volume),
            'total_fees_collected': str(self.total_fees_collected),
            'swap_count': self.swap_count,
            'pool_count': len(self.pools),
            'tvl': self._calculate_tvl()
        }
    
    def _calculate_tvl(self) -> Dict[str, Decimal]:
        """Calculate total value locked"""
        tvl = defaultdict(Decimal)
        
        for pool in self.pools.values():
            tvl[pool.token0] += pool.reserve0
            tvl[pool.token1] += pool.reserve1
        
        return dict(tvl)
    
    def _get_pool_key(self, token0: str, token1: str) -> str:
        """Get standardized pool key"""
        return f"{min(token0, token1)}/{max(token0, token1)}"

def main():
    """Demonstration of optimized AMM"""
    print("=" * 60)
    print(" QENEX OPTIMIZED AMM - PRODUCTION READY")
    print("=" * 60)
    
    amm = OptimizedAMM()
    
    # Create pool
    pool = amm.create_pool('ETH', 'USDC')
    print("\n[✓] Created ETH/USDC pool")
    
    # Add initial liquidity
    result = amm.add_liquidity('alice', 'ETH', 'USDC', 
                              Decimal('100'), Decimal('200000'))
    print(f"[✓] Added liquidity: {result['shares']} LP tokens")
    
    # Perform swap
    swap_result = amm.swap('bob', 'ETH', 'USDC', Decimal('1'))
    print(f"[✓] Swap: 1 ETH -> {swap_result['amount_out']:.2f} USDC")
    print(f"    Price impact: {swap_result['price_impact'] * 100:.2f}%")
    
    # Place limit order
    order_id = amm.place_limit_order('charlie', 'USDC', 'ETH',
                                    Decimal('2000'), Decimal('0.0005'))
    print(f"[✓] Placed limit order: {order_id[:10]}...")
    
    # Get metrics
    metrics = amm.get_metrics()
    print("\n[📊] System Metrics:")
    print(f"    Total Volume: {metrics['total_volume']}")
    print(f"    Fees Collected: {metrics['total_fees_collected']}")
    print(f"    Swap Count: {metrics['swap_count']}")
    
    print("\n" + "=" * 60)
    print(" OPTIMIZED AMM READY FOR PRODUCTION")
    print("=" * 60)

if __name__ == "__main__":
    main()