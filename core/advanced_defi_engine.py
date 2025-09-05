"""
QENEX Advanced DeFi Engine
Production-ready decentralized finance protocols with institutional-grade features
"""

import asyncio
import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from decimal import Decimal, getcontext
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple
import logging
import uuid

# Configure precision for DeFi calculations
getcontext().prec = 38  # Higher precision for DeFi

logger = logging.getLogger(__name__)


class PoolType(Enum):
    """Liquidity pool types"""
    CONSTANT_PRODUCT = auto()  # x * y = k (Uniswap V2 style)
    STABLE_SWAP = auto()  # For stablecoins
    CONCENTRATED = auto()  # Concentrated liquidity (Uniswap V3 style)
    WEIGHTED = auto()  # Balancer-style weighted pools
    META = auto()  # Pool of pools


class OrderType(Enum):
    """Order types for DEX"""
    MARKET = auto()
    LIMIT = auto()
    STOP_LOSS = auto()
    TAKE_PROFIT = auto()
    TRAILING_STOP = auto()


@dataclass
class Token:
    """Token representation"""
    symbol: str
    address: str
    decimals: int = 18
    total_supply: Decimal = Decimal("0")
    circulating_supply: Decimal = Decimal("0")
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def format_amount(self, amount: Decimal) -> Decimal:
        """Format amount with correct decimals"""
        return amount / Decimal(10 ** self.decimals)


@dataclass
class LiquidityPosition:
    """Liquidity provider position"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    provider: str = ""
    pool_id: str = ""
    token0_amount: Decimal = Decimal("0")
    token1_amount: Decimal = Decimal("0")
    liquidity_tokens: Decimal = Decimal("0")
    timestamp: float = field(default_factory=time.time)
    fee_tier: Decimal = Decimal("0.003")  # 0.3% default
    
    def calculate_share(self, total_liquidity: Decimal) -> Decimal:
        """Calculate pool share percentage"""
        if total_liquidity == 0:
            return Decimal("0")
        return (self.liquidity_tokens / total_liquidity) * Decimal("100")


class AutomatedMarketMaker:
    """Advanced AMM implementation"""
    
    def __init__(self):
        self.pools: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, LiquidityPosition] = {}
        self.fee_tiers = [
            Decimal("0.0005"),  # 0.05% - Stable pairs
            Decimal("0.003"),   # 0.3% - Standard
            Decimal("0.01"),    # 1% - Exotic pairs
        ]
        self.protocol_fee = Decimal("0.0005")  # 0.05% protocol fee
        
    def create_pool(
        self,
        token0: Token,
        token1: Token,
        pool_type: PoolType = PoolType.CONSTANT_PRODUCT,
        fee_tier: Decimal = Decimal("0.003")
    ) -> str:
        """Create a new liquidity pool"""
        pool_id = f"{token0.symbol}_{token1.symbol}_{int(time.time())}"
        
        self.pools[pool_id] = {
            "token0": token0,
            "token1": token1,
            "reserve0": Decimal("0"),
            "reserve1": Decimal("0"),
            "total_liquidity": Decimal("0"),
            "pool_type": pool_type,
            "fee_tier": fee_tier,
            "volume_24h": Decimal("0"),
            "fees_collected": Decimal("0"),
            "created": time.time(),
            "price_history": []
        }
        
        logger.info(f"Created pool {pool_id} with fee tier {fee_tier}")
        return pool_id
    
    def add_liquidity(
        self,
        pool_id: str,
        provider: str,
        amount0: Decimal,
        amount1: Decimal
    ) -> Optional[LiquidityPosition]:
        """Add liquidity to pool"""
        if pool_id not in self.pools:
            logger.error(f"Pool {pool_id} not found")
            return None
        
        pool = self.pools[pool_id]
        
        # Calculate liquidity tokens
        if pool["total_liquidity"] == 0:
            # First liquidity provider
            liquidity_tokens = (amount0 * amount1).sqrt()
            pool["reserve0"] = amount0
            pool["reserve1"] = amount1
        else:
            # Subsequent providers must maintain ratio
            ratio = pool["reserve1"] / pool["reserve0"]
            expected_amount1 = amount0 * ratio
            
            if abs(amount1 - expected_amount1) > expected_amount1 * Decimal("0.01"):
                logger.error("Liquidity amounts don't match pool ratio")
                return None
            
            # Calculate liquidity tokens proportionally
            liquidity_tokens = min(
                (amount0 / pool["reserve0"]) * pool["total_liquidity"],
                (amount1 / pool["reserve1"]) * pool["total_liquidity"]
            )
            
            pool["reserve0"] += amount0
            pool["reserve1"] += amount1
        
        pool["total_liquidity"] += liquidity_tokens
        
        # Create position
        position = LiquidityPosition(
            provider=provider,
            pool_id=pool_id,
            token0_amount=amount0,
            token1_amount=amount1,
            liquidity_tokens=liquidity_tokens,
            fee_tier=pool["fee_tier"]
        )
        
        self.positions[position.id] = position
        
        logger.info(f"Added liquidity: {amount0} + {amount1} to pool {pool_id}")
        return position
    
    def remove_liquidity(
        self,
        position_id: str
    ) -> Optional[Tuple[Decimal, Decimal]]:
        """Remove liquidity from pool"""
        if position_id not in self.positions:
            logger.error(f"Position {position_id} not found")
            return None
        
        position = self.positions[position_id]
        pool = self.pools[position.pool_id]
        
        # Calculate tokens to return
        share = position.liquidity_tokens / pool["total_liquidity"]
        amount0 = pool["reserve0"] * share
        amount1 = pool["reserve1"] * share
        
        # Update pool
        pool["reserve0"] -= amount0
        pool["reserve1"] -= amount1
        pool["total_liquidity"] -= position.liquidity_tokens
        
        # Remove position
        del self.positions[position_id]
        
        logger.info(f"Removed liquidity: {amount0} + {amount1} from pool {position.pool_id}")
        return (amount0, amount1)
    
    def swap(
        self,
        pool_id: str,
        token_in: str,
        amount_in: Decimal,
        min_amount_out: Decimal = Decimal("0")
    ) -> Optional[Decimal]:
        """Execute token swap"""
        if pool_id not in self.pools:
            logger.error(f"Pool {pool_id} not found")
            return None
        
        pool = self.pools[pool_id]
        
        # Determine swap direction
        is_token0 = token_in == pool["token0"].symbol
        
        if is_token0:
            reserve_in = pool["reserve0"]
            reserve_out = pool["reserve1"]
        else:
            reserve_in = pool["reserve1"]
            reserve_out = pool["reserve0"]
        
        # Apply fee
        fee_amount = amount_in * pool["fee_tier"]
        protocol_fee_amount = amount_in * self.protocol_fee
        amount_in_after_fee = amount_in - fee_amount - protocol_fee_amount
        
        # Calculate output using constant product formula
        # (x + Δx) * (y - Δy) = x * y
        amount_out = self._calculate_output_amount(
            amount_in_after_fee,
            reserve_in,
            reserve_out,
            pool["pool_type"]
        )
        
        if amount_out < min_amount_out:
            logger.error(f"Slippage too high: {amount_out} < {min_amount_out}")
            return None
        
        # Update reserves
        if is_token0:
            pool["reserve0"] += amount_in
            pool["reserve1"] -= amount_out
        else:
            pool["reserve1"] += amount_in
            pool["reserve0"] -= amount_out
        
        # Update metrics
        pool["volume_24h"] += amount_in
        pool["fees_collected"] += fee_amount
        
        # Record price
        price = pool["reserve1"] / pool["reserve0"]
        pool["price_history"].append({
            "timestamp": time.time(),
            "price": float(price),
            "volume": float(amount_in)
        })
        
        logger.info(f"Swap executed: {amount_in} -> {amount_out} in pool {pool_id}")
        return amount_out
    
    def _calculate_output_amount(
        self,
        amount_in: Decimal,
        reserve_in: Decimal,
        reserve_out: Decimal,
        pool_type: PoolType
    ) -> Decimal:
        """Calculate output amount based on pool type"""
        if pool_type == PoolType.CONSTANT_PRODUCT:
            # x * y = k formula
            k = reserve_in * reserve_out
            new_reserve_in = reserve_in + amount_in
            new_reserve_out = k / new_reserve_in
            amount_out = reserve_out - new_reserve_out
            
        elif pool_type == PoolType.STABLE_SWAP:
            # Stable swap formula (simplified Curve formula)
            # For stablecoins, we use a formula that reduces slippage
            A = Decimal("100")  # Amplification coefficient
            D = reserve_in + reserve_out  # Total liquidity
            
            # Calculate new balance
            new_reserve_in = reserve_in + amount_in
            
            # Solve for new_reserve_out using stable swap invariant
            # This is simplified - production would use iterative solving
            amount_out = amount_in * reserve_out / reserve_in
            amount_out *= (Decimal("1") - Decimal("0.0004"))  # Small slippage
            
        else:
            # Default to constant product
            amount_out = (amount_in * reserve_out) / (reserve_in + amount_in)
        
        return amount_out
    
    def get_pool_info(self, pool_id: str) -> Dict[str, Any]:
        """Get detailed pool information"""
        if pool_id not in self.pools:
            return {"error": "Pool not found"}
        
        pool = self.pools[pool_id]
        
        # Calculate APY from fees
        if pool["total_liquidity"] > 0:
            daily_fees = pool["fees_collected"]
            apy = (daily_fees / pool["total_liquidity"]) * Decimal("365") * Decimal("100")
        else:
            apy = Decimal("0")
        
        return {
            "pool_id": pool_id,
            "token0": pool["token0"].symbol,
            "token1": pool["token1"].symbol,
            "reserve0": str(pool["reserve0"]),
            "reserve1": str(pool["reserve1"]),
            "total_liquidity": str(pool["total_liquidity"]),
            "price": str(pool["reserve1"] / pool["reserve0"]) if pool["reserve0"] > 0 else "0",
            "volume_24h": str(pool["volume_24h"]),
            "fees_collected": str(pool["fees_collected"]),
            "apy": str(apy),
            "fee_tier": str(pool["fee_tier"])
        }


class LendingProtocol:
    """Decentralized lending and borrowing protocol"""
    
    def __init__(self):
        self.markets: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.liquidation_threshold = Decimal("0.75")  # 75% LTV
        self.liquidation_penalty = Decimal("0.1")  # 10% penalty
        self.base_rate = Decimal("0.02")  # 2% base interest rate
        
    def create_market(
        self,
        token: Token,
        collateral_factor: Decimal = Decimal("0.7")
    ) -> str:
        """Create a lending market for a token"""
        market_id = f"market_{token.symbol}_{int(time.time())}"
        
        self.markets[market_id] = {
            "token": token,
            "total_supply": Decimal("0"),
            "total_borrowed": Decimal("0"),
            "collateral_factor": collateral_factor,
            "supply_rate": self.base_rate,
            "borrow_rate": self.base_rate * Decimal("1.5"),
            "utilization": Decimal("0"),
            "created": time.time()
        }
        
        logger.info(f"Created lending market {market_id} for {token.symbol}")
        return market_id
    
    def supply(
        self,
        market_id: str,
        supplier: str,
        amount: Decimal
    ) -> bool:
        """Supply tokens to lending market"""
        if market_id not in self.markets:
            logger.error(f"Market {market_id} not found")
            return False
        
        market = self.markets[market_id]
        market["total_supply"] += amount
        
        # Update user position
        if supplier not in self.positions:
            self.positions[supplier] = {}
        
        if market_id not in self.positions[supplier]:
            self.positions[supplier][market_id] = {
                "supplied": Decimal("0"),
                "borrowed": Decimal("0")
            }
        
        self.positions[supplier][market_id]["supplied"] += amount
        
        # Update interest rates
        self._update_interest_rates(market_id)
        
        logger.info(f"{supplier} supplied {amount} to market {market_id}")
        return True
    
    def borrow(
        self,
        market_id: str,
        borrower: str,
        amount: Decimal
    ) -> bool:
        """Borrow tokens from lending market"""
        if market_id not in self.markets:
            logger.error(f"Market {market_id} not found")
            return False
        
        market = self.markets[market_id]
        
        # Check available liquidity
        available = market["total_supply"] - market["total_borrowed"]
        if amount > available:
            logger.error(f"Insufficient liquidity: {amount} > {available}")
            return False
        
        # Check collateral
        if not self._check_collateral(borrower, market_id, amount):
            logger.error(f"Insufficient collateral for {borrower}")
            return False
        
        market["total_borrowed"] += amount
        
        # Update user position
        if borrower not in self.positions:
            self.positions[borrower] = {}
        
        if market_id not in self.positions[borrower]:
            self.positions[borrower][market_id] = {
                "supplied": Decimal("0"),
                "borrowed": Decimal("0")
            }
        
        self.positions[borrower][market_id]["borrowed"] += amount
        
        # Update interest rates
        self._update_interest_rates(market_id)
        
        logger.info(f"{borrower} borrowed {amount} from market {market_id}")
        return True
    
    def repay(
        self,
        market_id: str,
        borrower: str,
        amount: Decimal
    ) -> bool:
        """Repay borrowed tokens"""
        if market_id not in self.markets:
            return False
        
        if borrower not in self.positions or market_id not in self.positions[borrower]:
            return False
        
        position = self.positions[borrower][market_id]
        repay_amount = min(amount, position["borrowed"])
        
        position["borrowed"] -= repay_amount
        self.markets[market_id]["total_borrowed"] -= repay_amount
        
        # Update interest rates
        self._update_interest_rates(market_id)
        
        logger.info(f"{borrower} repaid {repay_amount} to market {market_id}")
        return True
    
    def withdraw(
        self,
        market_id: str,
        supplier: str,
        amount: Decimal
    ) -> bool:
        """Withdraw supplied tokens"""
        if market_id not in self.markets:
            return False
        
        if supplier not in self.positions or market_id not in self.positions[supplier]:
            return False
        
        position = self.positions[supplier][market_id]
        market = self.markets[market_id]
        
        # Check available amount
        max_withdraw = min(
            position["supplied"],
            market["total_supply"] - market["total_borrowed"]
        )
        
        if amount > max_withdraw:
            logger.error(f"Cannot withdraw {amount}, max is {max_withdraw}")
            return False
        
        position["supplied"] -= amount
        market["total_supply"] -= amount
        
        # Update interest rates
        self._update_interest_rates(market_id)
        
        logger.info(f"{supplier} withdrew {amount} from market {market_id}")
        return True
    
    def _check_collateral(
        self,
        user: str,
        borrow_market: str,
        borrow_amount: Decimal
    ) -> bool:
        """Check if user has sufficient collateral"""
        if user not in self.positions:
            return False
        
        total_collateral = Decimal("0")
        total_borrowed = Decimal("0")
        
        for market_id, position in self.positions[user].items():
            market = self.markets[market_id]
            
            # Calculate collateral value
            collateral_value = position["supplied"] * market["collateral_factor"]
            total_collateral += collateral_value
            
            # Add existing borrows
            total_borrowed += position["borrowed"]
        
        # Add new borrow
        total_borrowed += borrow_amount
        
        # Check if within threshold
        if total_collateral == 0:
            return False
        
        ltv = total_borrowed / total_collateral
        return ltv <= self.liquidation_threshold
    
    def _update_interest_rates(self, market_id: str):
        """Update market interest rates based on utilization"""
        market = self.markets[market_id]
        
        if market["total_supply"] == 0:
            market["utilization"] = Decimal("0")
            return
        
        # Calculate utilization
        utilization = market["total_borrowed"] / market["total_supply"]
        market["utilization"] = utilization
        
        # Update rates based on utilization curve
        if utilization < Decimal("0.8"):
            # Normal rate
            market["borrow_rate"] = self.base_rate + (utilization * Decimal("0.1"))
        else:
            # Jump rate when utilization is high
            market["borrow_rate"] = self.base_rate + (utilization * Decimal("0.5"))
        
        # Supply rate is borrow rate * utilization * (1 - reserve factor)
        reserve_factor = Decimal("0.1")  # 10% reserve
        market["supply_rate"] = (
            market["borrow_rate"] * utilization * (Decimal("1") - reserve_factor)
        )
    
    def liquidate(
        self,
        liquidator: str,
        user: str,
        market_id: str,
        repay_amount: Decimal
    ) -> Optional[Decimal]:
        """Liquidate undercollateralized position"""
        if user not in self.positions:
            return None
        
        # Check if position is liquidatable
        if self._check_collateral(user, market_id, Decimal("0")):
            logger.error(f"Position for {user} is not liquidatable")
            return None
        
        position = self.positions[user][market_id]
        market = self.markets[market_id]
        
        # Calculate collateral to seize
        collateral_amount = repay_amount * (Decimal("1") + self.liquidation_penalty)
        
        # Execute liquidation
        actual_repay = min(repay_amount, position["borrowed"])
        actual_collateral = min(collateral_amount, position["supplied"])
        
        position["borrowed"] -= actual_repay
        position["supplied"] -= actual_collateral
        
        market["total_borrowed"] -= actual_repay
        market["total_supply"] -= actual_collateral
        
        logger.info(f"Liquidated {user}: repaid {actual_repay}, seized {actual_collateral}")
        return actual_collateral


class YieldFarming:
    """Yield farming and staking rewards"""
    
    def __init__(self):
        self.farms: Dict[str, Dict[str, Any]] = {}
        self.stakes: Dict[str, Dict[str, Any]] = {}
        self.reward_token = Token("QREWARD", "0xreward", 18)
        
    def create_farm(
        self,
        farm_id: str,
        staking_token: Token,
        reward_rate: Decimal,
        duration: int = 2592000  # 30 days default
    ) -> bool:
        """Create a yield farm"""
        self.farms[farm_id] = {
            "staking_token": staking_token,
            "reward_rate": reward_rate,  # Rewards per second
            "total_staked": Decimal("0"),
            "duration": duration,
            "start_time": time.time(),
            "end_time": time.time() + duration,
            "last_update": time.time(),
            "reward_per_token": Decimal("0")
        }
        
        logger.info(f"Created farm {farm_id} with reward rate {reward_rate}/s")
        return True
    
    def stake(
        self,
        farm_id: str,
        staker: str,
        amount: Decimal
    ) -> bool:
        """Stake tokens in farm"""
        if farm_id not in self.farms:
            return False
        
        farm = self.farms[farm_id]
        
        # Update rewards
        self._update_rewards(farm_id)
        
        # Update stake
        if staker not in self.stakes:
            self.stakes[staker] = {}
        
        if farm_id not in self.stakes[staker]:
            self.stakes[staker][farm_id] = {
                "amount": Decimal("0"),
                "reward_debt": Decimal("0"),
                "pending_rewards": Decimal("0")
            }
        
        stake = self.stakes[staker][farm_id]
        
        # Calculate pending rewards for existing stake
        if stake["amount"] > 0:
            pending = self._calculate_pending_rewards(staker, farm_id)
            stake["pending_rewards"] += pending
        
        stake["amount"] += amount
        stake["reward_debt"] = stake["amount"] * farm["reward_per_token"]
        
        farm["total_staked"] += amount
        
        logger.info(f"{staker} staked {amount} in farm {farm_id}")
        return True
    
    def unstake(
        self,
        farm_id: str,
        staker: str,
        amount: Decimal
    ) -> Optional[Tuple[Decimal, Decimal]]:
        """Unstake tokens and claim rewards"""
        if farm_id not in self.farms:
            return None
        
        if staker not in self.stakes or farm_id not in self.stakes[staker]:
            return None
        
        # Update rewards
        self._update_rewards(farm_id)
        
        stake = self.stakes[staker][farm_id]
        farm = self.farms[farm_id]
        
        unstake_amount = min(amount, stake["amount"])
        
        # Calculate rewards
        rewards = self._calculate_pending_rewards(staker, farm_id)
        rewards += stake["pending_rewards"]
        
        # Update stake
        stake["amount"] -= unstake_amount
        stake["reward_debt"] = stake["amount"] * farm["reward_per_token"]
        stake["pending_rewards"] = Decimal("0")
        
        farm["total_staked"] -= unstake_amount
        
        logger.info(f"{staker} unstaked {unstake_amount} and claimed {rewards} rewards")
        return (unstake_amount, rewards)
    
    def _update_rewards(self, farm_id: str):
        """Update reward accumulator"""
        farm = self.farms[farm_id]
        
        if farm["total_staked"] == 0:
            farm["last_update"] = time.time()
            return
        
        current_time = min(time.time(), farm["end_time"])
        time_elapsed = current_time - farm["last_update"]
        
        if time_elapsed > 0:
            rewards = Decimal(str(time_elapsed)) * farm["reward_rate"]
            farm["reward_per_token"] += rewards / farm["total_staked"]
            farm["last_update"] = current_time
    
    def _calculate_pending_rewards(self, staker: str, farm_id: str) -> Decimal:
        """Calculate pending rewards for staker"""
        if staker not in self.stakes or farm_id not in self.stakes[staker]:
            return Decimal("0")
        
        stake = self.stakes[staker][farm_id]
        farm = self.farms[farm_id]
        
        accumulated = stake["amount"] * farm["reward_per_token"]
        pending = accumulated - stake["reward_debt"]
        
        return pending


class UnifiedDeFiEngine:
    """Main DeFi orchestrator"""
    
    def __init__(self):
        self.amm = AutomatedMarketMaker()
        self.lending = LendingProtocol()
        self.farming = YieldFarming()
        
        # Create default tokens
        self.tokens = {
            "QXC": Token("QXC", "0xqxc", 18, Decimal("1000000000")),
            "USDT": Token("USDT", "0xusdt", 6, Decimal("1000000000")),
            "ETH": Token("ETH", "0xeth", 18, Decimal("1000000")),
            "BTC": Token("BTC", "0xbtc", 8, Decimal("21000000"))
        }
        
        self.user_balances: Dict[str, Dict[str, Decimal]] = {}
        
    async def initialize(self):
        """Initialize DeFi ecosystem"""
        logger.info("Initializing QENEX DeFi Engine...")
        
        # Create default pools
        self.amm.create_pool(
            self.tokens["QXC"],
            self.tokens["USDT"],
            PoolType.CONSTANT_PRODUCT,
            Decimal("0.003")
        )
        
        self.amm.create_pool(
            self.tokens["ETH"],
            self.tokens["USDT"],
            PoolType.CONSTANT_PRODUCT,
            Decimal("0.003")
        )
        
        # Create lending markets
        for token in self.tokens.values():
            self.lending.create_market(token)
        
        # Create yield farms
        self.farming.create_farm(
            "QXC_STAKING",
            self.tokens["QXC"],
            Decimal("10")  # 10 tokens per second
        )
        
        logger.info("DeFi Engine initialized successfully")
    
    def get_user_balance(self, user: str, token: str) -> Decimal:
        """Get user token balance"""
        if user not in self.user_balances:
            return Decimal("0")
        
        return self.user_balances[user].get(token, Decimal("0"))
    
    def transfer(
        self,
        sender: str,
        receiver: str,
        token: str,
        amount: Decimal
    ) -> bool:
        """Transfer tokens between users"""
        sender_balance = self.get_user_balance(sender, token)
        
        if sender_balance < amount:
            logger.error(f"Insufficient balance: {sender_balance} < {amount}")
            return False
        
        # Update balances
        if sender not in self.user_balances:
            self.user_balances[sender] = {}
        if receiver not in self.user_balances:
            self.user_balances[receiver] = {}
        
        self.user_balances[sender][token] = sender_balance - amount
        self.user_balances[receiver][token] = self.get_user_balance(receiver, token) + amount
        
        logger.info(f"Transferred {amount} {token} from {sender} to {receiver}")
        return True
    
    async def get_ecosystem_stats(self) -> Dict[str, Any]:
        """Get comprehensive DeFi ecosystem statistics"""
        total_tvl = Decimal("0")
        
        # Calculate AMM TVL
        for pool_id, pool in self.amm.pools.items():
            total_tvl += pool["reserve0"] + pool["reserve1"]
        
        # Calculate lending TVL
        for market in self.lending.markets.values():
            total_tvl += market["total_supply"]
        
        # Calculate farming TVL
        for farm in self.farming.farms.values():
            total_tvl += farm["total_staked"]
        
        return {
            "total_value_locked": str(total_tvl),
            "amm": {
                "pools": len(self.amm.pools),
                "positions": len(self.amm.positions),
                "total_volume": str(sum(p["volume_24h"] for p in self.amm.pools.values()))
            },
            "lending": {
                "markets": len(self.lending.markets),
                "total_supplied": str(sum(m["total_supply"] for m in self.lending.markets.values())),
                "total_borrowed": str(sum(m["total_borrowed"] for m in self.lending.markets.values()))
            },
            "farming": {
                "farms": len(self.farming.farms),
                "total_staked": str(sum(f["total_staked"] for f in self.farming.farms.values()))
            }
        }


# Main execution
async def main():
    """Main DeFi application"""
    engine = UnifiedDeFiEngine()
    await engine.initialize()
    
    # Get ecosystem stats
    stats = await engine.get_ecosystem_stats()
    logger.info(f"DeFi Ecosystem Stats: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())