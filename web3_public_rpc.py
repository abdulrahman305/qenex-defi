#!/usr/bin/env python3
"""
Public Web3 RPC Endpoint for QXC
Accessible via HTTPS at qenex.ai
"""

import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl

class QXCPublicRPC(BaseHTTPRequestHandler):
    """Public RPC endpoint handler"""
    
    def do_POST(self):
        # Handle CORS
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request = json.loads(post_data.decode('utf-8'))
            
            # Process RPC request
            response = self.process_rpc(request)
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": 1
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests for RPC info"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        info = {
            "network": "QENEX Network",
            "chainId": 942857,  # Custom QENEX chain ID
            "rpcVersion": "2.0",
            "methods": [
                "eth_chainId",
                "eth_accounts", 
                "eth_getBalance",
                "eth_blockNumber",
                "qxc_getMiningOperations",
                "qxc_getCurrentBalance"
            ]
        }
        self.wfile.write(json.dumps(info).encode('utf-8'))
    
    def process_rpc(self, request):
        """Process JSON-RPC request"""
        method = request.get('method')
        params = request.get('params', [])
        req_id = request.get('id', 1)
        
        # Get result based on method
        result = None
        
        if method == "eth_chainId":
            result = "0xe6b09"  # 942857 in hex
            
        elif method == "eth_blockNumber":
            # Get latest block from database
            result = self.get_latest_block()
            
        elif method == "eth_accounts":
            result = ["0x00b926807c4585bab1faed84dfb54725abc37318"]
            
        elif method == "eth_getBalance":
            result = self.get_balance(params[0] if params else None)
            
        elif method == "qxc_getMiningOperations":
            result = self.get_mining_operations(params[0] if params else 20)
            
        elif method == "qxc_getCurrentBalance":
            result = self.get_current_balance()
            
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": "Method not found"},
                "id": req_id
            }
        
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": req_id
        }
    
    def get_latest_block(self):
        """Get latest block number"""
        try:
            db_path = Path('/opt/qenex-os/mining_operations.db')
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute('SELECT MAX(block_number) FROM mining_operations')
                result = cursor.fetchone()
                conn.close()
                if result and result[0]:
                    return hex(result[0])
        except:
            pass
        return "0x609"  # Default 1545
    
    def get_balance(self, address):
        """Get balance for address"""
        try:
            db_path = Path('/opt/qenex-os/mining_operations.db')
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT SUM(amount) FROM mining_operations
                    WHERE status = 'success'
                ''')
                result = cursor.fetchone()
                conn.close()
                if result and result[0]:
                    # Convert to Wei
                    balance_wei = int(result[0] * 10**18)
                    return hex(balance_wei)
        except:
            pass
        return "0x0"
    
    def get_current_balance(self):
        """Get current QXC balance"""
        try:
            db_path = Path('/opt/qenex-os/mining_operations.db')
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT SUM(amount) FROM mining_operations
                    WHERE status = 'success'
                ''')
                result = cursor.fetchone()
                conn.close()
                if result and result[0]:
                    return {"balance": result[0], "symbol": "QXC"}
        except:
            pass
        return {"balance": 0, "symbol": "QXC"}
    
    def get_mining_operations(self, limit):
        """Get recent mining operations"""
        operations = []
        try:
            db_path = Path('/opt/qenex-os/mining_operations.db')
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT transaction_hash, wallet_address, amount, 
                           improvement_percentage, category, timestamp, 
                           block_number
                    FROM mining_operations
                    WHERE status = 'success'
                    ORDER BY block_number DESC
                    LIMIT ?
                ''', (limit,))
                
                for row in cursor.fetchall():
                    operations.append({
                        "txHash": row[0] if row[0] else "",
                        "wallet": row[1],
                        "amount": row[2],
                        "improvement": row[3],
                        "category": row[4],
                        "timestamp": row[5],
                        "block": row[6]
                    })
                conn.close()
        except:
            pass
        return operations
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def create_rpc_config():
    """Create nginx configuration for RPC endpoint"""
    nginx_config = """
# QXC Web3 RPC Endpoint
location /rpc {
    proxy_pass http://localhost:8546;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    
    # CORS headers
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Content-Type' always;
    
    if ($request_method = 'OPTIONS') {
        return 204;
    }
}
"""
    
    config_path = Path('/etc/nginx/sites-available/qenex-rpc')
    config_path.write_text(nginx_config)
    
    print("✅ Nginx RPC configuration created")
    return config_path

def start_public_rpc():
    """Start the public RPC server"""
    port = 8546
    server = HTTPServer(('0.0.0.0', port), QXCPublicRPC)
    
    print(f"🌐 Public Web3 RPC Server starting on port {port}")
    print(f"📡 Accessible at: https://abdulrahman305.github.io/qenex-docs)
    print(f"🔗 Chain ID: 1337 | Network: QENEX")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down RPC server...")
        server.shutdown()

if __name__ == "__main__":
    print("🚀 QXC Public Web3 RPC Endpoint")
    print("=" * 50)
    
    # Create nginx config
    create_rpc_config()
    
    # Start server
    start_public_rpc()