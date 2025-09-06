const hre = require("hardhat");
const fs = require('fs');

/**
 * Pause Staking Script
 * Pauses staking contract to prevent new stakes
 */
async function main() {
  console.log("⏸️  PAUSE STAKING CONTRACT\n");
  
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
    
    // Check if already paused
    const isPaused = await staking.paused();
    if (isPaused) {
      console.log("✅ Staking already paused");
      return;
    }
    
    // Check owner
    const owner = await staking.owner();
    console.log(`Staking owner: ${owner}`);
    
    if (owner.toLowerCase() === signer.address.toLowerCase()) {
      // Direct pause
      console.log("\n🔓 Direct pause available");
      const tx = await staking.pause();
      await tx.wait();
      console.log("✅ Staking paused successfully");
      
    } else if (owner.toLowerCase() === deployment.contracts.multiSig.toLowerCase()) {
      // Queue via multi-sig
      console.log("\n🔐 Queueing pause via multi-sig");
      
      const pauseData = staking.interface.encodeFunctionData("pause");
      const txId = await multiSig.queueTransaction(
        deployment.contracts.staking,
        pauseData,
        0,
        true // Emergency for 24hr timelock
      );
      
      console.log(`✅ Transaction queued (ID: ${txId})`);
      console.log("⏳ Requires 2-of-3 signatures + 24hr timelock");
      
    } else {
      throw new Error(`Cannot pause - not owner (owner: ${owner})`);
    }
    
    // Verify status
    const finalPaused = await staking.paused();
    console.log(`\n📊 Final Status: ${finalPaused ? "✅ PAUSED" : "⏳ PENDING"}`);
    
  } catch (error) {
    console.error("\n❌ PAUSE FAILED:", error.message);
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Script failed:", error);
    process.exit(1);
  });