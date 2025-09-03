# QXC Token - Development Project

## ⚠️ PROJECT STATUS: DEVELOPMENT/TESTING ONLY

**CRITICAL NOTICE: This project is NOT deployed to mainnet and should NOT be used with real funds.**

## What This Actually Is

QXC Token is an **educational cryptocurrency project** for learning blockchain development. It includes example implementations of various DeFi concepts but is **not production-ready**.

## Current State

### ✅ What Works
- Basic ERC-20 token contract (local testing only)
- Example staking contract (needs funding mechanism)
- Simple web interface for demonstration
- Local development environment setup

### ❌ What Doesn't Work
- **NOT deployed to any blockchain**
- No actual AI integration (conceptual only)
- Staking rewards need manual funding
- Many features are incomplete stubs

## Security Status

### Fixed Issues
- ✅ Added max supply enforcement
- ✅ Implemented reentrancy guards
- ✅ Added proper access controls
- ✅ Removed hardcoded private keys

### Remaining Issues
- ⚠️ Contracts not audited
- ⚠️ No multi-signature wallets
- ⚠️ Centralized control structure
- ⚠️ Missing comprehensive tests

## Installation (Development Only)

### Prerequisites
- Node.js 16+
- Git
- MetaMask (for testing)

### Quick Start

```bash
# Clone repository
git clone https://github.com/abdulrahman305/qenex-os.git
cd qenex-os

# For simple demo
node simple-server.js

# For full development
cd qxc-token
npm install
npx hardhat node  # Start local blockchain
npx hardhat compile  # Compile contracts
```

## Testing Instructions

### Local Testing Only
1. Start local blockchain: `npx hardhat node`
2. Deploy to local: `npx hardhat run scripts/deploy.js --network localhost`
3. Use test accounts provided by Hardhat
4. **NEVER use real private keys**

## Technical Specifications

### Token Details
- Name: QENEX Coin (QXC)
- Type: ERC-20
- Max Supply: 21,000,000 (enforced in fixed version)
- Initial Supply: 1,525.30

### Smart Contracts
- `FIXED_QXCToken.sol` - Secure token implementation
- `FIXED_QXCStaking.sol` - Staking with reentrancy protection
- Other contracts are examples/incomplete

## Development Roadmap

### Phase 1: Foundation (Current)
- [x] Basic token contract
- [x] Security fixes
- [ ] Comprehensive testing
- [ ] Documentation cleanup

### Phase 2: Testing
- [ ] Unit tests
- [ ] Integration tests
- [ ] Security audit
- [ ] Testnet deployment

### Phase 3: Future (Conceptual)
- [ ] Multi-sig implementation
- [ ] DAO governance
- [ ] Real reward mechanisms
- [ ] Mainnet consideration (after audit)

## Important Disclaimers

1. **NOT INVESTMENT ADVICE** - This is educational software
2. **NOT DEPLOYED** - No contracts on mainnet
3. **NOT AUDITED** - Security vulnerabilities likely exist
4. **TEST ONLY** - Use only with test networks
5. **NO WARRANTY** - Provided as-is for learning

## Contributing

This is an educational project. Contributions should focus on:
- Security improvements
- Test coverage
- Documentation accuracy
- Educational value

## Support

For development questions only:
- GitHub Issues: [Report bugs](https://github.com/abdulrahman305/qenex-os/issues)
- Documentation: See `/docs` folder

## License

MIT License - Educational use encouraged

---

**Remember: This is a learning project. Do not use with real funds.**