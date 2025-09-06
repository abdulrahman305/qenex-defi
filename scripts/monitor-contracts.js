const { ethers } = require("hardhat");
const fs = require('fs');

// Configuration
const ALERT_THRESHOLDS = {
  gasPrice: 150, // Alert if gas > 150 gwei
  largeTransfer: 10000, // Alert if transfer > 10,000 QXC
  lowRewardPool: 1000, // Alert if reward pool < 1,000 QXC
  highStakingRatio: 0.5, // Alert if > 50% of supply staked
};

async function main() {
  console.log("🔍 QXC Contract Monitor\n");
  
  // Load deployment
  if (!fs.existsSync('mainnet-deployment.json')) {
    throw new Error("No deployment file found");
  }
  
  const deployment = JSON.parse(fs.readFileSync('mainnet-deployment.json'));
  const alerts = [];
  
  // Connect to contracts
  const token = await ethers.getContractAt("QXCTokenProduction", deployment.contracts.token);
  const staking = await ethers.getContractAt("QXCStakingFixed", deployment.contracts.staking);
  const multiSig = await ethers.getContractAt("TimelockMultiSig", deployment.contracts.multiSig);
  
  // Monitor gas prices
  const gasPrice = await ethers.provider.getFeeData();
  const gasPriceGwei = Number(gasPrice.gasPrice) / 1e9;
  
  console.log(`⛽ Gas Price: ${gasPriceGwei.toFixed(2)} gwei`);
  if (gasPriceGwei > ALERT_THRESHOLDS.gasPrice) {
    alerts.push(`HIGH GAS: ${gasPriceGwei.toFixed(2)} gwei`);
  }
  
  // Monitor token metrics
  console.log("\n📊 Token Metrics:");
  const totalSupply = await token.totalSupply();
  const isPaused = await token.paused();
  
  console.log(`  Total Supply: ${ethers.formatEther(totalSupply)} QXC`);
  console.log(`  Contract Paused: ${isPaused}`);
  
  if (isPaused) {
    alerts.push("TOKEN CONTRACT IS PAUSED");
  }
  
  // Monitor staking metrics
  console.log("\n🎯 Staking Metrics:");
  const totalStaked = await staking.totalStaked();
  const rewardPool = await staking.rewardPool();
  const stakingRatio = Number(totalStaked) / Number(totalSupply);
  
  console.log(`  Total Staked: ${ethers.formatEther(totalStaked)} QXC`);
  console.log(`  Reward Pool: ${ethers.formatEther(rewardPool)} QXC`);
  console.log(`  Staking Ratio: ${(stakingRatio * 100).toFixed(2)}%`);
  
  if (Number(ethers.formatEther(rewardPool)) < ALERT_THRESHOLDS.lowRewardPool) {
    alerts.push(`LOW REWARD POOL: ${ethers.formatEther(rewardPool)} QXC`);
  }
  
  if (stakingRatio > ALERT_THRESHOLDS.highStakingRatio) {
    alerts.push(`HIGH STAKING RATIO: ${(stakingRatio * 100).toFixed(2)}%`);
  }
  
  // Monitor multi-sig
  console.log("\n🔐 Multi-Sig Status:");
  const pendingCount = await multiSig.getTransactionCount();
  const executedCount = await multiSig.executedCount();
  
  console.log(`  Pending Transactions: ${pendingCount - executedCount}`);
  console.log(`  Executed Transactions: ${executedCount}`);
  
  // Set up event listeners
  console.log("\n📡 Setting up event monitors...");
  
  // Token events
  token.on("Transfer", (from, to, amount) => {
    const amountQXC = Number(ethers.formatEther(amount));
    console.log(`[Transfer] ${from.slice(0,6)}...${from.slice(-4)} → ${to.slice(0,6)}...${to.slice(-4)}: ${amountQXC.toFixed(2)} QXC`);
    
    if (amountQXC > ALERT_THRESHOLDS.largeTransfer) {
      console.log(`⚠️ LARGE TRANSFER DETECTED: ${amountQXC.toFixed(2)} QXC`);
    }
  });
  
  token.on("Paused", (account) => {
    console.log(`🛑 CONTRACT PAUSED by ${account}`);
    alerts.push("CONTRACT PAUSED");
  });
  
  token.on("Unpaused", (account) => {
    console.log(`✅ CONTRACT UNPAUSED by ${account}`);
  });
  
  // Staking events
  staking.on("Staked", (user, amount) => {
    console.log(`[Stake] ${user.slice(0,6)}...${user.slice(-4)}: ${ethers.formatEther(amount)} QXC`);
  });
  
  staking.on("Withdrawn", (user, amount) => {
    console.log(`[Unstake] ${user.slice(0,6)}...${user.slice(-4)}: ${ethers.formatEther(amount)} QXC`);
  });
  
  staking.on("RewardPaid", (user, reward) => {
    console.log(`[Reward] ${user.slice(0,6)}...${user.slice(-4)}: ${ethers.formatEther(reward)} QXC`);
  });
  
  // Multi-sig events
  multiSig.on("TransactionSubmitted", (transactionId, submitter) => {
    console.log(`[MultiSig] Transaction #${transactionId} submitted by ${submitter.slice(0,6)}...${submitter.slice(-4)}`);
  });
  
  multiSig.on("TransactionApproved", (transactionId, approver) => {
    console.log(`[MultiSig] Transaction #${transactionId} approved by ${approver.slice(0,6)}...${approver.slice(-4)}`);
  });
  
  multiSig.on("TransactionExecuted", (transactionId) => {
    console.log(`[MultiSig] Transaction #${transactionId} EXECUTED`);
  });
  
  // Display alerts
  if (alerts.length > 0) {
    console.log("\n⚠️ ALERTS:");
    alerts.forEach(alert => console.log(`  - ${alert}`));
  }
  
  console.log("\n✅ Monitor running... Press Ctrl+C to stop");
  
  // Keep monitoring
  setInterval(async () => {
    // Periodic checks every 5 minutes
    const currentGas = await ethers.provider.getFeeData();
    const currentGasGwei = Number(currentGas.gasPrice) / 1e9;
    
    if (currentGasGwei > ALERT_THRESHOLDS.gasPrice) {
      console.log(`⚠️ HIGH GAS ALERT: ${currentGasGwei.toFixed(2)} gwei`);
    }
    
    const currentRewardPool = await staking.rewardPool();
    if (Number(ethers.formatEther(currentRewardPool)) < ALERT_THRESHOLDS.lowRewardPool) {
      console.log(`⚠️ LOW REWARD POOL: ${ethers.formatEther(currentRewardPool)} QXC`);
    }
  }, 300000); // 5 minutes
}

main().catch((error) => {
  console.error("Monitor error:", error);
  process.exit(1);
});