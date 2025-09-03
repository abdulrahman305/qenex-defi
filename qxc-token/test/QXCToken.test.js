const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("QXC Token", function () {
  let qxcToken;
  let owner;
  let addr1;
  let addr2;

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
    
    const QXCToken = await ethers.getContractFactory("QXCToken");
    qxcToken = await QXCToken.deploy();
    await qxcToken.deployed();
  });

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      expect(await qxcToken.owner()).to.equal(owner.address);
    });

    it("Should assign the initial supply to the owner", async function () {
      const ownerBalance = await qxcToken.balanceOf(owner.address);
      expect(await qxcToken.totalSupply()).to.equal(ownerBalance);
    });

    it("Should have correct name and symbol", async function () {
      expect(await qxcToken.name()).to.equal("QENEX Coin");
      expect(await qxcToken.symbol()).to.equal("QXC");
    });
  });

  describe("Transactions", function () {
    it("Should transfer tokens between accounts", async function () {
      await qxcToken.transfer(addr1.address, 50);
      expect(await qxcToken.balanceOf(addr1.address)).to.equal(50);

      await qxcToken.connect(addr1).transfer(addr2.address, 50);
      expect(await qxcToken.balanceOf(addr2.address)).to.equal(50);
      expect(await qxcToken.balanceOf(addr1.address)).to.equal(0);
    });

    it("Should fail if sender doesn't have enough tokens", async function () {
      const initialOwnerBalance = await qxcToken.balanceOf(owner.address);

      await expect(
        qxcToken.connect(addr1).transfer(owner.address, 1)
      ).to.be.revertedWith("ERC20: transfer amount exceeds balance");

      expect(await qxcToken.balanceOf(owner.address)).to.equal(
        initialOwnerBalance
      );
    });
  });

  describe("Minting", function () {
    it("Should allow minter to mint new tokens", async function () {
      await qxcToken.mint(addr1.address, ethers.utils.parseEther("100"));
      expect(await qxcToken.balanceOf(addr1.address)).to.equal(
        ethers.utils.parseEther("100")
      );
    });

    it("Should not allow non-minter to mint", async function () {
      await expect(
        qxcToken.connect(addr1).mint(addr2.address, 100)
      ).to.be.revertedWith("Not a minter");
    });

    it("Should not exceed max supply", async function () {
      const maxSupply = await qxcToken.MAX_SUPPLY();
      await expect(
        qxcToken.mint(addr1.address, maxSupply.add(1))
      ).to.be.revertedWith("Max supply exceeded");
    });
  });

  describe("Blacklist", function () {
    it("Should block blacklisted addresses", async function () {
      await qxcToken.transfer(addr1.address, 100);
      await qxcToken.blacklist(addr1.address);

      await expect(
        qxcToken.connect(addr1).transfer(addr2.address, 50)
      ).to.be.revertedWith("Sender blacklisted");
    });

    it("Should unblacklist addresses", async function () {
      await qxcToken.blacklist(addr1.address);
      await qxcToken.unblacklist(addr1.address);

      await qxcToken.transfer(addr1.address, 100);
      expect(await qxcToken.balanceOf(addr1.address)).to.equal(100);
    });
  });

  describe("Pause", function () {
    it("Should pause and unpause transfers", async function () {
      await qxcToken.pause();

      await expect(
        qxcToken.transfer(addr1.address, 100)
      ).to.be.revertedWith("Pausable: paused");

      await qxcToken.unpause();
      await qxcToken.transfer(addr1.address, 100);
      expect(await qxcToken.balanceOf(addr1.address)).to.equal(100);
    });
  });
});