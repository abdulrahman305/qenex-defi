const hre = require("hardhat");
const { ethers } = require("hardhat");
const fs = require('fs');

/**
 * Post-Deployment Setup Script
 * Executes critical ownership transfers and configurations after deployment
 * MUST BE RUN IMMEDIATELY AFTER DEPLOYMENT
 */
async function main() {
  console.log("🔧 POST-DEPLOYMENT SETUP\n");
  
  // Load deployment
  if (!fs.existsSync('mainnet-deployment.json')) {
    throw new Error("❌ No deployment file found. Run deployment first.");
  }
  
  const deployment = JSON.parse(fs.readFileSync('mainnet-deployment.json'));
  const [deployer] = await ethers.getSigners();
  
  console.log(`Executing from: ${deployer.address}`);
  console.log(`Network: ${deployment.network}\n`);
  
  const results = {
    timestamp: new Date().toISOString(),
    checks: {},
    actions: []
  };
  
  try {
    // Connect to contracts
    const token = await ethers.getContractAt("QXCTokenProduction", deployment.contracts.token);
    const staking = await ethers.getContractAt("QXCStakingFixed", deployment.contracts.staking);
    const multiSig = await ethers.getContractAt("TimelockMultiSig", deployment.contracts.multiSig);
    
    console.log("=" * 50);
    console.log("1️⃣ OWNERSHIP VERIFICATION");
    console.log("=" * 50);
    
    // Check token controller
    const tokenController = await token.multiSigController();
    const isTokenCorrect = tokenController.toLowerCase() === deployment.contracts.multiSig.toLowerCase();
    console.log(`\nToken Controller:`);
    console.log(`  Current: ${tokenController}`);
    console.log(`  Expected: ${deployment.contracts.multiSig}`);
    console.log(`  Status: ${isTokenCorrect ? "✅ CORRECT" : "❌ WRONG"}`);
    results.checks.tokenController = isTokenCorrect;
    
    // Check staking owner
    const stakingOwner = await staking.owner();
    const isStakingCorrect = stakingOwner.toLowerCase() === deployment.contracts.multiSig.toLowerCase();
    console.log(`\nStaking Owner:`);
    console.log(`  Current: ${stakingOwner}`);
    console.log(`  Expected: ${deployment.contracts.multiSig}`);
    console.log(`  Status: ${isStakingCorrect ? "✅ CORRECT" : "❌ NEEDS TRANSFER"}`);
    results.checks.stakingOwner = isStakingCorrect;
    
    // Transfer staking ownership if needed
    if (!isStakingCorrect && stakingOwner.toLowerCase() === deployer.address.toLowerCase()) {
      console.log("\n🔄 Transferring staking ownership to multi-sig...");
      const tx = await staking.transferOwnership(deployment.contracts.multiSig);
      await tx.wait();
      console.log("✅ Ownership transferred");
      results.actions.push("Transferred staking ownership to multi-sig");
    }
    
    console.log("\n" + "=" * 50);
    console.log("2️⃣ MULTI-SIG VERIFICATION");
    console.log("=" * 50);
    
    // Verify signers
    const signers = await multiSig.getSigners();
    console.log(`\nMulti-sig Signers (${signers.length}):`);
    signers.forEach((signer, i) => {
      console.log(`  ${i + 1}. ${signer}`);
    });
    
    const requiredSigs = 2; // Hardcoded in contract
    console.log(`\nRequired Signatures: ${requiredSigs}/${signers.length}`);
    results.checks.multiSigSetup = signers.length >= 3;
    
    console.log("\n" + "=" * 50);
    console.log("3️⃣ INITIAL CONFIGURATION");
    console.log("=" * 50);
    
    // Check if trading is enabled
    const tradingEnabled = await token.tradingEnabled();
    console.log(`\nTrading Status: ${tradingEnabled ? "✅ ENABLED" : "⏸️ DISABLED"}`);
    results.checks.tradingEnabled = tradingEnabled;
    
    if (!tradingEnabled) {
      console.log("ℹ️  Trading must be enabled via multi-sig when ready");
      console.log("   Use: npx hardhat run scripts/enable-trading.js");
    }
    
    // Check staking reward pool
    const rewardPool = await staking.rewardPool();
    const totalStaked = await staking.totalStaked();
    console.log(`\nStaking Status:`);
    console.log(`  Reward Pool: ${ethers.formatEther(rewardPool)} QXC`);
    console.log(`  Total Staked: ${ethers.formatEther(totalStaked)} QXC`);
    results.checks.rewardPoolFunded = Number(rewardPool) > 0;
    
    if (Number(rewardPool) === 0) {
      console.log("⚠️  Reward pool needs funding");
      console.log("   Use: REWARD_AMOUNT=10000 npx hardhat run scripts/fund-rewards.js");
    }
    
    console.log("\n" + "=" * 50);
    console.log("4️⃣ SECURITY CHECKS");
    console.log("=" * 50);
    
    // Check pause status
    const tokenPaused = await token.paused();
    const stakingPaused = await staking.paused();
    console.log(`\nContract Status:`);
    console.log(`  Token: ${tokenPaused ? "⏸️ PAUSED" : "✅ ACTIVE"}`);
    console.log(`  Staking: ${stakingPaused ? "⏸️ PAUSED" : "✅ ACTIVE"}`);
    results.checks.contractsActive = !tokenPaused && !stakingPaused;
    
    // Check emergency stop
    const emergencyStop = await multiSig.emergencyStop();
    console.log(`  Emergency Stop: ${emergencyStop ? "🛑 ACTIVE" : "✅ INACTIVE"}`);
    results.checks.noEmergency = !emergencyStop;
    
    // Save results
    fs.writeFileSync(
      'post-deployment-results.json',
      JSON.stringify(results, null, 2)
    );
    
    console.log("\n" + "=" * 50);
    console.log("📊 SETUP SUMMARY");
    console.log("=" * 50);
    
    const allChecks = Object.values(results.checks);
    const passedChecks = allChecks.filter(c => c).length;
    
    console.log(`\nChecks Passed: ${passedChecks}/${allChecks.length}`);
    
    if (passedChecks === allChecks.length) {
      console.log("✅ ALL CHECKS PASSED - READY FOR MAINNET");
    } else {
      console.log("⚠️  SOME CHECKS FAILED - REVIEW NEEDED");
      
      console.log("\n📝 Required Actions:");
      if (!results.checks.stakingOwner) {
        console.log("  • Transfer staking ownership to multi-sig");
      }
      if (!results.checks.tradingEnabled) {
        console.log("  • Enable trading when ready");
      }
      if (!results.checks.rewardPoolFunded) {
        console.log("  • Fund staking reward pool");
      }
    }
    
    console.log("\n📁 Results saved to post-deployment-results.json");
    
  } catch (error) {
    console.error("\n❌ SETUP FAILED:", error.message);
    results.error = error.message;
    fs.writeFileSync(
      'post-deployment-results.json',
      JSON.stringify(results, null, 2)
    );
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Script failed:", error);
    process.exit(1);
  });