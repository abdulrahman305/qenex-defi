const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("QXC Token", function () {
    let token;
    let owner;
    let addr1;
    let addr2;

    beforeEach(async function () {
        [owner, addr1, addr2] = await ethers.getSigners();
        
        const Token = await ethers.getContractFactory("QXCToken");
        token = await Token.deploy();
        await token.waitForDeployment();
    });

    describe("Deployment", function () {
        it("Should set the right name and symbol", async function () {
            expect(await token.name()).to.equal("QENEX Coin");
            expect(await token.symbol()).to.equal("QXC");
        });

        it("Should assign the initial supply to the owner", async function () {
            const ownerBalance = await token.balanceOf(owner.address);
            expect(ownerBalance).to.equal(ethers.parseEther("1525.30"));
        });

        it("Should set the correct max supply", async function () {
            const cap = await token.cap();
            expect(cap).to.equal(ethers.parseEther("21000000"));
        });
    });

    describe("Minting", function () {
        it("Should allow owner to mint tokens", async function () {
            const mintAmount = ethers.parseEther("100");
            await token.mint(addr1.address, mintAmount);
            expect(await token.balanceOf(addr1.address)).to.equal(mintAmount);
        });

        it("Should not allow non-owner to mint", async function () {
            const mintAmount = ethers.parseEther("100");
            await expect(
                token.connect(addr1).mint(addr2.address, mintAmount)
            ).to.be.reverted;
        });

        it("Should not mint beyond max supply", async function () {
            const maxSupply = await token.cap();
            const currentSupply = await token.totalSupply();
            const overAmount = maxSupply - currentSupply + ethers.parseEther("1");
            
            await expect(
                token.mint(addr1.address, overAmount)
            ).to.be.revertedWithCustomError(token, "ERC20ExceededCap");
        });
    });

    describe("Trading Control", function () {
        it("Should prevent transfers when trading is disabled", async function () {
            // Transfer to addr1 first (admin can transfer)
            await token.transfer(addr1.address, ethers.parseEther("100"));
            
            // addr1 cannot transfer when trading is disabled
            await expect(
                token.connect(addr1).transfer(addr2.address, ethers.parseEther("50"))
            ).to.be.revertedWith("Trading not enabled");
        });

        it("Should allow transfers after trading is enabled", async function () {
            await token.enableTrading();
            await token.transfer(addr1.address, ethers.parseEther("100"));
            
            await token.connect(addr1).transfer(addr2.address, ethers.parseEther("50"));
            expect(await token.balanceOf(addr2.address)).to.equal(ethers.parseEther("50"));
        });
    });

    describe("Pause", function () {
        it("Should prevent transfers when paused", async function () {
            await token.enableTrading();
            await token.pause();
            
            await expect(
                token.transfer(addr1.address, ethers.parseEther("100"))
            ).to.be.revertedWithCustomError(token, "EnforcedPause");
        });

        it("Should allow transfers when unpaused", async function () {
            await token.enableTrading();
            await token.pause();
            await token.unpause();
            
            await token.transfer(addr1.address, ethers.parseEther("100"));
            expect(await token.balanceOf(addr1.address)).to.equal(ethers.parseEther("100"));
        });
    });

    describe("Burn", function () {
        it("Should allow users to burn their tokens", async function () {
            await token.enableTrading();
            const burnAmount = ethers.parseEther("100");
            const initialSupply = await token.totalSupply();
            
            await token.burn(burnAmount);
            
            expect(await token.totalSupply()).to.equal(initialSupply - burnAmount);
        });
    });
});