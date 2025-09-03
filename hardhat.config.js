require("@nomicfoundation/hardhat-toolbox");
require("@openzeppelin/hardhat-upgrades");
require("hardhat-contract-sizer");
require("hardhat-gas-reporter");
require("solidity-coverage");
require("dotenv").config();

// Ensure we have required environment variables
const SEPOLIA_RPC_URL = process.env.SEPOLIA_RPC_URL || "https://rpc.sepolia.org";
const MAINNET_RPC_URL = process.env.MAINNET_RPC_URL || "https://eth.llamarpc.com";
const PRIVATE_KEY = process.env.PRIVATE_KEY || "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY || "";

// Safety check for mainnet
if (process.env.NETWORK === "mainnet" && PRIVATE_KEY.startsWith("0xac0974")) {
    console.error("ERROR: Cannot use default test key for mainnet!");
    process.exit(1);
}

module.exports = {
    solidity: {
        version: "0.8.19",
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
            viaIR: true
        }
    },
    networks: {
        hardhat: {
            chainId: 31337,
            forking: process.env.FORK_MAINNET === "true" ? {
                url: MAINNET_RPC_URL,
                blockNumber: 18900000
            } : undefined,
            mining: {
                auto: true,
                interval: 0
            },
            gasPrice: 1000000000, // 1 gwei
            initialBaseFeePerGas: 0
        },
        localhost: {
            url: "http://127.0.0.1:8545",
            chainId: 31337
        },
        sepolia: {
            url: SEPOLIA_RPC_URL,
            accounts: PRIVATE_KEY !== "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80" 
                ? [PRIVATE_KEY] 
                : [],
            chainId: 11155111,
            gasPrice: "auto",
            gasMultiplier: 1.2
        },
        mainnet: {
            url: MAINNET_RPC_URL,
            accounts: process.env.MAINNET_PRIVATE_KEY ? [process.env.MAINNET_PRIVATE_KEY] : [],
            chainId: 1,
            gasPrice: "auto",
            gasMultiplier: 1.1
        }
    },
    etherscan: {
        apiKey: {
            mainnet: ETHERSCAN_API_KEY,
            sepolia: ETHERSCAN_API_KEY
        }
    },
    gasReporter: {
        enabled: process.env.REPORT_GAS === "true",
        currency: "USD",
        coinmarketcap: process.env.COINMARKETCAP_API_KEY,
        outputFile: "gas-report.txt",
        noColors: true,
        excludeContracts: ["contracts/test/", "contracts/mock/"]
    },
    contractSizer: {
        alphaSort: true,
        disambiguatePaths: false,
        runOnCompile: true,
        strict: true,
        only: []
    },
    paths: {
        sources: "./contracts",
        tests: "./test",
        cache: "./cache",
        artifacts: "./artifacts"
    },
    mocha: {
        timeout: 40000
    }
};