const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time, loadFixture } = require("@nomicfoundation/hardhat-network-helpers");

describe("QXCTokenV2", function () {
    // Fixture for deployment
    async function deployTokenFixture() {
        const [owner, minter, pauser, user1, user2, attacker, treasury] = await ethers.getSigners();
        
        const Token = await ethers.getContractFactory("QXCTokenV2");
        const token = await Token.deploy(treasury.address);
        await token.deployed();
        
        // Grant roles
        const MINTER_ROLE = await token.MINTER_ROLE();
        const PAUSER_ROLE = await token.PAUSER_ROLE();
        const BLACKLIST_ROLE = await token.BLACKLIST_ROLE();
        
        await token.grantRole(MINTER_ROLE, minter.address);
        await token.grantRole(PAUSER_ROLE, pauser.address);
        
        return { token, owner, minter, pauser, user1, user2, attacker, treasury, MINTER_ROLE, PAUSER_ROLE, BLACKLIST_ROLE };
    }
    
    describe("Deployment", function () {
        it("Should set the correct name and symbol", async function () {
            const { token } = await loadFixture(deployTokenFixture);
            expect(await token.name()).to.equal("QENEX Coin");
            expect(await token.symbol()).to.equal("QXC");
        });
        
        it("Should mint initial supply to owner", async function () {
            const { token, owner } = await loadFixture(deployTokenFixture);
            const initialSupply = ethers.utils.parseEther("1525.30");
            expect(await token.balanceOf(owner.address)).to.equal(initialSupply);
        });
        
        it("Should set correct max supply", async function () {
            const { token } = await loadFixture(deployTokenFixture);
            const maxSupply = ethers.utils.parseEther("21000000");
            expect(await token.cap()).to.equal(maxSupply);
        });
        
        it("Should assign roles correctly", async function () {
            const { token, owner, minter, pauser, MINTER_ROLE, PAUSER_ROLE } = await loadFixture(deployTokenFixture);
            
            expect(await token.hasRole(MINTER_ROLE, owner.address)).to.be.true;
            expect(await token.hasRole(MINTER_ROLE, minter.address)).to.be.true;
            expect(await token.hasRole(PAUSER_ROLE, pauser.address)).to.be.true;
        });
    });
    
    describe("Minting", function () {
        it("Should allow minter to mint tokens", async function () {
            const { token, minter, user1 } = await loadFixture(deployTokenFixture);
            const amount = ethers.utils.parseEther("100");
            
            await token.connect(minter).mint(user1.address, amount);
            expect(await token.balanceOf(user1.address)).to.equal(amount);
        });
        
        it("Should not allow non-minters to mint", async function () {
            const { token, attacker, user1 } = await loadFixture(deployTokenFixture);
            const amount = ethers.utils.parseEther("100");
            
            await expect(
                token.connect(attacker).mint(user1.address, amount)
            ).to.be.reverted;
        });
        
        it("Should not allow minting beyond max supply", async function () {
            const { token, minter, user1 } = await loadFixture(deployTokenFixture);
            const maxSupply = await token.cap();
            const currentSupply = await token.totalSupply();
            const overAmount = maxSupply.sub(currentSupply).add(1);
            
            await expect(
                token.connect(minter).mint(user1.address, overAmount)
            ).to.be.revertedWith("ERC20Capped: cap exceeded");
        });
    });
    
    describe("Trading Control", function () {
        it("Should prevent transfers when trading is disabled", async function () {
            const { token, owner, user1, user2 } = await loadFixture(deployTokenFixture);
            
            // Transfer some tokens to user1
            await token.transfer(user1.address, ethers.utils.parseEther("100"));
            
            // User1 should not be able to transfer when trading is disabled
            await expect(
                token.connect(user1).transfer(user2.address, ethers.utils.parseEther("50"))
            ).to.be.revertedWithCustomError(token, "TradingNotEnabled");
        });
        
        it("Should allow transfers after trading is enabled", async function () {
            const { token, owner, user1, user2 } = await loadFixture(deployTokenFixture);
            
            // Enable trading
            await token.enableTrading();
            
            // Transfer some tokens to user1
            await token.transfer(user1.address, ethers.utils.parseEther("100"));
            
            // User1 should be able to transfer
            await token.connect(user1).transfer(user2.address, ethers.utils.parseEther("50"));
            expect(await token.balanceOf(user2.address)).to.equal(ethers.utils.parseEther("50"));
        });
        
        it("Should allow admin transfers even when trading is disabled", async function () {
            const { token, owner, user1 } = await loadFixture(deployTokenFixture);
            
            // Owner should be able to transfer even when trading is disabled
            await token.transfer(user1.address, ethers.utils.parseEther("100"));
            expect(await token.balanceOf(user1.address)).to.equal(ethers.utils.parseEther("100"));
        });
    });
    
    describe("Blacklist", function () {
        it("Should prevent blacklisted addresses from transferring", async function () {
            const { token, owner, user1, user2 } = await loadFixture(deployTokenFixture);
            
            await token.enableTrading();
            await token.transfer(user1.address, ethers.utils.parseEther("100"));
            
            // Blacklist user1
            await token.blacklist(user1.address);
            
            // User1 should not be able to transfer
            await expect(
                token.connect(user1).transfer(user2.address, ethers.utils.parseEther("50"))
            ).to.be.revertedWithCustomError(token, "BlacklistedAddress");
        });
        
        it("Should prevent transfers to blacklisted addresses", async function () {
            const { token, owner, user1, user2 } = await loadFixture(deployTokenFixture);
            
            await token.enableTrading();
            await token.transfer(user1.address, ethers.utils.parseEther("100"));
            
            // Blacklist user2
            await token.blacklist(user2.address);
            
            // Should not be able to transfer to user2
            await expect(
                token.connect(user1).transfer(user2.address, ethers.utils.parseEther("50"))
            ).to.be.revertedWithCustomError(token, "BlacklistedAddress");
        });
        
        it("Should allow transfers after unblacklisting", async function () {
            const { token, owner, user1, user2 } = await loadFixture(deployTokenFixture);
            
            await token.enableTrading();
            await token.transfer(user1.address, ethers.utils.parseEther("100"));
            
            // Blacklist and then unblacklist user1
            await token.blacklist(user1.address);
            await token.unblacklist(user1.address);
            
            // User1 should be able to transfer again
            await token.connect(user1).transfer(user2.address, ethers.utils.parseEther("50"));
            expect(await token.balanceOf(user2.address)).to.equal(ethers.utils.parseEther("50"));
        });
    });
    
    describe("Pause", function () {
        it("Should prevent transfers when paused", async function () {
            const { token, pauser, owner, user1 } = await loadFixture(deployTokenFixture);
            
            await token.enableTrading();
            await token.transfer(user1.address, ethers.utils.parseEther("100"));
            
            // Pause the contract
            await token.connect(pauser).pause();
            
            // Should not be able to transfer
            await expect(
                token.connect(user1).transfer(owner.address, ethers.utils.parseEther("50"))
            ).to.be.revertedWith("Pausable: paused");
        });
        
        it("Should allow transfers after unpausing", async function () {
            const { token, pauser, owner, user1 } = await loadFixture(deployTokenFixture);
            
            await token.enableTrading();
            await token.transfer(user1.address, ethers.utils.parseEther("100"));
            
            // Pause and unpause
            await token.connect(pauser).pause();
            await token.connect(pauser).unpause();
            
            // Should be able to transfer again
            await token.connect(user1).transfer(owner.address, ethers.utils.parseEther("50"));
            expect(await token.balanceOf(owner.address)).to.be.gt(0);
        });
    });
    
    describe("Transfer Fees", function () {
        it("Should apply transfer fees correctly", async function () {
            const { token, owner, user1, user2, treasury } = await loadFixture(deployTokenFixture);
            
            await token.enableTrading();
            
            // Set 1% transfer fee (100 basis points)
            await token.updateTransferFee(100);
            
            // Transfer 100 tokens from owner to user1
            const amount = ethers.utils.parseEther("100");
            await token.transfer(user1.address, amount);
            
            // User1 should receive 100 tokens initially
            expect(await token.balanceOf(user1.address)).to.equal(amount);
            
            // When user1 transfers to user2, fee should be applied
            await token.connect(user1).transfer(user2.address, amount);
            
            // User2 should receive 100 tokens initially, but fee is taken after
            const fee = amount.mul(100).div(10000); // 1% fee
            
            // Treasury should receive the fee
            expect(await token.balanceOf(treasury.address)).to.equal(fee);
        });
        
        it("Should not allow fees above maximum", async function () {
            const { token } = await loadFixture(deployTokenFixture);
            
            // Try to set 6% fee (600 basis points, above 5% max)
            await expect(
                token.updateTransferFee(600)
            ).to.be.revertedWithCustomError(token, "FeeTooHigh");
        });
    });
    
    describe("Rate Limiting", function () {
        it("Should enforce rate limiting between transactions", async function () {
            const { token, owner, user1, user2 } = await loadFixture(deployTokenFixture);
            
            await token.enableTrading();
            
            // Set rate limit to 10 seconds
            await token.updateRateLimit(10);
            
            // Transfer to user1
            await token.transfer(user1.address, ethers.utils.parseEther("200"));
            
            // First transfer should work
            await token.connect(user1).transfer(user2.address, ethers.utils.parseEther("50"));
            
            // Second transfer immediately should fail
            await expect(
                token.connect(user1).transfer(user2.address, ethers.utils.parseEther("50"))
            ).to.be.revertedWithCustomError(token, "TransactionTooFrequent");
            
            // Wait 10 seconds
            await time.increase(10);
            
            // Should work now
            await token.connect(user1).transfer(user2.address, ethers.utils.parseEther("50"));
        });
    });
    
    describe("Snapshot", function () {
        it("Should create snapshots correctly", async function () {
            const { token, owner, user1 } = await loadFixture(deployTokenFixture);
            
            await token.enableTrading();
            
            // Transfer some tokens
            await token.transfer(user1.address, ethers.utils.parseEther("100"));
            
            // Create snapshot
            await token.snapshot();
            const snapshotId = 1;
            
            // Transfer more tokens
            await token.transfer(user1.address, ethers.utils.parseEther("50"));
            
            // Check balances at snapshot
            expect(await token.balanceOfAt(user1.address, snapshotId)).to.equal(
                ethers.utils.parseEther("100")
            );
            
            // Current balance should be different
            expect(await token.balanceOf(user1.address)).to.equal(
                ethers.utils.parseEther("150")
            );
        });
    });
    
    describe("Governance", function () {
        it("Should allow token holders to delegate votes", async function () {
            const { token, owner, user1, user2 } = await loadFixture(deployTokenFixture);
            
            await token.enableTrading();
            await token.transfer(user1.address, ethers.utils.parseEther("100"));
            
            // Delegate votes
            await token.connect(user1).delegate(user2.address);
            
            // User2 should have voting power
            expect(await token.getVotes(user2.address)).to.equal(
                ethers.utils.parseEther("100")
            );
        });
    });
    
    describe("Burning", function () {
        it("Should allow token burning", async function () {
            const { token, owner, user1 } = await loadFixture(deployTokenFixture);
            
            await token.enableTrading();
            await token.transfer(user1.address, ethers.utils.parseEther("100"));
            
            const initialSupply = await token.totalSupply();
            
            // Burn tokens
            await token.connect(user1).burn(ethers.utils.parseEther("50"));
            
            // Check balance and total supply
            expect(await token.balanceOf(user1.address)).to.equal(ethers.utils.parseEther("50"));
            expect(await token.totalSupply()).to.equal(
                initialSupply.sub(ethers.utils.parseEther("50"))
            );
        });
    });
    
    describe("Emergency Functions", function () {
        it("Should allow emergency withdrawal of stuck tokens", async function () {
            const { token, owner } = await loadFixture(deployTokenFixture);
            
            // Send some ETH to the contract
            await owner.sendTransaction({
                to: token.address,
                value: ethers.utils.parseEther("1")
            });
            
            const initialBalance = await ethers.provider.getBalance(owner.address);
            
            // Emergency withdraw ETH
            await token.emergencyWithdraw(ethers.constants.AddressZero, ethers.utils.parseEther("1"));
            
            const finalBalance = await ethers.provider.getBalance(owner.address);
            expect(finalBalance).to.be.gt(initialBalance);
        });
    });
});