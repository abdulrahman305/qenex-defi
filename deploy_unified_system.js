#!/usr/bin/env node

/**
 * QXC Unified System Deployment Script
 * Deploys and integrates all components of the financial ecosystem
 */

const { ethers } = require('hardhat');
const fs = require('fs');
const path = require('path');

// Deployment configuration
const CONFIG = {
    network: process.env.NETWORK || 'localhost',
    qxcTokenAddress: process.env.QXC_TOKEN_ADDRESS || null,
    initialLiquidity: {
        qxc: ethers.utils.parseEther('10000'),
        usdc: ethers.utils.parseEther('10000'),
        dai: ethers.utils.parseEther('10000')
    },
    stakingRewardPool: ethers.utils.parseEther('100000'),
    governanceTreasury: ethers.utils.parseEther('50000')
};

// Contract ABIs and bytecodes would be loaded from compiled artifacts
const CONTRACTS = {
    QXCToken: 'FIXED_QXCToken',
    QXCStaking: 'FIXED_QXCStaking',
    QXCUnifiedProtocol: 'QXCUnifiedProtocol',
    QXCAutomatedMarketMaker: 'QXCAutomatedMarketMaker',
    QXCGovernance: 'QXCGovernance'
};

class UnifiedSystemDeployer {
    constructor() {
        this.deployedContracts = {};
        this.signer = null;
    }

    async initialize() {
        console.log('🚀 Initializing QXC Unified System Deployment...\n');
        
        // Get signer
        const signers = await ethers.getSigners();
        this.signer = signers[0];
        console.log(`📝 Deploying from address: ${this.signer.address}`);
        
        // Check balance
        const balance = await this.signer.getBalance();
        console.log(`💰 Balance: ${ethers.utils.formatEther(balance)} ETH\n`);
        
        if (balance.lt(ethers.utils.parseEther('0.1'))) {
            throw new Error('Insufficient ETH balance for deployment');
        }
    }

    async deployQXCToken() {
        console.log('1️⃣  Deploying QXC Token...');
        
        if (CONFIG.qxcTokenAddress) {
            console.log(`   ✅ Using existing token at ${CONFIG.qxcTokenAddress}`);
            this.deployedContracts.QXCToken = CONFIG.qxcTokenAddress;
            return;
        }
        
        const QXCToken = await ethers.getContractFactory(CONTRACTS.QXCToken);
        const qxcToken = await QXCToken.deploy();
        await qxcToken.deployed();
        
        this.deployedContracts.QXCToken = qxcToken.address;
        console.log(`   ✅ QXC Token deployed at: ${qxcToken.address}`);
        
        // Verify initial supply
        const totalSupply = await qxcToken.totalSupply();
        console.log(`   📊 Initial supply: ${ethers.utils.formatEther(totalSupply)} QXC\n`);
    }

    async deployStaking() {
        console.log('2️⃣  Deploying Staking Contract...');
        
        const QXCStaking = await ethers.getContractFactory(CONTRACTS.QXCStaking);
        const staking = await QXCStaking.deploy(this.deployedContracts.QXCToken);
        await staking.deployed();
        
        this.deployedContracts.QXCStaking = staking.address;
        console.log(`   ✅ Staking deployed at: ${staking.address}`);
        
        // Fund reward pool
        console.log(`   💰 Funding reward pool with ${ethers.utils.formatEther(CONFIG.stakingRewardPool)} QXC...`);
        const qxcToken = await ethers.getContractAt(CONTRACTS.QXCToken, this.deployedContracts.QXCToken);
        
        await qxcToken.approve(staking.address, CONFIG.stakingRewardPool);
        await staking.fundRewardPool(CONFIG.stakingRewardPool);
        console.log(`   ✅ Reward pool funded\n`);
    }

    async deployUnifiedProtocol() {
        console.log('3️⃣  Deploying Unified Protocol...');
        
        const QXCUnifiedProtocol = await ethers.getContractFactory(CONTRACTS.QXCUnifiedProtocol);
        const unifiedProtocol = await QXCUnifiedProtocol.deploy(this.deployedContracts.QXCToken);
        await unifiedProtocol.deployed();
        
        this.deployedContracts.QXCUnifiedProtocol = unifiedProtocol.address;
        console.log(`   ✅ Unified Protocol deployed at: ${unifiedProtocol.address}`);
        
        // Initialize components
        console.log('   🔧 Initializing protocol components...');
        await unifiedProtocol.initializeComponents();
        
        // Get component addresses
        const identityAddress = await unifiedProtocol.identitySystem();
        const paymentsAddress = await unifiedProtocol.paymentSystem();
        const lendingAddress = await unifiedProtocol.lendingSystem();
        const supplyChainAddress = await unifiedProtocol.supplyChainSystem();
        const yieldAddress = await unifiedProtocol.yieldSystem();
        
        console.log(`   📍 Identity System: ${identityAddress}`);
        console.log(`   📍 Payment System: ${paymentsAddress}`);
        console.log(`   📍 Lending System: ${lendingAddress}`);
        console.log(`   📍 Supply Chain: ${supplyChainAddress}`);
        console.log(`   📍 Yield Optimizer: ${yieldAddress}\n`);
    }

    async deployAMM() {
        console.log('4️⃣  Deploying Automated Market Maker...');
        
        const QXCAutomatedMarketMaker = await ethers.getContractFactory(CONTRACTS.QXCAutomatedMarketMaker);
        const amm = await QXCAutomatedMarketMaker.deploy(this.deployedContracts.QXCToken);
        await amm.deployed();
        
        this.deployedContracts.QXCAutomatedMarketMaker = amm.address;
        console.log(`   ✅ AMM deployed at: ${amm.address}`);
        
        // Deploy mock stablecoins for testing
        console.log('   🪙 Deploying test stablecoins...');
        const MockToken = await ethers.getContractFactory('MockERC20');
        
        const usdc = await MockToken.deploy('USD Coin', 'USDC', 6);
        await usdc.deployed();
        console.log(`   📍 Mock USDC: ${usdc.address}`);
        
        const dai = await MockToken.deploy('Dai Stablecoin', 'DAI', 18);
        await dai.deployed();
        console.log(`   📍 Mock DAI: ${dai.address}`);
        
        // Authorize tokens
        console.log('   🔑 Authorizing tokens for AMM...');
        await amm.authorizeToken(usdc.address);
        await amm.authorizeToken(dai.address);
        
        // Create initial liquidity pools
        console.log('   💧 Creating liquidity pools...');
        const qxcToken = await ethers.getContractAt(CONTRACTS.QXCToken, this.deployedContracts.QXCToken);
        
        // Mint test tokens
        await usdc.mint(this.signer.address, CONFIG.initialLiquidity.usdc);
        await dai.mint(this.signer.address, CONFIG.initialLiquidity.dai);
        
        // Approve AMM
        await qxcToken.approve(amm.address, CONFIG.initialLiquidity.qxc.mul(2));
        await usdc.approve(amm.address, CONFIG.initialLiquidity.usdc);
        await dai.approve(amm.address, CONFIG.initialLiquidity.dai);
        
        // Create pools
        await amm.createPool(usdc.address, CONFIG.initialLiquidity.qxc, CONFIG.initialLiquidity.usdc);
        console.log(`   ✅ QXC/USDC pool created`);
        
        await amm.createPool(dai.address, CONFIG.initialLiquidity.qxc, CONFIG.initialLiquidity.dai);
        console.log(`   ✅ QXC/DAI pool created\n`);
        
        this.deployedContracts.MockUSDC = usdc.address;
        this.deployedContracts.MockDAI = dai.address;
    }

    async deployGovernance() {
        console.log('5️⃣  Deploying Governance System...');
        
        const QXCGovernance = await ethers.getContractFactory(CONTRACTS.QXCGovernance);
        const governance = await QXCGovernance.deploy(this.deployedContracts.QXCToken);
        await governance.deployed();
        
        this.deployedContracts.QXCGovernance = governance.address;
        console.log(`   ✅ Governance deployed at: ${governance.address}`);
        
        // Fund treasury
        console.log(`   💰 Funding treasury with ${ethers.utils.formatEther(CONFIG.governanceTreasury)} QXC...`);
        const qxcToken = await ethers.getContractAt(CONTRACTS.QXCToken, this.deployedContracts.QXCToken);
        await qxcToken.transfer(governance.address, CONFIG.governanceTreasury);
        console.log(`   ✅ Treasury funded\n`);
    }

    async integrateComponents() {
        console.log('6️⃣  Integrating Components...');
        
        const qxcToken = await ethers.getContractAt(CONTRACTS.QXCToken, this.deployedContracts.QXCToken);
        const unifiedProtocol = await ethers.getContractAt(CONTRACTS.QXCUnifiedProtocol, this.deployedContracts.QXCUnifiedProtocol);
        
        // Add unified protocol as minter
        console.log('   🔑 Granting minter role to Unified Protocol...');
        await qxcToken.addMinter(unifiedProtocol.address);
        
        // Add AMM as authorized contract in unified protocol
        console.log('   🔗 Linking AMM to Unified Protocol...');
        await unifiedProtocol.setAMM(this.deployedContracts.QXCAutomatedMarketMaker);
        
        // Set governance in unified protocol
        console.log('   ⚖️ Setting governance contract...');
        await unifiedProtocol.setGovernance(this.deployedContracts.QXCGovernance);
        
        console.log('   ✅ All components integrated\n');
    }

    async saveDeploymentInfo() {
        console.log('7️⃣  Saving Deployment Information...');
        
        const deploymentInfo = {
            network: CONFIG.network,
            deployedAt: new Date().toISOString(),
            deployer: this.signer.address,
            contracts: this.deployedContracts,
            configuration: {
                stakingAPY: '15%',
                minStake: '10 QXC',
                lockPeriod: '7 days',
                ammDefaultFee: '0.3%',
                governanceQuorum: '4%',
                votingPeriod: '3 days'
            }
        };
        
        const deploymentPath = path.join(__dirname, 'deployment.json');
        fs.writeFileSync(deploymentPath, JSON.stringify(deploymentInfo, null, 2));
        
        console.log(`   ✅ Deployment info saved to ${deploymentPath}\n`);
        
        return deploymentInfo;
    }

    async verifyDeployment() {
        console.log('8️⃣  Verifying Deployment...');
        
        const checks = [
            { name: 'QXC Token', address: this.deployedContracts.QXCToken },
            { name: 'Staking', address: this.deployedContracts.QXCStaking },
            { name: 'Unified Protocol', address: this.deployedContracts.QXCUnifiedProtocol },
            { name: 'AMM', address: this.deployedContracts.QXCAutomatedMarketMaker },
            { name: 'Governance', address: this.deployedContracts.QXCGovernance }
        ];
        
        for (const check of checks) {
            const code = await ethers.provider.getCode(check.address);
            if (code === '0x') {
                console.log(`   ❌ ${check.name} not deployed properly`);
                throw new Error(`Deployment verification failed for ${check.name}`);
            }
            console.log(`   ✅ ${check.name} verified`);
        }
        
        console.log('\n');
    }

    async displaySummary() {
        console.log('═══════════════════════════════════════════════════════');
        console.log('            🎉 DEPLOYMENT SUCCESSFUL! 🎉               ');
        console.log('═══════════════════════════════════════════════════════');
        console.log('\n📋 CONTRACT ADDRESSES:\n');
        
        Object.entries(this.deployedContracts).forEach(([name, address]) => {
            console.log(`   ${name.padEnd(25)} ${address}`);
        });
        
        console.log('\n🚀 NEXT STEPS:\n');
        console.log('   1. Fund lending pool: npm run fund-lending');
        console.log('   2. Create first proposal: npm run create-proposal');
        console.log('   3. Start frontend: npm run frontend');
        console.log('   4. View dashboard: https://abdulrahman305.github.io/qenex-docs);
        console.log('\n═══════════════════════════════════════════════════════');
    }

    async deploy() {
        try {
            await this.initialize();
            await this.deployQXCToken();
            await this.deployStaking();
            await this.deployUnifiedProtocol();
            await this.deployAMM();
            await this.deployGovernance();
            await this.integrateComponents();
            await this.saveDeploymentInfo();
            await this.verifyDeployment();
            await this.displaySummary();
            
            console.log('\n✨ QXC Unified Financial Ecosystem deployed successfully!\n');
            
        } catch (error) {
            console.error('\n❌ Deployment failed:', error.message);
            console.error('\nStack trace:', error.stack);
            process.exit(1);
        }
    }
}

// Mock ERC20 for testing
const MockERC20Source = `
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract MockERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    string public name;
    string public symbol;
    uint8 public decimals;
    uint256 public totalSupply;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    
    constructor(string memory _name, string memory _symbol, uint8 _decimals) {
        name = _name;
        symbol = _symbol;
        decimals = _decimals;
    }
    
    function mint(address to, uint256 amount) external {
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }
    
    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }
    
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        allowance[from][msg.sender] -= amount;
        emit Transfer(from, to, amount);
        return true;
    }
}
`;

// Main execution
if (require.main === module) {
    const deployer = new UnifiedSystemDeployer();
    deployer.deploy().catch((error) => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
}

module.exports = UnifiedSystemDeployer;