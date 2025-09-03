#!/bin/bash

echo "🚀 QXC Token Ecosystem Setup"
echo "============================"

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    echo "❌ Node.js version 16+ required"
    exit 1
fi

# Create necessary directories
mkdir -p deployments
mkdir -p server/abis
mkdir -p client/public
mkdir -p test
mkdir -p scripts

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Copy environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please update .env with your configuration"
fi

# Compile contracts
echo "🔨 Compiling contracts..."
npx hardhat compile

# Run tests
echo "🧪 Running tests..."
npm test

# Generate contract ABIs
echo "📄 Extracting ABIs..."
node -e "
const fs = require('fs');
const path = require('path');

const artifactsDir = './artifacts/contracts';
const abisDir = './server/abis';

if (!fs.existsSync(abisDir)) {
    fs.mkdirSync(abisDir, { recursive: true });
}

function extractABI(contractPath, contractName) {
    try {
        const artifact = JSON.parse(
            fs.readFileSync(
                path.join(artifactsDir, contractPath, contractName + '.sol', contractName + '.json'),
                'utf8'
            )
        );
        fs.writeFileSync(
            path.join(abisDir, contractName + '.json'),
            JSON.stringify(artifact.abi, null, 2)
        );
        console.log('✅ Extracted ABI for', contractName);
    } catch (error) {
        console.log('⚠️  Could not extract ABI for', contractName);
    }
}

// Extract ABIs for main contracts
extractABI('core', 'QXCToken');
extractABI('defi', 'QXCStaking');
extractABI('defi', 'QXCLaunchpad');
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env with your configuration"
echo "2. Deploy contracts: npm run deploy"
echo "3. Start server: npm start"
echo ""
echo "For development:"
echo "- Local blockchain: npx hardhat node"
echo "- Deploy locally: npx hardhat run scripts/deploy.js --network localhost"
echo "- Development server: npm run dev"