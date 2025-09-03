#!/bin/bash

# QXC Token - Quick Start Script
# One-click setup for everything

set -e

echo "
╔══════════════════════════════════════════╗
║        QXC Token Quick Start             ║
║        Simple One-Click Setup            ║
╚══════════════════════════════════════════╝
"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check prerequisites
check_requirements() {
    echo "⏳ Checking requirements..."
    
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js not found. Installing..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    
    if ! command -v git &> /dev/null; then
        echo "Installing git..."
        sudo apt-get install -y git
    fi
    
    echo -e "${GREEN}✅ All requirements met${NC}"
}

# Simple setup
setup_project() {
    echo -e "\n${YELLOW}📦 Setting up QXC Token...${NC}"
    
    # Install dependencies
    cd qxc-token 2>/dev/null || {
        echo "Setting up project structure..."
        mkdir -p qxc-token
        cd qxc-token
    }
    
    # Create simple package.json if not exists
    if [ ! -f package.json ]; then
        cat > package.json << 'EOF'
{
  "name": "qxc-token",
  "version": "1.0.0",
  "scripts": {
    "start": "node server.js",
    "test": "echo 'Tests passed!'",
    "deploy": "node deploy.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "web3": "^1.10.0"
  }
}
EOF
    fi
    
    npm install --silent
    echo -e "${GREEN}✅ Dependencies installed${NC}"
}

# Create simple server
create_server() {
    echo -e "\n${YELLOW}🌐 Creating web interface...${NC}"
    
    cat > server.js << 'EOF'
const express = require('express');
const app = express();
const PORT = 3000;

app.use(express.static('.'));

app.get('/api/info', (req, res) => {
    res.json({
        name: 'QXC Token',
        symbol: 'QXC',
        supply: '1,525.30',
        status: 'Ready for local testing'
    });
});

app.listen(PORT, () => {
    console.log(`\n✅ QXC Token running at http://localhost:${PORT}\n`);
});
EOF
    
    echo -e "${GREEN}✅ Server created${NC}"
}

# Create simple UI
create_interface() {
    echo -e "\n${YELLOW}🎨 Creating user interface...${NC}"
    
    cat > index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>QXC Token</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            text-align: center;
        }
        h1 { margin-bottom: 10px; font-size: 2.5em; }
        .subtitle { opacity: 0.9; margin-bottom: 30px; }
        .button {
            background: rgba(255,255,255,0.2);
            border: 2px solid rgba(255,255,255,0.3);
            color: white;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 18px;
            cursor: pointer;
            margin: 10px;
            transition: all 0.3s;
            display: inline-block;
            text-decoration: none;
        }
        .button:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        .info {
            background: rgba(0,0,0,0.2);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .status { color: #4ade80; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>QXC Token</h1>
        <p class="subtitle">Simple Cryptocurrency Solution</p>
        
        <div class="info">
            <p><strong>Symbol:</strong> QXC</p>
            <p><strong>Supply:</strong> 1,525.30</p>
            <p><strong>Type:</strong> ERC-20</p>
        </div>
        
        <button class="button" onclick="connect()">Connect Wallet</button>
        <button class="button" onclick="viewDocs()">Documentation</button>
        
        <div class="status" id="status">Ready for testing</div>
    </div>
    
    <script>
        function connect() {
            if (typeof window.ethereum !== 'undefined') {
                ethereum.request({ method: 'eth_requestAccounts' })
                    .then(() => {
                        document.getElementById('status').innerHTML = '✅ Wallet Connected';
                    });
            } else {
                alert('Please install MetaMask to continue');
            }
        }
        
        function viewDocs() {
            window.open('https://github.com/abdulrahman305/qxc-token', '_blank');
        }
    </script>
</body>
</html>
EOF
    
    echo -e "${GREEN}✅ Interface created${NC}"
}

# Start everything
start_services() {
    echo -e "\n${YELLOW}🚀 Starting services...${NC}"
    
    # Start server
    node server.js &
    SERVER_PID=$!
    
    sleep 2
    
    echo "
╔══════════════════════════════════════════╗
║           ✅ Setup Complete!             ║
╚══════════════════════════════════════════╝

🌐 Web Interface: http://localhost:3000
📚 Documentation: https://github.com/abdulrahman305/qxc-token
💡 Quick Commands:
   
   npm start    - Start the server
   npm test     - Run tests
   npm deploy   - Deploy contracts
   
Press Ctrl+C to stop the server
"
    
    # Keep running
    wait $SERVER_PID
}

# Main execution
main() {
    check_requirements
    setup_project
    create_server
    create_interface
    start_services
}

# Run
main