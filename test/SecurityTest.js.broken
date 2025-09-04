const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("Security Test Suite", function () {
    let token, staking;
    let owner, attacker, user1, user2;
    
    beforeEach(async function () {
        [owner, attacker, user1, user2] = await ethers.getSigners();
        
        // Deploy contracts
        const Token = await ethers.getContractFactory("SecureQXCToken");
        token = await Token.deploy();
        
        const Staking = await ethers.getContractFactory("SecureStaking");
        staking = await Staking.deploy(token.address);
        
        // Setup
        await token.mint(user1.address, ethers.utils.parseEther("1000"));
        await token.mint(user2.address, ethers.utils.parseEther("1000"));
    });
    
    describe("Access Control Tests", function () {
        it("Should not allow unauthorized minting", async function () {
            await expect(
                token.connect(attacker).mint(attacker.address, ethers.utils.parseEther("1000000"))
            ).to.be.reverted;
        });
        
        it("Should not allow minting beyond max supply", async function () {
            const maxSupply = await token.cap();
            await expect(
                token.mint(owner.address, maxSupply.add(1))
            ).to.be.reverted;
        });
        
        it("Should not allow unauthorized pause", async function () {
            await expect(
                token.connect(attacker).pause()
            ).to.be.reverted;
        });
    });
    
    describe("Reentrancy Tests", function () {
        it("Should prevent reentrancy attacks on staking", async function () {
            // Deploy malicious contract
            const Attacker = await ethers.getContractFactory("ReentrancyAttacker");
            const attackContract = await Attacker.deploy(staking.address);
            
            // Fund attacker
            await token.mint(attackContract.address, ethers.utils.parseEther("100"));
            await token.connect(attackContract.address).approve(
                staking.address, 
                ethers.utils.parseEther("100")
            );
            
            // Attempt attack
            await expect(
                attackContract.attack()
            ).to.be.revertedWith("ReentrancyGuard: reentrant call");
        });
    });
    
    describe("Staking Security", function () {
        it("Should enforce lock period", async function () {
            const amount = ethers.utils.parseEther("100");
            
            await token.connect(user1).approve(staking.address, amount);
            await staking.connect(user1).stake(amount);
            
            // Try to unstake immediately
            await expect(
                staking.connect(user1).unstake()
            ).to.be.revertedWith("Still locked");
            
            // Fast forward time
            await time.increase(7 * 24 * 60 * 60); // 7 days
            
            // Now should work
            await expect(
                staking.connect(user1).unstake()
            ).to.not.be.reverted;
        });
        
        it("Should calculate rewards correctly", async function () {
            const amount = ethers.utils.parseEther("100");
            
            await token.connect(user1).approve(staking.address, amount);
            await staking.connect(user1).stake(amount);
            
            // Fast forward 1 year
            await time.increase(365 * 24 * 60 * 60);
            
            // Check reward calculation (15% APY)
            const expectedReward = amount.mul(15).div(100);
            
            // Unstake and verify reward
            const balanceBefore = await token.balanceOf(user1.address);
            await staking.connect(user1).unstake();
            const balanceAfter = await token.balanceOf(user1.address);
            
            const received = balanceAfter.sub(balanceBefore);
            const expectedTotal = amount.add(expectedReward);
            
            // Allow 0.1% variance for rounding
            expect(received).to.be.closeTo(
                expectedTotal, 
                expectedTotal.div(1000)
            );
        });
    });
    
    describe("Pause Mechanism", function () {
        it("Should block transfers when paused", async function () {
            await token.pause();
            
            await expect(
                token.connect(user1).transfer(user2.address, ethers.utils.parseEther("10"))
            ).to.be.revertedWith("Pausable: paused");
        });
        
        it("Should block staking when paused", async function () {
            await staking.pause();
            
            await token.connect(user1).approve(staking.address, ethers.utils.parseEther("100"));
            
            await expect(
                staking.connect(user1).stake(ethers.utils.parseEther("100"))
            ).to.be.revertedWith("Pausable: paused");
        });
    });
});

// Malicious contract for testing
contract ReentrancyAttacker {
    address public target;
    uint256 public attackCount = 0;
    
    constructor(address _target) {
        target = _target;
    }
    
    function attack() external {
        IStaking(target).unstake();
    }
    
    receive() external payable {
        attackCount++;
        if (attackCount < 10) {
            IStaking(target).unstake();
        }
    }
}