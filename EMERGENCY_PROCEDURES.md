# 🚨 EMERGENCY RESPONSE PROCEDURES

## Critical Incident Response

### 1. CONTRACT COMPROMISE
**Indicators:**
- Unauthorized transfers
- Unexpected contract behavior
- Suspicious multi-sig transactions

**IMMEDIATE ACTIONS:**
```bash
# 1. PAUSE ALL CONTRACTS (requires 2-of-3 multi-sig)
npx hardhat run scripts/emergency-pause.js --network mainnet

# 2. Verify pause status
npx hardhat run scripts/verify-deployment.js --network mainnet

# 3. Alert team
# Send message to all signers immediately
```

**Recovery Steps:**
1. Analyze the attack vector
2. Deploy patched contracts
3. Migrate user balances via snapshot
4. Resume operations after 48-hour timelock

---

### 2. PRIVATE KEY COMPROMISE
**IMMEDIATE ACTIONS:**
```bash
# 1. If deployer key compromised:
#    - Cannot pause (needs multi-sig)
#    - Monitor for malicious transactions

# 2. If one multi-sig signer compromised:
#    - Other 2 signers must act immediately
#    - Remove compromised signer
npx hardhat run scripts/remove-signer.js --network mainnet

# 3. If 2+ signers compromised:
#    - EMERGENCY: Pause all contracts
#    - Deploy emergency migration contract
```

---

### 3. CRITICAL BUG DISCOVERED
**Severity Levels:**

**CRITICAL (Funds at risk):**
```bash
# Immediate pause
npx hardhat run scripts/emergency-pause.js --network mainnet

# Deploy fix (24-hour emergency timelock)
npx hardhat run scripts/deploy-emergency-fix.js --network mainnet
```

**HIGH (Functionality broken):**
```bash
# Prepare fix
# Submit through normal 48-hour timelock
npx hardhat run scripts/submit-upgrade.js --network mainnet
```

**MEDIUM/LOW:**
- Document issue
- Include in next scheduled upgrade

---

### 4. STAKING INSOLVENCY
**Indicators:**
- Reward pool < Total pending rewards
- Users cannot withdraw rewards

**IMMEDIATE ACTIONS:**
```bash
# 1. Stop new stakes
npx hardhat run scripts/pause-staking.js --network mainnet

# 2. Fund reward pool
npx hardhat run scripts/fund-rewards.js --network mainnet

# 3. Resume staking
npx hardhat run scripts/resume-staking.js --network mainnet
```

---

### 5. LIQUIDITY CRISIS
**Indicators:**
- DEX pool drained
- Price manipulation detected
- Extreme volatility

**IMMEDIATE ACTIONS:**
```bash
# 1. Pause DEX interactions (if possible)
npx hardhat run scripts/pause-dex.js --network mainnet

# 2. Add emergency liquidity
npx hardhat run scripts/add-emergency-liquidity.js --network mainnet

# 3. Implement transfer limits
npx hardhat run scripts/set-transfer-limits.js --network mainnet
```

---

## Command Reference

### Emergency Scripts

**Pause Everything:**
```bash
export EMERGENCY=true
npx hardhat run scripts/emergency-pause.js --network mainnet
```

**Check System Status:**
```bash
npx hardhat run scripts/system-health.js --network mainnet
```

**Emergency Migration:**
```bash
# Take snapshot
npx hardhat run scripts/snapshot-balances.js --network mainnet

# Deploy new contracts
npx hardhat run scripts/deploy-emergency.js --network mainnet

# Migrate balances
npx hardhat run scripts/migrate-balances.js --network mainnet
```

---

## Contact Points

### Multi-Sig Signers
- Signer 1: [SECURE CONTACT]
- Signer 2: [SECURE CONTACT]  
- Signer 3: [SECURE CONTACT]

### Security Team
- Primary: [CONTACT]
- Backup: [CONTACT]

### Legal
- Counsel: [CONTACT]

---

## Recovery Procedures

### Post-Incident Checklist
- [ ] All contracts secured
- [ ] Root cause identified
- [ ] Fix deployed and tested
- [ ] User funds verified safe
- [ ] Communication sent to users
- [ ] Post-mortem completed
- [ ] Procedures updated

### Communication Template
```
Subject: [URGENT/INFO] QXC Contract Update

Dear QXC Community,

[Brief description of issue]

Actions Taken:
- [Action 1]
- [Action 2]

User Impact:
- [Impact description]

Next Steps:
- [Step 1]
- [Step 2]

Your funds are [safe/being secured].

Updates: [Link]
Questions: [Contact]

- QXC Team
```

---

## Testing Emergency Procedures

**Run drills monthly:**
```bash
# On testnet only!
npm run emergency-drill
```

**Verify all signers can:**
- [ ] Access multi-sig
- [ ] Submit transactions
- [ ] Execute emergency pause
- [ ] Deploy contracts
- [ ] Access backups

---

## Important Notes

1. **NEVER** panic - follow procedures
2. **ALWAYS** verify actions on Etherscan
3. **COMMUNICATE** with team immediately
4. **DOCUMENT** everything
5. **TEST** fixes on testnet first (if time permits)

---

## Emergency Timelock Override

In extreme circumstances (imminent fund loss), emergency 24-hour timelock can be used:

```javascript
// Requires all 3 signers
await multiSig.declareEmergency();

// Then execute with 24-hour delay instead of 48
await multiSig.executeTransaction(txId);
```

---

*Last Updated: September 2025*
*Version: 1.0.0*

**KEEP THIS DOCUMENT SECURE AND ACCESSIBLE**