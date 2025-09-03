#!/usr/bin/env node

const { ethers } = require("hardhat");
const readline = require("readline");

// ANSI color codes
const colors = {
    red: "\x1b[31m",
    yellow: "\x1b[33m",
    green: "\x1b[32m",
    cyan: "\x1b[36m",
    reset: "\x1b[0m"
};

// Configuration
const CONTRACTS = {
    token: process.env.TOKEN_ADDRESS,
    staking: process.env.STAKING_ADDRESS,
    amm: process.env.AMM_ADDRESS,
    lending: process.env.LENDING_ADDRESS,
    governor: process.env.GOVERNOR_ADDRESS
};

// Create readline interface for user input
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

function askQuestion(question) {
    return new Promise((resolve) => {
        rl.question(question, (answer) => {
            resolve(answer);
        });
    });
}

async function checkCurrentStatus(provider) {
    console.log(`\n${colors.cyan}📊 Checking current contract status...${colors.reset}\n`);
    
    const status = {};
    
    // Check token
    if (CONTRACTS.token) {
        try {
            const token = await ethers.getContractAt("QXCTokenV2", CONTRACTS.token, provider);
            const paused = await token.paused();
            const tradingEnabled = await token.tradingEnabled();
            
            status.token = {
                address: CONTRACTS.token,
                paused,
                tradingEnabled
            };
            
            console.log(`Token (${CONTRACTS.token}):`);
            console.log(`  Paused: ${paused ? colors.red + "YES" + colors.reset : colors.green + "NO" + colors.reset}`);
            console.log(`  Trading: ${tradingEnabled ? colors.green + "ENABLED" + colors.reset : colors.red + "DISABLED" + colors.reset}`);
        } catch (error) {
            console.log(`Token: ${colors.red}ERROR - ${error.message}${colors.reset}`);
        }
    }
    
    // Check staking
    if (CONTRACTS.staking) {
        try {
            const staking = await ethers.getContractAt("QXCStakingV2", CONTRACTS.staking, provider);
            const paused = await staking.paused();
            
            status.staking = {
                address: CONTRACTS.staking,
                paused
            };
            
            console.log(`\nStaking (${CONTRACTS.staking}):`);
            console.log(`  Paused: ${paused ? colors.red + "YES" + colors.reset : colors.green + "NO" + colors.reset}`);
        } catch (error) {
            console.log(`Staking: ${colors.red}ERROR - ${error.message}${colors.reset}`);
        }
    }
    
    return status;
}

async function pauseContract(contract, name, signer) {
    try {
        console.log(`\n${colors.yellow}⏸️  Pausing ${name}...${colors.reset}`);
        
        const tx = await contract.pause({ gasLimit: 100000 });
        console.log(`  Transaction: ${tx.hash}`);
        
        const receipt = await tx.wait();
        console.log(`  ${colors.green}✅ ${name} paused successfully!${colors.reset}`);
        console.log(`  Gas used: ${receipt.gasUsed.toString()}`);
        
        return true;
    } catch (error) {
        console.log(`  ${colors.red}❌ Failed to pause ${name}: ${error.message}${colors.reset}`);
        return false;
    }
}

async function unpauseContract(contract, name, signer) {
    try {
        console.log(`\n${colors.green}▶️  Unpausing ${name}...${colors.reset}`);
        
        const tx = await contract.unpause({ gasLimit: 100000 });
        console.log(`  Transaction: ${tx.hash}`);
        
        const receipt = await tx.wait();
        console.log(`  ${colors.green}✅ ${name} unpaused successfully!${colors.reset}`);
        console.log(`  Gas used: ${receipt.gasUsed.toString()}`);
        
        return true;
    } catch (error) {
        console.log(`  ${colors.red}❌ Failed to unpause ${name}: ${error.message}${colors.reset}`);
        return false;
    }
}

async function emergencyPauseAll(signer) {
    console.log(`\n${colors.red}🚨 EMERGENCY PAUSE - PAUSING ALL CONTRACTS 🚨${colors.reset}\n`);
    
    const results = [];
    
    // Pause token
    if (CONTRACTS.token) {
        const token = await ethers.getContractAt("QXCTokenV2", CONTRACTS.token, signer);
        const result = await pauseContract(token, "Token", signer);
        results.push({ name: "Token", success: result });
    }
    
    // Pause staking
    if (CONTRACTS.staking) {
        const staking = await ethers.getContractAt("QXCStakingV2", CONTRACTS.staking, signer);
        const result = await pauseContract(staking, "Staking", signer);
        results.push({ name: "Staking", success: result });
    }
    
    // Pause AMM
    if (CONTRACTS.amm) {
        const amm = await ethers.getContractAt("QXCAutomatedMarketMaker", CONTRACTS.amm, signer);
        const result = await pauseContract(amm, "AMM", signer);
        results.push({ name: "AMM", success: result });
    }
    
    // Pause lending
    if (CONTRACTS.lending) {
        const lending = await ethers.getContractAt("QXCLending", CONTRACTS.lending, signer);
        const result = await pauseContract(lending, "Lending", signer);
        results.push({ name: "Lending", success: result });
    }
    
    return results;
}

async function emergencyUnpauseAll(signer) {
    console.log(`\n${colors.green}✅ RESUMING OPERATIONS - UNPAUSING ALL CONTRACTS ✅${colors.reset}\n`);
    
    const results = [];
    
    // Unpause token
    if (CONTRACTS.token) {
        const token = await ethers.getContractAt("QXCTokenV2", CONTRACTS.token, signer);
        const result = await unpauseContract(token, "Token", signer);
        results.push({ name: "Token", success: result });
    }
    
    // Unpause staking
    if (CONTRACTS.staking) {
        const staking = await ethers.getContractAt("QXCStakingV2", CONTRACTS.staking, signer);
        const result = await unpauseContract(staking, "Staking", signer);
        results.push({ name: "Staking", success: result });
    }
    
    // Unpause AMM
    if (CONTRACTS.amm) {
        const amm = await ethers.getContractAt("QXCAutomatedMarketMaker", CONTRACTS.amm, signer);
        const result = await unpauseContract(amm, "AMM", signer);
        results.push({ name: "AMM", success: result });
    }
    
    // Unpause lending
    if (CONTRACTS.lending) {
        const lending = await ethers.getContractAt("QXCLending", CONTRACTS.lending, signer);
        const result = await unpauseContract(lending, "Lending", signer);
        results.push({ name: "Lending", success: result });
    }
    
    return results;
}

async function main() {
    console.log(`${colors.red}=====================================`);
    console.log(`    🚨 EMERGENCY CONTROL PANEL 🚨`);
    console.log(`=====================================${colors.reset}\n`);
    
    try {
        // Get signer
        const [signer] = await ethers.getSigners();
        const provider = signer.provider;
        const network = await provider.getNetwork();
        
        console.log(`Network: ${network.name || "Unknown"} (Chain ID: ${network.chainId})`);
        console.log(`Operator: ${signer.address}`);
        
        // Check if operator has necessary roles
        console.log(`\n${colors.yellow}⚠️  WARNING: You must have PAUSER_ROLE to execute emergency functions${colors.reset}`);
        
        // Check current status
        const status = await checkCurrentStatus(provider);
        
        // Show menu
        console.log(`\n${colors.cyan}═══════════════════════════════`);
        console.log(`         ACTIONS MENU`);
        console.log(`═══════════════════════════════${colors.reset}`);
        console.log(`1. ${colors.red}EMERGENCY PAUSE ALL${colors.reset} - Stop all contract operations`);
        console.log(`2. ${colors.green}RESUME ALL${colors.reset} - Unpause all contracts`);
        console.log(`3. ${colors.yellow}PAUSE SPECIFIC${colors.reset} - Pause individual contract`);
        console.log(`4. ${colors.green}UNPAUSE SPECIFIC${colors.reset} - Unpause individual contract`);
        console.log(`5. ${colors.cyan}REFRESH STATUS${colors.reset} - Check current status`);
        console.log(`6. ${colors.red}EXIT${colors.reset} - Exit emergency panel\n`);
        
        const action = await askQuestion("Select action (1-6): ");
        
        switch (action) {
            case "1": {
                // Emergency pause all
                const confirm = await askQuestion(
                    `\n${colors.red}⚠️  This will PAUSE ALL contracts. Are you sure? (yes/no): ${colors.reset}`
                );
                
                if (confirm.toLowerCase() === "yes") {
                    const results = await emergencyPauseAll(signer);
                    
                    console.log(`\n${colors.cyan}═══════════════════════════════`);
                    console.log(`       PAUSE RESULTS`);
                    console.log(`═══════════════════════════════${colors.reset}`);
                    
                    results.forEach((result) => {
                        const icon = result.success ? "✅" : "❌";
                        const color = result.success ? colors.green : colors.red;
                        console.log(`${icon} ${result.name}: ${color}${result.success ? "PAUSED" : "FAILED"}${colors.reset}`);
                    });
                    
                    const allSuccess = results.every(r => r.success);
                    
                    if (allSuccess) {
                        console.log(`\n${colors.green}✅ All contracts paused successfully!${colors.reset}`);
                        console.log(`${colors.yellow}⚠️  Remember to investigate the issue and unpause when safe${colors.reset}`);
                    } else {
                        console.log(`\n${colors.red}⚠️  Some contracts failed to pause. Manual intervention required!${colors.reset}`);
                    }
                }
                break;
            }
            
            case "2": {
                // Resume all
                const confirm = await askQuestion(
                    `\n${colors.green}⚠️  This will UNPAUSE ALL contracts. Are you sure the issue is resolved? (yes/no): ${colors.reset}`
                );
                
                if (confirm.toLowerCase() === "yes") {
                    const results = await emergencyUnpauseAll(signer);
                    
                    console.log(`\n${colors.cyan}═══════════════════════════════`);
                    console.log(`      UNPAUSE RESULTS`);
                    console.log(`═══════════════════════════════${colors.reset}`);
                    
                    results.forEach((result) => {
                        const icon = result.success ? "✅" : "❌";
                        const color = result.success ? colors.green : colors.red;
                        console.log(`${icon} ${result.name}: ${color}${result.success ? "RESUMED" : "FAILED"}${colors.reset}`);
                    });
                    
                    const allSuccess = results.every(r => r.success);
                    
                    if (allSuccess) {
                        console.log(`\n${colors.green}✅ All contracts resumed successfully!${colors.reset}`);
                        console.log(`${colors.cyan}ℹ️  Normal operations have been restored${colors.reset}`);
                    } else {
                        console.log(`\n${colors.red}⚠️  Some contracts failed to unpause. Manual intervention required!${colors.reset}`);
                    }
                }
                break;
            }
            
            case "3": {
                // Pause specific
                console.log(`\n${colors.yellow}Select contract to pause:${colors.reset}`);
                console.log("1. Token");
                console.log("2. Staking");
                console.log("3. AMM");
                console.log("4. Lending");
                
                const choice = await askQuestion("Select (1-4): ");
                
                let contractAddress, contractName;
                switch (choice) {
                    case "1":
                        contractAddress = CONTRACTS.token;
                        contractName = "Token";
                        break;
                    case "2":
                        contractAddress = CONTRACTS.staking;
                        contractName = "Staking";
                        break;
                    case "3":
                        contractAddress = CONTRACTS.amm;
                        contractName = "AMM";
                        break;
                    case "4":
                        contractAddress = CONTRACTS.lending;
                        contractName = "Lending";
                        break;
                    default:
                        console.log(`${colors.red}Invalid selection${colors.reset}`);
                        break;
                }
                
                if (contractAddress && contractName) {
                    const contract = await ethers.getContractAt(`QXC${contractName}V2`, contractAddress, signer);
                    await pauseContract(contract, contractName, signer);
                }
                break;
            }
            
            case "4": {
                // Unpause specific
                console.log(`\n${colors.green}Select contract to unpause:${colors.reset}`);
                console.log("1. Token");
                console.log("2. Staking");
                console.log("3. AMM");
                console.log("4. Lending");
                
                const choice = await askQuestion("Select (1-4): ");
                
                let contractAddress, contractName;
                switch (choice) {
                    case "1":
                        contractAddress = CONTRACTS.token;
                        contractName = "Token";
                        break;
                    case "2":
                        contractAddress = CONTRACTS.staking;
                        contractName = "Staking";
                        break;
                    case "3":
                        contractAddress = CONTRACTS.amm;
                        contractName = "AMM";
                        break;
                    case "4":
                        contractAddress = CONTRACTS.lending;
                        contractName = "Lending";
                        break;
                    default:
                        console.log(`${colors.red}Invalid selection${colors.reset}`);
                        break;
                }
                
                if (contractAddress && contractName) {
                    const contract = await ethers.getContractAt(`QXC${contractName}V2`, contractAddress, signer);
                    await unpauseContract(contract, contractName, signer);
                }
                break;
            }
            
            case "5": {
                // Refresh status
                await checkCurrentStatus(provider);
                break;
            }
            
            case "6": {
                // Exit
                console.log(`\n${colors.cyan}Exiting emergency panel...${colors.reset}`);
                break;
            }
            
            default:
                console.log(`${colors.red}Invalid selection${colors.reset}`);
        }
        
        rl.close();
        
    } catch (error) {
        console.error(`\n${colors.red}❌ Emergency action failed:${colors.reset}`, error.message);
        rl.close();
        process.exit(1);
    }
}

// Run emergency panel
main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });