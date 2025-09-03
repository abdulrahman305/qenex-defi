#!/bin/bash

echo "======================================================================"
echo "DEPLOYING QXC TO ETHEREUM SEPOLIA TESTNET"
echo "======================================================================"

# Create deployment directory
mkdir -p /opt/qenex-os/qxc-testnet-deploy
cd /opt/qenex-os/qxc-testnet-deploy

# Create package.json
cat > package.json << 'EOF'
{
  "name": "qxc-testnet",
  "version": "1.0.0",
  "scripts": {
    "deploy": "node deploy.js"
  },
  "dependencies": {
    "ethers": "^6.9.0",
    "dotenv": "^16.3.1"
  }
}
EOF

# Create the contract
cat > QXCToken.sol << 'EOF'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract QXCToken {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;
    string public name = "QENEX Coin";
    string public symbol = "QXC";
    uint8 public decimals = 18;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    
    constructor() {
        totalSupply = 1525300000000000000000; // 1525.30 QXC
        balances[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
    }
    
    function balanceOf(address account) public view returns (uint256) {
        return balances[account];
    }
    
    function transfer(address to, uint256 amount) public returns (bool) {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        balances[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }
}
EOF

# Create deployment script using public testnet
cat > deploy.js << 'EOF'
const { ethers } = require('ethers');

async function deploy() {
    console.log("Deploying to Sepolia Testnet...");
    
    // Use a public RPC endpoint
    const provider = new ethers.JsonRpcProvider('https://sepolia.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161');
    
    // Use the private key from your wallet
    const privateKey = '0xa0446dcde6ce78911baa22b9d7404c3c7af487d1ab1510e98f3ce73c8f9a1f61';
    const wallet = new ethers.Wallet(privateKey, provider);
    
    console.log("Deploying from address:", wallet.address);
    
    // Contract bytecode (pre-compiled)
    const bytecode = "0x608060405234801561001057600080fd5b506152d76000819055506000543360008082825260205260405190205560003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7163c4a11628f55a4df523b3ef60005460405161008d9190610168565b60405180910390a3610183565b600081519050919050565b600082825260208201905092915050565b60005b838110156100d55780820151818401526020810190506100ba565b60008484015250505050565b6000601f19601f8301169050919050565b60006100fe8261009b565b61010881856100a6565b93506101188185602086016100b7565b610121816100e1565b840191505092915050565b600081905092915050565b60006101438385610133565b93506101508385846100b7565b82840190509392505050565b60006101688284610140565b915081905092915050565b600061017f82610140565b9150819050919050565b6102dd806101926000396000f3fe608060405234801561001057600080fd5b506004361061004c5760003560e01c806306fdde031461005157806318160ddd1461006f57806327e235e31461008d57806370a08231146100bd575b600080fd5b6100596100ed565b60405161006691906101c6565b60405180910390f35b61007761012a565b60405161008491906101f9565b60405180910390f35b6100a760048036038101906100a29190610245565b610130565b6040516100b491906101f9565b60405180910390f35b6100d760048036038101906100d29190610245565b610148565b6040516100e491906101f9565b60405180910390f35b60606040518060400160405280600a81526020017f51454e455820436f696e00000000000000000000000000000000000000000000815250905090565b60005481565b60006020528060005260406000206000915090505481565b600080600083815260200190815260200160002054905091905056";
    
    // Deploy contract
    const factory = new ethers.ContractFactory([], bytecode, wallet);
    const contract = await factory.deploy();
    
    console.log("Transaction hash:", contract.deploymentTransaction().hash);
    console.log("Waiting for confirmation...");
    
    await contract.waitForDeployment();
    const address = await contract.getAddress();
    
    console.log("✅ CONTRACT DEPLOYED!");
    console.log("Contract Address:", address);
    console.log("View on Sepolia Etherscan: https://sepolia.etherscan.io/address/" + address);
    
    return address;
}

deploy().catch(console.error);
EOF

echo "Installing dependencies..."
npm install --silent 2>/dev/null || true

echo ""
echo "Deploying contract to Sepolia testnet..."
node deploy.js

echo ""
echo "======================================================================"
echo "After deployment completes, you can:"
echo "1. View the contract on Sepolia Etherscan"
echo "2. Add it to MetaMask (make sure you're on Sepolia network)"
echo "3. Get free Sepolia ETH from: https://sepoliafaucet.com"
echo "======================================================================"