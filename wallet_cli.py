#!/usr/bin/env python3
"""
QENEX Wallet CLI - Access and manage your QXC wallet
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict
import sqlite3
import hashlib
from datetime import datetime

class WalletCLI:
    def __init__(self):
        self.wallet_dir = Path('/opt/qenex-os/wallets')
        self.db_path = self.wallet_dir / 'wallets.db'
        self.user_wallet = self.wallet_dir / 'USER_WALLET.wallet'
        
    def get_wallet_balance(self, wallet_name: str = "USER_WALLET") -> Dict:
        """Get balance for a specific wallet"""
        wallet_file = self.wallet_dir / f"{wallet_name}.wallet"
        
        if wallet_file.exists():
            try:
                with open(wallet_file, 'r') as f:
                    data = json.load(f)
                    return {
                        'wallet': wallet_name,
                        'address': data.get('address', 'N/A'),
                        'balance': data.get('balance', 0),
                        'mining_rewards': data.get('mining_rewards', 0),
                        'last_updated': data.get('last_activity', 'Never')
                    }
            except:
                pass
                
        # Check database
        if self.db_path.exists():
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT address, balance FROM wallets WHERE name = ?", (wallet_name,))
                result = cursor.fetchone()
                if result:
                    return {
                        'wallet': wallet_name,
                        'address': result[0],
                        'balance': result[1],
                        'source': 'database'
                    }
            except:
                pass
            finally:
                conn.close()
                
        return {'error': f'Wallet {wallet_name} not found'}
        
    def list_all_wallets(self):
        """List all available wallets"""
        wallets = []
        
        # Get wallet files
        for wallet_file in self.wallet_dir.glob("*.wallet"):
            wallet_name = wallet_file.stem
            info = self.get_wallet_balance(wallet_name)
            if 'error' not in info:
                wallets.append(info)
                
        return wallets
        
    def show_mining_status(self):
        """Show current mining status"""
        status = {
            'mining_active': False,
            'total_mined': 0,
            'current_hashrate': 0
        }
        
        # Check if mining processes are running
        import subprocess
        try:
            result = subprocess.run(['pgrep', '-f', 'mining'], capture_output=True, text=True)
            if result.returncode == 0:
                status['mining_active'] = True
        except:
            pass
            
        # Get total mined from all wallets
        for wallet_info in self.list_all_wallets():
            if 'balance' in wallet_info:
                status['total_mined'] += wallet_info.get('mining_rewards', 0)
                
        return status
        
    def create_new_wallet(self, name: str) -> Dict:
        """Create a new wallet"""
        wallet_file = self.wallet_dir / f"{name}.wallet"
        
        if wallet_file.exists():
            return {'error': 'Wallet already exists'}
            
        # Generate wallet address
        address = hashlib.sha256(f"{name}_{datetime.now().isoformat()}".encode()).hexdigest()[:40]
        
        wallet_data = {
            'address': f"qxc_{address}",
            'balance': 0,
            'mining_rewards': 0,
            'created': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'transactions': []
        }
        
        with open(wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=2)
            
        return {
            'success': True,
            'wallet': name,
            'address': wallet_data['address']
        }

def main():
    cli = WalletCLI()
    
    if len(sys.argv) < 2:
        print("QENEX Wallet CLI")
        print("================")
        print("\nUsage:")
        print("  python3 wallet_cli.py balance [wallet_name]  - Show wallet balance")
        print("  python3 wallet_cli.py list                   - List all wallets")
        print("  python3 wallet_cli.py mining                 - Show mining status")
        print("  python3 wallet_cli.py create <name>          - Create new wallet")
        print("\nExamples:")
        print("  python3 wallet_cli.py balance                # Show USER_WALLET balance")
        print("  python3 wallet_cli.py balance ORIGINAL_MASTER")
        print("  python3 wallet_cli.py list")
        return
        
    command = sys.argv[1].lower()
    
    if command == 'balance':
        wallet_name = sys.argv[2] if len(sys.argv) > 2 else "USER_WALLET"
        info = cli.get_wallet_balance(wallet_name)
        
        if 'error' in info:
            print(f"Error: {info['error']}")
        else:
            print(f"\n{'='*50}")
            print(f"Wallet: {info['wallet']}")
            print(f"Address: {info['address']}")
            print(f"Balance: {info['balance']:.2f} QXC")
            if 'mining_rewards' in info:
                print(f"Mining Rewards: {info['mining_rewards']:.2f} QXC")
            if 'last_updated' in info:
                print(f"Last Activity: {info['last_updated']}")
            print(f"{'='*50}\n")
            
    elif command == 'list':
        wallets = cli.list_all_wallets()
        print(f"\n{'='*60}")
        print(f"{'Wallet Name':<20} {'Balance':>12} {'Mining Rewards':>15}")
        print(f"{'='*60}")
        
        total_balance = 0
        total_mining = 0
        
        for wallet in wallets:
            balance = wallet.get('balance', 0)
            mining = wallet.get('mining_rewards', 0)
            total_balance += balance
            total_mining += mining
            
            print(f"{wallet['wallet']:<20} {balance:>12.2f} QXC {mining:>12.2f} QXC")
            
        print(f"{'='*60}")
        print(f"{'TOTAL':<20} {total_balance:>12.2f} QXC {total_mining:>12.2f} QXC")
        print(f"{'='*60}\n")
        
    elif command == 'mining':
        status = cli.show_mining_status()
        print(f"\n{'='*40}")
        print(f"Mining Status")
        print(f"{'='*40}")
        print(f"Active: {'Yes' if status['mining_active'] else 'No'}")
        print(f"Total Mined: {status['total_mined']:.2f} QXC")
        print(f"{'='*40}\n")
        
    elif command == 'create':
        if len(sys.argv) < 3:
            print("Error: Please provide wallet name")
            return
            
        name = sys.argv[2].upper()
        result = cli.create_new_wallet(name)
        
        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            print(f"\n{'='*50}")
            print(f"✓ Wallet created successfully!")
            print(f"Name: {result['wallet']}")
            print(f"Address: {result['address']}")
            print(f"{'='*50}\n")
            
    else:
        print(f"Unknown command: {command}")
        print("Use 'python3 wallet_cli.py' for help")

if __name__ == '__main__':
    main()