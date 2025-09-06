const hre = require("hardhat");
const fs = require('fs');

/**
 * Submit Upgrade Script
 * Submits a contract upgrade transaction to multi-sig
 */
async function main() {
  console.log("🔧 SUBMIT CONTRACT UPGRADE\n");
  
  // Load deployment
  if (!fs.existsSync('mainnet-deployment.json')) {
    throw new Error("❌ No deployment file found");
  }
  
  const deployment = JSON.parse(fs.readFileSync('mainnet-deployment.json'));
  const [signer] = await ethers.getSigners();
  
  // Get upgrade parameters from environment
  const TARGET_CONTRACT = process.env.TARGET_CONTRACT || deployment.contracts.token;
  const FUNCTION_NAME = process.env.FUNCTION_NAME || "pause";
  const FUNCTION_ARGS = process.env.FUNCTION_ARGS ? JSON.parse(process.env.FUNCTION_ARGS) : [];
  const IS_EMERGENCY = process.env.IS_EMERGENCY === "true";
  
  console.log("📋 Upgrade Details:");
  console.log(`  Target: ${TARGET_CONTRACT}`);
  console.log(`  Function: ${FUNCTION_NAME}`);
  console.log(`  Arguments: ${JSON.stringify(FUNCTION_ARGS)}`);
  console.log(`  Emergency: ${IS_EMERGENCY ? "Yes (24hr)" : "No (48hr)"}`);
  console.log(`  Submitter: ${signer.address}\n`);
  
  try {
    const multiSig = await ethers.getContractAt("TimelockMultiSig", deployment.contracts.multiSig);
    
    // Check if signer is authorized
    const isSigner = await multiSig.isSigner(signer.address);
    if (!isSigner) {
      throw new Error("You are not a multi-sig signer");
    }
    
    // Get target contract ABI for encoding
    let targetInterface;
    if (TARGET_CONTRACT === deployment.contracts.token) {
      const Token = await ethers.getContractFactory("QXCTokenProduction");
      targetInterface = Token.interface;
    } else if (TARGET_CONTRACT === deployment.contracts.staking) {
      const Staking = await ethers.getContractFactory("QXCStakingFixed");
      targetInterface = Staking.interface;
    } else {
      throw new Error("Unknown target contract");
    }
    
    // Encode function call
    const callData = targetInterface.encodeFunctionData(FUNCTION_NAME, FUNCTION_ARGS);
    
    // Submit to multi-sig
    console.log("🔐 Submitting to multi-sig...");
    const tx = await multiSig.queueTransaction(
      TARGET_CONTRACT,
      callData,
      0, // No ETH value
      IS_EMERGENCY
    );
    
    const receipt = await tx.wait();
    
    // Get transaction ID from events
    const event = receipt.events?.find(e => e.event === 'TransactionQueued');
    const txId = event?.args?.txId;
    
    console.log("\n✅ UPGRADE SUBMITTED");
    console.log(`  Transaction ID: ${txId}`);
    console.log(`  Status: Pending signatures (1/${await multiSig.REQUIRED_SIGNATURES()})`);
    console.log(`  Timelock: ${IS_EMERGENCY ? "24 hours" : "48 hours"}`);
    
    // Calculate execution time
    const currentTime = Math.floor(Date.now() / 1000);
    const timelock = IS_EMERGENCY ? 24 * 3600 : 48 * 3600;
    const executionTime = new Date((currentTime + timelock) * 1000);
    
    console.log(`  Executable after: ${executionTime.toUTCString()}`);
    
    console.log("\n📝 Next Steps:");
    console.log("1. Get additional signatures from other signers");
    console.log("2. Wait for timelock to expire");
    console.log("3. Execute transaction using execute-transaction.js");
    
    // Save transaction details
    const upgradeDetails = {
      txId: txId?.toString(),
      target: TARGET_CONTRACT,
      function: FUNCTION_NAME,
      args: FUNCTION_ARGS,
      emergency: IS_EMERGENCY,
      submittedBy: signer.address,
      submittedAt: new Date().toISOString(),
      executionTime: executionTime.toISOString()
    };
    
    fs.writeFileSync(
      `upgrade-${txId}.json`,
      JSON.stringify(upgradeDetails, null, 2)
    );
    console.log(`\n💾 Details saved to upgrade-${txId}.json`);
    
  } catch (error) {
    console.error("\n❌ SUBMISSION FAILED:", error.message);
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Script failed:", error);
    process.exit(1);
  });