#!/usr/bin/env python3
"""
Automated Market Maker Implementation
"""

from decimal import Decimal, getcontext
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import time
import logging

# Set decimal precision
getcontext().prec = 28

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Pool:
    """Liquidity pool representation"""
    token0: str
    token1: str
    reserve0: Decimal
    reserve1: Decimal
    total_shares: Decimal
    fee: Decimal = Decimal('0.003')  # 0.3% fee
    
    @property
    def k(self) -> Decimal:
        """Constant product"""
        return self.reserve0 * self.reserve1
    
    def get_price(self, token: str) -> Optional[Decimal]:
        """Get price of token in terms of the other token"""
        if token == self.token0 and self.reserve0 > 0:
            return self.reserve1 / self.reserve0
        elif token == self.token1 and self.reserve1 > 0:
            return self.reserve0 / self.reserve1
        return None
    
    def quote(self, amount0: Decimal) -> Decimal:
        """Quote amount of token1 needed for given amount0"""
        if self.reserve0 == 0:
            return Decimal('0')
        return (amount0 * self.reserve1) / self.reserve0


class AMM:
    """Automated Market Maker system"""
    
    def __init__(self):
        self.pools: Dict[str, Pool] = {}
        self.liquidity_providers: Dict[str, Dict[str, Decimal]] = {}
    
    def create_pool(self, token0: str, token1: str) -> str:
        """Create new liquidity pool"""
        # Ensure consistent ordering
        if token0 > token1:
            token0, token1 = token1, token0
        
        pool_id = f"{token0}-{token1}"
        
        if pool_id in self.pools:
            raise ValueError(f"Pool {pool_id} already exists")
        
        self.pools[pool_id] = Pool(
            token0=token0,
            token1=token1,
            reserve0=Decimal('0'),
            reserve1=Decimal('0'),
            total_shares=Decimal('0')
        )
        
        logger.info(f"Created pool: {pool_id}")
        return pool_id
    
    def add_liquidity(
        self,
        provider: str,
        token0: str,
        token1: str,
        amount0: Decimal,
        amount1: Decimal
    ) -> Decimal:
        """Add liquidity to pool and return LP tokens"""
        # Ensure consistent ordering
        if token0 > token1:
            token0, token1 = token1, token0
            amount0, amount1 = amount1, amount0
        
        pool_id = f"{token0}-{token1}"
        pool = self.pools.get(pool_id)
        
        if not pool:
            raise ValueError(f"Pool {pool_id} does not exist")
        
        if amount0 <= 0 or amount1 <= 0:
            raise ValueError("Amounts must be positive")
        
        # Calculate shares
        if pool.total_shares == 0:
            # First liquidity provider
            shares = (amount0 * amount1).sqrt()
        else:
            # Subsequent providers - maintain ratio
            shares = min(
                (amount0 * pool.total_shares) / pool.reserve0,
                (amount1 * pool.total_shares) / pool.reserve1
            )
        
        # Update pool reserves
        pool.reserve0 += amount0
        pool.reserve1 += amount1
        pool.total_shares += shares
        
        # Track provider's shares
        if provider not in self.liquidity_providers:
            self.liquidity_providers[provider] = {}
        
        if pool_id not in self.liquidity_providers[provider]:
            self.liquidity_providers[provider][pool_id] = Decimal('0')
        
        self.liquidity_providers[provider][pool_id] += shares
        
        logger.info(f"Added liquidity: {provider} -> {pool_id}: {shares} shares")
        return shares
    
    def remove_liquidity(
        self,
        provider: str,
        token0: str,
        token1: str,
        shares: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """Remove liquidity and return tokens"""
        # Ensure consistent ordering
        if token0 > token1:
            token0, token1 = token1, token0
        
        pool_id = f"{token0}-{token1}"
        pool = self.pools.get(pool_id)
        
        if not pool:
            raise ValueError(f"Pool {pool_id} does not exist")
        
        if provider not in self.liquidity_providers or \
           pool_id not in self.liquidity_providers[provider]:
            raise ValueError(f"No liquidity position for {provider} in {pool_id}")
        
        provider_shares = self.liquidity_providers[provider][pool_id]
        
        if shares > provider_shares:
            raise ValueError(f"Insufficient shares: {shares} > {provider_shares}")
        
        # Calculate token amounts
        share_ratio = shares / pool.total_shares
        amount0 = pool.reserve0 * share_ratio
        amount1 = pool.reserve1 * share_ratio
        
        # Update pool
        pool.reserve0 -= amount0
        pool.reserve1 -= amount1
        pool.total_shares -= shares
        
        # Update provider's shares
        self.liquidity_providers[provider][pool_id] -= shares
        
        logger.info(f"Removed liquidity: {provider} -> {pool_id}: {amount0} {token0}, {amount1} {token1}")
        return amount0, amount1
    
    def swap(
        self,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        slippage_tolerance: Decimal = Decimal('0.01')
    ) -> Tuple[Decimal, Decimal]:
        """Swap tokens and return output amount and price impact"""
        if amount_in <= 0:
            raise ValueError("Input amount must be positive")
        
        # Find pool
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
        
        if reserve_in == 0 or reserve_out == 0:
            raise ValueError("Pool has no liquidity")
        
        # Calculate output amount with fee
        amount_in_with_fee = amount_in * (Decimal('1') - pool.fee)
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in + amount_in_with_fee
        amount_out = numerator / denominator
        
        # Calculate price impact
        price_before = reserve_out / reserve_in
        price_after = (reserve_out - amount_out) / (reserve_in + amount_in)
        price_impact = abs(price_after - price_before) / price_before
        
        # Check slippage
        if price_impact > slippage_tolerance:
            raise ValueError(f"Price impact {price_impact:.2%} exceeds tolerance {slippage_tolerance:.2%}")
        
        # Update reserves
        if token_in == pool.token0:
            pool.reserve0 += amount_in
            pool.reserve1 -= amount_out
        else:
            pool.reserve1 += amount_in
            pool.reserve0 -= amount_out
        
        logger.info(f"Swap: {amount_in} {token_in} -> {amount_out} {token_out} (impact: {price_impact:.2%})")
        return amount_out, price_impact
    
    def get_pool_info(self, token0: str, token1: str) -> Dict:
        """Get pool information"""
        if token0 > token1:
            token0, token1 = token1, token0
        
        pool_id = f"{token0}-{token1}"
        pool = self.pools.get(pool_id)
        
        if not pool:
            return None
        
        return {
            'pool_id': pool_id,
            'token0': pool.token0,
            'token1': pool.token1,
            'reserve0': str(pool.reserve0),
            'reserve1': str(pool.reserve1),
            'total_shares': str(pool.total_shares),
            'k': str(pool.k),
            'price0': str(pool.get_price(pool.token0)) if pool.get_price(pool.token0) else '0',
            'price1': str(pool.get_price(pool.token1)) if pool.get_price(pool.token1) else '0',
            'fee': str(pool.fee)
        }
    
    def calculate_price_impact(
        self,
        token_in: str,
        token_out: str,
        amount_in: Decimal
    ) -> Decimal:
        """Calculate price impact for a swap without executing"""
        pool_id = f"{min(token_in, token_out)}-{max(token_in, token_out)}"
        pool = self.pools.get(pool_id)
        
        if not pool:
            return Decimal('0')
        
        if token_in == pool.token0:
            reserve_in = pool.reserve0
            reserve_out = pool.reserve1
        else:
            reserve_in = pool.reserve1
            reserve_out = pool.reserve0
        
        if reserve_in == 0 or reserve_out == 0:
            return Decimal('1')  # 100% impact
        
        price_before = reserve_out / reserve_in
        amount_in_with_fee = amount_in * (Decimal('1') - pool.fee)
        amount_out = (amount_in_with_fee * reserve_out) / (reserve_in + amount_in_with_fee)
        price_after = (reserve_out - amount_out) / (reserve_in + amount_in)
        
        return abs(price_after - price_before) / price_before


def demo():
    """Demonstration of AMM functionality"""
    print("\n" + "="*60)
    print(" AMM DEMONSTRATION")
    print("="*60)
    
    amm = AMM()
    
    # Create pools
    print("\n[1] Creating Pools...")
    amm.create_pool('ETH', 'USDC')
    amm.create_pool('BTC', 'USDC')
    print("    Created ETH-USDC pool")
    print("    Created BTC-USDC pool")
    
    # Add liquidity
    print("\n[2] Adding Liquidity...")
    shares1 = amm.add_liquidity('alice', 'ETH', 'USDC', Decimal('10'), Decimal('20000'))
    shares2 = amm.add_liquidity('bob', 'BTC', 'USDC', Decimal('2'), Decimal('80000'))
    print(f"    Alice added 10 ETH + 20,000 USDC -> {shares1:.2f} LP tokens")
    print(f"    Bob added 2 BTC + 80,000 USDC -> {shares2:.2f} LP tokens")
    
    # Get pool info
    print("\n[3] Pool Information:")
    eth_pool = amm.get_pool_info('ETH', 'USDC')
    btc_pool = amm.get_pool_info('BTC', 'USDC')
    print(f"    ETH-USDC: {eth_pool['reserve0']} ETH / {eth_pool['reserve1']} USDC")
    print(f"    ETH Price: ${eth_pool['price0']}")
    print(f"    BTC-USDC: {btc_pool['reserve0']} BTC / {btc_pool['reserve1']} USDC")
    print(f"    BTC Price: ${btc_pool['price0']}")
    
    # Calculate price impact
    print("\n[4] Price Impact Analysis:")
    impact1 = amm.calculate_price_impact('ETH', 'USDC', Decimal('1'))
    impact2 = amm.calculate_price_impact('ETH', 'USDC', Decimal('5'))
    print(f"    Swapping 1 ETH: {impact1:.2%} impact")
    print(f"    Swapping 5 ETH: {impact2:.2%} impact")
    
    # Perform swaps
    print("\n[5] Performing Swaps...")
    usdc_out, impact = amm.swap('ETH', 'USDC', Decimal('0.5'))
    print(f"    Swapped 0.5 ETH -> {usdc_out:.2f} USDC (impact: {impact:.2%})")
    
    eth_out, impact = amm.swap('USDC', 'ETH', Decimal('1000'))
    print(f"    Swapped 1000 USDC -> {eth_out:.4f} ETH (impact: {impact:.2%})")
    
    # Updated pool info
    print("\n[6] Updated Pool State:")
    eth_pool = amm.get_pool_info('ETH', 'USDC')
    print(f"    ETH-USDC: {eth_pool['reserve0']} ETH / {eth_pool['reserve1']} USDC")
    print(f"    New ETH Price: ${eth_pool['price0']}")
    print(f"    Constant K: {eth_pool['k']}")
    
    # Remove liquidity
    print("\n[7] Removing Liquidity...")
    amount0, amount1 = amm.remove_liquidity('alice', 'ETH', 'USDC', shares1 / 2)
    print(f"    Alice removed 50% -> received {amount0:.4f} ETH + {amount1:.2f} USDC")
    
    print("\n" + "="*60)
    print(" DEMONSTRATION COMPLETE")
    print("="*60 + "\n")


if __name__ == '__main__':
    demo()