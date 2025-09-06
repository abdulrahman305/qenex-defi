#!/usr/bin/env python3
"""
DeFi Core System
"""

import json
import time
import hashlib
import secrets
from decimal import Decimal, getcontext
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from contextlib import contextmanager

# Set decimal precision
getcontext().prec = 28

# Configuration
CONFIG = {
    'db_path': Path('data/defi.db'),
    'min_liquidity': Decimal('0.01'),
    'max_slippage': Decimal('0.05'),
    'fee_rate': Decimal('0.003'),
}

CONFIG['db_path'].parent.mkdir(parents=True, exist_ok=True)


@dataclass
class Token:
    """Token representation"""
    symbol: str
    name: str
    decimals: int
    total_supply: Decimal
    
    def format_amount(self, amount: Decimal) -> str:
        """Format token amount for display"""
        return f"{amount:.{self.decimals}f} {self.symbol}"


@dataclass
class Pool:
    """Liquidity pool"""
    token_a: str
    token_b: str
    reserve_a: Decimal
    reserve_b: Decimal
    lp_supply: Decimal
    fee_rate: Decimal
    
    def get_price(self, token: str) -> Optional[Decimal]:
        """Get price of token in pool"""
        if token == self.token_a:
            return self.reserve_b / self.reserve_a if self.reserve_a > 0 else None
        elif token == self.token_b:
            return self.reserve_a / self.reserve_b if self.reserve_b > 0 else None
        return None
    
    def calculate_swap(self, token_in: str, amount_in: Decimal) -> Optional[Decimal]:
        """Calculate swap output amount"""
        if amount_in <= 0:
            return None
        
        if token_in == self.token_a:
            reserve_in, reserve_out = self.reserve_a, self.reserve_b
        elif token_in == self.token_b:
            reserve_in, reserve_out = self.reserve_b, self.reserve_a
        else:
            return None
        
        # Apply fee
        amount_with_fee = amount_in * (Decimal('1') - self.fee_rate)
        
        # Calculate output (x * y = k formula)
        numerator = amount_with_fee * reserve_out
        denominator = reserve_in + amount_with_fee
        
        return numerator / denominator if denominator > 0 else None


class Database:
    """DeFi database handler"""
    
    def __init__(self, db_path: Path = CONFIG['db_path']):
        self.db_path = db_path
        self.init_schema()
    
    def init_schema(self):
        """Initialize database schema"""
        with self.connection() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS tokens (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    decimals INTEGER NOT NULL,
                    total_supply TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS balances (
                    address TEXT NOT NULL,
                    token TEXT NOT NULL,
                    balance TEXT NOT NULL,
                    PRIMARY KEY (address, token),
                    FOREIGN KEY (token) REFERENCES tokens(symbol)
                );
                
                CREATE TABLE IF NOT EXISTS pools (
                    id INTEGER PRIMARY KEY,
                    token_a TEXT NOT NULL,
                    token_b TEXT NOT NULL,
                    reserve_a TEXT NOT NULL,
                    reserve_b TEXT NOT NULL,
                    lp_supply TEXT NOT NULL,
                    fee_rate TEXT NOT NULL,
                    UNIQUE(token_a, token_b),
                    FOREIGN KEY (token_a) REFERENCES tokens(symbol),
                    FOREIGN KEY (token_b) REFERENCES tokens(symbol)
                );
                
                CREATE TABLE IF NOT EXISTS liquidity (
                    address TEXT NOT NULL,
                    pool_id INTEGER NOT NULL,
                    lp_tokens TEXT NOT NULL,
                    PRIMARY KEY (address, pool_id),
                    FOREIGN KEY (pool_id) REFERENCES pools(id)
                );
                
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    type TEXT NOT NULL,
                    address TEXT NOT NULL,
                    details TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_balances_address ON balances(address);
                CREATE INDEX IF NOT EXISTS idx_transactions_address ON transactions(address);
            ''')
    
    @contextmanager
    def connection(self):
        """Database connection context manager"""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level='DEFERRED'
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class DeFi:
    """DeFi system implementation"""
    
    def __init__(self):
        self.db = Database()
        self.tokens = {}
        self.pools = {}
        self._load_data()
    
    def _load_data(self):
        """Load tokens and pools from database"""
        with self.db.connection() as conn:
            # Load tokens
            cursor = conn.execute('SELECT * FROM tokens')
            for row in cursor:
                token = Token(
                    symbol=row['symbol'],
                    name=row['name'],
                    decimals=row['decimals'],
                    total_supply=Decimal(row['total_supply'])
                )
                self.tokens[token.symbol] = token
            
            # Load pools
            cursor = conn.execute('SELECT * FROM pools')
            for row in cursor:
                pool = Pool(
                    token_a=row['token_a'],
                    token_b=row['token_b'],
                    reserve_a=Decimal(row['reserve_a']),
                    reserve_b=Decimal(row['reserve_b']),
                    lp_supply=Decimal(row['lp_supply']),
                    fee_rate=Decimal(row['fee_rate'])
                )
                pool_key = self._get_pool_key(pool.token_a, pool.token_b)
                self.pools[pool_key] = pool
    
    def _get_pool_key(self, token_a: str, token_b: str) -> str:
        """Get canonical pool key"""
        return f"{min(token_a, token_b)}-{max(token_a, token_b)}"
    
    def create_token(self, symbol: str, name: str, decimals: int = 18, 
                    total_supply: Decimal = Decimal('1000000')) -> bool:
        """Create new token"""
        if symbol in self.tokens:
            return False
        
        token = Token(symbol, name, decimals, total_supply)
        
        with self.db.connection() as conn:
            conn.execute(
                'INSERT INTO tokens VALUES (?, ?, ?, ?)',
                (symbol, name, decimals, str(total_supply))
            )
            
            # Creator gets initial supply
            conn.execute(
                'INSERT INTO balances VALUES (?, ?, ?)',
                ('creator', symbol, str(total_supply))
            )
        
        self.tokens[symbol] = token
        return True
    
    def get_balance(self, address: str, token: str) -> Decimal:
        """Get token balance for address"""
        with self.db.connection() as conn:
            cursor = conn.execute(
                'SELECT balance FROM balances WHERE address = ? AND token = ?',
                (address, token)
            )
            row = cursor.fetchone()
            return Decimal(row['balance']) if row else Decimal('0')
    
    def transfer(self, from_addr: str, to_addr: str, token: str, amount: Decimal) -> bool:
        """Transfer tokens between addresses"""
        if amount <= 0:
            return False
        
        with self.db.connection() as conn:
            # Check balance
            from_balance = self.get_balance(from_addr, token)
            if from_balance < amount:
                return False
            
            # Update balances
            new_from_balance = from_balance - amount
            to_balance = self.get_balance(to_addr, token)
            new_to_balance = to_balance + amount
            
            # Update from balance
            if new_from_balance > 0:
                conn.execute(
                    'UPDATE balances SET balance = ? WHERE address = ? AND token = ?',
                    (str(new_from_balance), from_addr, token)
                )
            else:
                conn.execute(
                    'DELETE FROM balances WHERE address = ? AND token = ?',
                    (from_addr, token)
                )
            
            # Update to balance
            conn.execute(
                'INSERT OR REPLACE INTO balances VALUES (?, ?, ?)',
                (to_addr, token, str(new_to_balance))
            )
            
            # Log transaction
            conn.execute(
                'INSERT INTO transactions (type, address, details) VALUES (?, ?, ?)',
                ('transfer', from_addr, json.dumps({
                    'to': to_addr,
                    'token': token,
                    'amount': str(amount)
                }))
            )
        
        return True
    
    def create_pool(self, token_a: str, token_b: str, 
                   amount_a: Decimal, amount_b: Decimal) -> Optional[int]:
        """Create liquidity pool"""
        if token_a not in self.tokens or token_b not in self.tokens:
            return None
        
        if amount_a < CONFIG['min_liquidity'] or amount_b < CONFIG['min_liquidity']:
            return None
        
        pool_key = self._get_pool_key(token_a, token_b)
        if pool_key in self.pools:
            return None
        
        # Calculate initial LP tokens (geometric mean)
        lp_supply = (amount_a * amount_b) ** Decimal('0.5')
        
        pool = Pool(
            token_a=token_a,
            token_b=token_b,
            reserve_a=amount_a,
            reserve_b=amount_b,
            lp_supply=lp_supply,
            fee_rate=CONFIG['fee_rate']
        )
        
        with self.db.connection() as conn:
            cursor = conn.execute(
                '''INSERT INTO pools (token_a, token_b, reserve_a, reserve_b, lp_supply, fee_rate)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (token_a, token_b, str(amount_a), str(amount_b), str(lp_supply), str(CONFIG['fee_rate']))
            )
            pool_id = cursor.lastrowid
            
            # Give LP tokens to creator
            conn.execute(
                'INSERT INTO liquidity VALUES (?, ?, ?)',
                ('creator', pool_id, str(lp_supply))
            )
        
        self.pools[pool_key] = pool
        return pool_id
    
    def swap(self, address: str, token_in: str, token_out: str, amount_in: Decimal) -> Optional[Decimal]:
        """Swap tokens"""
        pool_key = self._get_pool_key(token_in, token_out)
        pool = self.pools.get(pool_key)
        
        if not pool:
            return None
        
        # Check balance
        balance = self.get_balance(address, token_in)
        if balance < amount_in:
            return None
        
        # Calculate output
        amount_out = pool.calculate_swap(token_in, amount_in)
        if not amount_out:
            return None
        
        # Check slippage
        expected_price = pool.get_price(token_in)
        if expected_price:
            actual_price = amount_out / amount_in
            slippage = abs(actual_price - expected_price) / expected_price
            if slippage > CONFIG['max_slippage']:
                return None
        
        # Execute swap
        with self.db.connection() as conn:
            # Update user balances
            self.transfer(address, 'pool', token_in, amount_in)
            self.transfer('pool', address, token_out, amount_out)
            
            # Update pool reserves
            if token_in == pool.token_a:
                pool.reserve_a += amount_in
                pool.reserve_b -= amount_out
            else:
                pool.reserve_b += amount_in
                pool.reserve_a -= amount_out
            
            conn.execute(
                'UPDATE pools SET reserve_a = ?, reserve_b = ? WHERE token_a = ? AND token_b = ?',
                (str(pool.reserve_a), str(pool.reserve_b), pool.token_a, pool.token_b)
            )
            
            # Log transaction
            conn.execute(
                'INSERT INTO transactions (type, address, details) VALUES (?, ?, ?)',
                ('swap', address, json.dumps({
                    'token_in': token_in,
                    'token_out': token_out,
                    'amount_in': str(amount_in),
                    'amount_out': str(amount_out)
                }))
            )
        
        return amount_out
    
    def add_liquidity(self, address: str, token_a: str, token_b: str,
                     amount_a: Decimal, amount_b: Decimal) -> Optional[Decimal]:
        """Add liquidity to pool"""
        pool_key = self._get_pool_key(token_a, token_b)
        pool = self.pools.get(pool_key)
        
        if not pool:
            return None
        
        # Check optimal ratio
        if pool.reserve_a > 0 and pool.reserve_b > 0:
            optimal_b = (amount_a * pool.reserve_b) / pool.reserve_a
            if abs(optimal_b - amount_b) / optimal_b > Decimal('0.01'):  # 1% tolerance
                return None
        
        # Check balances
        if self.get_balance(address, token_a) < amount_a:
            return None
        if self.get_balance(address, token_b) < amount_b:
            return None
        
        # Calculate LP tokens
        if pool.lp_supply == 0:
            lp_tokens = (amount_a * amount_b) ** Decimal('0.5')
        else:
            lp_tokens = min(
                (amount_a * pool.lp_supply) / pool.reserve_a,
                (amount_b * pool.lp_supply) / pool.reserve_b
            )
        
        # Execute
        with self.db.connection() as conn:
            # Transfer tokens to pool
            self.transfer(address, 'pool', token_a, amount_a)
            self.transfer(address, 'pool', token_b, amount_b)
            
            # Update pool
            pool.reserve_a += amount_a
            pool.reserve_b += amount_b
            pool.lp_supply += lp_tokens
            
            conn.execute(
                'UPDATE pools SET reserve_a = ?, reserve_b = ?, lp_supply = ? WHERE token_a = ? AND token_b = ?',
                (str(pool.reserve_a), str(pool.reserve_b), str(pool.lp_supply), pool.token_a, pool.token_b)
            )
            
            # Give LP tokens
            cursor = conn.execute(
                'SELECT pool_id FROM pools WHERE token_a = ? AND token_b = ?',
                (pool.token_a, pool.token_b)
            )
            pool_id = cursor.fetchone()['pool_id']
            
            current_lp = Decimal('0')
            cursor = conn.execute(
                'SELECT lp_tokens FROM liquidity WHERE address = ? AND pool_id = ?',
                (address, pool_id)
            )
            row = cursor.fetchone()
            if row:
                current_lp = Decimal(row['lp_tokens'])
            
            conn.execute(
                'INSERT OR REPLACE INTO liquidity VALUES (?, ?, ?)',
                (address, pool_id, str(current_lp + lp_tokens))
            )
        
        return lp_tokens
    
    def get_stats(self) -> Dict:
        """Get DeFi statistics"""
        stats = {
            'tokens': len(self.tokens),
            'pools': len(self.pools),
            'total_liquidity': Decimal('0'),
            'total_volume': Decimal('0')
        }
        
        with self.db.connection() as conn:
            # Calculate total liquidity (in USD equivalent)
            for pool in self.pools.values():
                # Assume token_b is stable coin worth $1
                liquidity_value = pool.reserve_b * 2
                stats['total_liquidity'] += liquidity_value
            
            # Calculate 24h volume
            cursor = conn.execute(
                '''SELECT COUNT(*) as count, SUM(
                    CAST(json_extract(details, '$.amount_in') AS REAL)
                ) as volume
                FROM transactions 
                WHERE type = 'swap' 
                AND timestamp > datetime('now', '-1 day')'''
            )
            row = cursor.fetchone()
            if row and row['volume']:
                stats['total_volume'] = Decimal(str(row['volume']))
            
            # Get unique users
            cursor = conn.execute('SELECT COUNT(DISTINCT address) as users FROM balances')
            stats['total_users'] = cursor.fetchone()['users']
        
        return stats


def main():
    """Main entry point"""
    defi = DeFi()
    
    # Create tokens
    defi.create_token('USDC', 'USD Coin', 6, Decimal('1000000'))
    defi.create_token('ETH', 'Ethereum', 18, Decimal('1000'))
    defi.create_token('QXC', 'QENEX Token', 18, Decimal('1000000'))
    
    # Create pools
    pool_id = defi.create_pool('ETH', 'USDC', Decimal('10'), Decimal('20000'))
    if pool_id:
        print(f'Created ETH/USDC pool: {pool_id}')
    
    pool_id = defi.create_pool('QXC', 'USDC', Decimal('10000'), Decimal('1000'))
    if pool_id:
        print(f'Created QXC/USDC pool: {pool_id}')
    
    # Get stats
    stats = defi.get_stats()
    print(f'\nDeFi Stats:')
    print(f'  Tokens: {stats["tokens"]}')
    print(f'  Pools: {stats["pools"]}')
    print(f'  Total Liquidity: ${stats["total_liquidity"]:,.2f}')
    print(f'  24h Volume: ${stats["total_volume"]:,.2f}')
    print(f'  Total Users: {stats["total_users"]}')


if __name__ == '__main__':
    main()