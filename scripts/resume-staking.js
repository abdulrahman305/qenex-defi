const hre = require("hardhat");
const fs = require('fs');

/**
 * Resume Staking Script
 * Unpauses staking contract to allow operations
 */
async function main() {
  console.log("▶️  RESUME STAKING CONTRACT\n");
  
  // Load deployment
  if (!fs.existsSync('mainnet-deployment.json')) {
    throw new Error("❌ No deployment file found");
  }
  
  const deployment = JSON.parse(fs.readFileSync('mainnet-deployment.json'));
  const [signer] = await ethers.getSigners();
  
  console.log(`Executing from: ${signer.address}\n`);
  
  try {
    const staking = await ethers.getContractAt("QXCStakingFixed", deployment.contracts.staking);
    const multiSig = await ethers.getContractAt("TimelockMultiSig", deployment.contracts.multiSig);
    
    // Check if paused
    const isPaused = await staking.paused();
    if (!isPaused) {
      console.log("✅ Staking already active");
      return;
    }
    
    // Check reward pool before resuming
    const rewardPool = await staking.rewardPool();
    const totalStaked = await staking.totalStaked();
    console.log("📊 Pre-resume Check:");
    console.log(`  Reward Pool: ${ethers.formatEther(rewardPool)} QXC`);
    console.log(`  Total Staked: ${ethers.formatEther(totalStaked)} QXC`);
    
    if (Number(rewardPool) === 0 && Number(totalStaked) > 0) {
      console.log("\n⚠️  WARNING: Reward pool is empty!");
      console.log("Consider funding rewards before resuming");
    }
    
    // Check owner
    const owner = await staking.owner();
    console.log(`\nStaking owner: ${owner}`);
    
    if (owner.toLowerCase() === signer.address.toLowerCase()) {
      // Direct unpause
      console.log("\n🔓 Direct unpause available");
      const tx = await staking.unpause();
      await tx.wait();
      console.log("✅ Staking resumed successfully");
      
    } else if (owner.toLowerCase() === deployment.contracts.multiSig.toLowerCase()) {
      // Queue via multi-sig
      console.log("\n🔐 Queueing unpause via multi-sig");
      
      const unpauseData = staking.interface.encodeFunctionData("unpause");
      const txId = await multiSig.queueTransaction(
        deployment.contracts.staking,
        unpauseData,
        0,
        false // Normal 48hr timelock for resume
      );
      
      console.log(`✅ Transaction queued (ID: ${txId})`);
      console.log("⏳ Requires 2-of-3 signatures + 48hr timelock");
      
    } else {
      throw new Error(`Cannot unpause - not owner (owner: ${owner})`);
    }
    
    // Verify status
    const finalPaused = await staking.paused();
    console.log(`\n📊 Final Status: ${finalPaused ? "⏳ STILL PAUSED" : "✅ ACTIVE"}`);
    
  } catch (error) {
    console.error("\n❌ RESUME FAILED:", error.message);
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Script failed:", error);
    process.exit(1);
  });