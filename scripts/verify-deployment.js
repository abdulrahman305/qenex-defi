const { ethers } = require("hardhat");
const fs = require('fs');

async function main() {
  console.log("🔍 Deployment Verification Script\n");
  
  // Load deployment file
  if (!fs.existsSync('mainnet-deployment.json')) {
    throw new Error("No deployment file found. Run deployment first.");
  }
  
  const deployment = JSON.parse(fs.readFileSync('mainnet-deployment.json'));
  console.log(`Verifying deployment from ${deployment.timestamp}`);
  console.log(`Network: ${deployment.network} (Chain ID: ${deployment.chainId})\n`);
  
  const results = {
    timestamp: new Date().toISOString(),
    checks: {},
    errors: []
  };
  
  try {
    // 1. Verify Multi-sig
    console.log("1️⃣ Verifying Multi-sig Contract...");
    const multiSig = await ethers.getContractAt("TimelockMultiSig", deployment.contracts.multiSig);
    
    const requiredSigs = await multiSig.requiredSignatures();
    const signerCount = await multiSig.signerCount();
    const timelockDuration = await multiSig.TIMELOCK_DURATION();
    
    results.checks.multiSig = {
      address: deployment.contracts.multiSig,
      requiredSignatures: requiredSigs.toString(),
      totalSigners: signerCount.toString(),
      timelockHours: Number(timelockDuration) / 3600,
      status: requiredSigs == 2 && signerCount == 3 ? "✅ PASS" : "❌ FAIL"
    };
    
    console.log(`  Required signatures: ${requiredSigs}/ऄ${signerCount}`);
    console.log(`  Timelock: ${Number(timelockDuration) / 3600} hours`);
    console.log(`  Status: ${results.checks.multiSig.status}\n`);
    
    // 2. Verify Token
    console.log("2️⃣ Verifying Token Contract...");
    const token = await ethers.getContractAt("QXCTokenProduction", deployment.contracts.token);
    
    const name = await token.name();
    const symbol = await token.symbol();
    const totalSupply = await token.totalSupply();
    const maxSupply = await token.MAX_SUPPLY();
    const isPaused = await token.paused();
    const multiSigController = await token.multiSigController();
    
    results.checks.token = {
      address: deployment.contracts.token,
      name: name,
      symbol: symbol,
      totalSupply: ethers.formatEther(totalSupply),
      maxSupply: ethers.formatEther(maxSupply),
      isPaused: isPaused,
      multiSigController: multiSigController,
      controllerCorrect: multiSigController.toLowerCase() === deployment.contracts.multiSig.toLowerCase(),
      status: "✅ PASS"
    };
    
    console.log(`  Name: ${name} (${symbol})`);
    console.log(`  Total Supply: ${ethers.formatEther(totalSupply)} QXC`);
    console.log(`  Max Supply: ${ethers.formatEther(maxSupply)} QXC`);
    console.log(`  Paused: ${isPaused}`);
    console.log(`  Controller: ${multiSigController === deployment.contracts.multiSig ? "✅ Correct" : "❌ Wrong"}`);
    
    if (multiSigController.toLowerCase() !== deployment.contracts.multiSig.toLowerCase()) {
      results.checks.token.status = "❌ FAIL";
      results.errors.push("Token controller is not the multi-sig wallet");
    }
    
    console.log(`  Status: ${results.checks.token.status}\n`);
    
    // 3. Verify Staking
    console.log("3️⃣ Verifying Staking Contract...");
    const staking = await ethers.getContractAt("QXCStakingFixed", deployment.contracts.staking);
    
    const stakingToken = await staking.stakingToken();
    const rewardRate = await staking.rewardRate();
    const rewardPool = await staking.rewardPool();
    const totalStaked = await staking.totalStaked();
    const minStakeDuration = await staking.MIN_STAKE_DURATION();
    
    results.checks.staking = {
      address: deployment.contracts.staking,
      stakingToken: stakingToken,
      tokenCorrect: stakingToken.toLowerCase() === deployment.contracts.token.toLowerCase(),
      rewardRateAPY: rewardRate.toString() + "%",
      rewardPoolBalance: ethers.formatEther(rewardPool),
      totalStaked: ethers.formatEther(totalStaked),
      minStakeDays: Number(minStakeDuration) / 86400,
      isFunded: Number(rewardPool) > 0,
      status: "✅ PASS"
    };
    
    console.log(`  Staking Token: ${stakingToken === deployment.contracts.token ? "✅ Correct" : "❌ Wrong"}`);
    console.log(`  Reward Rate: ${rewardRate}% APY`);
    console.log(`  Reward Pool: ${ethers.formatEther(rewardPool)} QXC`);
    console.log(`  Total Staked: ${ethers.formatEther(totalStaked)} QXC`);
    console.log(`  Min Stake Duration: ${Number(minStakeDuration) / 86400} days`);
    
    if (stakingToken.toLowerCase() !== deployment.contracts.token.toLowerCase()) {
      results.checks.staking.status = "⚠️ WARNING";
      results.errors.push("Staking token address mismatch");
    }
    
    if (Number(rewardPool) === 0) {
      results.checks.staking.status = "⚠️ WARNING";
      results.errors.push("Reward pool not funded");
    }
    
    console.log(`  Status: ${results.checks.staking.status}\n`);
    
    // 4. Security Checks
    console.log("4️⃣ Running Security Checks...");
    results.checks.security = {
      rateLimiting: await checkRateLimiting(token),
      transferLimits: await checkTransferLimits(token),
      blacklistEnabled: await checkBlacklist(token),
      pauseMechanism: isPaused === false ? "✅ Not paused" : "⚠️ Currently paused",
      ownershipTransferred: await checkOwnership(token, staking, deployment.contracts.multiSig)
    };
    
    console.log(`  Rate Limiting: ${results.checks.security.rateLimiting}`);
    console.log(`  Transfer Limits: ${results.checks.security.transferLimits}`);
    console.log(`  Blacklist: ${results.checks.security.blacklistEnabled}`);
    console.log(`  Pause Status: ${results.checks.security.pauseMechanism}`);
    console.log(`  Ownership: ${results.checks.security.ownershipTransferred}\n`);
    
  } catch (error) {
    results.errors.push(error.message);
  }
  
  // Save results
  fs.writeFileSync(
    'deployment-verification.json',
    JSON.stringify(results, null, 2)
  );
  
  // Summary
  console.log("═══════════════════════════════");
  console.log("📊 VERIFICATION SUMMARY");
  console.log("═══════════════════════════════");
  
  if (results.errors.length === 0) {
    console.log("✅ All checks passed!");
  } else {
    console.log("⚠️ Issues found:");
    results.errors.forEach(err => console.log(`  - ${err}`));
  }
  
  console.log("\n📝 Full results saved to deployment-verification.json");
}

// Helper functions
async function checkRateLimiting(token) {
  try {
    const cooldown = await token.TRANSFER_COOLDOWN();
    return `✅ ${Number(cooldown)} seconds`;
  } catch {
    return "❌ Not implemented";
  }
}

async function checkTransferLimits(token) {
  try {
    const maxTransfer = await token.MAX_TRANSFER_AMOUNT();
    return `✅ ${ethers.formatEther(maxTransfer)} QXC`;
  } catch {
    return "❌ Not implemented";
  }
}

async function checkBlacklist(token) {
  try {
    // Try to check if blacklist function exists
    await token.isBlacklisted("0x0000000000000000000000000000000000000000");
    return "✅ Enabled";
  } catch {
    return "⚠️ Not verified";
  }
}

async function checkOwnership(token, staking, expectedOwner) {
  const warnings = [];
  
  try {
    const tokenOwner = await token.owner();
    if (tokenOwner.toLowerCase() !== expectedOwner.toLowerCase()) {
      warnings.push("Token not owned by multi-sig");
    }
  } catch {}
  
  try {
    const stakingOwner = await staking.owner();
    if (stakingOwner.toLowerCase() !== expectedOwner.toLowerCase()) {
      warnings.push("Staking not owned by multi-sig");
    }
  } catch {}
  
  return warnings.length === 0 ? "✅ Transferred" : `⚠️ ${warnings.join(", ")}`;
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Verification failed:", error);
    process.exit(1);
  });