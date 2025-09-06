const hre = require("hardhat");

async function main() {
    console.log("Deploying QXC Token to network...");
    
    const [deployer] = await ethers.getSigners();
    console.log("Deploying contracts with account:", deployer.address);
    
    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("Account balance:", ethers.formatEther(balance));
    
    // Deploy QXCToken
    const Token = await ethers.getContractFactory("QXCToken");
    const token = await Token.deploy();
    await token.waitForDeployment();
    
    const tokenAddress = await token.getAddress();
    console.log("QXCToken deployed to:", tokenAddress);
    
    // Deploy QXCStaking
    const Staking = await ethers.getContractFactory("QXCStaking");
    const staking = await Staking.deploy(tokenAddress);
    await staking.waitForDeployment();
    
    const stakingAddress = await staking.getAddress();
    console.log("QXCStaking deployed to:", stakingAddress);
    
    // Enable trading on token
    console.log("Enabling trading...");
    await token.enableTrading();
    console.log("Trading enabled!");
    
    // Grant minter role to staking contract
    const MINTER_ROLE = await token.MINTER_ROLE();
    await token.grantRole(MINTER_ROLE, stakingAddress);
    console.log("Minter role granted to staking contract");
    
    console.log("\n=== Deployment Summary ===");
    console.log("QXC Token:", tokenAddress);
    console.log("QXC Staking:", stakingAddress);
    console.log("Network:", hre.network.name);
    console.log("========================\n");
    
    // Verify deployment
    const name = await token.name();
    const symbol = await token.symbol();
    const totalSupply = await token.totalSupply();
    const cap = await token.cap();
    
    console.log("Token Details:");
    console.log("- Name:", name);
    console.log("- Symbol:", symbol);
    console.log("- Total Supply:", ethers.formatEther(totalSupply));
    console.log("- Max Supply:", ethers.formatEther(cap));
    
    return {
        token: tokenAddress,
        staking: stakingAddress
    };
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });