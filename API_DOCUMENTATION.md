# QENEX OS API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Core APIs](#core-apis)
   - [System API](#system-api)
   - [Blockchain API](#blockchain-api)
   - [Wallet API](#wallet-api)
   - [Mining API](#mining-api)
   - [AI Model API](#ai-model-api)
   - [P2P Network API](#p2p-network-api)
4. [WebSocket Events](#websocket-events)
5. [Error Codes](#error-codes)
6. [Rate Limiting](#rate-limiting)
7. [Examples](#examples)

## Overview

The QENEX OS API provides programmatic access to all system functions including blockchain operations, wallet management, AI model interactions, and mining control.

**Base URL**: `http://localhost:8000/api`  
**Protocol**: HTTP/HTTPS, WebSocket  
**Format**: JSON

## Authentication

### API Key Authentication
```http
Authorization: Bearer YOUR_API_KEY
```

### Generate API Key
```bash
qenex api generate-key --name "My Application"
```

## Core APIs

### System API

#### Get System Status
```http
GET /api/system/status
```

**Response:**
```json
{
  "status": "running",
  "uptime": 3600,
  "version": "5.0.0",
  "kernel": {
    "version": "1.0.0",
    "boot_time": 1699123456,
    "system_calls": 1234567
  },
  "resources": {
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "disk_usage": 35.1,
    "network_io": {
      "bytes_sent": 1048576,
      "bytes_recv": 2097152
    }
  }
}
```

#### Restart System
```http
POST /api/system/restart
```

**Request:**
```json
{
  "component": "all",  // or "kernel", "mining", "ai"
  "force": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "System restart initiated"
}
```

### Blockchain API

#### Get Blockchain Info
```http
GET /api/blockchain/info
```

**Response:**
```json
{
  "height": 42,
  "total_supply": 2100.0,
  "max_supply": 21000000.0,
  "difficulty": "0000",
  "last_block": {
    "index": 42,
    "hash": "0000abc123...",
    "timestamp": 1699123456,
    "miner": "MINER_WALLET"
  }
}
```

#### Get Block by Height
```http
GET /api/blockchain/block/{height}
```

**Response:**
```json
{
  "index": 42,
  "timestamp": 1699123456,
  "transactions": [...],
  "previous_hash": "0000def456...",
  "hash": "0000abc123...",
  "nonce": 12345,
  "difficulty": "0000",
  "merkle_root": "789xyz...",
  "miner": "MINER_WALLET",
  "ai_improvements": {
    "mathematics": 0.023,
    "language": 0.015
  }
}
```

#### Submit Transaction
```http
POST /api/blockchain/transaction
```

**Request:**
```json
{
  "sender": "QXCabc123...",
  "recipient": "QXCdef456...",
  "amount": 10.5,
  "private_key": "...",  // For signing
  "metadata": {}
}
```

**Response:**
```json
{
  "tx_id": "xyz789...",
  "status": "pending",
  "signature": "sig123..."
}
```

#### Get Transaction
```http
GET /api/blockchain/transaction/{tx_id}
```

**Response:**
```json
{
  "tx_id": "xyz789...",
  "sender": "QXCabc123...",
  "recipient": "QXCdef456...",
  "amount": 10.5,
  "timestamp": 1699123456,
  "block_height": 42,
  "confirmations": 6,
  "status": "confirmed"
}
```

### Wallet API

#### Create Wallet
```http
POST /api/wallet/create
```

**Request:**
```json
{
  "wallet_id": "my_wallet",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "wallet_id": "my_wallet",
  "address": "QXCabc123def456...",
  "public_key": "-----BEGIN PUBLIC KEY-----..."
}
```

#### Get Wallet Info
```http
GET /api/wallet/{wallet_id}
```

**Response:**
```json
{
  "wallet_id": "my_wallet",
  "address": "QXCabc123def456...",
  "balance": 100.5,
  "locked": false,
  "transaction_count": 15
}
```

#### Get Balance
```http
GET /api/wallet/{wallet_id}/balance
```

**Response:**
```json
{
  "confirmed": 100.5,
  "pending": 10.0,
  "total": 110.5
}
```

#### Send Transaction
```http
POST /api/wallet/{wallet_id}/send
```

**Request:**
```json
{
  "recipient": "QXCdef456...",
  "amount": 25.0,
  "password": "WalletPassword",
  "message": "Payment for services"
}
```

**Response:**
```json
{
  "tx_id": "abc123...",
  "amount": 25.0,
  "fee": 0.01,
  "total": 25.01,
  "status": "broadcast"
}
```

#### Lock/Unlock Wallet
```http
POST /api/wallet/{wallet_id}/lock
POST /api/wallet/{wallet_id}/unlock
```

**Unlock Request:**
```json
{
  "password": "WalletPassword"
}
```

### Mining API

#### Get Mining Status
```http
GET /api/mining/status
```

**Response:**
```json
{
  "mining": true,
  "hashrate": 1234567,
  "blocks_mined": 5,
  "total_rewards": 250.0,
  "current_difficulty": "0000",
  "next_halving": 209958
}
```

#### Start/Stop Mining
```http
POST /api/mining/start
POST /api/mining/stop
```

**Start Request:**
```json
{
  "wallet": "MINER_WALLET",
  "threads": 4
}
```

#### Get Mining Statistics
```http
GET /api/mining/stats
```

**Response:**
```json
{
  "total_blocks": 42,
  "total_rewards": 2100.0,
  "average_block_time": 31.2,
  "network_hashrate": 987654321,
  "mining_revenue_24h": 50.0
}
```

### AI Model API

#### Get Model Info
```http
GET /api/ai/model
```

**Response:**
```json
{
  "version": 42,
  "capabilities": {
    "mathematics": {
      "algebra": 0.72,
      "calculus": 0.68,
      "statistics": 0.70
    },
    "language": {
      "syntax": 0.75,
      "semantics": 0.71,
      "generation": 0.69
    },
    "code": {
      "correctness": 0.73,
      "efficiency": 0.67,
      "readability": 0.70
    }
  },
  "total_improvements": 125,
  "last_update": 1699123456
}
```

#### Evaluate Performance
```http
POST /api/ai/evaluate
```

**Request:**
```json
{
  "test_suite": "standard",  // or "mathematics", "language", "code"
  "iterations": 10
}
```

**Response:**
```json
{
  "scores": {
    "mathematics": 0.72,
    "language": 0.71,
    "code": 0.70
  },
  "improvement": 0.023,
  "mining_triggered": true
}
```

#### Train Model
```http
POST /api/ai/train
```

**Request:**
```json
{
  "data": {...},
  "epochs": 100,
  "learning_rate": 0.001
}
```

### P2P Network API

#### Get Peer List
```http
GET /api/network/peers
```

**Response:**
```json
{
  "peers": [
    {
      "node_id": "node_1234",
      "address": "192.168.1.100:8333",
      "version": "1.0.0",
      "latency": 0.023,
      "last_seen": 1699123456
    }
  ],
  "total": 15,
  "active": 12
}
```

#### Add Peer
```http
POST /api/network/peer
```

**Request:**
```json
{
  "host": "peer.qenex.ai",
  "port": 8333
}
```

#### Broadcast Message
```http
POST /api/network/broadcast
```

**Request:**
```json
{
  "type": "block",  // or "transaction"
  "data": {...}
}
```

## WebSocket Events

Connect to `ws://localhost:8000/ws` for real-time updates.

### Subscribe to Events
```json
{
  "action": "subscribe",
  "events": ["blocks", "transactions", "mining", "system"]
}
```

### Event Types

#### New Block
```json
{
  "event": "new_block",
  "data": {
    "index": 43,
    "hash": "0000abc...",
    "miner": "MINER_WALLET",
    "reward": 50.0
  }
}
```

#### New Transaction
```json
{
  "event": "new_transaction",
  "data": {
    "tx_id": "abc123...",
    "amount": 10.5,
    "status": "pending"
  }
}
```

#### Mining Update
```json
{
  "event": "mining_update",
  "data": {
    "hashrate": 1234567,
    "shares_found": 10,
    "blocks_found": 1
  }
}
```

#### System Metrics
```json
{
  "event": "metrics",
  "data": {
    "cpu": 45.2,
    "memory": 62.8,
    "network": {...}
  }
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid API key |
| 403 | Forbidden - Access denied |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Error Response Format
```json
{
  "error": {
    "code": 400,
    "message": "Invalid wallet address",
    "details": "Address must start with 'QXC'"
  }
}
```

## Rate Limiting

- **Default**: 100 requests per minute
- **Authenticated**: 1000 requests per minute
- **Mining operations**: 10 requests per minute

Headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699123456
```

## Examples

### Python Example
```python
import requests

# Configuration
API_URL = "http://localhost:8000/api"
API_KEY = "your_api_key"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Get blockchain info
response = requests.get(f"{API_URL}/blockchain/info", headers=headers)
data = response.json()
print(f"Blockchain height: {data['height']}")

# Create wallet
wallet_data = {
    "wallet_id": "my_wallet",
    "password": "SecurePassword123!"
}
response = requests.post(f"{API_URL}/wallet/create", 
                         json=wallet_data, headers=headers)
wallet = response.json()
print(f"Wallet address: {wallet['address']}")

# Send transaction
tx_data = {
    "recipient": "QXCdef456...",
    "amount": 10.0,
    "password": "SecurePassword123!"
}
response = requests.post(f"{API_URL}/wallet/my_wallet/send",
                         json=tx_data, headers=headers)
tx = response.json()
print(f"Transaction ID: {tx['tx_id']}")
```

### JavaScript Example
```javascript
const API_URL = 'http://localhost:8000/api';
const API_KEY = 'your_api_key';

const headers = {
  'Authorization': `Bearer ${API_KEY}`,
  'Content-Type': 'application/json'
};

// Get system status
fetch(`${API_URL}/system/status`, { headers })
  .then(res => res.json())
  .then(data => console.log('System status:', data));

// WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    events: ['blocks', 'transactions']
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.event, data.data);
};
```

### cURL Examples
```bash
# Get blockchain info
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/api/blockchain/info

# Create wallet
curl -X POST \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"wallet_id":"test","password":"Pass123!"}' \
     http://localhost:8000/api/wallet/create

# Start mining
curl -X POST \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"wallet":"MINER_WALLET","threads":4}' \
     http://localhost:8000/api/mining/start
```

## SDKs and Libraries

Official SDKs available for:
- Python: `pip install qenex-sdk`
- JavaScript/Node.js: `npm install qenex-sdk`
- Go: `go get github.com/qenex/qenex-go`
- Rust: `cargo add qenex`

## Support

- Documentation: https://docs.qenex.ai
- GitHub: https://github.com/abdulrahman305/qenex-os
- API Status: https://status.qenex.ai

---

*API Version: 1.0.0 | Last Updated: November 2024*