#!/usr/bin/env python3

import math
import time
import json
import secrets
import hashlib
import sqlite3
import threading
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, getcontext, ROUND_DOWN, ROUND_UP
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
from queue import Queue, PriorityQueue
import base64

getcontext().prec = 256

@dataclass
class Token:
    symbol: str
    name: str
    total_supply: Decimal
    decimals: int = 18
    address: str = ""
    owner: str = ""
    minted: Decimal = field(default_factory=lambda: Decimal("0"))
    burned: Decimal = field(default_factory=lambda: Decimal("0"))

@dataclass
class LiquidityPool:
    token_a: str
    token_b: str
    reserve_a: Decimal
    reserve_b: Decimal
    lp_token_supply: Decimal = field(default_factory=lambda: Decimal("0"))
    fee_rate: Decimal = field(default_factory=lambda: Decimal("0.003"))
    protocol_fee: Decimal = field(default_factory=lambda: Decimal("0.0005"))
    k_constant: Decimal = field(default_factory=lambda: Decimal("0"))

@dataclass
class Position:
    owner: str
    pool_address: str
    lp_tokens: Decimal
    entry_price: Decimal
    timestamp: float
    rewards_claimed: Decimal = field(default_factory=lambda: Decimal("0"))

@dataclass
class Order:
    order_id: str
    trader: str
    order_type: str  
    token_in: str
    token_out: str
    amount_in: Decimal
    min_amount_out: Decimal
    price: Decimal
    timestamp: float
    status: str = "pending"
    filled_amount: Decimal = field(default_factory=lambda: Decimal("0"))

class AMM:
    def __init__(self):
        self.pools = {}
        self.fee_rate = Decimal("0.003")
        
    def create_pool(self, token_a: str, token_b: str, 
                   initial_a: Decimal, initial_b: Decimal) -> str:
        pool_address = self.generate_pool_address(token_a, token_b)
        
        if pool_address in self.pools:
            return pool_address
        
        k_constant = initial_a * initial_b
        lp_supply = (initial_a * initial_b).sqrt()
        
        pool = LiquidityPool(
            token_a=token_a,
            token_b=token_b,
            reserve_a=initial_a,
            reserve_b=initial_b,
            lp_token_supply=lp_supply,
            k_constant=k_constant
        )
        
        self.pools[pool_address] = pool
        return pool_address
    
    def generate_pool_address(self, token_a: str, token_b: str) -> str:
        tokens = sorted([token_a, token_b])
        data = f"{tokens[0]}{tokens[1]}".encode()
        return "LP" + hashlib.sha256(data).hexdigest()[:40]
    
    def swap(self, pool_address: str, token_in: str, amount_in: Decimal) -> Decimal:
        if pool_address not in self.pools:
            return Decimal("0")
        
        pool = self.pools[pool_address]
        
        if token_in == pool.token_a:
            reserve_in = pool.reserve_a
            reserve_out = pool.reserve_b
        elif token_in == pool.token_b:
            reserve_in = pool.reserve_b
            reserve_out = pool.reserve_a
        else:
            return Decimal("0")
        
        amount_in_with_fee = amount_in * (Decimal("1") - self.fee_rate)
        amount_out = (reserve_out * amount_in_with_fee) / (reserve_in + amount_in_with_fee)
        
        if token_in == pool.token_a:
            pool.reserve_a += amount_in
            pool.reserve_b -= amount_out
        else:
            pool.reserve_b += amount_in
            pool.reserve_a -= amount_out
        
        pool.k_constant = pool.reserve_a * pool.reserve_b
        
        return amount_out
    
    def add_liquidity(self, pool_address: str, amount_a: Decimal, 
                     amount_b: Decimal) -> Decimal:
        if pool_address not in self.pools:
            return Decimal("0")
        
        pool = self.pools[pool_address]
        
        if pool.lp_token_supply == 0:
            lp_tokens = (amount_a * amount_b).sqrt()
        else:
            lp_tokens = min(
                amount_a * pool.lp_token_supply / pool.reserve_a,
                amount_b * pool.lp_token_supply / pool.reserve_b
            )
        
        pool.reserve_a += amount_a
        pool.reserve_b += amount_b
        pool.lp_token_supply += lp_tokens
        pool.k_constant = pool.reserve_a * pool.reserve_b
        
        return lp_tokens
    
    def remove_liquidity(self, pool_address: str, lp_tokens: Decimal) -> Tuple[Decimal, Decimal]:
        if pool_address not in self.pools:
            return Decimal("0"), Decimal("0")
        
        pool = self.pools[pool_address]
        
        if lp_tokens > pool.lp_token_supply:
            return Decimal("0"), Decimal("0")
        
        share = lp_tokens / pool.lp_token_supply
        amount_a = pool.reserve_a * share
        amount_b = pool.reserve_b * share
        
        pool.reserve_a -= amount_a
        pool.reserve_b -= amount_b
        pool.lp_token_supply -= lp_tokens
        pool.k_constant = pool.reserve_a * pool.reserve_b
        
        return amount_a, amount_b
    
    def get_price(self, pool_address: str, token: str) -> Decimal:
        if pool_address not in self.pools:
            return Decimal("0")
        
        pool = self.pools[pool_address]
        
        if token == pool.token_a:
            return pool.reserve_b / pool.reserve_a
        elif token == pool.token_b:
            return pool.reserve_a / pool.reserve_b
        
        return Decimal("0")

class OrderBook:
    def __init__(self):
        self.buy_orders = PriorityQueue()
        self.sell_orders = PriorityQueue()
        self.orders = {}
        self.trades = []
        
    def place_order(self, order: Order) -> str:
        order_id = secrets.token_hex(16)
        order.order_id = order_id
        self.orders[order_id] = order
        
        if order.order_type == "buy":
            self.buy_orders.put((-float(order.price), order_id))
        else:
            self.sell_orders.put((float(order.price), order_id))
        
        self.match_orders()
        return order_id
    
    def match_orders(self):
        while not self.buy_orders.empty() and not self.sell_orders.empty():
            buy_price, buy_id = self.buy_orders.queue[0]
            sell_price, sell_id = self.sell_orders.queue[0]
            
            buy_order = self.orders.get(buy_id)
            sell_order = self.orders.get(sell_id)
            
            if not buy_order or not sell_order:
                if not buy_order:
                    self.buy_orders.get()
                if not sell_order:
                    self.sell_orders.get()
                continue
            
            if -buy_price >= sell_price:
                trade_amount = min(
                    buy_order.amount_in - buy_order.filled_amount,
                    sell_order.amount_in - sell_order.filled_amount
                )
                
                trade_price = (Decimal(str(-buy_price)) + Decimal(str(sell_price))) / 2
                
                buy_order.filled_amount += trade_amount
                sell_order.filled_amount += trade_amount
                
                self.trades.append({
                    'buy_order': buy_id,
                    'sell_order': sell_id,
                    'amount': trade_amount,
                    'price': trade_price,
                    'timestamp': time.time()
                })
                
                if buy_order.filled_amount >= buy_order.amount_in:
                    buy_order.status = "filled"
                    self.buy_orders.get()
                
                if sell_order.filled_amount >= sell_order.amount_in:
                    sell_order.status = "filled"
                    self.sell_orders.get()
            else:
                break
    
    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            order = self.orders[order_id]
            order.status = "cancelled"
            return True
        return False
    
    def get_order_book(self) -> Dict:
        buys = []
        sells = []
        
        for _, order_id in list(self.buy_orders.queue)[:10]:
            order = self.orders.get(order_id)
            if order and order.status == "pending":
                buys.append({
                    'price': float(order.price),
                    'amount': float(order.amount_in - order.filled_amount)
                })
        
        for _, order_id in list(self.sell_orders.queue)[:10]:
            order = self.orders.get(order_id)
            if order and order.status == "pending":
                sells.append({
                    'price': float(order.price),
                    'amount': float(order.amount_in - order.filled_amount)
                })
        
        return {'buys': buys, 'sells': sells}

class LendingProtocol:
    def __init__(self):
        self.markets = {}
        self.deposits = defaultdict(lambda: defaultdict(Decimal))
        self.borrows = defaultdict(lambda: defaultdict(Decimal))
        self.interest_rates = {}
        self.collateral_factors = {}
        self.liquidation_threshold = Decimal("0.8")
        
    def create_market(self, token: str, base_rate: Decimal = Decimal("0.02"),
                     collateral_factor: Decimal = Decimal("0.75")):
        self.markets[token] = {
            'total_deposits': Decimal("0"),
            'total_borrows': Decimal("0"),
            'base_rate': base_rate,
            'utilization': Decimal("0")
        }
        self.collateral_factors[token] = collateral_factor
        self.interest_rates[token] = base_rate
    
    def deposit(self, user: str, token: str, amount: Decimal) -> bool:
        if token not in self.markets:
            return False
        
        self.deposits[user][token] += amount
        self.markets[token]['total_deposits'] += amount
        self.update_interest_rate(token)
        
        return True
    
    def withdraw(self, user: str, token: str, amount: Decimal) -> bool:
        if self.deposits[user][token] < amount:
            return False
        
        if not self.check_health_factor(user):
            return False
        
        self.deposits[user][token] -= amount
        self.markets[token]['total_deposits'] -= amount
        self.update_interest_rate(token)
        
        return True
    
    def borrow(self, user: str, token: str, amount: Decimal) -> bool:
        if token not in self.markets:
            return False
        
        available_liquidity = (self.markets[token]['total_deposits'] - 
                              self.markets[token]['total_borrows'])
        
        if amount > available_liquidity:
            return False
        
        max_borrow = self.calculate_max_borrow(user)
        current_borrow_value = self.get_total_borrow_value(user)
        
        if current_borrow_value + amount > max_borrow:
            return False
        
        self.borrows[user][token] += amount
        self.markets[token]['total_borrows'] += amount
        self.update_interest_rate(token)
        
        return True
    
    def repay(self, user: str, token: str, amount: Decimal) -> bool:
        if self.borrows[user][token] < amount:
            amount = self.borrows[user][token]
        
        self.borrows[user][token] -= amount
        self.markets[token]['total_borrows'] -= amount
        self.update_interest_rate(token)
        
        return True
    
    def update_interest_rate(self, token: str):
        market = self.markets[token]
        
        if market['total_deposits'] > 0:
            utilization = market['total_borrows'] / market['total_deposits']
        else:
            utilization = Decimal("0")
        
        market['utilization'] = utilization
        
        if utilization < Decimal("0.8"):
            rate = market['base_rate'] * (Decimal("1") + utilization * 2)
        else:
            rate = market['base_rate'] * (Decimal("1") + utilization * 10)
        
        self.interest_rates[token] = rate
    
    def calculate_max_borrow(self, user: str) -> Decimal:
        total_collateral = Decimal("0")
        
        for token, amount in self.deposits[user].items():
            if token in self.collateral_factors:
                value = amount
                total_collateral += value * self.collateral_factors[token]
        
        return total_collateral
    
    def get_total_borrow_value(self, user: str) -> Decimal:
        total = Decimal("0")
        for token, amount in self.borrows[user].items():
            total += amount
        return total
    
    def check_health_factor(self, user: str) -> bool:
        max_borrow = self.calculate_max_borrow(user)
        current_borrow = self.get_total_borrow_value(user)
        
        if current_borrow == 0:
            return True
        
        health_factor = max_borrow / current_borrow
        return health_factor > self.liquidation_threshold
    
    def liquidate(self, liquidator: str, user: str, token: str, 
                 amount: Decimal) -> Tuple[bool, Decimal]:
        if self.check_health_factor(user):
            return False, Decimal("0")
        
        max_liquidation = self.borrows[user][token] * Decimal("0.5")
        liquidation_amount = min(amount, max_liquidation)
        
        self.borrows[user][token] -= liquidation_amount
        self.markets[token]['total_borrows'] -= liquidation_amount
        
        bonus = liquidation_amount * Decimal("0.05")
        collateral_seized = liquidation_amount + bonus
        
        for collateral_token, collateral_amount in self.deposits[user].items():
            if collateral_amount >= collateral_seized:
                self.deposits[user][collateral_token] -= collateral_seized
                self.deposits[liquidator][collateral_token] += collateral_seized
                break
        
        return True, collateral_seized

class YieldFarming:
    def __init__(self):
        self.farms = {}
        self.stakes = defaultdict(lambda: defaultdict(dict))
        self.rewards = defaultdict(lambda: defaultdict(Decimal))
        self.reward_rate = Decimal("0.0001")
        
    def create_farm(self, farm_id: str, staking_token: str, reward_token: str,
                   reward_per_block: Decimal = Decimal("1")):
        self.farms[farm_id] = {
            'staking_token': staking_token,
            'reward_token': reward_token,
            'reward_per_block': reward_per_block,
            'total_staked': Decimal("0"),
            'last_update_block': 0,
            'acc_reward_per_share': Decimal("0")
        }
    
    def stake(self, user: str, farm_id: str, amount: Decimal) -> bool:
        if farm_id not in self.farms:
            return False
        
        farm = self.farms[farm_id]
        self.update_farm(farm_id)
        
        if user in self.stakes[farm_id]:
            pending = self.calculate_pending_rewards(user, farm_id)
            self.rewards[user][farm['reward_token']] += pending
        
        if user not in self.stakes[farm_id]:
            self.stakes[farm_id][user] = {
                'amount': Decimal("0"),
                'reward_debt': Decimal("0")
            }
        
        self.stakes[farm_id][user]['amount'] += amount
        self.stakes[farm_id][user]['reward_debt'] = (
            self.stakes[farm_id][user]['amount'] * farm['acc_reward_per_share']
        )
        
        farm['total_staked'] += amount
        return True
    
    def unstake(self, user: str, farm_id: str, amount: Decimal) -> bool:
        if farm_id not in self.farms or user not in self.stakes[farm_id]:
            return False
        
        stake = self.stakes[farm_id][user]
        if stake['amount'] < amount:
            return False
        
        self.update_farm(farm_id)
        
        pending = self.calculate_pending_rewards(user, farm_id)
        self.rewards[user][self.farms[farm_id]['reward_token']] += pending
        
        stake['amount'] -= amount
        stake['reward_debt'] = stake['amount'] * self.farms[farm_id]['acc_reward_per_share']
        
        self.farms[farm_id]['total_staked'] -= amount
        return True
    
    def update_farm(self, farm_id: str):
        farm = self.farms[farm_id]
        current_block = int(time.time() / 10)
        
        if current_block <= farm['last_update_block']:
            return
        
        if farm['total_staked'] == 0:
            farm['last_update_block'] = current_block
            return
        
        blocks_elapsed = current_block - farm['last_update_block']
        reward = farm['reward_per_block'] * blocks_elapsed
        
        farm['acc_reward_per_share'] += reward / farm['total_staked']
        farm['last_update_block'] = current_block
    
    def calculate_pending_rewards(self, user: str, farm_id: str) -> Decimal:
        if farm_id not in self.farms or user not in self.stakes[farm_id]:
            return Decimal("0")
        
        farm = self.farms[farm_id]
        stake = self.stakes[farm_id][user]
        
        acc_reward = farm['acc_reward_per_share']
        
        if farm['total_staked'] > 0:
            current_block = int(time.time() / 10)
            blocks_elapsed = current_block - farm['last_update_block']
            reward = farm['reward_per_block'] * blocks_elapsed
            acc_reward += reward / farm['total_staked']
        
        return stake['amount'] * acc_reward - stake['reward_debt']
    
    def claim_rewards(self, user: str, farm_id: str) -> Decimal:
        if farm_id not in self.farms or user not in self.stakes[farm_id]:
            return Decimal("0")
        
        self.update_farm(farm_id)
        
        pending = self.calculate_pending_rewards(user, farm_id)
        
        if pending > 0:
            self.rewards[user][self.farms[farm_id]['reward_token']] += pending
            stake = self.stakes[farm_id][user]
            stake['reward_debt'] = stake['amount'] * self.farms[farm_id]['acc_reward_per_share']
        
        return pending

class DeFiProtocol:
    def __init__(self):
        self.amm = AMM()
        self.order_book = OrderBook()
        self.lending = LendingProtocol()
        self.farming = YieldFarming()
        self.tokens = {}
        self.balances = defaultdict(lambda: defaultdict(Decimal))
        self.db = self.init_database()
        
    def init_database(self) -> sqlite3.Connection:
        conn = sqlite3.connect(':memory:', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE tokens (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                total_supply REAL,
                decimals INTEGER,
                address TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE balances (
                user TEXT,
                token TEXT,
                balance REAL,
                PRIMARY KEY (user, token)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE pools (
                address TEXT PRIMARY KEY,
                token_a TEXT,
                token_b TEXT,
                reserve_a REAL,
                reserve_b REAL,
                lp_supply REAL
            )
        ''')
        
        conn.commit()
        return conn
    
    def create_token(self, symbol: str, name: str, total_supply: Decimal) -> str:
        address = "TK" + hashlib.sha256(f"{symbol}{time.time()}".encode()).hexdigest()[:40]
        
        token = Token(
            symbol=symbol,
            name=name,
            total_supply=total_supply,
            address=address
        )
        
        self.tokens[symbol] = token
        self.save_token(token)
        
        return address
    
    def mint_tokens(self, user: str, token: str, amount: Decimal):
        if token not in self.tokens:
            return False
        
        self.balances[user][token] += amount
        self.tokens[token].minted += amount
        return True
    
    def transfer(self, sender: str, recipient: str, token: str, amount: Decimal) -> bool:
        if self.balances[sender][token] < amount:
            return False
        
        self.balances[sender][token] -= amount
        self.balances[recipient][token] += amount
        return True
    
    def save_token(self, token: Token):
        cursor = self.db.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO tokens (symbol, name, total_supply, decimals, address)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            token.symbol,
            token.name,
            float(token.total_supply),
            token.decimals,
            token.address
        ))
        self.db.commit()
    
    def get_portfolio_value(self, user: str) -> Decimal:
        total_value = Decimal("0")
        
        for token, balance in self.balances[user].items():
            total_value += balance
        
        for farm_id, stakes in self.farming.stakes.items():
            if user in stakes:
                total_value += stakes[user]['amount']
        
        for token, amount in self.lending.deposits[user].items():
            total_value += amount
        
        return total_value

def main():
    print("QENEX DeFi Protocols")
    print("=" * 50)
    
    defi = DeFiProtocol()
    
    print("\n1. Creating tokens...")
    qxc = defi.create_token("QXC", "QENEX Coin", Decimal("1000000000"))
    usdt = defi.create_token("USDT", "Tether", Decimal("1000000000"))
    print(f"  QXC Token: {qxc}")
    print(f"  USDT Token: {usdt}")
    
    print("\n2. Minting tokens to users...")
    defi.mint_tokens("Alice", "QXC", Decimal("10000"))
    defi.mint_tokens("Alice", "USDT", Decimal("10000"))
    defi.mint_tokens("Bob", "QXC", Decimal("5000"))
    defi.mint_tokens("Bob", "USDT", Decimal("5000"))
    print("  Alice: 10,000 QXC, 10,000 USDT")
    print("  Bob: 5,000 QXC, 5,000 USDT")
    
    print("\n3. Creating AMM liquidity pool...")
    pool_address = defi.amm.create_pool("QXC", "USDT", Decimal("1000"), Decimal("1000"))
    print(f"  Pool created: {pool_address[:16]}...")
    print(f"  Initial reserves: 1000 QXC / 1000 USDT")
    
    print("\n4. Performing swap...")
    amount_out = defi.amm.swap(pool_address, "QXC", Decimal("100"))
    print(f"  Swapped 100 QXC for {amount_out:.2f} USDT")
    
    print("\n5. Adding liquidity...")
    lp_tokens = defi.amm.add_liquidity(pool_address, Decimal("500"), Decimal("500"))
    print(f"  Added liquidity, received {lp_tokens:.2f} LP tokens")
    
    print("\n6. Creating lending market...")
    defi.lending.create_market("QXC", Decimal("0.05"))
    defi.lending.create_market("USDT", Decimal("0.03"))
    print("  QXC Market: 5% base rate")
    print("  USDT Market: 3% base rate")
    
    print("\n7. Deposit and borrow...")
    defi.lending.deposit("Alice", "QXC", Decimal("1000"))
    defi.lending.borrow("Alice", "USDT", Decimal("500"))
    print("  Alice deposited 1000 QXC")
    print("  Alice borrowed 500 USDT")
    
    print("\n8. Creating yield farm...")
    defi.farming.create_farm("FARM1", "LP-QXC-USDT", "QXC", Decimal("10"))
    print("  Farm created: Stake LP tokens, earn QXC")
    print("  Reward rate: 10 QXC per block")
    
    print("\n9. Staking in farm...")
    defi.farming.stake("Bob", "FARM1", Decimal("100"))
    print("  Bob staked 100 LP tokens")
    
    time.sleep(1)
    
    rewards = defi.farming.calculate_pending_rewards("Bob", "FARM1")
    print(f"  Pending rewards: {rewards:.4f} QXC")
    
    print("\n10. Portfolio summary:")
    alice_portfolio = defi.get_portfolio_value("Alice")
    bob_portfolio = defi.get_portfolio_value("Bob")
    print(f"  Alice portfolio value: {alice_portfolio:.2f}")
    print(f"  Bob portfolio value: {bob_portfolio:.2f}")
    
    print("\n11. Protocol statistics:")
    pool = defi.amm.pools[pool_address]
    print(f"  AMM TVL: {(pool.reserve_a + pool.reserve_b):.2f}")
    print(f"  Lending TVL: {sum(m['total_deposits'] for m in defi.lending.markets.values()):.2f}")
    print(f"  Farming TVL: {sum(f['total_staked'] for f in defi.farming.farms.values()):.2f}")
    
    print("\n✅ DeFi protocols operational")

if __name__ == "__main__":
    main()