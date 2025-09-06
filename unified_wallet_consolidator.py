#!/usr/bin/env python3
"""
QENEX Unified Wallet Consolidator
Consolidates all wallets into a single USER_WALLET
"""

import json
import os
import time
from pathlib import Path
from typing import Dict
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('WalletConsolidator')

class WalletConsolidator:
    def __init__(self):
        self.wallet_dir = Path('/opt/qenex-os/wallets')
        self.primary_wallet = self.wallet_dir / 'USER_WALLET.wallet'
        self.consolidation_interval = 10  # Consolidate every 10 seconds
        self.running = False
        
    def get_all_balances(self) -> Dict[str, float]:
        """Get balances from all wallet files"""
        balances = {}
        
        for wallet_file in self.wallet_dir.glob("*.wallet"):
            if wallet_file == self.primary_wallet:
                continue  # Skip the primary wallet
                
            try:
                with open(wallet_file, 'r') as f:
                    data = json.load(f)
                    wallet_name = wallet_file.stem
                    balance = float(data.get('balance', 0))
                    balances[wallet_name] = balance
            except Exception as e:
                logger.debug(f"Could not read {wallet_file}: {e}")
                
        return balances
        
    def consolidate_wallets(self):
        """Consolidate all wallet balances into USER_WALLET"""
        logger.info("Starting wallet consolidation...")
        
        # Get all balances
        all_balances = self.get_all_balances()
        new_balance = sum(all_balances.values())
        
        # Read or create USER_WALLET
        user_wallet_data = {
            'address': 'qxc_unified_user_wallet_main',
            'balance': 0,
            'mining_rewards': 0,
            'consolidated_from': {},
            'last_consolidation': None,
            'transactions': []
        }
        
        if self.primary_wallet.exists():
            try:
                with open(self.primary_wallet, 'r') as f:
                    existing_data = json.load(f)
                    user_wallet_data.update(existing_data)
            except:
                pass
                
        # Add new balance to existing balance (accumulate, don't replace)
        existing_balance = user_wallet_data.get('balance', 0)
        total_balance = existing_balance + new_balance
        
        # Update wallet data
        user_wallet_data['balance'] = total_balance
        user_wallet_data['consolidated_from'] = all_balances
        user_wallet_data['last_consolidation'] = time.time()
        user_wallet_data['mining_rewards'] = total_balance  # All balance comes from mining
        
        # Add consolidation transaction
        transaction = {
            'type': 'consolidation',
            'timestamp': time.time(),
            'amount': total_balance,
            'from_wallets': list(all_balances.keys()),
            'details': f"Consolidated {len(all_balances)} wallets"
        }
        
        if 'transactions' not in user_wallet_data:
            user_wallet_data['transactions'] = []
        user_wallet_data['transactions'].append(transaction)
        
        # Keep only last 100 transactions
        user_wallet_data['transactions'] = user_wallet_data['transactions'][-100:]
        
        # Save consolidated wallet
        with open(self.primary_wallet, 'w') as f:
            json.dump(user_wallet_data, f, indent=2)
            
        # Zero out other wallets (they're now consolidated)
        for wallet_file in self.wallet_dir.glob("*.wallet"):
            if wallet_file == self.primary_wallet:
                continue
                
            try:
                with open(wallet_file, 'r') as f:
                    data = json.load(f)
                
                # Keep wallet structure but move balance to consolidated
                data['balance'] = 0
                data['consolidated_to'] = 'USER_WALLET'
                data['consolidated_at'] = time.time()
                
                with open(wallet_file, 'w') as f:
                    json.dump(data, f, indent=2)
            except:
                pass
                
        logger.info(f"✓ Consolidated {len(all_balances)} wallets")
        logger.info(f"✓ Total balance: {total_balance:.2f} QXC")
        logger.info(f"✓ All funds now in USER_WALLET")
        
        return total_balance
        
    def run_continuous(self):
        """Run consolidation continuously"""
        self.running = True
        
        while self.running:
            try:
                self.consolidate_wallets()
            except Exception as e:
                logger.error(f"Consolidation error: {e}")
                
            time.sleep(self.consolidation_interval)
            
    def start(self):
        """Start the consolidation service"""
        logger.info("Starting Wallet Consolidation Service")
        consolidation_thread = threading.Thread(target=self.run_continuous, daemon=True)
        consolidation_thread.start()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down consolidation service")
            self.running = False

def main():
    consolidator = WalletConsolidator()
    
    # Do one immediate consolidation
    total = consolidator.consolidate_wallets()
    
    print("\n" + "="*60)
    print("QENEX WALLET CONSOLIDATION COMPLETE")
    print("="*60)
    print(f"✓ All wallets consolidated into USER_WALLET")
    print(f"✓ Total Balance: {total:.2f} QXC")
    print("="*60)
    print("\nAccess your unified wallet:")
    print("  python3 /opt/qenex-os/wallet_cli.py balance USER_WALLET")
    print("\nStarting continuous consolidation service...")
    print("(Press Ctrl+C to stop)")
    
    # Start continuous consolidation
    consolidator.start()

if __name__ == '__main__':
    main()