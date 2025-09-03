# 🚀 QXC Token - Quick Start Guide

## Start in 30 Seconds

### Option 1: One-Click Start (Easiest)
```bash
bash <(curl -s https://raw.githubusercontent.com/abdulrahman305/qenex-os/main/quick-start.sh)
```

### Option 2: Three Commands
```bash
git clone https://github.com/abdulrahman305/qxc-token.git
cd qxc-token
npm start
```

**That's it!** Open http://localhost:3000

---

## 📱 Connect Your Wallet

1. **Install MetaMask**
   - [Download MetaMask](https://metamask.io/download/)
   - Create or import wallet
   - Switch to "Localhost 8545" network

2. **Get Test QXC**
   - Open http://localhost:3000
   - Click "Connect Wallet"
   - Click "Get Test Tokens"
   - You'll receive 100 QXC

---

## 🎮 What Can You Do?

### Send Tokens
- Click "Send"
- Enter address and amount
- Confirm in MetaMask

### Stake for Rewards
- Click "Stake"
- Enter amount
- Earn 15% APY

### Swap Tokens
- Click "Swap"
- Select tokens
- Execute trade

---

## 🛠️ For Developers

### Deploy Your Own
```javascript
// Deploy with one line
npx hardhat run scripts/deploy.js
```

### Customize Token
Edit `contracts/QXCComplete.sol`:
```solidity
string public name = "Your Token";
string public symbol = "YOUR";
uint256 public totalSupply = 1000000 ether;
```

### Build Frontend
```bash
npm run build
npm run serve
```

---

## 💡 Common Issues & Solutions

| Problem | Solution |
|---------|----------|
| MetaMask not connecting | Switch to Localhost 8545 network |
| No balance showing | Click "Get Test Tokens" |
| Transaction failed | Check you have enough gas |
| Port 3000 in use | Change port: `PORT=3001 npm start` |

---

## 📚 Learn More

- **Video Tutorial**: [YouTube](https://youtube.com/qxc-tutorial)
- **Documentation**: [GitHub Wiki](https://github.com/abdulrahman305/qxc-token/wiki)
- **Examples**: [Code Examples](https://github.com/abdulrahman305/qxc-token/examples)

---

## 🆘 Get Help

- **Discord**: [Join Community](https://discord.gg/qxc)
- **Telegram**: [@qxctoken](https://t.me/qxctoken)
- **Email**: support@qenex.ai

---

## ⚡ Advanced Features

Once you're comfortable with basics:

- **Metaverse**: Virtual world with NFTs
- **AI Trading**: Automated strategies
- **Governance**: Vote on proposals
- **Bridge**: Cross-chain transfers
- **Insurance**: DeFi protection

---

**Remember**: This is for testing only. Never use real funds with test software.

---

Made with ❤️ by QENEX Team