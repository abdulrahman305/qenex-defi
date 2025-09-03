#!/usr/bin/env python3
"""
QENEX OS Local Testnet Launcher
Creates a local test network with multiple nodes for development
"""

import asyncio
import json
import logging
import multiprocessing
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TestnetLauncher')

class TestnetConfig:
    """Configuration for local testnet"""
    NUM_NODES = 3
    BASE_PORT = 9000
    BASE_RPC_PORT = 10000
    DATA_DIR = Path('/opt/qenex-os/testnet')
    GENESIS_BALANCE = 1000000  # 1M QXC per wallet
    
class TestNode:
    """Represents a single testnet node"""
    
    def __init__(self, node_id: int):
        self.node_id = node_id
        self.port = TestnetConfig.BASE_PORT + node_id
        self.rpc_port = TestnetConfig.BASE_RPC_PORT + node_id
        self.data_dir = TestnetConfig.DATA_DIR / f'node_{node_id}'
        self.wallet_file = self.data_dir / 'wallet.json'
        self.blockchain_file = self.data_dir / 'blockchain.json'
        self.process = None
        
    def setup(self):
        """Initialize node directories and files"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create initial wallet
        wallet_data = {
            'address': f'testnet_wallet_{self.node_id}',
            'balance': TestnetConfig.GENESIS_BALANCE,
            'private_key': f'test_key_{self.node_id}',
            'public_key': f'test_pub_{self.node_id}'
        }
        
        with open(self.wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=2)
            
        # Create genesis block
        genesis_block = {
            'index': 0,
            'timestamp': time.time(),
            'transactions': [{
                'from': 'genesis',
                'to': wallet_data['address'],
                'amount': TestnetConfig.GENESIS_BALANCE,
                'timestamp': time.time()
            }],
            'proof': 0,
            'previous_hash': '0'
        }
        
        blockchain = {
            'chain': [genesis_block],
            'pending_transactions': [],
            'nodes': []
        }
        
        with open(self.blockchain_file, 'w') as f:
            json.dump(blockchain, f, indent=2)
            
        logger.info(f"Node {self.node_id} initialized at port {self.port}")
        
    def start(self):
        """Start the node process"""
        # Create node startup script
        startup_script = self.data_dir / 'start_node.py'
        
        script_content = f'''#!/usr/bin/env python3
import asyncio
import json
import logging
from pathlib import Path
from aiohttp import web
import sys
sys.path.append('/opt/qenex-os')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Node_{self.node_id}')

class TestnetNode:
    def __init__(self):
        self.node_id = {self.node_id}
        self.port = {self.port}
        self.rpc_port = {self.rpc_port}
        self.data_dir = Path("{self.data_dir}")
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
            block = {{
                'index': len(self.blockchain['chain']),
                'timestamp': time.time(),
                'transactions': self.blockchain['pending_transactions'][:],
                'proof': self.node_id * 1000 + len(self.blockchain['chain']),
                'previous_hash': str(hash(str(self.blockchain['chain'][-1])))
            }}
            
            # Add block to chain
            self.blockchain['chain'].append(block)
            self.blockchain['pending_transactions'] = []
            
            # Mining reward
            self.wallet['balance'] += 50  # 50 QXC mining reward
            
            logger.info(f"Mined block #{{block['index']}} - Reward: 50 QXC - Balance: {{self.wallet['balance']}} QXC")
            
            # Save state
            self.save_state()
            
    def save_state(self):
        with open(self.data_dir / "wallet.json", 'w') as f:
            json.dump(self.wallet, f, indent=2)
        with open(self.data_dir / "blockchain.json", 'w') as f:
            json.dump(self.blockchain, f, indent=2)
            
    async def handle_status(self, request):
        return web.json_response({{
            'node_id': self.node_id,
            'wallet': self.wallet['address'],
            'balance': self.wallet['balance'],
            'chain_height': len(self.blockchain['chain']),
            'pending_tx': len(self.blockchain['pending_transactions']),
            'peers': len(self.peers)
        }})
        
    async def handle_transaction(self, request):
        data = await request.json()
        tx = {{
            'from': data.get('from', self.wallet['address']),
            'to': data['to'],
            'amount': data['amount'],
            'timestamp': time.time()
        }}
        self.blockchain['pending_transactions'].append(tx)
        return web.json_response({{'status': 'Transaction added to pool'}})
        
    async def start_server(self):
        app = web.Application()
        app.router.add_get('/status', self.handle_status)
        app.router.add_post('/transaction', self.handle_transaction)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.rpc_port)
        await site.start()
        
        logger.info(f"Node {{self.node_id}} RPC server started on port {{self.rpc_port}}")
        
        # Start mining
        await self.mine_block()
        
import time        
async def main():
    node = TestnetNode()
    await node.start_server()
    
if __name__ == '__main__':
    asyncio.run(main())
'''
        
        with open(startup_script, 'w') as f:
            f.write(script_content)
            
        os.chmod(startup_script, 0o755)
        
        # Start the node process
        import subprocess
        self.process = subprocess.Popen(
            [sys.executable, str(startup_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logger.info(f"Node {self.node_id} started with PID {self.process.pid}")
        
class TestnetLauncher:
    """Main testnet launcher"""
    
    def __init__(self):
        self.nodes: List[TestNode] = []
        
    def setup_testnet(self):
        """Initialize all testnet nodes"""
        logger.info(f"Setting up testnet with {TestnetConfig.NUM_NODES} nodes")
        
        # Create testnet directory
        TestnetConfig.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize nodes
        for i in range(TestnetConfig.NUM_NODES):
            node = TestNode(i)
            node.setup()
            self.nodes.append(node)
            
        # Create peer connections config
        peers_config = []
        for node in self.nodes:
            peers_config.append({
                'id': node.node_id,
                'address': f'localhost:{node.port}',
                'rpc': f'http://localhost:{node.rpc_port}'
            })
            
        # Save peers config
        with open(TestnetConfig.DATA_DIR / 'peers.json', 'w') as f:
            json.dump(peers_config, f, indent=2)
            
        logger.info("Testnet setup complete")
        
    def start_testnet(self):
        """Start all testnet nodes"""
        logger.info("Starting testnet nodes...")
        
        for node in self.nodes:
            try:
                node.start()
                time.sleep(2)  # Stagger node starts
            except Exception as e:
                logger.error(f"Failed to start node {node.node_id}: {e}")
                
    def stop_testnet(self):
        """Stop all testnet nodes"""
        logger.info("Stopping testnet nodes...")
        
        for node in self.nodes:
            if node.process:
                node.process.terminate()
                node.process.wait()
                logger.info(f"Node {node.node_id} stopped")
                
    def get_status(self):
        """Get testnet status"""
        import requests
        
        status = []
        for node in self.nodes:
            try:
                response = requests.get(f'http://localhost:{node.rpc_port}/status', timeout=2)
                status.append(response.json())
            except:
                status.append({'node_id': node.node_id, 'status': 'offline'})
                
        return status
        
def main():
    """Main entry point"""
    launcher = TestnetLauncher()
    
    try:
        # Setup and start testnet
        launcher.setup_testnet()
        launcher.start_testnet()
        
        logger.info("=" * 50)
        logger.info("QENEX OS Testnet is running!")
        logger.info(f"Nodes: {TestnetConfig.NUM_NODES}")
        logger.info(f"RPC Ports: {TestnetConfig.BASE_RPC_PORT}-{TestnetConfig.BASE_RPC_PORT + TestnetConfig.NUM_NODES - 1}")
        logger.info("=" * 50)
        
        # Monitor testnet
        while True:
            time.sleep(30)
            status = launcher.get_status()
            
            logger.info("\n=== Testnet Status ===")
            for node_status in status:
                if 'chain_height' in node_status:
                    logger.info(f"Node {node_status['node_id']}: Height={node_status['chain_height']}, Balance={node_status['balance']} QXC")
                else:
                    logger.info(f"Node {node_status['node_id']}: OFFLINE")
                    
    except KeyboardInterrupt:
        logger.info("\nShutting down testnet...")
        launcher.stop_testnet()
        
    except Exception as e:
        logger.error(f"Testnet error: {e}")
        launcher.stop_testnet()
        
if __name__ == '__main__':
    main()