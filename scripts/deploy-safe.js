const { ethers, upgrades } = require("hardhat");
const fs = require("fs");
const path = require("path");

// Configuration
const CONFIG = {
    TREASURY: process.env.TREASURY_ADDRESS || ethers.constants.AddressZero,
    MULTISIG: process.env.MULTISIG_ADDRESS || ethers.constants.AddressZero,
    MIN_ETH_BALANCE: ethers.utils.parseEther("0.5"),
    MAX_GAS_PRICE: ethers.utils.parseUnits("100", "gwei"),
    TIMELOCK_DELAY: 172800, // 48 hours
    
    // Staking configuration
    REWARD_POOL_INITIAL: ethers.utils.parseEther("100000"),
    REWARD_PER_SECOND: ethers.utils.parseEther("0.1"),
    
    // AMM configuration
    INITIAL_LIQUIDITY_QXC: ethers.utils.parseEther("10000"),
    INITIAL_LIQUIDITY_USDC: ethers.utils.parseEther("10000")
};

// Safety checks before deployment
async function performSafetyChecks(signer, network) {
    console.log("\n🔍 Performing Safety Checks...\n");
    
    // Check network
    if (network.name === "mainnet") {
        console.log("⚠️  WARNING: Deploying to MAINNET!");
        
        // Check for audit
        if (!process.env.AUDIT_COMPLETE) {
            throw new Error("❌ AUDIT_COMPLETE environment variable not set. Refusing to deploy to mainnet without audit.");
        }
        
        // Check for multisig
        if (CONFIG.MULTISIG === ethers.constants.AddressZero) {
            throw new Error("❌ No multisig address configured for mainnet deployment");
        }
        
        // Require explicit confirmation
        if (process.env.CONFIRM_MAINNET_DEPLOYMENT !== "YES_I_AM_SURE") {
            throw new Error("❌ Set CONFIRM_MAINNET_DEPLOYMENT=YES_I_AM_SURE to deploy to mainnet");
        }
    }
    
    // Check deployer balance
    const balance = await signer.getBalance();
    console.log(`💰 Deployer balance: ${ethers.utils.formatEther(balance)} ETH`);
    
    if (balance.lt(CONFIG.MIN_ETH_BALANCE)) {
        throw new Error(`❌ Insufficient ETH balance. Need at least ${ethers.utils.formatEther(CONFIG.MIN_ETH_BALANCE)} ETH`);
    }
    
    // Check gas price
    const gasPrice = await signer.getGasPrice();
    console.log(`⛽ Current gas price: ${ethers.utils.formatUnits(gasPrice, "gwei")} gwei`);
    
    if (gasPrice.gt(CONFIG.MAX_GAS_PRICE)) {
        throw new Error(`❌ Gas price too high. Current: ${ethers.utils.formatUnits(gasPrice, "gwei")} gwei, Max: ${ethers.utils.formatUnits(CONFIG.MAX_GAS_PRICE, "gwei")} gwei`);
    }
    
    // Check treasury address
    if (CONFIG.TREASURY === ethers.constants.AddressZero) {
        console.log("⚠️  Warning: No treasury address set, using deployer address");
        CONFIG.TREASURY = signer.address;
    }
    
    console.log("✅ All safety checks passed\n");
}

// Deploy contracts
async function deployContracts(signer) {
    const deployments = {};
    
    console.log("🚀 Starting Deployment...\n");
    
    // 1. Deploy Token
    console.log("1️⃣  Deploying QXC Token V2...");
    const Token = await ethers.getContractFactory("QXCTokenV2");
    const token = await Token.deploy(CONFIG.TREASURY);
    await token.deployed();
    deployments.token = token.address;
    console.log(`   ✅ Token deployed at: ${token.address}`);
    
    // Verify initial supply
    const totalSupply = await token.totalSupply();
    console.log(`   📊 Initial supply: ${ethers.utils.formatEther(totalSupply)} QXC`);
    
    // 2. Deploy Staking
    console.log("\n2️⃣  Deploying Staking V2...");
    const Staking = await ethers.getContractFactory("QXCStakingV2");
    const staking = await Staking.deploy(token.address);
    await staking.deployed();
    deployments.staking = staking.address;
    console.log(`   ✅ Staking deployed at: ${staking.address}`);
    
    // 3. Deploy Timelock
    console.log("\n3️⃣  Deploying Timelock Controller...");
    const Timelock = await ethers.getContractFactory("TimelockController");
    const timelock = await Timelock.deploy(
        CONFIG.TIMELOCK_DELAY,
        [CONFIG.MULTISIG || signer.address], // proposers
        [CONFIG.MULTISIG || signer.address], // executors
        signer.address // admin (will be renounced)
    );
    await timelock.deployed();
    deployments.timelock = timelock.address;
    console.log(`   ✅ Timelock deployed at: ${timelock.address}`);
    console.log(`   ⏰ Timelock delay: ${CONFIG.TIMELOCK_DELAY} seconds (${CONFIG.TIMELOCK_DELAY / 3600} hours)`);
    
    // 4. Deploy Governor
    console.log("\n4️⃣  Deploying Governor...");
    const Governor = await ethers.getContractFactory("QXCGovernor");
    const governor = await Governor.deploy(
        token.address,
        timelock.address
    );
    await governor.deployed();
    deployments.governor = governor.address;
    console.log(`   ✅ Governor deployed at: ${governor.address}`);
    
    // 5. Deploy Price Oracle
    console.log("\n5️⃣  Deploying Price Oracle...");
    const Oracle = await ethers.getContractFactory("PriceOracle");
    const oracle = await Oracle.deploy();
    await oracle.deployed();
    deployments.oracle = oracle.address;
    console.log(`   ✅ Oracle deployed at: ${oracle.address}`);
    
    return deployments;
}

// Configure contracts
async function configureContracts(deployments, signer) {
    console.log("\n⚙️  Configuring Contracts...\n");
    
    const token = await ethers.getContractAt("QXCTokenV2", deployments.token);
    const staking = await ethers.getContractAt("QXCStakingV2", deployments.staking);
    const timelock = await ethers.getContractAt("TimelockController", deployments.timelock);
    
    // 1. Grant roles
    console.log("1️⃣  Setting up roles...");
    
    const MINTER_ROLE = await token.MINTER_ROLE();
    const PAUSER_ROLE = await token.PAUSER_ROLE();
    
    // Grant minter role to staking contract (for rewards)
    await token.grantRole(MINTER_ROLE, staking.address);
    console.log(`   ✅ Granted MINTER_ROLE to staking contract`);
    
    // Grant pauser role to timelock
    await token.grantRole(PAUSER_ROLE, timelock.address);
    console.log(`   ✅ Granted PAUSER_ROLE to timelock`);
    
    // 2. Fund staking rewards
    console.log("\n2️⃣  Funding staking rewards...");
    await token.approve(staking.address, CONFIG.REWARD_POOL_INITIAL);
    await staking.fundRewardPool(CONFIG.REWARD_POOL_INITIAL);
    await staking.updateRewardRate(CONFIG.REWARD_PER_SECOND);
    console.log(`   ✅ Funded with ${ethers.utils.formatEther(CONFIG.REWARD_POOL_INITIAL)} QXC`);
    console.log(`   ✅ Reward rate: ${ethers.utils.formatEther(CONFIG.REWARD_PER_SECOND)} QXC/second`);
    
    // 3. Enable trading
    console.log("\n3️⃣  Enabling trading...");
    await token.enableTrading();
    console.log(`   ✅ Trading enabled`);
    
    // 4. Transfer ownership to multisig/timelock
    if (CONFIG.MULTISIG !== ethers.constants.AddressZero) {
        console.log("\n4️⃣  Transferring ownership to multisig...");
        
        const DEFAULT_ADMIN_ROLE = await token.DEFAULT_ADMIN_ROLE();
        
        // Grant admin role to multisig
        await token.grantRole(DEFAULT_ADMIN_ROLE, CONFIG.MULTISIG);
        console.log(`   ✅ Granted admin role to multisig: ${CONFIG.MULTISIG}`);
        
        // Revoke admin role from deployer
        await token.renounceRole(DEFAULT_ADMIN_ROLE, signer.address);
        console.log(`   ✅ Renounced admin role from deployer`);
        
        // Transfer timelock admin
        await timelock.renounceRole(await timelock.TIMELOCK_ADMIN_ROLE(), signer.address);
        console.log(`   ✅ Renounced timelock admin role`);
    }
    
    console.log("\n✅ Configuration complete!");
}

// Save deployment info
async function saveDeploymentInfo(deployments, network) {
    const deploymentInfo = {
        network: network.name,
        chainId: network.config.chainId,
        deployedAt: new Date().toISOString(),
        contracts: deployments,
        configuration: {
            treasury: CONFIG.TREASURY,
            multisig: CONFIG.MULTISIG,
            timelockDelay: CONFIG.TIMELOCK_DELAY,
            rewardPoolInitial: CONFIG.REWARD_POOL_INITIAL.toString(),
            rewardPerSecond: CONFIG.REWARD_PER_SECOND.toString()
        }
    };
    
    const filename = `deployment-${network.name}-${Date.now()}.json`;
    const filepath = path.join(__dirname, "..", "deployments", filename);
    
    // Create deployments directory if it doesn't exist
    const dir = path.dirname(filepath);
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
    
    fs.writeFileSync(filepath, JSON.stringify(deploymentInfo, null, 2));
    
    console.log(`\n💾 Deployment info saved to: ${filepath}`);
    
    return deploymentInfo;
}

// Verify contracts on Etherscan
async function verifyContracts(deployments, network) {
    if (network.name === "localhost" || network.name === "hardhat") {
        console.log("\n⏭️  Skipping verification on local network");
        return;
    }
    
    console.log("\n🔍 Verifying contracts on Etherscan...\n");
    
    try {
        // Verify token
        console.log("Verifying token...");
        await hre.run("verify:verify", {
            address: deployments.token,
            constructorArguments: [CONFIG.TREASURY]
        });
        
        // Verify staking
        console.log("Verifying staking...");
        await hre.run("verify:verify", {
            address: deployments.staking,
            constructorArguments: [deployments.token]
        });
        
        console.log("\n✅ Verification complete!");
    } catch (error) {
        console.log("\n⚠️  Verification failed:", error.message);
        console.log("You can verify manually later using: npx hardhat verify --network", network.name);
    }
}

// Main deployment function
async function main() {
    try {
        // Get network and signer
        const [signer] = await ethers.getSigners();
        const network = await ethers.provider.getNetwork();
        
        console.log("=====================================");
        console.log("   QXC DeFi Ecosystem Deployment");
        console.log("=====================================");
        console.log(`Network: ${network.name || "Unknown"} (Chain ID: ${network.chainId})`);
        console.log(`Deployer: ${signer.address}`);
        console.log("=====================================\n");
        
        // Perform safety checks
        await performSafetyChecks(signer, network);
        
        // Deploy contracts
        const deployments = await deployContracts(signer);
        
        // Configure contracts
        await configureContracts(deployments, signer);
        
        // Save deployment info
        const deploymentInfo = await saveDeploymentInfo(deployments, network);
        
        // Verify on Etherscan
        await verifyContracts(deployments, network);
        
        // Print summary
        console.log("\n=====================================");
        console.log("      🎉 DEPLOYMENT SUCCESSFUL!");
        console.log("=====================================");
        console.log("\n📋 Contract Addresses:");
        Object.entries(deployments).forEach(([name, address]) => {
            console.log(`   ${name.padEnd(15)} ${address}`);
        });
        console.log("\n=====================================\n");
        
        console.log("📝 Next Steps:");
        console.log("1. Verify contracts on Etherscan (if not auto-verified)");
        console.log("2. Transfer remaining roles to multisig");
        console.log("3. Add liquidity to AMM pools");
        console.log("4. Announce deployment to community");
        console.log("5. Begin monitoring with scripts/monitor.js");
        
    } catch (error) {
        console.error("\n❌ Deployment failed:", error.message);
        console.error("\nStack trace:", error.stack);
        process.exit(1);
    }
}

// Execute deployment
main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });