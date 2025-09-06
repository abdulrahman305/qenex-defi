const hre = require("hardhat");
const fs = require("fs");

async function main() {
  console.log("Starting QXC Ecosystem Deployment...\n");

  const [deployer] = await ethers.getSigners();
  console.log("Deploying with account:", deployer.address);
  console.log("Account balance:", (await deployer.getBalance()).toString());

  const deployments = {};

  // 1. Deploy QXC Token
  console.log("\n1. Deploying QXC Token...");
  const QXCToken = await hre.ethers.getContractFactory("QXCToken");
  const qxcToken = await QXCToken.deploy();
  await qxcToken.deployed();
  deployments.QXCToken = qxcToken.address;
  console.log("✅ QXC Token deployed to:", qxcToken.address);

  // 2. Deploy Oracle
  console.log("\n2. Deploying Oracle...");
  const QXCOracle = await hre.ethers.getContractFactory("QXCOracle");
  const oracle = await QXCOracle.deploy();
  await oracle.deployed();
  deployments.QXCOracle = oracle.address;
  console.log("✅ Oracle deployed to:", oracle.address);

  // 3. Deploy Staking
  console.log("\n3. Deploying Staking...");
  const QXCStaking = await hre.ethers.getContractFactory("QXCStaking");
  const staking = await QXCStaking.deploy(qxcToken.address);
  await staking.deployed();
  deployments.QXCStaking = staking.address;
  console.log("✅ Staking deployed to:", staking.address);

  // 4. Deploy DEX Aggregator
  console.log("\n4. Deploying DEX Aggregator...");
  const QXCDEXAggregator = await hre.ethers.getContractFactory("QXCDEXAggregator");
  const dex = await QXCDEXAggregator.deploy();
  await dex.deployed();
  deployments.QXCDEXAggregator = dex.address;
  console.log("✅ DEX Aggregator deployed to:", dex.address);

  // 5. Deploy Launchpad
  console.log("\n5. Deploying Launchpad...");
  const QXCLaunchpad = await hre.ethers.getContractFactory("QXCLaunchpad");
  const launchpad = await QXCLaunchpad.deploy(qxcToken.address);
  await launchpad.deployed();
  deployments.QXCLaunchpad = launchpad.address;
  console.log("✅ Launchpad deployed to:", launchpad.address);

  // 6. Deploy Insurance
  console.log("\n6. Deploying Insurance...");
  const QXCInsurance = await hre.ethers.getContractFactory("QXCInsurance");
  const insurance = await QXCInsurance.deploy();
  await insurance.deployed();
  deployments.QXCInsurance = insurance.address;
  console.log("✅ Insurance deployed to:", insurance.address);

  // 7. Deploy Layer 2
  console.log("\n7. Deploying Layer 2...");
  const QXCLayer2 = await hre.ethers.getContractFactory("QXCLayer2");
  const layer2 = await QXCLayer2.deploy();
  await layer2.deployed();
  deployments.QXCLayer2 = layer2.address;
  console.log("✅ Layer 2 deployed to:", layer2.address);

  // Save deployment addresses
  const deploymentData = {
    network: hre.network.name,
    timestamp: new Date().toISOString(),
    deployments: deployments
  };

  fs.writeFileSync(
    `./deployments/${hre.network.name}.json`,
    JSON.stringify(deploymentData, null, 2)
  );

  console.log("\n✅ All contracts deployed successfully!");
  console.log("\nDeployment addresses saved to deployments/" + hre.network.name + ".json");

  // Verify contracts on Etherscan
  if (hre.network.name !== "localhost" && hre.network.name !== "hardhat") {
    console.log("\nVerifying contracts on Etherscan...");
    
    for (const [name, address] of Object.entries(deployments)) {
      try {
        await hre.run("verify:verify", {
          address: address,
          constructorArguments: getConstructorArgs(name, deployments),
        });
        console.log(`✅ ${name} verified`);
      } catch (error) {
        console.log(`❌ Error verifying ${name}:`, error.message);
      }
    }
  }
}

function getConstructorArgs(contractName, deployments) {
  switch(contractName) {
    case "QXCToken":
      return [];
    case "QXCStaking":
    case "QXCLaunchpad":
      return [deployments.QXCToken];
    default:
      return [];
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });