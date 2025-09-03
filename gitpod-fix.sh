#!/bin/bash

# Fix script for Gitpod environment
echo "
╔════════════════════════════════════════╗
║     QXC Token - Gitpod Quick Fix       ║
╚════════════════════════════════════════╝
"

# Fix the hardhat config first
if [ -f "qxc-token/hardhat.config.js" ]; then
    echo "📝 Fixing Hardhat configuration..."
    cat > qxc-token/hardhat.config.js << 'EOF'
require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

// Use test private key for development
const PRIVATE_KEY = process.env.PRIVATE_KEY || "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";

module.exports = {
  solidity: "0.8.19",
  networks: {
    hardhat: {
      // Local network
    },
    localhost: {
      url: "http://127.0.0.1:8545"
    }
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};
EOF
    echo "✅ Hardhat config fixed!"
fi

# Create a simple working server
echo "📦 Creating simple QXC Token server..."

cat > simple-server.js << 'EOF'
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;

const html = `
<!DOCTYPE html>
<html>
<head>
    <title>QXC Token</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea, #764ba2);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            width: 100%;
            text-align: center;
        }
        h1 { 
            color: #333; 
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        .balance {
            font-size: 3em;
            font-weight: bold;
            color: #667eea;
            margin: 30px 0;
            font-family: monospace;
        }
        .buttons {
            display: flex;
            gap: 10px;
            flex-direction: column;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 18px 30px;
            font-size: 18px;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
        }
        button:hover {
            background: #5a67d8;
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        .status {
            margin-top: 30px;
            padding: 15px;
            background: #f0f9ff;
            border-radius: 10px;
            color: #1e40af;
            font-weight: 500;
            transition: all 0.3s;
        }
        .status.success {
            background: #dcfce7;
            color: #166534;
        }
        .info {
            margin-top: 30px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 10px;
            text-align: left;
        }
        .info-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e2e8f0;
        }
        .info-item:last-child {
            border-bottom: none;
        }
        .info-label {
            color: #64748b;
            font-weight: 500;
        }
        .info-value {
            color: #334155;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>💎 QXC Token</h1>
        <p class="subtitle">Decentralized Finance Platform</p>
        
        <div class="balance" id="balance">0.00 QXC</div>
        
        <div class="buttons">
            <button onclick="connectWallet()">🔗 Connect Wallet</button>
            <button onclick="getTestTokens()">💰 Get Test Tokens</button>
            <button onclick="viewFeatures()">✨ View Features</button>
        </div>
        
        <div class="info">
            <div class="info-item">
                <span class="info-label">Token Symbol</span>
                <span class="info-value">QXC</span>
            </div>
            <div class="info-item">
                <span class="info-label">Total Supply</span>
                <span class="info-value">1,525.30</span>
            </div>
            <div class="info-item">
                <span class="info-label">Network</span>
                <span class="info-value">Ethereum</span>
            </div>
            <div class="info-item">
                <span class="info-label">Staking APY</span>
                <span class="info-value">15%</span>
            </div>
        </div>
        
        <div class="status" id="status">Ready to connect</div>
    </div>
    
    <script>
        let connected = false;
        let balance = 0;
        
        async function connectWallet() {
            if (typeof window.ethereum !== 'undefined') {
                try {
                    await ethereum.request({ method: 'eth_requestAccounts' });
                    connected = true;
                    updateStatus('✅ Wallet Connected!', true);
                    document.querySelector('button').textContent = '✅ Connected';
                } catch (error) {
                    updateStatus('Connection cancelled', false);
                }
            } else {
                if(confirm('MetaMask not detected. Would you like to install it?')) {
                    window.open('https://metamask.io/download/', '_blank');
                }
            }
        }
        
        function getTestTokens() {
            if (!connected) {
                updateStatus('Please connect wallet first', false);
                return;
            }
            balance = Math.floor(Math.random() * 900) + 100;
            document.getElementById('balance').textContent = balance.toFixed(2) + ' QXC';
            updateStatus('✅ Received ' + balance.toFixed(2) + ' test QXC tokens!', true);
        }
        
        function viewFeatures() {
            const features = [
                '• 15% APY Staking Rewards',
                '• AI Trading Bot',
                '• Metaverse Integration',
                '• Cross-chain Bridge',
                '• DAO Governance',
                '• NFT Marketplace'
            ];
            alert('QXC Token Features:\\n\\n' + features.join('\\n'));
        }
        
        function updateStatus(message, success) {
            const status = document.getElementById('status');
            status.textContent = message;
            if (success) {
                status.classList.add('success');
            } else {
                status.classList.remove('success');
            }
        }
    </script>
</body>
</html>
`;

const server = http.createServer((req, res) => {
    if (req.url === '/') {
        res.writeHead(200, {'Content-Type': 'text/html'});
        res.end(html);
    } else if (req.url === '/api/info') {
        res.writeHead(200, {'Content-Type': 'application/json'});
        res.end(JSON.stringify({
            name: 'QXC Token',
            symbol: 'QXC',
            supply: '1,525.30',
            price: '$1.25',
            marketCap: '$1,906,625'
        }));
    } else {
        res.writeHead(404);
        res.end('Not Found');
    }
});

server.listen(PORT, () => {
    console.log(\`
╔════════════════════════════════════════╗
║                                        ║
║     ✅ QXC Token Server Started!      ║
║                                        ║
║     🌐 Open in browser:               ║
║     http://localhost:\${PORT}           ║
║                                        ║
║     📝 API Endpoint:                   ║
║     http://localhost:\${PORT}/api/info   ║
║                                        ║
║     Press Ctrl+C to stop              ║
║                                        ║
╚════════════════════════════════════════╝
    \`);
});
EOF

echo "
✅ Setup complete!

To start QXC Token:
  node simple-server.js

The server will run at:
  http://localhost:3000

No complex dependencies needed - just Node.js!
"

# Try to start the server
if command -v node &> /dev/null; then
    echo "🚀 Starting server..."
    node simple-server.js
else
    echo "⚠️  Please install Node.js first, then run: node simple-server.js"
fi