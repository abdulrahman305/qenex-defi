# 🚀 DEPLOY QXC TO ETHEREUM MAINNET

## IMMEDIATE DEPLOYMENT via Remix

### 1️⃣ Open Remix
Go to: **https://remix.ethereum.org**

### 2️⃣ Create Contract File
- Click **"contracts"** folder
- Create new file: **QXCToken.sol**
- Paste this code:

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

### 3️⃣ Compile
- Click **"Solidity Compiler"** tab (left side)
- Compiler version: **0.8.0+**
- Click **"Compile QXCToken.sol"**

### 4️⃣ Deploy to MAINNET
- Click **"Deploy & Run"** tab (left side)
- **ENVIRONMENT:** Select **"Injected Provider - MetaMask"**
- Make sure MetaMask is on **Ethereum Mainnet**
- Click **"Deploy"** button
- **CONFIRM** transaction in MetaMask (will cost ~0.01-0.02 ETH in gas)

### 5️⃣ Get Your Contract Address
- After deployment, copy the contract address
- This is your REAL QXC contract on mainnet!

### 6️⃣ Verify on Etherscan
1. Go to: https://etherscan.io/address/[YOUR-CONTRACT-ADDRESS]
2. Click **"Contract"** tab
3. Click **"Verify and Publish"**
4. Compiler Type: **Solidity (Single file)**
5. Compiler Version: **v0.8.0+**
6. License: **MIT**

### 7️⃣ Add to MetaMask
- Click **"Import tokens"** in MetaMask
- **Token Contract Address:** [Your deployed address]
- **Token Symbol:** QXC
- **Token Decimal:** 18
- Your **1,525.30 QXC** appears!

---

## 💰 DEPLOYMENT COST
- **Estimated Gas:** ~1,200,000 gas units
- **Cost in ETH:** ~0.01-0.02 ETH (depends on gas price)
- **Current Gas Price:** Check https://etherscan.io/gastracker

## ✅ AFTER DEPLOYMENT
Your QXC token will be:
- **Live on Ethereum mainnet**
- **Visible on Etherscan**
- **Tradeable on DEXs** (once liquidity added)
- **Real ERC-20 token**

---

## ⚡ QUICK DEPLOYMENT CHECKLIST
- [ ] Have ~0.02 ETH in wallet for gas
- [ ] MetaMask on Ethereum Mainnet
- [ ] Copy contract code to Remix
- [ ] Compile contract
- [ ] Deploy contract
- [ ] Save contract address
- [ ] Add to MetaMask
- [ ] Verify on Etherscan

Your balance of **1,525.30 QXC** will be immediately available after deployment!