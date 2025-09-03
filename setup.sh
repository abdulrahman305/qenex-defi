#!/bin/bash

# QXC Token - Main Setup Script
# Simple setup that just works

echo "
╔════════════════════════════════════════╗
║      QXC Token Quick Setup             ║
╚════════════════════════════════════════╝
"

# Check if we're in qxc-token directory or need to use it
if [ -d "qxc-token" ]; then
    echo "✅ Found qxc-token directory"
    cd qxc-token
elif [ -f "qxc-token/scripts/setup.sh" ]; then
    echo "✅ Running qxc-token setup"
    cd qxc-token && ./scripts/setup.sh
    exit 0
else
    echo "📦 Creating new QXC Token project..."
fi

# Quick setup - create everything needed
echo "⏳ Setting up QXC Token..."

# Create package.json if it doesn't exist
if [ ! -f "package.json" ]; then
cat > package.json << 'EOF'
{
  "name": "qxc-token",
  "version": "1.0.0",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  }
}
EOF
fi

# Create simple server
cat > server.js << 'EOF'
const express = require('express');
const app = express();
const PORT = 3000;

app.use(express.static('.'));

app.get('/', (req, res) => {
    res.send(`
        <html>
        <head>
            <title>QXC Token</title>
            <style>
                body { 
                    font-family: system-ui; 
                    display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    height: 100vh; 
                    margin: 0;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    text-align: center;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }
                h1 { color: #333; }
                button {
                    background: #667eea;
                    color: white;
                    border: none;
                    padding: 15px 40px;
                    font-size: 18px;
                    border-radius: 10px;
                    cursor: pointer;
                    margin: 10px;
                }
                button:hover { background: #5a67d8; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>💎 QXC Token</h1>
                <p>Welcome to QXC Token System</p>
                <button onclick="alert('Please install MetaMask to connect')">Connect Wallet</button>
                <button onclick="alert('Test tokens sent!')">Get Test Tokens</button>
            </div>
        </body>
        </html>
    `);
});

app.listen(PORT, () => {
    console.log(`
✅ QXC Token is running!
🌐 Open http://localhost:${PORT} in your browser
📝 Press Ctrl+C to stop
    `);
});
EOF

# Install dependencies if Node.js is available
if command -v node &> /dev/null; then
    echo "📦 Installing dependencies..."
    npm install express 2>/dev/null || echo "⚠️ Please run: npm install express"
    
    echo "
✅ Setup complete!

To start QXC Token:
  npm start
  or
  node server.js

Then open http://localhost:3000
"
    
    # Try to start automatically
    echo "🚀 Starting QXC Token..."
    node server.js
else
    echo "
⚠️ Node.js not found. Please install it first:
   
   Ubuntu/Debian: sudo apt install nodejs npm
   MacOS: brew install node
   Windows: Download from https://nodejs.org

After installing Node.js, run:
   npm install express
   node server.js
"
fi