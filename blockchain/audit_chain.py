"""Blockchain-based audit logging for QENEX OS"""
import hashlib
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Any
import sqlite3
import threading
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

class Block:
    """Represents a block in the audit blockchain"""
    
    def __init__(self, index: int, timestamp: float, data: Dict, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate block hash"""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int):
        """Mine block with proof of work"""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def to_dict(self) -> Dict:
        """Convert block to dictionary"""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }

class AuditBlockchain:
    """Blockchain for immutable audit logging"""
    
    def __init__(self, db_path: str = "audit_blockchain.db", difficulty: int = 2):
        self.difficulty = difficulty
        self.db_path = db_path
        self.chain: List[Block] = []
        self.pending_logs: List[Dict] = []
        self.lock = threading.Lock()
        
        # Initialize database
        self.init_db()
        
        # Load existing chain or create genesis block
        if not self.load_chain():
            self.chain.append(self.create_genesis_block())
            self.save_block(self.chain[0])
        
        # Generate cryptographic keys for signing
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
    
    def init_db(self):
        """Initialize SQLite database for persistent storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocks (
                block_index INTEGER PRIMARY KEY,
                timestamp REAL,
                data TEXT,
                previous_hash TEXT,
                nonce INTEGER,
                hash TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_index INTEGER,
                event_type TEXT,
                user_id TEXT,
                action TEXT,
                details TEXT,
                timestamp REAL,
                signature TEXT,
                FOREIGN KEY(block_index) REFERENCES blocks(block_index)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_genesis_block(self) -> Block:
        """Create the first block in the chain"""
        return Block(
            index=0,
            timestamp=time.time(),
            data={
                "event": "genesis",
                "message": "QENEX OS Audit Blockchain Genesis Block",
                "version": "5.0.0"
            },
            previous_hash="0"
        )
    
    def get_latest_block(self) -> Block:
        """Get the most recent block"""
        with self.lock:
            return self.chain[-1]
    
    def add_audit_log(self, event_type: str, user_id: str, action: str, details: Dict) -> str:
        """Add an audit log entry"""
        log_entry = {
            "event_type": event_type,
            "user_id": user_id,
            "action": action,
            "details": details,
            "timestamp": time.time(),
            "iso_timestamp": datetime.now().isoformat()
        }
        
        # Sign the log entry
        signature = self.sign_data(log_entry)
        log_entry["signature"] = signature.hex()
        
        with self.lock:
            self.pending_logs.append(log_entry)
        
        # Mine block if we have enough pending logs
        if len(self.pending_logs) >= 10:
            self.mine_pending_logs()
        
        return signature.hex()
    
    def mine_pending_logs(self):
        """Mine pending logs into a new block"""
        if not self.pending_logs:
            return
        
        with self.lock:
            # Create new block
            new_block = Block(
                index=len(self.chain),
                timestamp=time.time(),
                data={
                    "logs": self.pending_logs,
                    "log_count": len(self.pending_logs)
                },
                previous_hash=self.chain[-1].hash
            )
            
            # Mine the block
            new_block.mine_block(self.difficulty)
            
            # Add to chain
            self.chain.append(new_block)
            self.save_block(new_block)
            
            # Clear pending logs
            self.pending_logs = []
    
    def validate_chain(self) -> bool:
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Check hash calculation
            if current.hash != current.calculate_hash():
                return False
            
            # Check chain linkage
            if current.previous_hash != previous.hash:
                return False
            
            # Check proof of work
            if current.hash[:self.difficulty] != "0" * self.difficulty:
                return False
        
        return True
    
    def sign_data(self, data: Dict) -> bytes:
        """Sign data with private key"""
        message = json.dumps(data, sort_keys=True).encode()
        signature = self.private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature
    
    def verify_signature(self, data: Dict, signature: bytes) -> bool:
        """Verify data signature"""
        message = json.dumps(data, sort_keys=True).encode()
        try:
            self.public_key.verify(
                signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except:
            return False
    
    def save_block(self, block: Block):
        """Save block to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO blocks (block_index, timestamp, data, previous_hash, nonce, hash)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            block.index,
            block.timestamp,
            json.dumps(block.data),
            block.previous_hash,
            block.nonce,
            block.hash
        ))
        
        # Save individual audit logs
        if "logs" in block.data:
            for log in block.data["logs"]:
                cursor.execute('''
                    INSERT INTO audit_logs (block_index, event_type, user_id, action, details, timestamp, signature)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    block.index,
                    log.get("event_type"),
                    log.get("user_id"),
                    log.get("action"),
                    json.dumps(log.get("details", {})),
                    log.get("timestamp"),
                    log.get("signature")
                ))
        
        conn.commit()
        conn.close()
    
    def load_chain(self) -> bool:
        """Load blockchain from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM blocks ORDER BY block_index')
        rows = cursor.fetchall()
        
        if rows:
            self.chain = []
            for row in rows:
                block = Block(
                    index=row[0],
                    timestamp=row[1],
                    data=json.loads(row[2]),
                    previous_hash=row[3]
                )
                block.nonce = row[4]
                block.hash = row[5]
                self.chain.append(block)
            
            conn.close()
            return True
        
        conn.close()
        return False
    
    def query_audit_logs(self, filters: Dict = None) -> List[Dict]:
        """Query audit logs with optional filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        
        if filters:
            if "event_type" in filters:
                query += " AND event_type = ?"
                params.append(filters["event_type"])
            if "user_id" in filters:
                query += " AND user_id = ?"
                params.append(filters["user_id"])
            if "start_time" in filters:
                query += " AND timestamp >= ?"
                params.append(filters["start_time"])
            if "end_time" in filters:
                query += " AND timestamp <= ?"
                params.append(filters["end_time"])
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "block_index": row[1],
                "event_type": row[2],
                "user_id": row[3],
                "action": row[4],
                "details": json.loads(row[5]),
                "timestamp": row[6],
                "signature": row[7]
            })
        
        conn.close()
        return logs
    
    def export_chain(self) -> List[Dict]:
        """Export entire blockchain"""
        return [block.to_dict() for block in self.chain]
    
    def get_chain_stats(self) -> Dict:
        """Get blockchain statistics"""
        return {
            "chain_length": len(self.chain),
            "pending_logs": len(self.pending_logs),
            "is_valid": self.validate_chain(),
            "latest_block_hash": self.chain[-1].hash if self.chain else None,
            "difficulty": self.difficulty
        }

# Audit event types
class AuditEventTypes:
    """Standard audit event types"""
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    API_CALL = "api_call"
    CONFIG_CHANGE = "config_change"
    SECURITY_ALERT = "security_alert"
    ERROR = "error"
    DEPLOYMENT = "deployment"
    BACKUP = "backup"
    RESTORE = "restore"
    AGENT_DEPLOY = "agent_deploy"
    AGENT_REMOVE = "agent_remove"

# Example usage
if __name__ == "__main__":
    # Initialize blockchain
    audit_chain = AuditBlockchain()
    
    # Log some events
    audit_chain.add_audit_log(
        event_type=AuditEventTypes.SYSTEM_START,
        user_id="system",
        action="System initialized",
        details={"version": "5.0.0", "mode": "production"}
    )
    
    audit_chain.add_audit_log(
        event_type=AuditEventTypes.USER_LOGIN,
        user_id="admin",
        action="User authenticated",
        details={"ip": "192.168.1.1", "method": "token"}
    )
    
    # Mine pending logs
    audit_chain.mine_pending_logs()
    
    # Validate chain
    print(f"Chain valid: {audit_chain.validate_chain()}")
    print(f"Chain stats: {audit_chain.get_chain_stats()}")
    
    # Query logs
    recent_logs = audit_chain.query_audit_logs({"event_type": AuditEventTypes.USER_LOGIN})
    print(f"Recent login events: {len(recent_logs)}")