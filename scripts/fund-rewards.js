const hre = require("hardhat");
const { ethers } = require("hardhat");
const fs = require('fs');

/**
 * Fund Staking Rewards Script
 * Deposits QXC tokens into the staking reward pool
 */
async function main() {
  console.log("💰 FUND STAKING REWARDS\n");
  
  // Load deployment
  if (!fs.existsSync('mainnet-deployment.json')) {
    throw new Error("❌ No deployment file found");
  }
  
  const deployment = JSON.parse(fs.readFileSync('mainnet-deployment.json'));
  const [signer] = await ethers.getSigners();
  
  // Get amount to fund
  const amountToFund = process.env.REWARD_AMOUNT || "10000";
  const amountWei = ethers.parseEther(amountToFund);
  
  console.log(`Amount to fund: ${amountToFund} QXC`);
  console.log(`From account: ${signer.address}\n`);
  
  try {
    // Connect to contracts
    const token = await ethers.getContractAt("QXCTokenProduction", deployment.contracts.token);
    const staking = await ethers.getContractAt("QXCStakingFixed", deployment.contracts.staking);
    const multiSig = await ethers.getContractAt("TimelockMultiSig", deployment.contracts.multiSig);
    
    // Check current state
    console.log("📊 Current State:");
    const rewardPool = await staking.rewardPool();
    const totalStaked = await staking.totalStaked();
    const rewardRate = await staking.rewardRate();
    
    console.log(`  Reward Pool: ${ethers.formatEther(rewardPool)} QXC`);
    console.log(`  Total Staked: ${ethers.formatEther(totalStaked)} QXC`);
    console.log(`  Reward Rate: ${rewardRate}% APY\n`);
    
    // Calculate required rewards for 1 year
    const annualRewards = (Number(ethers.formatEther(totalStaked)) * Number(rewardRate)) / 100;
    const currentRewards = Number(ethers.formatEther(rewardPool));
    const deficit = Math.max(0, annualRewards - currentRewards);
    
    console.log("📈 Reward Analysis:");
    console.log(`  Annual rewards needed: ${annualRewards.toFixed(2)} QXC`);
    console.log(`  Current reward pool: ${currentRewards.toFixed(2)} QXC`);
    console.log(`  Deficit: ${deficit.toFixed(2)} QXC`);
    
    if (deficit > 0) {
      console.log(`  ⚠️  Recommended funding: ${deficit.toFixed(2)} QXC`);
    } else {
      console.log(`  ✅ Reward pool is sufficient for 1 year`);
    }
    
    // Check balance
    const balance = await token.balanceOf(signer.address);
    console.log(`\n💳 Your Balance: ${ethers.formatEther(balance)} QXC`);
    
    if (balance < amountWei) {
      throw new Error("Insufficient QXC balance");
    }
    
    // Check staking owner
    const stakingOwner = await staking.owner();
    const isMultiSigOwner = stakingOwner.toLowerCase() === deployment.contracts.multiSig.toLowerCase();
    
    if (isMultiSigOwner) {
      console.log("\n🔐 Staking is owned by multi-sig");
      console.log("Creating funding transaction for multi-sig approval...");
      
      // First approve tokens to staking contract
      console.log("\n1️⃣ Approving tokens...");
      const approveTx = await token.approve(deployment.contracts.staking, amountWei);
      await approveTx.wait();
      console.log("   ✅ Tokens approved");
      
      // Create depositRewards transaction for multi-sig
      const depositData = staking.interface.encodeFunctionData("depositRewards", [amountWei]);
      const txId = await multiSig.queueTransaction(
        deployment.contracts.staking,
        depositData,
        0,
        false // Normal timelock (48 hours)
      );
      
      console.log(`\n2️⃣ Transaction queued (ID: ${txId})`);
      console.log("   ⏳ Requires 2-of-3 signatures");
      console.log("   ⏳ 48-hour timelock");
      
    } else if (stakingOwner.toLowerCase() === signer.address.toLowerCase()) {
      // Direct funding
      console.log("\n🔓 You own the staking contract");
      console.log("Funding rewards directly...");
      
      // Approve and deposit
      console.log("\n1️⃣ Approving tokens...");
      const approveTx = await token.approve(deployment.contracts.staking, amountWei);
      await approveTx.wait();
      console.log("   ✅ Tokens approved");
      
      console.log("\n2️⃣ Depositing rewards...");
      const depositTx = await staking.depositRewards(amountWei);
      await depositTx.wait();
      console.log("   ✅ Rewards deposited");
      
      // Check new balance
      const newRewardPool = await staking.rewardPool();
      console.log(`\n✅ New Reward Pool: ${ethers.formatEther(newRewardPool)} QXC`);
      
    } else {
      throw new Error(`Staking owned by ${stakingOwner}, cannot fund`);
    }
    
    console.log("\n✅ FUNDING COMPLETE");
    
  } catch (error) {
    console.error("\n❌ FUNDING FAILED:", error.message);
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Script failed:", error);
    process.exit(1);
  });