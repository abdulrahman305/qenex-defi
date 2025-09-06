# Deploy QXC Token to Ethereum - REAL DEPLOYMENT

## Quick Method: Use Remix IDE (Browser-based)

### Step 1: Open Remix IDE
Go to: https://remix.ethereum.org

### Step 2: Create New File
1. Click "File" → "New File"
2. Name it: `QXCToken.sol`

### Step 3: Copy This Contract Code
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract QXCToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    uint256 public totalSupply = 1525300000000000000000; // 1525.30 QXC
    string public name = "QENEX Coin";
    string public symbol = "QXC";
    uint8 public decimals = 18;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    
    constructor() {
        balanceOf[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
    }
    
    function transfer(address to, uint256 amount) public returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }
    
    function approve(address spender, uint256 amount) public returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        allowance[from][msg.sender] -= amount;
        
        emit Transfer(from, to, amount);
        return true;
    }
}
```

### Step 4: Compile
1. Click on "Solidity Compiler" (left sidebar)
2. Click "Compile QXCToken.sol"

### Step 5: Deploy
1. Click on "Deploy & Run" (left sidebar)
2. Environment: Select "Injected Provider - MetaMask"
3. Make sure your MetaMask is connected
4. Click "Deploy"
5. Confirm transaction in MetaMask

### Step 6: Get Contract Address
After deployment:
1. Copy the contract address from Remix
2. This is your REAL QXC token contract address!

### Step 7: Add to MetaMask
1. In MetaMask, click "Import tokens"
2. Paste your new contract address
3. Symbol: QXC
4. Decimals: 18
5. Your 1,525.30 QXC will appear!

---

## Alternative: Deploy to Sepolia Testnet First (FREE)

### Get Free Test ETH:
1. Switch MetaMask to Sepolia network
2. Get free ETH from: https://sepoliafaucet.com
3. Deploy using same steps above
4. View on: https://sepolia.etherscan.io

---

## Your Wallet Details:
- **Your Address:** 0x44aB7...
- **QXC Balance:** 1,525.30 QXC
- **Private Key:** Already in your MetaMask

Once deployed, the contract address will be real and verifiable on Etherscan!