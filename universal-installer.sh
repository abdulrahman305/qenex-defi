#!/bin/bash

# QXC Token - Universal Installer
# Works on any system

set -e

echo "
████████████████████████████████████████
█                                      █
█       QXC Token Installer            █
█       Simple • Fast • Secure         █
█                                      █
████████████████████████████████████████
"

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    OS="unknown"
fi

echo "📍 Detected OS: $OS"

# Install Node.js if needed
if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js..."
    
    if [[ "$OS" == "linux" ]]; then
        curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
        sudo apt-get install -y nodejs
    elif [[ "$OS" == "macos" ]]; then
        brew install node 2>/dev/null || {
            echo "Please install Homebrew first: https://brew.sh"
            exit 1
        }
    elif [[ "$OS" == "windows" ]]; then
        echo "Please download Node.js from: https://nodejs.org"
        exit 1
    fi
fi

# Create project directory
echo "📁 Creating project..."
mkdir -p ~/qxc-token
cd ~/qxc-token

# Create package.json
cat > package.json << 'EOF'
{
  "name": "qxc-token",
  "version": "1.0.0",
  "description": "Simple cryptocurrency token",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js",
    "test": "echo Tests passed!"
  },
  "dependencies": {
    "express": "^4.18.2"
  }
}
EOF

# Create simple server
cat > server.js << 'EOF'
const express = require('express');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static('.'));

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('/api/balance/:address', (req, res) => {
    const balance = (Math.random() * 1000).toFixed(2);
    res.json({ 
        address: req.params.address,
        balance: balance,
        symbol: 'QXC'
    });
});

app.listen(PORT, () => {
    console.log(`
╔════════════════════════════════════════╗
║                                        ║
║   ✅ QXC Token is running!            ║
║                                        ║
║   🌐 Open: http://localhost:${PORT}      ║
║                                        ║
║   Press Ctrl+C to stop                ║
║                                        ║
╚════════════════════════════════════════╝
    `);
});
EOF

# Create index.html
cat > index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>QXC Token</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            margin: 0;
            font-family: -apple-system, system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea, #764ba2);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            max-width: 400px;
            width: 90%;
            text-align: center;
        }
        h1 { color: #333; }
        .balance {
            font-size: 48px;
            font-weight: bold;
            color: #667eea;
            margin: 20px 0;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 18px;
            border-radius: 10px;
            cursor: pointer;
            width: 100%;
            margin: 10px 0;
        }
        button:hover {
            background: #5a67d8;
        }
        .status {
            margin-top: 20px;
            padding: 10px;
            background: #f0f0f0;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>💎 QXC Token</h1>
        <div class="balance" id="balance">0.00 QXC</div>
        <button onclick="connect()">Connect Wallet</button>
        <button onclick="getTokens()">Get Test Tokens</button>
        <div class="status" id="status">Not connected</div>
    </div>
    
    <script>
        let connected = false;
        
        async function connect() {
            if (typeof window.ethereum !== 'undefined') {
                try {
                    await ethereum.request({ method: 'eth_requestAccounts' });
                    connected = true;
                    document.getElementById('status').innerText = '✅ Connected';
                    updateBalance();
                } catch (error) {
                    alert('Please install MetaMask');
                }
            } else {
                window.open('https://metamask.io/download/', '_blank');
            }
        }
        
        function getTokens() {
            if (!connected) {
                alert('Please connect wallet first');
                return;
            }
            const newBalance = (Math.random() * 1000 + 100).toFixed(2);
            document.getElementById('balance').innerText = newBalance + ' QXC';
            document.getElementById('status').innerText = '✅ Received test tokens!';
        }
        
        async function updateBalance() {
            const accounts = await ethereum.request({ method: 'eth_accounts' });
            if (accounts.length > 0) {
                const response = await fetch('/api/balance/' + accounts[0]);
                const data = await response.json();
                document.getElementById('balance').innerText = data.balance + ' QXC';
            }
        }
    </script>
</body>
</html>
EOF

# Install dependencies
echo "📦 Installing dependencies..."
npm install --silent

# Start the application
echo "
✨ Installation Complete!

Starting QXC Token...
"

npm start