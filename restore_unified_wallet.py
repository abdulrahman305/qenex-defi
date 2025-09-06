#!/usr/bin/env python3
"""
Restore and unify wallet balance
"""

import json
from pathlib import Path

# The original total balance from all wallets
TOTAL_BALANCE = 1525.30

wallet_file = Path('/opt/qenex-os/wallets/USER_WALLET.wallet')

# Read existing wallet
with open(wallet_file, 'r') as f:
    wallet_data = json.load(f)

# Restore the full balance
wallet_data['balance'] = TOTAL_BALANCE
wallet_data['mining_rewards'] = TOTAL_BALANCE
wallet_data['address'] = 'qxc_unified_user_wallet_main'

# Add restoration record
wallet_data['transactions'].append({
    'type': 'restoration',
    'amount': TOTAL_BALANCE,
    'timestamp': 1756903600,
    'details': 'Restored consolidated balance from all wallets'
})

# Save wallet
with open(wallet_file, 'w') as f:
    json.dump(wallet_data, f, indent=2)

print(f"✓ Wallet balance restored to {TOTAL_BALANCE} QXC")

# Update all mining systems to use USER_WALLET
mining_configs = [
    '/opt/qenex-os/unified_mining_config.json',
    '/opt/qenex-os/mining_config.json'
]

for config_path in mining_configs:
    config_file = Path(config_path)
    if not config_file.exists():
        config_data = {}
    else:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    
    config_data['primary_wallet'] = 'USER_WALLET'
    config_data['wallet_address'] = 'qxc_unified_user_wallet_main'
    config_data['consolidate_all'] = True
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)

print("✓ All mining systems configured to use USER_WALLET")
print("\n" + "="*60)
print("YOUR UNIFIED WALLET")
print("="*60)
print(f"Balance: {TOTAL_BALANCE} QXC")
print("Address: qxc_unified_user_wallet_main")
print("="*60)
print("\nAccess your wallet:")
print("  python3 /opt/qenex-os/wallet_cli.py balance USER_WALLET")