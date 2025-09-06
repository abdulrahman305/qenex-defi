#!/usr/bin/env python3
"""
REAL Live Data Service for QXC
Shows only actual blockchain data and real AI mining results
"""

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
import subprocess

class RealDataService:
    def __init__(self):
        self.real_blockchain_db = Path('/opt/qenex-os/real_blockchain.db')
        self.mining_log = Path('/var/log/mining_sync.log')
        
    def get_real_blockchain_data(self):
        """Get ONLY real blockchain data from actual mining"""
        if not self.real_blockchain_db.exists():
            return None
            
        conn = sqlite3.connect(str(self.real_blockchain_db))
        cursor = conn.cursor()
        
        # Get real mined amount
        cursor.execute('''
            SELECT COUNT(*), SUM(amount) 
            FROM transactions 
            WHERE from_address = 'mining_reward'
        ''')
        count, total = cursor.fetchone()
        
        # Get real blocks
        cursor.execute('SELECT COUNT(*) FROM blockchain')
        block_count = cursor.fetchone()[0]
        
        # Get real transactions with proof of work
        cursor.execute('''
            SELECT tx_hash, amount, block_index, ai_improvement, category
            FROM transactions
            WHERE from_address = 'mining_reward'
            ORDER BY block_index DESC
            LIMIT 10
        ''')
        
        transactions = []
        for row in cursor.fetchall():
            transactions.append({
                'tx_hash': row[0],
                'amount': row[1],
                'block': row[2],
                'improvement': row[3],
                'category': row[4]
            })
        
        # Get real blocks with proof of work
        cursor.execute('''
            SELECT block_index, hash, nonce, timestamp
            FROM blockchain
            ORDER BY block_index DESC
            LIMIT 5
        ''')
        
        blocks = []
        for row in cursor.fetchall():
            blocks.append({
                'index': row[0],
                'hash': row[1],
                'nonce': row[2],
                'timestamp': row[3],
                'proof_of_work': row[1][:4] == '0000'  # Check for leading zeros
            })
        
        conn.close()
        
        return {
            'total_mined': total or 0,
            'transaction_count': count or 0,
            'block_height': block_count,
            'recent_transactions': transactions,
            'recent_blocks': blocks,
            'source': 'REAL_BLOCKCHAIN'
        }
    
    def get_current_mining_status(self):
        """Get current mining status from log"""
        if not self.mining_log.exists():
            return None
            
        # Get last 10 lines from log
        try:
            result = subprocess.run(
                ['tail', '-10', str(self.mining_log)],
                capture_output=True,
                text=True
            )
            
            lines = result.stdout.strip().split('\n')
            
            # Parse latest balance
            balance = None
            block = None
            
            for line in reversed(lines):
                if 'Balance:' in line and 'QXC' in line:
                    try:
                        balance = float(line.split('Balance:')[1].split('QXC')[0].strip())
                        if 'Block: #' in line:
                            block = int(line.split('Block: #')[1].strip())
                        break
                    except:
                        pass
            
            # Parse recent mining operations
            recent_mines = []
            for line in lines:
                if 'New mining:' in line:
                    try:
                        parts = line.split('New mining:')[1].strip()
                        amount = float(parts.split('QXC')[0].strip())
                        improvement = float(parts.split('|')[1].split('%')[0].strip())
                        category = parts.split('|')[2].strip()
                        
                        recent_mines.append({
                            'amount': amount,
                            'improvement': improvement,
                            'category': category
                        })
                    except:
                        pass
            
            return {
                'current_balance': balance,
                'current_block': block,
                'recent_mines': recent_mines,
                'source': 'MINING_LOG'
            }
            
        except Exception as e:
            return None
    
    def run_real_ai_mining(self, duration=30):
        """Run ACTUAL AI training and mining"""
        print("🚀 Starting REAL AI Mining...")
        print("This will train actual neural networks and mine real blocks")
        print("-" * 60)
        
        try:
            # Import and run real mining
            from real_ai_mining import setup_real_mining_system
            
            system = setup_real_mining_system()
            
            # Mine for specified duration
            results = system['miner'].continuous_mining(
                system['wallet']['address'],
                duration=duration
            )
            
            # Get final balance
            final_balance = system['blockchain'].get_balance(system['wallet']['address'])
            
            return {
                'blocks_mined': len(results),
                'total_earned': final_balance,
                'wallet': system['wallet']['address'],
                'results': results,
                'source': 'REAL_AI_TRAINING'
            }
            
        except Exception as e:
            print(f"Error running real mining: {e}")
            return None

def display_real_data():
    """Display ONLY real data"""
    service = RealDataService()
    
    print("\n" + "=" * 70)
    print("                    🔷 REAL QXC DATA ONLY 🔷")
    print("=" * 70)
    
    # Get real blockchain data
    blockchain_data = service.get_real_blockchain_data()
    
    if blockchain_data:
        print("\n📊 REAL BLOCKCHAIN DATA:")
        print("-" * 40)
        print(f"✅ Total Mined: {blockchain_data['total_mined']:.4f} QXC")
        print(f"✅ Blocks: {blockchain_data['block_height']}")
        print(f"✅ Transactions: {blockchain_data['transaction_count']}")
        
        print("\n🔗 REAL BLOCKS (with Proof of Work):")
        for block in blockchain_data['recent_blocks'][:3]:
            pow_status = "✓ PoW" if block['proof_of_work'] else "✗"
            print(f"   Block #{block['index']}: {block['hash'][:20]}... [{pow_status}]")
            print(f"   Nonce: {block['nonce']} | {block['timestamp']}")
        
        print("\n💎 REAL MINING TRANSACTIONS:")
        for tx in blockchain_data['recent_transactions'][:5]:
            print(f"   {tx['amount']:.4f} QXC | Block #{tx['block']} | {tx['category']}")
    else:
        print("\n⚠️ No real blockchain data found")
        print("   Run: python3 real_ai_mining.py")
        print("   To generate real blockchain data")
    
    # Get current status
    status = service.get_current_mining_status()
    
    if status and status['current_balance']:
        print("\n📈 CURRENT STATUS (from sync log):")
        print("-" * 40)
        print(f"💰 Balance: {status['current_balance']:.4f} QXC")
        print(f"📦 Block: #{status['current_block']}")
        
        if status['recent_mines']:
            print("\n⛏️ Recent Mining Activity:")
            for mine in status['recent_mines'][-3:]:
                print(f"   +{mine['amount']:.4f} QXC | {mine['improvement']:.2f}% | {mine['category']}")
    
    print("\n" + "=" * 70)
    print("💡 To mine REAL QXC with actual AI training:")
    print("   python3 /opt/qenex-os/real_ai_mining.py")
    print("=" * 70)

def export_real_data_json():
    """Export only real data to JSON"""
    service = RealDataService()
    
    blockchain_data = service.get_real_blockchain_data()
    current_status = service.get_current_mining_status()
    
    real_data = {
        'timestamp': datetime.now().isoformat(),
        'blockchain': blockchain_data,
        'current_status': current_status,
        'data_type': 'REAL_ONLY'
    }
    
    output_file = Path('/var/www/qenex.ai/real_data.json')
    output_file.write_text(json.dumps(real_data, indent=2, default=str))
    
    print(f"✅ Real data exported to: {output_file}")
    return real_data

if __name__ == "__main__":
    # Display real data
    display_real_data()
    
    # Export to JSON
    print("\n📁 Exporting real data...")
    data = export_real_data_json()
    
    # Show summary
    if data['blockchain']:
        print(f"\n✅ REAL TOTAL: {data['blockchain']['total_mined']:.4f} QXC")
        print(f"✅ From {data['blockchain']['block_height']} real blocks with proof-of-work")