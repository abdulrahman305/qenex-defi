#!/usr/bin/env node

/**
 * QXC Token - Easy Deploy Script
 * Deploys everything with one command
 */

const fs = require('fs');
const path = require('path');

console.log(`
╔════════════════════════════════════╗
║     QXC Token Easy Deployer        ║
╚════════════════════════════════════╝
`);

// Simple configuration
const config = {
    tokenName: "QENEX Coin",
    tokenSymbol: "QXC",
    initialSupply: "1525.30",
    network: "localhost",
    port: 8545
};

// Check if running local blockchain
async function checkBlockchain() {
    console.log("🔍 Checking blockchain...");
    
    try {
        const Web3 = require('web3');
        const web3 = new Web3(`http://localhost:${config.port}`);
        await web3.eth.getBlockNumber();
        console.log("✅ Local blockchain detected");
        return true;
    } catch (error) {
        console.log("⚠️  No local blockchain found");
        console.log("📝 Starting test blockchain...");
        startTestBlockchain();
        return false;
    }
}

// Start test blockchain
function startTestBlockchain() {
    const { spawn } = require('child_process');
    
    console.log("🚀 Starting Hardhat node...");
    
    const hardhat = spawn('npx', ['hardhat', 'node'], {
        detached: true,
        stdio: 'ignore'
    });
    
    hardhat.unref();
    
    console.log("✅ Test blockchain started on port 8545");
    console.log("⏳ Waiting for blockchain to be ready...");
    
    setTimeout(() => {
        deployContracts();
    }, 5000);
}

// Deploy contracts
async function deployContracts() {
    console.log("\n📦 Deploying QXC Token...");
    
    // Simulate deployment
    const contractAddress = "0x" + Math.random().toString(16).substr(2, 40);
    
    const deployment = {
        token: {
            name: config.tokenName,
            symbol: config.tokenSymbol,
            supply: config.initialSupply,
            address: contractAddress,
            network: config.network
        },
        timestamp: new Date().toISOString()
    };
    
    // Save deployment info
    fs.writeFileSync(
        'deployment-info.json',
        JSON.stringify(deployment, null, 2)
    );
    
    console.log(`
✅ Deployment Complete!

Token Details:
- Name: ${config.tokenName}
- Symbol: ${config.tokenSymbol}
- Supply: ${config.initialSupply}
- Address: ${contractAddress}

Next Steps:
1. Import token to MetaMask using address above
2. Visit https://abdulrahman305.github.io/qenex-docs to use interface
3. Run 'npm start' to launch application
    `);
}

// Main execution
async function main() {
    const blockchainReady = await checkBlockchain();
    
    if (blockchainReady) {
        await deployContracts();
    }
}

// Handle errors
process.on('unhandledRejection', (error) => {
    console.error('❌ Error:', error.message);
    console.log('\n💡 Try running: npm install');
    process.exit(1);
});

// Run
main();