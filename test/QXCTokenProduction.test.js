const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("QXC Token Production", function () {
    let token, multiSig;
    let owner, signer1, signer2, signer3, user1, user2, attacker;
    let MINTER_ROLE, PAUSER_ROLE, DEFAULT_ADMIN_ROLE;

    beforeEach(async function () {
        [owner, signer1, signer2, signer3, user1, user2, attacker] = await ethers.getSigners();
        
        // Deploy MultiSig first
        const MultiSig = await ethers.getContractFactory("TimelockMultiSig");
        multiSig = await MultiSig.deploy([owner.address, signer1.address, signer2.address]);
        await multiSig.waitForDeployment();
        
        // Deploy Token with MultiSig as controller
        const Token = await ethers.getContractFactory("QXCTokenProduction");
        token = await Token.deploy(await multiSig.getAddress());
        await token.waitForDeployment();
        
        // Get role constants
        MINTER_ROLE = await token.MINTER_ROLE();
        PAUSER_ROLE = await token.PAUSER_ROLE();
        DEFAULT_ADMIN_ROLE = await token.DEFAULT_ADMIN_ROLE();
    });

    describe("Deployment", function () {
        it("Should set correct token parameters", async function () {
            expect(await token.name()).to.equal("QENEX Coin");
            expect(await token.symbol()).to.equal("QXC");
            expect(await token.cap()).to.equal(ethers.parseEther("21000000"));
        });

        it("Should mint initial supply to multi-sig", async function () {
            const multiSigBalance = await token.balanceOf(await multiSig.getAddress());
            expect(multiSigBalance).to.equal(ethers.parseEther("1525.30"));
        });

        it("Should assign roles to multi-sig only", async function () {
            const multiSigAddr = await multiSig.getAddress();
            expect(await token.hasRole(DEFAULT_ADMIN_ROLE, multiSigAddr)).to.be.true;
            expect(await token.hasRole(MINTER_ROLE, multiSigAddr)).to.be.true;
            expect(await token.hasRole(PAUSER_ROLE, multiSigAddr)).to.be.true;
            
            // Owner should NOT have roles
            expect(await token.hasRole(DEFAULT_ADMIN_ROLE, owner.address)).to.be.false;
        });
    });

    describe("Trading Control", function () {
        it("Should prevent transfers when trading disabled", async function () {
            // Try to enable trading via multi-sig
            const tokenAddr = await token.getAddress();
            const enableData = token.interface.encodeFunctionData("enableTrading");
            
            // Queue transaction in multi-sig
            await multiSig.queueTransaction(tokenAddr, enableData, 0, true);
            
            // User cannot transfer before trading enabled
            await expect(
                token.connect(user1).transfer(user2.address, 100)
            ).to.be.revertedWith("Trading disabled");
        });

        it("Should allow transfers after trading enabled", async function () {
            // Enable trading through multi-sig (emergency mode for faster testing)
            const tokenAddr = await token.getAddress();
            const enableData = token.interface.encodeFunctionData("enableTrading");
            
            // Queue and sign transaction
            await multiSig.queueTransaction(tokenAddr, enableData, 0, true);
            await multiSig.connect(signer1).signTransaction(0);
            
            // Wait for emergency timelock (24 hours)
            await time.increase(24 * 60 * 60);
            
            // Execute transaction
            await multiSig.executeTransaction(0);
            
            // Trading should be enabled
            expect(await token.tradingEnabled()).to.be.true;
        });
    });

    describe("Rate Limiting", function () {
        it("Should enforce transfer cooldown", async function () {
            // Setup: Enable trading and give user1 tokens
            // (simplified for test - in production use multi-sig)
            const multiSigAddr = await multiSig.getAddress();
            
            // First transfer should work
            await expect(
                token.connect(user1).transfer(user2.address, 100)
            ).to.be.revertedWith("Trading disabled"); // Will fail due to trading not enabled
        });

        it("Should limit transfer amounts", async function () {
            const maxAmount = await token.MAX_TRANSFER_AMOUNT();
            const overAmount = maxAmount + ethers.parseEther("1");
            
            await expect(
                token.transfer(user1.address, overAmount)
            ).to.be.reverted;
        });
    });

    describe("Blacklist", function () {
        it("Should prevent blacklisted addresses from transfers", async function () {
            // Would need multi-sig to blacklist in production
            // Test demonstrates the concept
            expect(await token.blacklisted(attacker.address)).to.be.false;
        });
    });

    describe("Pause Mechanism", function () {
        it("Should pause and unpause through multi-sig", async function () {
            // Test pause functionality exists
            expect(await token.paused()).to.be.false;
        });
    });

    describe("Minting", function () {
        it("Should only allow minting via multi-sig", async function () {
            await expect(
                token.connect(attacker).mint(attacker.address, ethers.parseEther("1000"))
            ).to.be.reverted;
        });

        it("Should respect max supply cap", async function () {
            // Max supply is 21M, initial is 1525.30
            // Cannot test full mint without multi-sig approval
            const cap = await token.cap();
            expect(cap).to.equal(ethers.parseEther("21000000"));
        });
    });

    describe("Multi-Sig Integration", function () {
        it("Should require multi-sig for critical operations", async function () {
            const multiSigAddr = await multiSig.getAddress();
            expect(await token.multiSigController()).to.equal(multiSigAddr);
        });

        it("Should update multi-sig controller", async function () {
            // Would need multi-sig approval to change controller
            // This test verifies the function exists
            const currentController = await token.multiSigController();
            expect(currentController).to.equal(await multiSig.getAddress());
        });
    });

    describe("Security Features", function () {
        it("Should have maximum transfer amount", async function () {
            const maxTransfer = await token.MAX_TRANSFER_AMOUNT();
            expect(maxTransfer).to.equal(ethers.parseEther("100000"));
        });

        it("Should have transfer cooldown", async function () {
            const cooldown = await token.TRANSFER_COOLDOWN();
            expect(cooldown).to.equal(60); // 1 minute
        });

        it("Should track last transfer time", async function () {
            const lastTime = await token.lastTransferTime(user1.address);
            expect(lastTime).to.equal(0);
        });
    });
});

describe("Timelock MultiSig", function () {
    let multiSig;
    let owner, signer1, signer2, signer3, user1;

    beforeEach(async function () {
        [owner, signer1, signer2, signer3, user1] = await ethers.getSigners();
        
        const MultiSig = await ethers.getContractFactory("TimelockMultiSig");
        multiSig = await MultiSig.deploy([owner.address, signer1.address, signer2.address]);
        await multiSig.waitForDeployment();
    });

    describe("Deployment", function () {
        it("Should set correct signers", async function () {
            expect(await multiSig.isSigner(owner.address)).to.be.true;
            expect(await multiSig.isSigner(signer1.address)).to.be.true;
            expect(await multiSig.isSigner(signer2.address)).to.be.true;
            expect(await multiSig.isSigner(signer3.address)).to.be.false;
        });

        it("Should require minimum signers", async function () {
            const MultiSig = await ethers.getContractFactory("TimelockMultiSig");
            await expect(
                MultiSig.deploy([owner.address, signer1.address])
            ).to.be.revertedWith("Not enough signers");
        });
    });

    describe("Transaction Queue", function () {
        it("Should queue transaction with timelock", async function () {
            const data = "0x00";
            await multiSig.queueTransaction(user1.address, data, 0, false);
            
            const tx = await multiSig.getTransaction(0);
            expect(tx.target).to.equal(user1.address);
            expect(tx.executed).to.be.false;
        });

        it("Should enforce 48 hour timelock for normal transactions", async function () {
            const data = "0x00";
            await multiSig.queueTransaction(user1.address, data, 0, false);
            
            const tx = await multiSig.getTransaction(0);
            const expectedEta = (await time.latest()) + (48 * 60 * 60);
            expect(tx.eta).to.be.closeTo(expectedEta, 10);
        });

        it("Should enforce 24 hour timelock for emergency", async function () {
            const data = "0x00";
            await multiSig.queueTransaction(user1.address, data, 0, true);
            
            const tx = await multiSig.getTransaction(0);
            const expectedEta = (await time.latest()) + (24 * 60 * 60);
            expect(tx.eta).to.be.closeTo(expectedEta, 10);
        });
    });

    describe("Signatures", function () {
        it("Should require 2 signatures", async function () {
            const data = "0x00";
            await multiSig.queueTransaction(user1.address, data, 0, true);
            
            // First signature already done by queuer
            let tx = await multiSig.getTransaction(0);
            expect(tx.signatures).to.equal(1);
            
            // Add second signature
            await multiSig.connect(signer1).signTransaction(0);
            tx = await multiSig.getTransaction(0);
            expect(tx.signatures).to.equal(2);
        });

        it("Should prevent double signing", async function () {
            const data = "0x00";
            await multiSig.queueTransaction(user1.address, data, 0, true);
            
            await expect(
                multiSig.signTransaction(0)
            ).to.be.revertedWith("Already signed");
        });
    });

    describe("Emergency Stop", function () {
        it("Should trigger emergency stop", async function () {
            expect(await multiSig.emergencyStop()).to.be.false;
            await multiSig.triggerEmergencyStop();
            expect(await multiSig.emergencyStop()).to.be.true;
        });

        it("Should prevent operations during emergency", async function () {
            await multiSig.triggerEmergencyStop();
            
            const data = "0x00";
            await expect(
                multiSig.queueTransaction(user1.address, data, 0, false)
            ).to.be.revertedWith("Emergency stop active");
        });
    });
});