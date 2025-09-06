#!/usr/bin/env python3
"""
Minimalist Financial Core
Single-file complete financial system
"""

import asyncio
import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from typing import Dict, List, Optional, Tuple
import logging

# Configure precision
getcontext().prec = 38

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Minimalist Architecture - Everything in One
# ============================================================================

class FinancialCore:
    """Complete financial system in minimal code"""
    
    def __init__(self, db_path: str = "financial.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
        
    def init_database(self):
        """Initialize database with all required tables"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        
        # Accounts table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                balance TEXT NOT NULL,
                currency TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL
            )
        """)
        
        # Transactions table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                destination TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (source) REFERENCES accounts(id),
                FOREIGN KEY (destination) REFERENCES accounts(id)
            )
        """)
        
        # Audit log
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                data TEXT
            )
        """)
        
        self.conn.commit()
    
    def create_account(self, account_id: str, initial_balance: Decimal = Decimal('0'), 
                      currency: str = 'USD') -> bool:
        """Create new account"""
        try:
            self.conn.execute("""
                INSERT INTO accounts (id, balance, currency, created_at)
                VALUES (?, ?, ?, ?)
            """, (account_id, str(initial_balance), currency, 
                  datetime.now(timezone.utc).isoformat()))
            
            self.conn.commit()
            self._audit('account_created', account_id, {'balance': str(initial_balance)})
            return True
        except sqlite3.IntegrityError:
            logger.error(f"Account {account_id} already exists")
            return False
    
    def transfer(self, source: str, destination: str, amount: Decimal, 
                currency: str = 'USD') -> Optional[str]:
        """Transfer funds between accounts"""
        tx_id = f"TX-{int(time.time() * 1000)}-{hashlib.md5(f'{source}{destination}{amount}'.encode()).hexdigest()[:8]}"
        
        try:
            # Start transaction
            cursor = self.conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            
            # Check source balance
            cursor.execute("SELECT balance FROM accounts WHERE id = ? AND currency = ?", 
                          (source, currency))
            row = cursor.fetchone()
            
            if not row:
                cursor.execute("ROLLBACK")
                return None
            
            source_balance = Decimal(row[0])
            
            if source_balance < amount:
                cursor.execute("ROLLBACK")
                logger.error(f"Insufficient funds: {source} has {source_balance}, needs {amount}")
                return None
            
            # Check destination exists
            cursor.execute("SELECT id FROM accounts WHERE id = ? AND currency = ?", 
                          (destination, currency))
            if not cursor.fetchone():
                cursor.execute("ROLLBACK")
                logger.error(f"Destination account {destination} not found")
                return None
            
            # Update balances
            cursor.execute("""
                UPDATE accounts 
                SET balance = CAST(CAST(balance AS REAL) - ? AS TEXT)
                WHERE id = ? AND currency = ?
            """, (str(amount), source, currency))
            
            cursor.execute("""
                UPDATE accounts 
                SET balance = CAST(CAST(balance AS REAL) + ? AS TEXT)
                WHERE id = ? AND currency = ?
            """, (str(amount), destination, currency))
            
            # Record transaction
            cursor.execute("""
                INSERT INTO transactions (id, source, destination, amount, currency, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (tx_id, source, destination, str(amount), currency, 'completed',
                  datetime.now(timezone.utc).isoformat()))
            
            cursor.execute("COMMIT")
            
            self._audit('transfer_completed', tx_id, {
                'source': source,
                'destination': destination,
                'amount': str(amount)
            })
            
            return tx_id
            
        except Exception as e:
            self.conn.execute("ROLLBACK")
            logger.error(f"Transfer failed: {e}")
            return None
    
    def get_balance(self, account_id: str, currency: str = 'USD') -> Optional[Decimal]:
        """Get account balance"""
        cursor = self.conn.execute(
            "SELECT balance FROM accounts WHERE id = ? AND currency = ?",
            (account_id, currency)
        )
        row = cursor.fetchone()
        return Decimal(row[0]) if row else None
    
    def get_transactions(self, account_id: str, limit: int = 100) -> List[Dict]:
        """Get account transactions"""
        cursor = self.conn.execute("""
            SELECT id, source, destination, amount, currency, status, timestamp
            FROM transactions
            WHERE source = ? OR destination = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (account_id, account_id, limit))
        
        return [
            {
                'id': row[0],
                'source': row[1],
                'destination': row[2],
                'amount': row[3],
                'currency': row[4],
                'status': row[5],
                'timestamp': row[6]
            }
            for row in cursor.fetchall()
        ]
    
    def _audit(self, event: str, entity_id: str, data: Dict = None):
        """Log audit event"""
        self.conn.execute("""
            INSERT INTO audit_log (event, entity_id, timestamp, data)
            VALUES (?, ?, ?, ?)
        """, (event, entity_id, datetime.now(timezone.utc).isoformat(),
              json.dumps(data) if data else None))
        self.conn.commit()
    
    def check_compliance(self, amount: Decimal, currency: str) -> Tuple[bool, List[str]]:
        """Simple compliance check"""
        issues = []
        
        # AML threshold check
        if currency == 'USD' and amount > 10000:
            issues.append("AML: Large transaction requires reporting")
        elif currency == 'EUR' and amount > 12500:
            issues.append("EU AML: Large transaction requires reporting")
        
        # Sanctions check (simplified)
        # In production, would check against actual sanctions lists
        
        return len(issues) == 0, issues
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

# ============================================================================
# Async Wrapper for High Performance
# ============================================================================

class AsyncFinancialSystem:
    """Async wrapper for the financial core"""
    
    def __init__(self):
        self.core = FinancialCore()
        self.processing_queue = asyncio.Queue()
        self.results = {}
        
    async def process_transaction(self, source: str, destination: str, 
                                 amount: Decimal, currency: str = 'USD') -> Dict:
        """Process transaction asynchronously"""
        # Compliance check
        compliant, issues = self.core.check_compliance(amount, currency)
        
        if not compliant:
            return {
                'success': False,
                'tx_id': None,
                'issues': issues
            }
        
        # Execute transfer
        tx_id = await asyncio.get_event_loop().run_in_executor(
            None, self.core.transfer, source, destination, amount, currency
        )
        
        return {
            'success': tx_id is not None,
            'tx_id': tx_id,
            'issues': [] if tx_id else ['Transfer failed']
        }
    
    async def batch_process(self, transactions: List[Dict]) -> List[Dict]:
        """Process multiple transactions"""
        tasks = []
        
        for tx in transactions:
            task = self.process_transaction(
                tx['source'],
                tx['destination'],
                Decimal(str(tx['amount'])),
                tx.get('currency', 'USD')
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results

# ============================================================================
# REST API Server
# ============================================================================

class SimpleAPIServer:
    """Minimal REST API server"""
    
    def __init__(self, financial_system: AsyncFinancialSystem):
        self.system = financial_system
        
    async def handle_request(self, method: str, path: str, body: Dict) -> Dict:
        """Handle API request"""
        if method == 'POST' and path == '/account':
            # Create account
            success = self.system.core.create_account(
                body['account_id'],
                Decimal(str(body.get('initial_balance', 0))),
                body.get('currency', 'USD')
            )
            return {'success': success}
            
        elif method == 'POST' and path == '/transfer':
            # Process transfer
            result = await self.system.process_transaction(
                body['source'],
                body['destination'],
                Decimal(str(body['amount'])),
                body.get('currency', 'USD')
            )
            return result
            
        elif method == 'GET' and path.startswith('/balance/'):
            # Get balance
            account_id = path.split('/')[-1]
            balance = self.system.core.get_balance(account_id)
            return {
                'account_id': account_id,
                'balance': str(balance) if balance else None
            }
            
        elif method == 'GET' and path.startswith('/transactions/'):
            # Get transactions
            account_id = path.split('/')[-1]
            transactions = self.system.core.get_transactions(account_id)
            return {'transactions': transactions}
            
        else:
            return {'error': 'Not found'}

# ============================================================================
# Complete System Runner
# ============================================================================

async def run_complete_system():
    """Run the complete financial system"""
    # Initialize
    system = AsyncFinancialSystem()
    api = SimpleAPIServer(system)
    
    # Create test accounts
    system.core.create_account('BANK_A', Decimal('1000000'), 'USD')
    system.core.create_account('BANK_B', Decimal('500000'), 'USD')
    system.core.create_account('BANK_C', Decimal('750000'), 'EUR')
    
    logger.info("System initialized with test accounts")
    
    # Process test transactions
    test_txs = [
        {'source': 'BANK_A', 'destination': 'BANK_B', 'amount': '1000'},
        {'source': 'BANK_B', 'destination': 'BANK_A', 'amount': '500'},
        {'source': 'BANK_A', 'destination': 'BANK_B', 'amount': '15000'},  # Triggers AML
    ]
    
    results = await system.batch_process(test_txs)
    
    for i, result in enumerate(results):
        logger.info(f"Transaction {i+1}: {result}")
    
    # Check final balances
    for account in ['BANK_A', 'BANK_B']:
        balance = system.core.get_balance(account)
        logger.info(f"{account} balance: {balance}")
    
    # Test API
    api_result = await api.handle_request('GET', '/balance/BANK_A', {})
    logger.info(f"API balance check: {api_result}")
    
    # Get transaction history
    history = system.core.get_transactions('BANK_A', limit=10)
    logger.info(f"Transaction history: {len(history)} transactions")
    
    # Cleanup
    system.core.close()
    logger.info("System shutdown complete")

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting Minimalist Financial Core")
    asyncio.run(run_complete_system())