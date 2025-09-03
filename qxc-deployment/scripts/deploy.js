
const hre = require("hardhat");

async function main() {
    console.log("Deploying QXC Token...");
    
    const QXCToken = await hre.ethers.getContractFactory("QXCToken");
    const qxc = await QXCToken.deploy();
    
    await qxc.waitForDeployment();
    
    const address = await qxc.getAddress();
    
    console.log("QXC Token deployed to:", address);
    console.log("Add this address to MetaMask:", address);
    console.log("Symbol: QXC");
    console.log("Decimals: 18");
    
    // Save deployment info
    const deployment = {
        address: address,
        network: hre.network.name,
        deployer: (await hre.ethers.getSigners())[0].address,
        timestamp: new Date().toISOString()
    };
    
    const fs = require('fs');
    fs.writeFileSync('deployment.json', JSON.stringify(deployment, null, 2));
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
