#!/usr/bin/env node

const { ethers } = require("hardhat");
const axios = require("axios");
const fs = require("fs");
const path = require("path");

// Configuration
const CONFIG = {
    RPC_URL: process.env.RPC_URL || "http://localhost:8545",
    CONTRACTS: {
        token: process.env.TOKEN_ADDRESS,
        staking: process.env.STAKING_ADDRESS,
        governor: process.env.GOVERNOR_ADDRESS,
        timelock: process.env.TIMELOCK_ADDRESS
    },
    ALERTS: {
        SLACK_WEBHOOK: process.env.SLACK_WEBHOOK_URL,
        DISCORD_WEBHOOK: process.env.DISCORD_WEBHOOK_URL,
        EMAIL: process.env.ALERT_EMAIL
    },
    THRESHOLDS: {
        MIN_LIQUIDITY: ethers.utils.parseEther("10000"),
        MAX_GAS_PRICE: ethers.utils.parseUnits("200", "gwei"),
        MIN_REWARD_POOL: ethers.utils.parseEther("1000"),
        LARGE_TRANSFER: ethers.utils.parseEther("10000"),
        UNUSUAL_ACTIVITY_THRESHOLD: 100 // transactions per minute
    },
    MONITORING_INTERVAL: 60000, // 1 minute
    LOG_FILE: "monitoring.log"
};

// State tracking
const state = {
    lastBlock: 0,
    alerts: [],
    metrics: {
        totalTransactions: 0,
        totalVolume: ethers.BigNumber.from(0),
        uniqueAddresses: new Set(),
        gasSpent: ethers.BigNumber.from(0)
    }
};

// Alert system
class AlertSystem {
    async sendAlert(level, message, details) {
        const alert = {
            level,
            message,
            details,
            timestamp: new Date().toISOString()
        };
        
        console.log(`🚨 ${level}: ${message}`);
        if (details) console.log(`   Details: ${JSON.stringify(details)}`);
        
        // Log to file
        this.logToFile(alert);
        
        // Send to external services
        if (CONFIG.ALERTS.SLACK_WEBHOOK) {
            await this.sendToSlack(alert);
        }
        
        if (CONFIG.ALERTS.DISCORD_WEBHOOK) {
            await this.sendToDiscord(alert);
        }
        
        state.alerts.push(alert);
    }
    
    logToFile(alert) {
        const logEntry = `${alert.timestamp} [${alert.level}] ${alert.message}\n`;
        fs.appendFileSync(CONFIG.LOG_FILE, logEntry);
    }
    
    async sendToSlack(alert) {
        try {
            await axios.post(CONFIG.ALERTS.SLACK_WEBHOOK, {
                text: `*${alert.level}*: ${alert.message}`,
                attachments: alert.details ? [{
                    color: alert.level === "CRITICAL" ? "danger" : "warning",
                    fields: Object.entries(alert.details).map(([key, value]) => ({
                        title: key,
                        value: String(value),
                        short: true
                    }))
                }] : []
            });
        } catch (error) {
            console.error("Failed to send Slack alert:", error.message);
        }
    }
    
    async sendToDiscord(alert) {
        try {
            await axios.post(CONFIG.ALERTS.DISCORD_WEBHOOK, {
                content: `**${alert.level}**: ${alert.message}`,
                embeds: alert.details ? [{
                    color: alert.level === "CRITICAL" ? 0xFF0000 : 0xFFFF00,
                    fields: Object.entries(alert.details).map(([key, value]) => ({
                        name: key,
                        value: String(value),
                        inline: true
                    }))
                }] : []
            });
        } catch (error) {
            console.error("Failed to send Discord alert:", error.message);
        }
    }
}

const alertSystem = new AlertSystem();

// Monitoring functions
class Monitor {
    constructor(provider) {
        this.provider = provider;
        this.contracts = {};
    }
    
    async initialize() {
        console.log("🔍 Initializing monitors...\n");
        
        // Load contract ABIs and create instances
        if (CONFIG.CONTRACTS.token) {
            this.contracts.token = await ethers.getContractAt(
                "QXCTokenV2",
                CONFIG.CONTRACTS.token,
                this.provider
            );
            console.log(`✅ Token contract loaded: ${CONFIG.CONTRACTS.token}`);
        }
        
        if (CONFIG.CONTRACTS.staking) {
            this.contracts.staking = await ethers.getContractAt(
                "QXCStakingV2",
                CONFIG.CONTRACTS.staking,
                this.provider
            );
            console.log(`✅ Staking contract loaded: ${CONFIG.CONTRACTS.staking}`);
        }
        
        // Get starting block
        state.lastBlock = await this.provider.getBlockNumber();
        console.log(`📦 Starting from block: ${state.lastBlock}\n`);
    }
    
    async monitorBlocks() {
        const currentBlock = await this.provider.getBlockNumber();
        
        if (currentBlock <= state.lastBlock) return;
        
        console.log(`📦 Processing blocks ${state.lastBlock + 1} to ${currentBlock}`);
        
        // Process each block
        for (let blockNumber = state.lastBlock + 1; blockNumber <= currentBlock; blockNumber++) {
            await this.processBlock(blockNumber);
        }
        
        state.lastBlock = currentBlock;
    }
    
    async processBlock(blockNumber) {
        try {
            const block = await this.provider.getBlockWithTransactions(blockNumber);
            
            // Check gas price
            const gasPrice = block.baseFeePerGas || ethers.BigNumber.from(0);
            if (gasPrice.gt(CONFIG.THRESHOLDS.MAX_GAS_PRICE)) {
                await alertSystem.sendAlert("WARNING", "High gas price detected", {
                    gasPrice: ethers.utils.formatUnits(gasPrice, "gwei") + " gwei",
                    block: blockNumber
                });
            }
            
            // Process transactions
            for (const tx of block.transactions) {
                await this.processTransaction(tx);
            }
            
            // Check transaction rate
            const txRate = block.transactions.length;
            if (txRate > CONFIG.THRESHOLDS.UNUSUAL_ACTIVITY_THRESHOLD) {
                await alertSystem.sendAlert("WARNING", "Unusual activity detected", {
                    transactions: txRate,
                    block: blockNumber
                });
            }
            
        } catch (error) {
            console.error(`Error processing block ${blockNumber}:`, error.message);
        }
    }
    
    async processTransaction(tx) {
        // Update metrics
        state.metrics.totalTransactions++;
        state.metrics.uniqueAddresses.add(tx.from);
        if (tx.to) state.metrics.uniqueAddresses.add(tx.to);
        
        // Check if transaction involves our contracts
        if (this.contracts.token && tx.to === this.contracts.token.address) {
            await this.monitorTokenTransaction(tx);
        }
        
        if (this.contracts.staking && tx.to === this.contracts.staking.address) {
            await this.monitorStakingTransaction(tx);
        }
    }
    
    async monitorTokenTransaction(tx) {
        try {
            const receipt = await this.provider.getTransactionReceipt(tx.hash);
            
            // Parse events
            for (const log of receipt.logs) {
                if (log.address === this.contracts.token.address) {
                    const parsed = this.contracts.token.interface.parseLog(log);
                    
                    if (parsed.name === "Transfer") {
                        const amount = parsed.args.value;
                        state.metrics.totalVolume = state.metrics.totalVolume.add(amount);
                        
                        // Check for large transfers
                        if (amount.gt(CONFIG.THRESHOLDS.LARGE_TRANSFER)) {
                            await alertSystem.sendAlert("INFO", "Large transfer detected", {
                                from: parsed.args.from,
                                to: parsed.args.to,
                                amount: ethers.utils.formatEther(amount) + " QXC",
                                txHash: tx.hash
                            });
                        }
                    }
                    
                    if (parsed.name === "Paused") {
                        await alertSystem.sendAlert("CRITICAL", "Token contract paused!", {
                            txHash: tx.hash
                        });
                    }
                    
                    if (parsed.name === "Blacklisted") {
                        await alertSystem.sendAlert("WARNING", "Address blacklisted", {
                            address: parsed.args.account,
                            txHash: tx.hash
                        });
                    }
                }
            }
        } catch (error) {
            console.error("Error monitoring token transaction:", error.message);
        }
    }
    
    async monitorStakingTransaction(tx) {
        try {
            const receipt = await this.provider.getTransactionReceipt(tx.hash);
            
            // Parse events
            for (const log of receipt.logs) {
                if (log.address === this.contracts.staking.address) {
                    const parsed = this.contracts.staking.interface.parseLog(log);
                    
                    if (parsed.name === "EmergencyWithdraw") {
                        await alertSystem.sendAlert("WARNING", "Emergency withdrawal", {
                            user: parsed.args.user,
                            amount: ethers.utils.formatEther(parsed.args.amount) + " QXC",
                            txHash: tx.hash
                        });
                    }
                    
                    if (parsed.name === "Slashed") {
                        await alertSystem.sendAlert("CRITICAL", "User slashed!", {
                            user: parsed.args.user,
                            amount: ethers.utils.formatEther(parsed.args.amount) + " QXC",
                            txHash: tx.hash
                        });
                    }
                }
            }
        } catch (error) {
            console.error("Error monitoring staking transaction:", error.message);
        }
    }
    
    async checkContractStates() {
        console.log("\n📊 Checking contract states...");
        
        // Check token state
        if (this.contracts.token) {
            const totalSupply = await this.contracts.token.totalSupply();
            const paused = await this.contracts.token.paused();
            const tradingEnabled = await this.contracts.token.tradingEnabled();
            
            console.log(`   Token Supply: ${ethers.utils.formatEther(totalSupply)} QXC`);
            console.log(`   Paused: ${paused}`);
            console.log(`   Trading: ${tradingEnabled}`);
            
            if (paused) {
                await alertSystem.sendAlert("CRITICAL", "Token contract is paused!");
            }
        }
        
        // Check staking state
        if (this.contracts.staking) {
            const totalStaked = await this.contracts.staking.totalStaked();
            const rewardPool = await this.contracts.staking.rewardPool();
            
            console.log(`   Total Staked: ${ethers.utils.formatEther(totalStaked)} QXC`);
            console.log(`   Reward Pool: ${ethers.utils.formatEther(rewardPool)} QXC`);
            
            if (rewardPool.lt(CONFIG.THRESHOLDS.MIN_REWARD_POOL)) {
                await alertSystem.sendAlert("WARNING", "Low reward pool", {
                    current: ethers.utils.formatEther(rewardPool) + " QXC",
                    threshold: ethers.utils.formatEther(CONFIG.THRESHOLDS.MIN_REWARD_POOL) + " QXC"
                });
            }
        }
    }
    
    async generateReport() {
        console.log("\n📈 Generating report...");
        
        const report = {
            timestamp: new Date().toISOString(),
            blocksProcessed: state.lastBlock,
            metrics: {
                totalTransactions: state.metrics.totalTransactions,
                totalVolume: ethers.utils.formatEther(state.metrics.totalVolume) + " QXC",
                uniqueAddresses: state.metrics.uniqueAddresses.size,
                gasSpent: ethers.utils.formatEther(state.metrics.gasSpent) + " ETH"
            },
            alerts: state.alerts.length,
            recentAlerts: state.alerts.slice(-5)
        };
        
        // Save report
        const reportPath = path.join(__dirname, "..", "reports", `report-${Date.now()}.json`);
        const dir = path.dirname(reportPath);
        
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        
        console.log(`   Report saved to: ${reportPath}`);
        console.log(`   Total transactions: ${report.metrics.totalTransactions}`);
        console.log(`   Total volume: ${report.metrics.totalVolume}`);
        console.log(`   Unique addresses: ${report.metrics.uniqueAddresses}`);
        console.log(`   Alerts triggered: ${report.alerts}`);
        
        return report;
    }
}

// Main monitoring loop
async function main() {
    console.log("=====================================");
    console.log("    QXC DeFi Ecosystem Monitor");
    console.log("=====================================\n");
    
    try {
        // Connect to provider
        const provider = new ethers.providers.JsonRpcProvider(CONFIG.RPC_URL);
        const network = await provider.getNetwork();
        
        console.log(`Connected to network: ${network.name || "Unknown"} (Chain ID: ${network.chainId})`);
        console.log(`RPC URL: ${CONFIG.RPC_URL}\n`);
        
        // Initialize monitor
        const monitor = new Monitor(provider);
        await monitor.initialize();
        
        console.log("🚀 Starting monitoring loop...\n");
        console.log(`Monitoring interval: ${CONFIG.MONITORING_INTERVAL / 1000} seconds`);
        console.log("Press Ctrl+C to stop\n");
        
        // Initial check
        await monitor.checkContractStates();
        
        // Start monitoring loop
        setInterval(async () => {
            try {
                await monitor.monitorBlocks();
                
                // Periodic state check (every 10 intervals)
                if (state.metrics.totalTransactions % 10 === 0) {
                    await monitor.checkContractStates();
                }
                
                // Generate report every hour
                if (state.metrics.totalTransactions % 60 === 0) {
                    await monitor.generateReport();
                }
                
            } catch (error) {
                console.error("Monitor error:", error.message);
                await alertSystem.sendAlert("ERROR", "Monitor error", {
                    error: error.message
                });
            }
        }, CONFIG.MONITORING_INTERVAL);
        
        // Handle graceful shutdown
        process.on("SIGINT", async () => {
            console.log("\n\n🛑 Stopping monitor...");
            
            // Generate final report
            const finalReport = await monitor.generateReport();
            
            console.log("\n=====================================");
            console.log("    Monitor Stopped");
            console.log("=====================================");
            console.log(`Final report saved`);
            console.log(`Total runtime transactions: ${finalReport.metrics.totalTransactions}`);
            
            process.exit(0);
        });
        
    } catch (error) {
        console.error("❌ Failed to start monitor:", error.message);
        process.exit(1);
    }
}

// Start monitoring
main();