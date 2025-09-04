require("@nomicfoundation/hardhat-toolbox");
require("@openzeppelin/hardhat-upgrades");
require("hardhat-contract-sizer");
require("hardhat-gas-reporter");
require("solidity-coverage");
require("dotenv").config({ path: ".env.production" });

// Production configuration with safety checks
const MAINNET_RPC_URL = process.env.MAINNET_RPC_URL;
const SEPOLIA_RPC_URL = process.env.SEPOLIA_RPC_URL;
const DEPLOYER_PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY;
const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY;

// Safety: Prevent using test keys on mainnet
if (process.env.NETWORK === "mainnet") {
    if (!DEPLOYER_PRIVATE_KEY || DEPLOYER_PRIVATE_KEY.includes("0xac0974")) {
        console.error("ERROR: Invalid private key for mainnet deployment!");
        process.exit(1);
    }
    if (!MAINNET_RPC_URL || MAINNET_RPC_URL.includes("localhost")) {
        console.error("ERROR: Invalid RPC URL for mainnet!");
        process.exit(1);
    }
}

module.exports = {
    solidity: {
        version: "0.8.20",
        settings: {
            optimizer: {
                enabled: true,
                runs: 200,
                details: {
                    yul: true,
                    yulDetails: {
                        stackAllocation: true,
                        optimizerSteps: "dhfoDgvulfnTUtnIf"
                    }
                }
            },
            viaIR: true,
            metadata: {
                bytecodeHash: "ipfs"
            }
        }
    },
    
    networks: {
        // Production Networks
        mainnet: {
            url: MAINNET_RPC_URL || "",
            chainId: 1,
            accounts: DEPLOYER_PRIVATE_KEY ? [DEPLOYER_PRIVATE_KEY] : [],
            gasPrice: 30000000000, // 30 gwei
            gasMultiplier: 1.2,
            timeout: 60000,
            confirmations: 5
        },
        
        // Test Networks
        sepolia: {
            url: SEPOLIA_RPC_URL || "",
            chainId: 11155111,
            accounts: DEPLOYER_PRIVATE_KEY ? [DEPLOYER_PRIVATE_KEY] : [],
            gasPrice: "auto",
            confirmations: 2
        },
        
        // Local Development
        hardhat: {
            chainId: 31337,
            forking: process.env.FORK_MAINNET ? {
                url: MAINNET_RPC_URL,
                blockNumber: 18000000
            } : undefined,
            mining: {
                auto: true,
                interval: 5000
            }
        }
    },
    
    etherscan: {
        apiKey: {
            mainnet: ETHERSCAN_API_KEY,
            sepolia: ETHERSCAN_API_KEY
        }
    },
    
    gasReporter: {
        enabled: true,
        currency: "USD",
        gasPrice: 30,
        coinmarketcap: process.env.COINMARKETCAP_API_KEY,
        outputFile: "gas-report.txt",
        noColors: true
    },
    
    contractSizer: {
        alphaSort: false,
        disambiguatePaths: false,
        runOnCompile: true,
        strict: true,
        only: ["QXCTokenProduction", "TimelockMultiSig", "QXCStakingFixed"]
    },
    
    paths: {
        sources: "./contracts",
        tests: "./test",
        cache: "./cache",
        artifacts: "./artifacts"
    },
    
    mocha: {
        timeout: 60000
    },
    
    // Security settings
    defender: {
        apiKey: process.env.DEFENDER_API_KEY,
        apiSecret: process.env.DEFENDER_API_SECRET
    }
};