#!/usr/bin/env python3
"""
QENEX P2P Networking Layer
Distributed peer-to-peer network for blockchain synchronization
"""

import socket
import threading
import json
import time
import hashlib
import struct
import random
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
import sqlite3
import os

# Network configuration
class NetworkConfig:
    VERSION = "1.0.0"
    NETWORK_ID = "QENEX_MAINNET"
    DEFAULT_PORT = 8333
    MAX_PEERS = 50
    BOOTSTRAP_NODES = [
        ("seed1.qenex.ai", 8333),
        ("seed2.qenex.ai", 8333),
        ("localhost", 8333)
    ]
    PING_INTERVAL = 30
    PEER_TIMEOUT = 120
    BLOCK_PROPAGATION_DELAY = 0.1

@dataclass
class Message:
    """P2P network message"""
    msg_type: str  # 'ping', 'pong', 'block', 'tx', 'getblocks', 'inv', 'getdata'
    payload: Dict
    timestamp: float
    sender: str
    
    def serialize(self) -> bytes:
        """Serialize message for network transmission"""
        data = {
            "type": self.msg_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "sender": self.sender
        }
        json_data = json.dumps(data)
        # Add message length header (4 bytes)
        length = struct.pack('>I', len(json_data))
        return length + json_data.encode()
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'Message':
        """Deserialize message from network"""
        json_data = json.loads(data.decode())
        return cls(
            msg_type=json_data["type"],
            payload=json_data["payload"],
            timestamp=json_data["timestamp"],
            sender=json_data["sender"]
        )

class Peer:
    """Represents a network peer"""
    
    def __init__(self, address: Tuple[str, int], conn: socket.socket = None):
        self.address = address
        self.conn = conn
        self.node_id = f"{address[0]}:{address[1]}"
        self.version = None
        self.last_seen = time.time()
        self.latency = 0
        self.score = 100  # Reputation score
        self.is_outbound = conn is not None
        self.synced = False
    
    def send_message(self, message: Message) -> bool:
        """Send message to peer"""
        try:
            if self.conn:
                self.conn.send(message.serialize())
                return True
        except Exception as e:
            print(f"Failed to send to {self.node_id}: {e}")
            self.score -= 10
        return False
    
    def receive_message(self) -> Optional[Message]:
        """Receive message from peer"""
        try:
            if self.conn:
                # Read message length
                length_data = self.conn.recv(4)
                if not length_data:
                    return None
                
                length = struct.unpack('>I', length_data)[0]
                
                # Read message data
                data = b""
                while len(data) < length:
                    chunk = self.conn.recv(min(4096, length - len(data)))
                    if not chunk:
                        return None
                    data += chunk
                
                return Message.deserialize(data)
        except Exception as e:
            print(f"Failed to receive from {self.node_id}: {e}")
            self.score -= 5
        return None
    
    def close(self):
        """Close peer connection"""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass

class P2PNode:
    """P2P network node implementation"""
    
    def __init__(self, port: int = NetworkConfig.DEFAULT_PORT, blockchain = None):
        self.port = port
        self.blockchain = blockchain
        self.peers: Dict[str, Peer] = {}
        self.server_socket = None
        self.running = False
        self.node_id = f"node_{random.randint(1000, 9999)}"
        
        # Message handlers
        self.message_handlers = {
            'ping': self.handle_ping,
            'pong': self.handle_pong,
            'block': self.handle_block,
            'tx': self.handle_transaction,
            'getblocks': self.handle_getblocks,
            'inv': self.handle_inventory,
            'getdata': self.handle_getdata,
            'version': self.handle_version
        }
        
        # Pending requests
        self.pending_blocks: Set[str] = set()
        self.pending_txs: Set[str] = set()
        
        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "blocks_received": 0,
            "txs_received": 0,
            "bytes_sent": 0,
            "bytes_received": 0
        }
    
    def start(self):
        """Start P2P node"""
        self.running = True
        
        # Start server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(NetworkConfig.MAX_PEERS)
        
        print(f"[P2P] Node {self.node_id} listening on port {self.port}")
        
        # Start threads
        threading.Thread(target=self.accept_connections, daemon=True).start()
        threading.Thread(target=self.connect_to_peers, daemon=True).start()
        threading.Thread(target=self.peer_maintenance, daemon=True).start()
        
        return True
    
    def stop(self):
        """Stop P2P node"""
        self.running = False
        
        # Close all peer connections
        for peer in self.peers.values():
            peer.close()
        
        # Close server socket
        if self.server_socket:
            self.server_socket.close()
        
        print(f"[P2P] Node {self.node_id} stopped")
    
    def accept_connections(self):
        """Accept incoming peer connections"""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                if len(self.peers) < NetworkConfig.MAX_PEERS:
                    peer = Peer(addr, conn)
                    self.add_peer(peer)
                    
                    # Start peer handler
                    threading.Thread(
                        target=self.handle_peer,
                        args=(peer,),
                        daemon=True
                    ).start()
                    
                    print(f"[P2P] Accepted connection from {peer.node_id}")
                else:
                    conn.close()
            except Exception as e:
                if self.running:
                    print(f"[P2P] Accept error: {e}")
    
    def connect_to_peers(self):
        """Connect to bootstrap and discovered peers"""
        time.sleep(2)  # Initial delay
        
        while self.running:
            try:
                # Connect to bootstrap nodes if few peers
                if len(self.peers) < 5:
                    for host, port in NetworkConfig.BOOTSTRAP_NODES:
                        if f"{host}:{port}" not in self.peers:
                            self.connect_to_peer(host, port)
                
                # Discover new peers from existing peers
                if len(self.peers) < NetworkConfig.MAX_PEERS // 2:
                    self.discover_peers()
                
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                print(f"[P2P] Connection error: {e}")
    
    def connect_to_peer(self, host: str, port: int) -> Optional[Peer]:
        """Connect to a specific peer"""
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(5)
            conn.connect((host, port))
            conn.settimeout(None)
            
            peer = Peer((host, port), conn)
            self.add_peer(peer)
            
            # Send version handshake
            self.send_version(peer)
            
            # Start peer handler
            threading.Thread(
                target=self.handle_peer,
                args=(peer,),
                daemon=True
            ).start()
            
            print(f"[P2P] Connected to {peer.node_id}")
            return peer
            
        except Exception as e:
            print(f"[P2P] Failed to connect to {host}:{port}: {e}")
            return None
    
    def add_peer(self, peer: Peer):
        """Add peer to active peers"""
        self.peers[peer.node_id] = peer
    
    def remove_peer(self, peer: Peer):
        """Remove peer from active peers"""
        if peer.node_id in self.peers:
            del self.peers[peer.node_id]
            peer.close()
    
    def handle_peer(self, peer: Peer):
        """Handle messages from a peer"""
        while self.running and peer.node_id in self.peers:
            try:
                message = peer.receive_message()
                if message:
                    peer.last_seen = time.time()
                    self.handle_message(peer, message)
                    self.stats["messages_received"] += 1
                else:
                    break  # Connection closed
            except Exception as e:
                print(f"[P2P] Error handling peer {peer.node_id}: {e}")
                break
        
        # Clean up disconnected peer
        self.remove_peer(peer)
    
    def handle_message(self, peer: Peer, message: Message):
        """Route message to appropriate handler"""
        if message.msg_type in self.message_handlers:
            self.message_handlers[message.msg_type](peer, message)
        else:
            print(f"[P2P] Unknown message type: {message.msg_type}")
    
    def handle_ping(self, peer: Peer, message: Message):
        """Handle ping message"""
        pong = Message(
            msg_type="pong",
            payload={"nonce": message.payload.get("nonce", 0)},
            timestamp=time.time(),
            sender=self.node_id
        )
        peer.send_message(pong)
    
    def handle_pong(self, peer: Peer, message: Message):
        """Handle pong message"""
        # Calculate latency
        if "nonce" in message.payload:
            peer.latency = time.time() - message.timestamp
    
    def handle_version(self, peer: Peer, message: Message):
        """Handle version handshake"""
        peer.version = message.payload.get("version")
        peer.synced = True
        
        # Send version acknowledgment
        if not peer.is_outbound:
            self.send_version(peer)
    
    def handle_block(self, peer: Peer, message: Message):
        """Handle new block announcement"""
        block_data = message.payload
        block_hash = block_data.get("hash")
        
        if block_hash not in self.pending_blocks:
            self.pending_blocks.add(block_hash)
            self.stats["blocks_received"] += 1
            
            # Validate and add to blockchain
            if self.blockchain:
                # Add block to local blockchain
                pass  # Implement blockchain integration
            
            # Propagate to other peers
            self.broadcast_message(message, exclude=peer)
    
    def handle_transaction(self, peer: Peer, message: Message):
        """Handle new transaction"""
        tx_data = message.payload
        tx_id = tx_data.get("tx_id")
        
        if tx_id not in self.pending_txs:
            self.pending_txs.add(tx_id)
            self.stats["txs_received"] += 1
            
            # Add to mempool
            if self.blockchain:
                # Add transaction to mempool
                pass  # Implement blockchain integration
            
            # Propagate to other peers
            self.broadcast_message(message, exclude=peer)
    
    def handle_getblocks(self, peer: Peer, message: Message):
        """Handle request for blocks"""
        # Send inventory of available blocks
        if self.blockchain:
            blocks = []  # Get block hashes from blockchain
            inv_message = Message(
                msg_type="inv",
                payload={"type": "block", "items": blocks},
                timestamp=time.time(),
                sender=self.node_id
            )
            peer.send_message(inv_message)
    
    def handle_inventory(self, peer: Peer, message: Message):
        """Handle inventory announcement"""
        inv_type = message.payload.get("type")
        items = message.payload.get("items", [])
        
        # Request missing items
        missing = []
        for item in items:
            if inv_type == "block" and item not in self.pending_blocks:
                missing.append(item)
            elif inv_type == "tx" and item not in self.pending_txs:
                missing.append(item)
        
        if missing:
            getdata = Message(
                msg_type="getdata",
                payload={"type": inv_type, "items": missing},
                timestamp=time.time(),
                sender=self.node_id
            )
            peer.send_message(getdata)
    
    def handle_getdata(self, peer: Peer, message: Message):
        """Handle request for specific data"""
        data_type = message.payload.get("type")
        items = message.payload.get("items", [])
        
        # Send requested data
        for item in items:
            if data_type == "block":
                # Get block from blockchain and send
                pass
            elif data_type == "tx":
                # Get transaction and send
                pass
    
    def send_version(self, peer: Peer):
        """Send version handshake"""
        version = Message(
            msg_type="version",
            payload={
                "version": NetworkConfig.VERSION,
                "network": NetworkConfig.NETWORK_ID,
                "node_id": self.node_id,
                "services": ["full_node", "mining"],
                "timestamp": time.time()
            },
            timestamp=time.time(),
            sender=self.node_id
        )
        peer.send_message(version)
    
    def broadcast_message(self, message: Message, exclude: Peer = None):
        """Broadcast message to all peers"""
        for peer in self.peers.values():
            if peer != exclude and peer.synced:
                peer.send_message(message)
                self.stats["messages_sent"] += 1
    
    def broadcast_block(self, block: Dict):
        """Broadcast new block to network"""
        message = Message(
            msg_type="block",
            payload=block,
            timestamp=time.time(),
            sender=self.node_id
        )
        self.broadcast_message(message)
        print(f"[P2P] Broadcasting block {block.get('index')} to {len(self.peers)} peers")
    
    def broadcast_transaction(self, transaction: Dict):
        """Broadcast new transaction to network"""
        message = Message(
            msg_type="tx",
            payload=transaction,
            timestamp=time.time(),
            sender=self.node_id
        )
        self.broadcast_message(message)
    
    def discover_peers(self):
        """Discover new peers from existing peers"""
        # Request peer lists from connected peers
        for peer in list(self.peers.values()):
            getpeers = Message(
                msg_type="getpeers",
                payload={},
                timestamp=time.time(),
                sender=self.node_id
            )
            peer.send_message(getpeers)
    
    def peer_maintenance(self):
        """Maintain peer connections"""
        while self.running:
            try:
                current_time = time.time()
                
                # Remove inactive peers
                for peer_id in list(self.peers.keys()):
                    peer = self.peers.get(peer_id)
                    if peer and current_time - peer.last_seen > NetworkConfig.PEER_TIMEOUT:
                        print(f"[P2P] Removing inactive peer {peer_id}")
                        self.remove_peer(peer)
                
                # Send ping to maintain connections
                for peer in self.peers.values():
                    if current_time - peer.last_seen > NetworkConfig.PING_INTERVAL:
                        ping = Message(
                            msg_type="ping",
                            payload={"nonce": random.randint(1, 1000000)},
                            timestamp=time.time(),
                            sender=self.node_id
                        )
                        peer.send_message(ping)
                
                time.sleep(NetworkConfig.PING_INTERVAL)
                
            except Exception as e:
                print(f"[P2P] Maintenance error: {e}")
    
    def get_peer_info(self) -> List[Dict]:
        """Get information about connected peers"""
        return [{
            "node_id": peer.node_id,
            "address": peer.address,
            "version": peer.version,
            "latency": peer.latency,
            "score": peer.score,
            "last_seen": peer.last_seen,
            "is_outbound": peer.is_outbound,
            "synced": peer.synced
        } for peer in self.peers.values()]
    
    def get_stats(self) -> Dict:
        """Get network statistics"""
        return {
            **self.stats,
            "peer_count": len(self.peers),
            "active_peers": sum(1 for p in self.peers.values() if p.synced),
            "avg_latency": sum(p.latency for p in self.peers.values()) / max(len(self.peers), 1)
        }

class P2PNetwork:
    """High-level P2P network manager"""
    
    def __init__(self, port: int = NetworkConfig.DEFAULT_PORT):
        self.node = P2PNode(port)
        self.running = False
    
    def start(self, blockchain = None):
        """Start P2P network"""
        self.node.blockchain = blockchain
        self.running = True
        
        print("\n" + "="*60)
        print("QENEX P2P NETWORK")
        print("="*60)
        print(f"Node ID: {self.node.node_id}")
        print(f"Port: {self.node.port}")
        print(f"Max Peers: {NetworkConfig.MAX_PEERS}")
        print("="*60 + "\n")
        
        return self.node.start()
    
    def stop(self):
        """Stop P2P network"""
        self.running = False
        self.node.stop()
    
    def broadcast_block(self, block: Dict):
        """Broadcast block to network"""
        self.node.broadcast_block(block)
    
    def broadcast_transaction(self, transaction: Dict):
        """Broadcast transaction to network"""
        self.node.broadcast_transaction(transaction)
    
    def get_peers(self) -> List[Dict]:
        """Get connected peers"""
        return self.node.get_peer_info()
    
    def get_stats(self) -> Dict:
        """Get network statistics"""
        return self.node.get_stats()

# Example usage
def main():
    """Test P2P network"""
    network = P2PNetwork(8333)
    
    try:
        network.start()
        
        # Monitor network
        while True:
            time.sleep(10)
            
            peers = network.get_peers()
            stats = network.get_stats()
            
            print(f"\n[P2P] Connected Peers: {len(peers)}")
            for peer in peers:
                print(f"  - {peer['node_id']} (latency: {peer['latency']:.2f}s)")
            
            print(f"[P2P] Network Stats:")
            print(f"  Messages: {stats['messages_sent']} sent, {stats['messages_received']} received")
            print(f"  Blocks: {stats['blocks_received']}")
            print(f"  Transactions: {stats['txs_received']}")
            
    except KeyboardInterrupt:
        print("\nShutting down P2P network...")
        network.stop()

if __name__ == "__main__":
    main()