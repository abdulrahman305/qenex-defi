#!/bin/bash

# QXC Token - Universal Start Script
# Works from anywhere

echo "
╔════════════════════════════════════════╗
║        QXC Token Launcher              ║
╚════════════════════════════════════════╝
"

# Function to find and run QXC Token
start_qxc() {
    # Option 1: Check if we have qxc-token directory
    if [ -d "qxc-token" ] && [ -f "qxc-token/scripts/setup.sh" ]; then
        echo "✅ Starting from qxc-token directory..."
        cd qxc-token
        ./scripts/setup.sh
        return 0
    fi
    
    # Option 2: Check current directory for package.json
    if [ -f "package.json" ]; then
        echo "✅ Found project files..."
        if [ -f "server/index.js" ]; then
            npm start 2>/dev/null || node server/index.js
        elif [ -f "server.js" ]; then
            node server.js
        else
            npm start
        fi
        return 0
    fi
    
    # Option 3: Create a simple server right here
    echo "📦 Creating QXC Token app..."
    
    # Create minimal package.json
    cat > package.json << 'EOF'
{
  "name": "qxc-token",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.2"
  }
}
EOF
    
    # Create minimal server
    cat > server.js << 'EOF'
const http = require('http');
const PORT = 3000;

const server = http.createServer((req, res) => {
    res.writeHead(200, {'Content-Type': 'text/html'});
    res.end(`
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
                .card {
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 400px;
                    width: 90%;
                }
                h1 { color: #333; margin-bottom: 10px; }
                p { color: #666; margin-bottom: 30px; }
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
                    padding: 15px 40px;
                    font-size: 18px;
                    border-radius: 10px;
                    cursor: pointer;
                    width: 100%;
                    margin: 10px 0;
                    transition: all 0.3s;
                }
                button:hover {
                    background: #5a67d8;
                    transform: translateY(-2px);
                }
                .status {
                    margin-top: 20px;
                    padding: 10px;
                    background: #f0f9ff;
                    border-radius: 8px;
                    color: #1e40af;
                }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>💎 QXC Token</h1>
                <p>Decentralized Finance Made Simple</p>
                <div class="balance">0.00 QXC</div>
                <button onclick="connect()">Connect Wallet</button>
                <button onclick="getTokens()">Get Test Tokens</button>
                <div class="status">Ready to connect</div>
            </div>
            <script>
                function connect() {
                    if (typeof window.ethereum !== 'undefined') {
                        ethereum.request({ method: 'eth_requestAccounts' })
                            .then(() => {
                                document.querySelector('.status').textContent = 'Wallet Connected!';
                                document.querySelector('.status').style.background = '#d4edda';
                                document.querySelector('.status').style.color = '#155724';
                            })
                            .catch(() => {
                                alert('Connection cancelled');
                            });
                    } else {
                        if(confirm('MetaMask not found. Open download page?')) {
                            window.open('https://metamask.io/download/', '_blank');
                        }
                    }
                }
                
                function getTokens() {
                    const balance = (Math.random() * 1000 + 100).toFixed(2);
                    document.querySelector('.balance').textContent = balance + ' QXC';
                    document.querySelector('.status').textContent = 'Test tokens received!';
                    document.querySelector('.status').style.background = '#d4edda';
                    document.querySelector('.status').style.color = '#155724';
                }
            </script>
        </body>
        </html>
    `);
});

server.listen(PORT, () => {
    console.log(\`
╔════════════════════════════════════════╗
║                                        ║
║     ✅ QXC Token is running!          ║
║                                        ║
║     🌐 Open in browser:               ║
║     http://localhost:\${PORT}           ║
║                                        ║
║     Press Ctrl+C to stop              ║
║                                        ║
╚════════════════════════════════════════╝
    \`);
});
EOF
    
    # Run the server
    echo "🚀 Starting QXC Token..."
    node server.js
}

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found!"
    echo ""
    echo "Please install Node.js first:"
    echo "  Ubuntu/Debian: sudo apt-get install nodejs"
    echo "  MacOS: brew install node"
    echo "  Windows: Download from https://nodejs.org"
    echo ""
    echo "After installing, run this script again."
    exit 1
fi

# Start QXC Token
start_qxc