const hre = require("hardhat");
const fs = require('fs');

/**
 * Emergency Pause Script
 * Pauses all contracts to prevent further operations
 * Requires multi-sig approval for token, direct for staking
 */
async function main() {
  console.log("🚨 EMERGENCY PAUSE PROCEDURE 🚨\n");
  
  // Load deployment
  if (!fs.existsSync('mainnet-deployment.json')) {
    throw new Error("❌ No deployment file found");
  }
  
  const deployment = JSON.parse(fs.readFileSync('mainnet-deployment.json'));
  const [signer] = await ethers.getSigners();
  
  console.log(`Executing from: ${signer.address}\n`);
  
  try {
    // 1. Pause Token (via multi-sig)
    console.log("1️⃣ Pausing QXC Token...");
    const token = await ethers.getContractAt("QXCTokenProduction", deployment.contracts.token);
    const multiSig = await ethers.getContractAt("TimelockMultiSig", deployment.contracts.multiSig);
    
    // Check if already paused
    const isTokenPaused = await token.paused();
    if (isTokenPaused) {
      console.log("   ✅ Token already paused");
    } else {
      // Create pause transaction for multi-sig
      const pauseData = token.interface.encodeFunctionData("pause");
      const txId = await multiSig.queueTransaction(
        deployment.contracts.token,
        pauseData,
        0,
        true // Emergency flag for 24-hour timelock
      );
      console.log(`   ⏳ Pause transaction queued (ID: ${txId})`);
      console.log("   ⚠️  Requires 2-of-3 signatures + 24hr timelock");
    }
    
    // 2. Pause Staking (if multi-sig is owner)
    console.log("\n2️⃣ Pausing Staking Contract...");
    const staking = await ethers.getContractAt("QXCStakingFixed", deployment.contracts.staking);
    
    // Check current owner
    const stakingOwner = await staking.owner();
    const isStakingPaused = await staking.paused();
    
    if (isStakingPaused) {
      console.log("   ✅ Staking already paused");
    } else if (stakingOwner.toLowerCase() === signer.address.toLowerCase()) {
      // Direct pause if we're the owner
      await staking.pause();
      console.log("   ✅ Staking paused directly");
    } else if (stakingOwner.toLowerCase() === deployment.contracts.multiSig.toLowerCase()) {
      // Queue via multi-sig
      const pauseStakingData = staking.interface.encodeFunctionData("pause");
      const stakingTxId = await multiSig.queueTransaction(
        deployment.contracts.staking,
        pauseStakingData,
        0,
        true // Emergency
      );
      console.log(`   ⏳ Pause transaction queued (ID: ${stakingTxId})`);
      console.log("   ⚠️  Requires 2-of-3 signatures + 24hr timelock");
    } else {
      console.log(`   ❌ Cannot pause - owner is ${stakingOwner}`);
    }
    
    // 3. Summary
    console.log("\n" + "=".repeat(50));
    console.log("📊 EMERGENCY PAUSE STATUS");
    console.log("=".repeat(50));
    
    const finalTokenPaused = await token.paused();
    const finalStakingPaused = await staking.paused();
    
    console.log(`Token:   ${finalTokenPaused ? "✅ PAUSED" : "⏳ PENDING"}`);
    console.log(`Staking: ${finalStakingPaused ? "✅ PAUSED" : "⏳ PENDING"}`);
    
    if (!finalTokenPaused || !finalStakingPaused) {
      console.log("\n⚠️  ACTION REQUIRED:");
      console.log("1. Get 2-of-3 multi-sig signatures");
      console.log("2. Wait for 24-hour emergency timelock");
      console.log("3. Execute queued transactions");
    }
    
    // 4. Alert
    console.log("\n🔔 NEXT STEPS:");
    console.log("1. Alert all team members immediately");
    console.log("2. Investigate the incident");
    console.log("3. Prepare fix if needed");
    console.log("4. Document incident for post-mortem");
    
  } catch (error) {
    console.error("\n❌ EMERGENCY PAUSE FAILED:", error.message);
    console.error("\n🚨 MANUAL INTERVENTION REQUIRED!");
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Script failed:", error);
    process.exit(1);
  });