const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    console.log("🚀 Starting Production Deployment...\n");
    
    // Safety checks
    const network = await ethers.provider.getNetwork();
    const chainId = network.chainId;
    
    console.log(`Network: ${hre.network.name}`);
    console.log(`Chain ID: ${chainId}\n`);
    
    // Prevent accidental mainnet deployment without confirmation
    if (chainId === 1n) {
        console.log("⚠️  WARNING: You are deploying to ETHEREUM MAINNET!");
        console.log("⚠️  This will cost real ETH!");
        console.log("⚠️  Type 'DEPLOY_TO_MAINNET' to confirm:");
        
        const readline = require('readline').createInterface({
            input: process.stdin,
            output: process.stdout
        });
        
        const answer = await new Promise(resolve => {
            readline.question('> ', resolve);
        });
        readline.close();
        
        if (answer !== 'DEPLOY_TO_MAINNET') {
            console.log("❌ Deployment cancelled");
            process.exit(1);
        }
    }
    
    const [deployer, signer1, signer2] = await ethers.getSigners();
    
    console.log("Deploying contracts with account:", deployer.address);
    console.log("Account balance:", ethers.formatEther(await ethers.provider.getBalance(deployer.address)));
    console.log();
    
    // Deploy Multi-Sig first
    console.log("1️⃣ Deploying Timelock Multi-Sig...");
    const signers = [deployer.address, signer1?.address || deployer.address, signer2?.address || deployer.address];
    
    const MultiSig = await ethers.getContractFactory("TimelockMultiSig");
    const multiSig = await MultiSig.deploy(signers);
    await multiSig.waitForDeployment();
    const multiSigAddress = await multiSig.getAddress();
    console.log("✅ Multi-Sig deployed to:", multiSigAddress);
    
    // Deploy Token
    console.log("\n2️⃣ Deploying QXC Token Production...");
    const Token = await ethers.getContractFactory("QXCTokenProduction");
    const token = await Token.deploy(multiSigAddress);
    await token.waitForDeployment();
    const tokenAddress = await token.getAddress();
    console.log("✅ Token deployed to:", tokenAddress);
    
    // Deploy Staking
    console.log("\n3️⃣ Deploying QXC Staking Fixed...");
    const Staking = await ethers.getContractFactory("QXCStakingFixed");
    const staking = await Staking.deploy(tokenAddress);
    await staking.waitForDeployment();
    const stakingAddress = await staking.getAddress();
    console.log("✅ Staking deployed to:", stakingAddress);
    
    // Save deployment info
    const deployment = {
        network: hre.network.name,
        chainId: chainId.toString(),
        timestamp: new Date().toISOString(),
        contracts: {
            multiSig: {
                address: multiSigAddress,
                signers: signers
            },
            token: {
                address: tokenAddress,
                name: await token.name(),
                symbol: await token.symbol(),
                totalSupply: ethers.formatEther(await token.totalSupply()),
                maxSupply: ethers.formatEther(await token.cap())
            },
            staking: {
                address: stakingAddress,
                rewardRate: (await staking.rewardRate()).toString() + "%"
            }
        },
        deployer: deployer.address,
        blockNumber: await ethers.provider.getBlockNumber()
    };
    
    // Save to file
    const deploymentPath = path.join(__dirname, "..", "deployments", `${hre.network.name}-${Date.now()}.json`);
    fs.mkdirSync(path.dirname(deploymentPath), { recursive: true });
    fs.writeFileSync(deploymentPath, JSON.stringify(deployment, null, 2));
    
    console.log("\n" + "=".repeat(60));
    console.log("📊 DEPLOYMENT SUMMARY");
    console.log("=".repeat(60));
    console.log("Multi-Sig:", multiSigAddress);
    console.log("Token:", tokenAddress);
    console.log("Staking:", stakingAddress);
    console.log("=".repeat(60));
    
    // Verify contracts on Etherscan (if API key provided)
    if (process.env.ETHERSCAN_API_KEY && chainId !== 31337n) {
        console.log("\n📝 Verifying contracts on Etherscan...");
        
        try {
            await hre.run("verify:verify", {
                address: multiSigAddress,
                constructorArguments: [signers]
            });
            console.log("✅ Multi-Sig verified");
        } catch (error) {
            console.log("⚠️  Multi-Sig verification failed:", error.message);
        }
        
        try {
            await hre.run("verify:verify", {
                address: tokenAddress,
                constructorArguments: [multiSigAddress]
            });
            console.log("✅ Token verified");
        } catch (error) {
            console.log("⚠️  Token verification failed:", error.message);
        }
        
        try {
            await hre.run("verify:verify", {
                address: stakingAddress,
                constructorArguments: [tokenAddress]
            });
            console.log("✅ Staking verified");
        } catch (error) {
            console.log("⚠️  Staking verification failed:", error.message);
        }
    }
    
    console.log("\n✅ DEPLOYMENT COMPLETE!");
    console.log("📄 Deployment saved to:", deploymentPath);
    
    // Post-deployment checklist
    console.log("\n📋 POST-DEPLOYMENT CHECKLIST:");
    console.log("[ ] Enable trading via multi-sig (after 48h timelock)");
    console.log("[ ] Fund staking rewards pool");
    console.log("[ ] Add liquidity to DEX");
    console.log("[ ] Update frontend with contract addresses");
    console.log("[ ] Start monitoring services");
    console.log("[ ] Announce deployment to community");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });