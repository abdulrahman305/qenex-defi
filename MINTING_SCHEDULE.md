# QXC Token Minting Schedule

## Overview
This document provides complete transparency on QXC token minting policies and schedule.

## Token Supply Breakdown

### Initial Supply
- **Amount**: 1,525.30 QXC
- **Percentage**: 0.0073% of max supply
- **Recipient**: Multi-sig treasury
- **Purpose**: Initial liquidity and operations

### Maximum Supply
- **Hard Cap**: 21,000,000 QXC
- **Enforcement**: ERC20Capped (cannot be exceeded)
- **Remaining Mintable**: 20,998,474.70 QXC

## Minting Schedule

### Year 1 (Months 1-12)
- **Maximum Mint**: 1,000,000 QXC
- **Purpose**: 
  - Staking rewards: 500,000 QXC
  - Liquidity provision: 300,000 QXC
  - Development fund: 200,000 QXC
- **Approval**: Requires 2-of-3 multi-sig + 48hr timelock

### Year 2 (Months 13-24)
- **Maximum Mint**: 750,000 QXC
- **Purpose**:
  - Staking rewards: 400,000 QXC
  - Ecosystem growth: 250,000 QXC
  - Reserve: 100,000 QXC
- **Approval**: Requires 2-of-3 multi-sig + 48hr timelock

### Year 3 (Months 25-36)
- **Maximum Mint**: 500,000 QXC
- **Purpose**:
  - Staking rewards: 300,000 QXC
  - Partnerships: 150,000 QXC
  - Reserve: 50,000 QXC
- **Approval**: Requires 2-of-3 multi-sig + 48hr timelock

### Years 4-10
- **Annual Maximum**: 250,000 QXC
- **Total Period**: 1,750,000 QXC
- **Purpose**: Staking rewards and ecosystem maintenance
- **Approval**: Requires 2-of-3 multi-sig + 48hr timelock

### Long-term (Year 10+)
- **Annual Maximum**: 100,000 QXC or 0.5% of circulating supply (whichever is lower)
- **Purpose**: Network security and maintenance
- **Approval**: Requires 2-of-3 multi-sig + 48hr timelock

## Minting Controls

### Technical Enforcement
```solidity
// Hard cap enforcement
contract QXCTokenProduction is ERC20Capped(21_000_000 ether)

// Per-transaction limit
uint256 public constant MAX_TRANSFER_AMOUNT = 100_000 ether;

// Only multi-sig can mint
function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE)
```

### Governance Requirements
1. **Proposal**: Any minting requires written proposal with:
   - Amount to mint
   - Specific purpose
   - Distribution plan
   - Expected impact

2. **Approval Process**:
   - 2-of-3 multi-sig signatures required
   - 48-hour timelock for community review
   - Public announcement before execution

3. **Transparency**:
   - All minting events logged on-chain
   - Quarterly reports published
   - Real-time supply tracking available

## Supply Projections

| Year | Cumulative Minted | % of Max Supply | Circulating Supply |
|------|-------------------|-----------------|-------------------|
| 0 | 1,525 | 0.01% | 1,525 |
| 1 | 1,001,525 | 4.77% | 1,001,525 |
| 2 | 1,751,525 | 8.34% | 1,751,525 |
| 3 | 2,251,525 | 10.72% | 2,251,525 |
| 5 | 2,751,525 | 13.10% | 2,751,525 |
| 10 | 4,001,525 | 19.05% | 4,001,525 |
| 20 | 5,001,525 | 23.82% | 5,001,525 |

## Emergency Minting

### Conditions
Emergency minting may only occur under:
1. Critical security incident requiring user compensation
2. Catastrophic smart contract failure
3. Regulatory requirement

### Requirements
- All 3 multi-sig signers must approve
- 24-hour emergency timelock
- Public disclosure required
- Post-mortem report within 7 days

## Burn Mechanism

### Deflationary Option
- Users can burn their tokens anytime
- Reduces total and max supply permanently
- No tokens can be minted to compensate burns

### Burn Events
All burns are:
- Irreversible
- Logged on-chain
- Reflected in total supply immediately

## Commitments

### We Commit To:
1. **Never** mint beyond published schedule without community approval
2. **Never** mint for personal benefit
3. **Always** provide 48-hour notice before minting
4. **Always** publish quarterly supply reports
5. **Never** exceed 21,000,000 QXC hard cap

### Accountability
- Multi-sig addresses are public
- All minting transactions are on-chain
- Community can verify compliance
- Violations would be immediately visible

## Monitoring

### How to Verify Supply
```javascript
// Check current supply
const totalSupply = await token.totalSupply();
console.log(`Current Supply: ${totalSupply}`);

// Check max supply
const maxSupply = await token.MAX_SUPPLY();
console.log(`Max Supply: ${maxSupply}`);

// Monitor minting events
token.on("Transfer", (from, to, amount) => {
  if (from === ethers.constants.AddressZero) {
    console.log(`MINTED: ${amount} to ${to}`);
  }
});
```

### Tools
- Supply Monitor: `npx hardhat run scripts/monitor-contracts.js`
- On-chain verification: Etherscan
- Real-time alerts: Contract events

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Sept 2025 | Initial minting schedule |

---

**Last Updated**: September 2025
**Next Review**: December 2025

*This is a living document. Changes require 2-of-3 multi-sig approval and 30-day notice.*