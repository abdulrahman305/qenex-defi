# 🎯 QXC Bug Bounty Program

## Overview

The QXC DeFi Ecosystem Bug Bounty Program is designed to incentivize security researchers to find and responsibly disclose vulnerabilities in our smart contracts and systems. We believe that working with the security community is crucial for maintaining the highest security standards.

## 💰 Rewards

### Smart Contract Vulnerabilities

| Severity | Reward Range | Examples |
|----------|-------------|----------|
| **Critical** | $10,000 - $50,000 | • Theft of user funds<br>• Permanent freezing of funds<br>• Protocol insolvency<br>• Unauthorized minting |
| **High** | $5,000 - $10,000 | • Temporary freezing of funds<br>• Griefing attacks (significant gas costs)<br>• Governance takeover<br>• Oracle manipulation |
| **Medium** | $1,000 - $5,000 | • Smart contract fails to deliver promised returns<br>• Bypass of timelock<br>• Minor loss of funds (<$1000) |
| **Low** | $100 - $1,000 | • Inefficient gas usage<br>• Missing events<br>• Non-optimal math operations |

### Web/App Vulnerabilities

| Severity | Reward Range | Examples |
|----------|-------------|----------|
| **Critical** | $5,000 - $25,000 | • Private key extraction<br>• RCE on infrastructure<br>• SQL injection with fund access |
| **High** | $2,500 - $5,000 | • Account takeover<br>• SSRF on critical systems<br>• Bypass of 2FA |
| **Medium** | $500 - $2,500 | • XSS on main domain<br>• CSRF on sensitive actions<br>• Information disclosure |
| **Low** | $50 - $500 | • Self-XSS<br>• Missing security headers<br>• Version disclosure |

## 📋 Scope

### In Scope

#### Smart Contracts (Mainnet)
```
QXCTokenV2: 0x[ADDRESS]
QXCStakingV2: 0x[ADDRESS]
QXCGovernor: 0x[ADDRESS]
QXCAMMv2: 0x[ADDRESS]
QXCLendingV2: 0x[ADDRESS]
QXCBridge: 0x[ADDRESS]
TimelockController: 0x[ADDRESS]
```

#### Web Applications
- https://app.qxc.finance
- https://governance.qxc.finance
- https://bridge.qxc.finance

#### Infrastructure
- API endpoints (api.qxc.finance/*)
- IPFS gateways
- Oracle feeds

### Out of Scope

- **Testnets** (Sepolia, Goerli)
- **Social engineering** attacks
- **Physical attacks** on team members
- **DoS attacks** without demonstration of fund loss
- **Known issues** listed in documentation
- **Third-party services** (Infura, Etherscan, etc.)
- **Best practice** violations without security impact
- **Recently deployed** contracts (<30 days)

## 🎓 Severity Classification

### Critical Severity
- Direct theft of any user funds
- Permanent freezing of funds
- Protocol insolvency
- Arbitrary code execution

### High Severity
- Theft of yield/rewards
- Temporary freezing of funds (>1 week)
- Manipulation of governance voting
- Bypass of critical security features

### Medium Severity
- Freezing of funds (<1 week)
- Bypass of non-critical features
- Moderate economic attacks
- Information leakage of sensitive data

### Low Severity
- Gas optimizations saving >20%
- Dead code removal
- Typos and improvements
- Non-security best practices

## 📝 Submission Guidelines

### Required Information

1. **Vulnerability Description**
   - Clear explanation of the vulnerability
   - Root cause analysis
   - Attack scenario

2. **Impact Assessment**
   - Potential damage
   - Number of users affected
   - Economic impact

3. **Proof of Concept**
   - Step-by-step reproduction
   - Code snippets or scripts
   - Screenshots/videos if applicable

4. **Remediation Suggestions**
   - Proposed fixes
   - Best practices to prevent

### Submission Template

```markdown
## Vulnerability Report

### Summary
[One paragraph summary]

### Severity
[Critical/High/Medium/Low]

### Vulnerability Details
[Detailed description]

### Impact
[What can an attacker achieve?]

### Proof of Concept
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Recommendation
[How to fix]

### References
[Links to similar issues]
```

## 📮 How to Submit

### Primary Channel
Email: security@qxc.finance

Subject: [SECURITY] [SEVERITY] Brief Description

### Alternative Channels
- Immunefi: https://immunefi.com/bounty/qxc
- Secure Form: https://qxc.finance/security
- Telegram: @QXCSecurityBot

### PGP Encryption (Recommended)
```
-----BEGIN PGP PUBLIC KEY BLOCK-----
[PUBLIC KEY HERE]
-----END PGP PUBLIC KEY BLOCK-----
```

## ⚖️ Rules

### ✅ Do's
- Test on testnets first
- Keep findings confidential
- Provide clear reports
- Allow time for fixes
- Be professional

### ❌ Don'ts
- Don't test on mainnet without permission
- Don't exploit vulnerabilities
- Don't publish before fix
- Don't demand ransoms
- Don't social engineer

## 🏆 Hall of Fame

Researchers who have contributed to our security:

| Researcher | Severity | Date | Acknowledgment |
|------------|----------|------|----------------|
| @researcher1 | Critical | 2024-01 | Public |
| Anonymous | High | 2024-02 | Anonymous |
| @researcher2 | Medium | 2024-03 | Public |

## 💳 Payment Process

1. **Report Submission** - You submit vulnerability
2. **Initial Review** (24-48 hours) - We acknowledge receipt
3. **Validation** (3-7 days) - We verify the vulnerability
4. **Severity Assessment** (1-2 days) - We determine severity
5. **Fix Development** (Variable) - We develop a fix
6. **Reward Determination** (1-2 days) - We calculate reward
7. **Payment** (3-5 days) - Payment sent via:
   - Cryptocurrency (ETH, USDC, USDT)
   - Wire transfer (KYC required)
   - Platform credit

## 📊 Statistics

### Program Metrics (2024)
- Total Reports: 127
- Valid Reports: 43
- Total Paid: $287,500
- Average Response: 36 hours
- Average Fix Time: 7 days

### Top Vulnerabilities Found
1. Reentrancy (8 reports)
2. Access Control (6 reports)
3. Integer Overflow (4 reports)
4. Oracle Manipulation (3 reports)
5. Flash Loan Attacks (2 reports)

## 🔒 Safe Harbor

We commit to:
- Not pursuing legal action for good-faith research
- Working with researchers to understand issues
- Providing updates on fix progress
- Acknowledging contributions (if desired)
- Protecting researcher anonymity (if requested)

## 📚 Resources

### Testing Tools
- [Hardhat](https://hardhat.org/)
- [Foundry](https://getfoundry.sh/)
- [Slither](https://github.com/crytic/slither)
- [Mythril](https://github.com/ConsenSys/mythril)
- [Echidna](https://github.com/crytic/echidna)

### Documentation
- [Technical Docs](https://docs.qxc.finance)
- [Smart Contract Guide](https://docs.qxc.finance/contracts)
- [Security Best Practices](https://docs.qxc.finance/security)

### Learning Resources
- [Ethernaut](https://ethernaut.openzeppelin.com/)
- [Damn Vulnerable DeFi](https://www.damnvulnerabledefi.xyz/)
- [Smart Contract Security](https://consensys.github.io/smart-contract-best-practices/)

## 🤝 Partnerships

We work with leading security platforms:
- **Immunefi** - Bug bounty platform
- **OpenZeppelin** - Security services
- **Consensys Diligence** - Audits
- **Trail of Bits** - Security research

## 📞 Contact

- **Primary**: security@qxc.finance
- **Emergency**: emergency@qxc.finance
- **General**: support@qxc.finance
- **Telegram**: @QXCSecurityBot
- **Discord**: discord.gg/qxc

## 📋 Legal

### Terms and Conditions

By participating in this program, you agree to:
1. Follow responsible disclosure
2. Not violate privacy of users
3. Not disrupt services
4. Act in good faith
5. Follow all applicable laws

### Eligibility

- Must be 18+ years old
- Not resident of sanctioned countries
- Not team member or family
- Not under NDA with QXC

### Tax Information

- Rewards may be taxable income
- We will issue 1099 forms (US residents)
- International researchers responsible for taxes
- KYC required for payments >$600

## 🔄 Updates

This program is regularly updated. Check back for:
- Scope changes
- Reward adjustments
- New rules
- Statistics updates

**Last Updated**: September 2024
**Version**: 1.0.0

---

## Quick Start Checklist

- [ ] Read all rules and guidelines
- [ ] Set up test environment
- [ ] Test on testnet first
- [ ] Document findings clearly
- [ ] Submit via secure channel
- [ ] Wait for response
- [ ] Work with team on fix
- [ ] Receive reward
- [ ] Get added to Hall of Fame

Thank you for helping secure the QXC ecosystem! 🙏