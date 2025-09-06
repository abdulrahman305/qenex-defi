#!/usr/bin/env python3
import asyncio
import json
import logging
from pathlib import Path
from aiohttp import web
import sys
sys.path.append('/opt/qenex-os')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Node_2')

class TestnetNode:
    def __init__(self):
        self.node_id = 2
        self.port = 9002
        self.rpc_port = 10002
        self.data_dir = Path("/opt/qenex-os/testnet/node_2")
        self.wallet = self.load_wallet()
        self.blockchain = self.load_blockchain()
        self.peers = []
        self.mining = True
        
    def load_wallet(self):
        with open(self.data_dir / "wallet.json") as f:
            return json.load(f)
            
    def load_blockchain(self):
        with open(self.data_dir / "blockchain.json") as f:
            return json.load(f)
            
    async def mine_block(self):
        """Simulate mining"""
        while self.mining:
            await asyncio.sleep(10)  # Mine every 10 seconds
            
            # Create new block
            block = {
                'index': len(self.blockchain['chain']),
                'timestamp': time.time(),
                'transactions': self.blockchain['pending_transactions'][:],
                'proof': self.node_id * 1000 + len(self.blockchain['chain']),
                'previous_hash': str(hash(str(self.blockchain['chain'][-1])))
            }
            
            # Add block to chain
            self.blockchain['chain'].append(block)
            self.blockchain['pending_transactions'] = []
            
            # Mining reward
            self.wallet['balance'] += 50  # 50 QXC mining reward
            
            logger.info(f"Mined block #{block['index']} - Reward: 50 QXC - Balance: {self.wallet['balance']} QXC")
            
            # Save state
            self.save_state()
            
    def save_state(self):
        with open(self.data_dir / "wallet.json", 'w') as f:
            json.dump(self.wallet, f, indent=2)
        with open(self.data_dir / "blockchain.json", 'w') as f:
            json.dump(self.blockchain, f, indent=2)
            
    async def handle_status(self, request):
        return web.json_response({
            'node_id': self.node_id,
            'wallet': self.wallet['address'],
            'balance': self.wallet['balance'],
            'chain_height': len(self.blockchain['chain']),
            'pending_tx': len(self.blockchain['pending_transactions']),
            'peers': len(self.peers)
        })
        
    async def handle_transaction(self, request):
        data = await request.json()
        tx = {
            'from': data.get('from', self.wallet['address']),
            'to': data['to'],
            'amount': data['amount'],
            'timestamp': time.time()
        }
        self.blockchain['pending_transactions'].append(tx)
        return web.json_response({'status': 'Transaction added to pool'})
        
    async def start_server(self):
        app = web.Application()
        app.router.add_get('/status', self.handle_status)
        app.router.add_post('/transaction', self.handle_transaction)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.rpc_port)
        await site.start()
        
        logger.info(f"Node {self.node_id} RPC server started on port {self.rpc_port}")
        
        # Start mining
        await self.mine_block()
        
import time        
async def main():
    node = TestnetNode()
    await node.start_server()
    
if __name__ == '__main__':
    asyncio.run(main())
