const hre = require("hardhat");
const { ethers } = require("hardhat");
const readline = require('readline');

// Mainnet deployment with maximum safety checks
async function main() {
  console.log("🚨 MAINNET DEPLOYMENT - MAXIMUM SAFETY MODE 🚨\n");
  
  // Safety check 1: Environment verification
  if (process.env.NETWORK !== 'mainnet') {
    throw new Error("❌ NETWORK env variable must be set to 'mainnet'");
  }
  
  // Safety check 2: Network verification
  const network = await ethers.provider.getNetwork();
  if (network.chainId !== 1n) {
    throw new Error(`❌ Not on mainnet! Chain ID: ${network.chainId}`);
  }
  
  // Safety check 3: Gas price check
  const gasPrice = await ethers.provider.getFeeData();
  const gasPriceGwei = Number(gasPrice.gasPrice) / 1e9;
  
  console.log(`Current gas price: ${gasPriceGwei.toFixed(2)} gwei`);
  if (gasPriceGwei > 100) {
    console.log("⚠️ WARNING: Gas price is very high!");
    const proceed = await confirm("Continue with high gas price?");
    if (!proceed) process.exit(1);
  }
  
  // Safety check 4: Deployer balance check
  const [deployer] = await ethers.getSigners();
  const balance = await ethers.provider.getBalance(deployer.address);
  const balanceETH = ethers.formatEther(balance);
  
  console.log(`\nDeployer: ${deployer.address}`);
  console.log(`Balance: ${balanceETH} ETH`);
  
  if (parseFloat(balanceETH) < 0.5) {
    throw new Error("❌ Insufficient ETH balance (need at least 0.5 ETH)");
  }
  
  // Safety check 5: Multi-sig addresses verification
  const signer1 = process.env.MULTISIG_SIGNER_1;
  const signer2 = process.env.MULTISIG_SIGNER_2;
  const signer3 = process.env.MULTISIG_SIGNER_3;
  
  if (!signer1 || !signer2 || !signer3) {
    throw new Error("❌ All three multi-sig signer addresses required");
  }
  
  // Validate addresses
  [signer1, signer2, signer3].forEach(addr => {
    if (!ethers.isAddress(addr)) {
      throw new Error(`❌ Invalid address: ${addr}`);
    }
  });
  
  // Safety check 6: Final confirmation
  console.log("\n📋 DEPLOYMENT SUMMARY:");
  console.log("═══════════════════════");
  console.log("Network: ETHEREUM MAINNET");
  console.log("Chain ID: 1");
  console.log(`Gas Price: ${gasPriceGwei.toFixed(2)} gwei`);
  console.log(`Deployer: ${deployer.address}`);
  console.log(`Balance: ${balanceETH} ETH`);
  console.log("\nMulti-sig Signers:");
  console.log(`  1: ${signer1}`);
  console.log(`  2: ${signer2}`);
  console.log(`  3: ${signer3}`);
  
  console.log("\n⚠️ THIS IS MAINNET - REAL MONEY ⚠️");
  const finalConfirm = await confirmExact("DEPLOY_TO_MAINNET");
  if (!finalConfirm) {
    console.log("❌ Deployment cancelled");
    process.exit(1);
  }
  
  // Start deployment
  console.log("\n🚀 Starting deployment...\n");
  
  // Deploy Multi-sig first
  console.log("Deploying TimelockMultiSig...");
  const MultiSig = await ethers.getContractFactory("TimelockMultiSig");
  const multiSig = await MultiSig.deploy(
    [signer1, signer2, signer3],
    2, // requiredSignatures
    { gasPrice: gasPrice.gasPrice }
  );
  await multiSig.waitForDeployment();
  const multiSigAddress = await multiSig.getAddress();
  console.log(`✅ MultiSig deployed: ${multiSigAddress}`);
  
  // Deploy Token
  console.log("\nDeploying QXCTokenProduction...");
  const Token = await ethers.getContractFactory("QXCTokenProduction");
  const token = await Token.deploy(
    multiSigAddress,
    { gasPrice: gasPrice.gasPrice }
  );
  await token.waitForDeployment();
  const tokenAddress = await token.getAddress();
  console.log(`✅ Token deployed: ${tokenAddress}`);
  
  // Deploy Staking
  console.log("\nDeploying QXCStakingFixed...");
  const Staking = await ethers.getContractFactory("QXCStakingFixed");
  const staking = await Staking.deploy(
    tokenAddress,
    10, // 10% APY
    { gasPrice: gasPrice.gasPrice }
  );
  await staking.waitForDeployment();
  const stakingAddress = await staking.getAddress();
  console.log(`✅ Staking deployed: ${stakingAddress}`);
  
  // Verify deployment
  console.log("\n🔍 Verifying deployment...");
  
  // Check multi-sig
  const signers = await multiSig.getSigners();
  console.log("Multi-sig signers verified:", signers.length === 3);
  
  // Check token
  const tokenName = await token.name();
  const tokenSymbol = await token.symbol();
  console.log(`Token: ${tokenName} (${tokenSymbol})`);
  
  // Save deployment info
  const deployment = {
    network: "mainnet",
    chainId: 1,
    timestamp: new Date().toISOString(),
    contracts: {
      multiSig: multiSigAddress,
      token: tokenAddress,
      staking: stakingAddress
    },
    deployer: deployer.address,
    gasPrice: gasPriceGwei,
    blockNumber: await ethers.provider.getBlockNumber()
  };
  
  const fs = require('fs');
  fs.writeFileSync(
    'mainnet-deployment.json',
    JSON.stringify(deployment, null, 2)
  );
  
  console.log("\n✅ DEPLOYMENT SUCCESSFUL!");
  console.log("═══════════════════════════");
  console.log("Multi-sig:", multiSigAddress);
  console.log("Token:", tokenAddress);
  console.log("Staking:", stakingAddress);
  console.log("\n📝 Deployment saved to mainnet-deployment.json");
  
  console.log("\n⚠️ NEXT STEPS:");
  console.log("1. Verify contracts on Etherscan");
  console.log("2. Transfer token ownership to multi-sig");
  console.log("3. Fund staking rewards pool");
  console.log("4. Enable monitoring");
  console.log("5. Add liquidity on DEX");
}

// Helper functions
function confirm(question) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  
  return new Promise(resolve => {
    rl.question(`${question} (yes/no): `, answer => {
      rl.close();
      resolve(answer.toLowerCase() === 'yes');
    });
  });
}

function confirmExact(expected) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  
  return new Promise(resolve => {
    rl.question(`Type '${expected}' to confirm: `, answer => {
      rl.close();
      resolve(answer === expected);
    });
  });
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });