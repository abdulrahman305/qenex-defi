#!/usr/bin/env python3
"""
QXC Wallet Access System
Access and manage your QXC tokens
"""

import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
import os

class QXCWalletManager:
    def __init__(self):
        self.db_path = Path('/opt/qenex-os/real_blockchain.db')
        self.wallet_file = Path('/opt/qenex-os/.qxc_wallet.json')
        self.mining_db = Path('/opt/qenex-os/mining_operations.db')
        
    def get_all_wallets(self):
        """Get all wallets from the blockchain database"""
        wallets = []
        
        # Check real blockchain database
        if self.db_path.exists():
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT address, balance, created_at 
                FROM wallets 
                ORDER BY balance DESC
            ''')
            
            for row in cursor.fetchall():
                wallets.append({
                    'address': row[0],
                    'balance': row[1] if row[1] else 0,
                    'created_at': row[2],
                    'source': 'blockchain'
                })
            
            conn.close()
        
        # Check mining operations database
        if self.mining_db.exists():
            conn = sqlite3.connect(str(self.mining_db))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT wallet_address, SUM(amount) as total
                FROM mining_operations
                WHERE status = 'success'
                GROUP BY wallet_address
            ''')
            
            for row in cursor.fetchall():
                if row[0] not in [w['address'] for w in wallets]:
                    wallets.append({
                        'address': row[0],
                        'balance': row[1] if row[1] else 0,
                        'created_at': 'N/A',
                        'source': 'mining'
                    })
            
            conn.close()
        
        return wallets
    
    def get_wallet_balance(self, address):
        """Get balance for a specific wallet"""
        balance = 0
        
        # Check blockchain database
        if self.db_path.exists():
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Calculate from transactions
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(CASE WHEN to_address = ? THEN amount ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN from_address = ? THEN amount ELSE 0 END), 0)
                FROM transactions
            ''', (address, address))
            
            result = cursor.fetchone()
            if result and result[0]:
                balance = result[0]
            
            conn.close()
        
        # Also check mining database
        if self.mining_db.exists():
            conn = sqlite3.connect(str(self.mining_db))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT SUM(amount) FROM mining_operations
                WHERE wallet_address = ? AND status = 'success'
            ''', (address,))
            
            result = cursor.fetchone()
            if result and result[0]:
                balance = max(balance, result[0])  # Use the higher balance
            
            conn.close()
        
        return balance
    
    def get_transaction_history(self, address):
        """Get transaction history for a wallet"""
        transactions = []
        
        if self.db_path.exists():
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tx_hash, from_address, to_address, amount, 
                       timestamp, block_index, category
                FROM transactions
                WHERE from_address = ? OR to_address = ?
                ORDER BY block_index DESC
            ''', (address, address))
            
            for row in cursor.fetchall():
                transactions.append({
                    'tx_hash': row[0],
                    'from': row[1],
                    'to': row[2],
                    'amount': row[3],
                    'timestamp': row[4],
                    'block': row[5],
                    'category': row[6] if row[6] else 'transfer',
                    'type': 'sent' if row[1] == address else 'received'
                })
            
            conn.close()
        
        return transactions
    
    def create_new_wallet(self):
        """Create a new QXC wallet"""
        # Generate wallet credentials
        private_key = hashlib.sha256(os.urandom(32)).hexdigest()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        address = 'qxc' + public_key[:40]
        
        wallet_data = {
            'address': address,
            'private_key': private_key,
            'public_key': public_key,
            'created_at': datetime.now().isoformat(),
            'balance': 0
        }
        
        # Save to wallet file
        self.wallet_file.write_text(json.dumps(wallet_data, indent=2))
        
        # Register in blockchain database
        if self.db_path.exists():
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO wallets (address, balance, public_key, created_at)
                VALUES (?, ?, ?, ?)
            ''', (address, 0, public_key, datetime.now()))
            
            conn.commit()
            conn.close()
        
        return wallet_data
    
    def load_wallet(self):
        """Load existing wallet from file"""
        if self.wallet_file.exists():
            return json.loads(self.wallet_file.read_text())
        return None
    
    def export_wallet(self, address):
        """Export wallet data for backup"""
        wallet_data = {
            'address': address,
            'balance': self.get_wallet_balance(address),
            'transactions': self.get_transaction_history(address),
            'exported_at': datetime.now().isoformat()
        }
        
        export_file = Path(f'/opt/qenex-os/qxc_wallet_export_{address[:10]}.json')
        export_file.write_text(json.dumps(wallet_data, indent=2))
        
        return str(export_file)

def main():
    """Main wallet access interface"""
    manager = QXCWalletManager()
    
    print("=" * 60)
    print("           💎 QXC WALLET ACCESS SYSTEM 💎")
    print("=" * 60)
    
    # Try to load existing wallet
    wallet = manager.load_wallet()
    
    if wallet:
        print(f"\n📱 Wallet Loaded Successfully!")
        print(f"   Address: {wallet['address']}")
        current_balance = manager.get_wallet_balance(wallet['address'])
        print(f"   Balance: {current_balance:.4f} QXC")
    else:
        print("\n⚠️ No wallet found in local storage")
    
    # Show all wallets
    print("\n📊 All QXC Wallets in System:")
    print("-" * 60)
    
    wallets = manager.get_all_wallets()
    
    if wallets:
        for i, w in enumerate(wallets, 1):
            balance = manager.get_wallet_balance(w['address'])
            print(f"{i}. {w['address'][:20]}...")
            print(f"   Balance: {balance:.4f} QXC")
            print(f"   Source: {w['source']}")
            print()
    
    # Show main wallet (from mining operations)
    main_wallet = 'qxc_unified_user_wallet_main'
    main_balance = manager.get_wallet_balance(main_wallet)
    
    print("\n🏆 Main Mining Wallet:")
    print(f"   Address: {main_wallet}")
    print(f"   Balance: {main_balance:.4f} QXC")
    
    # Show recent transactions
    print("\n📜 Recent Transactions:")
    print("-" * 60)
    
    if wallet:
        transactions = manager.get_transaction_history(wallet['address'])[:5]
    else:
        transactions = manager.get_transaction_history(main_wallet)[:5]
    
    if transactions:
        for tx in transactions:
            symbol = "⬆️" if tx['type'] == 'sent' else "⬇️"
            print(f"{symbol} {tx['amount']:.4f} QXC | Block #{tx['block']} | {tx['category']}")
            print(f"   {tx['tx_hash'][:40]}...")
    else:
        print("   No transactions found")
    
    # Options menu
    print("\n" + "=" * 60)
    print("🔧 WALLET OPTIONS:")
    print("=" * 60)
    print("1. Create New Wallet")
    print("2. Export Wallet Data")
    print("3. Check Balance")
    print("4. View Transaction History")
    print("5. Access Web Dashboard")
    print()
    
    try:
        choice = input("Select option (1-5) or press Enter to skip: ").strip()
        
        if choice == '1':
            print("\n🔄 Creating new wallet...")
            new_wallet = manager.create_new_wallet()
            print(f"✅ New wallet created!")
            print(f"   Address: {new_wallet['address']}")
            print(f"   Private Key: {new_wallet['private_key'][:20]}...")
            print(f"\n⚠️ IMPORTANT: Save your private key securely!")
            print(f"   Wallet saved to: {manager.wallet_file}")
            
        elif choice == '2':
            address = input("Enter wallet address to export (or press Enter for main): ").strip()
            if not address:
                address = main_wallet if not wallet else wallet['address']
            
            export_path = manager.export_wallet(address)
            print(f"\n✅ Wallet exported to: {export_path}")
            
        elif choice == '3':
            address = input("Enter wallet address (or press Enter for main): ").strip()
            if not address:
                address = main_wallet if not wallet else wallet['address']
            
            balance = manager.get_wallet_balance(address)
            print(f"\n💰 Balance for {address[:20]}...")
            print(f"   {balance:.4f} QXC")
            
        elif choice == '4':
            address = input("Enter wallet address (or press Enter for main): ").strip()
            if not address:
                address = main_wallet if not wallet else wallet['address']
            
            transactions = manager.get_transaction_history(address)
            print(f"\n📜 Transaction History for {address[:20]}...")
            for tx in transactions[:10]:
                symbol = "⬆️" if tx['type'] == 'sent' else "⬇️"
                print(f"{symbol} {tx['amount']:.4f} QXC | {tx['timestamp']} | {tx['category']}")
                
        elif choice == '5':
            print("\n🌐 Access your QXC tokens via web dashboard:")
            print("   https://abdulrahman305.github.io/qenex-docs)
            print("   https://abdulrahman305.github.io/qenex-docs)
            print("   https://abdulrahman305.github.io/qenex-docs)
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    
    print("\n" + "=" * 60)
    print("📌 Your QXC Balance Summary:")
    print(f"   Main Wallet: {main_balance:.4f} QXC")
    if wallet:
        print(f"   Personal Wallet: {manager.get_wallet_balance(wallet['address']):.4f} QXC")
    print("\n💡 Access dashboards at: https://abdulrahman305.github.io/qenex-docs)
    print("=" * 60)

if __name__ == "__main__":
    main()