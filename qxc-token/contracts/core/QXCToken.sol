// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";

contract QXCToken is ERC20, ERC20Burnable, Pausable, Ownable, ERC20Permit {
    uint256 public constant INITIAL_SUPPLY = 1525.30 ether;
    uint256 public constant MAX_SUPPLY = 21_000_000 ether;
    
    mapping(address => bool) public minters;
    mapping(address => bool) public blacklisted;
    
    event MinterAdded(address indexed minter);
    event MinterRemoved(address indexed minter);
    event Blacklisted(address indexed account);
    event Unblacklisted(address indexed account);
    event AIReward(address indexed recipient, uint256 amount);
    
    modifier onlyMinter() {
        require(minters[msg.sender], "Not a minter");
        _;
    }
    
    modifier notBlacklisted(address account) {
        require(!blacklisted[account], "Account blacklisted");
        _;
    }
    
    constructor() 
        ERC20("QENEX Coin", "QXC") 
        ERC20Permit("QENEX Coin")
    {
        _mint(msg.sender, INITIAL_SUPPLY);
        minters[msg.sender] = true;
    }
    
    function mint(address to, uint256 amount) 
        external 
        onlyMinter 
        notBlacklisted(to) 
    {
        require(totalSupply() + amount <= MAX_SUPPLY, "Max supply exceeded");
        _mint(to, amount);
    }
    
    function rewardAIImprovement(address contributor, uint256 amount) 
        external 
        onlyMinter 
        notBlacklisted(contributor)
    {
        require(totalSupply() + amount <= MAX_SUPPLY, "Max supply exceeded");
        _mint(contributor, amount);
        emit AIReward(contributor, amount);
    }
    
    function addMinter(address minter) external onlyOwner {
        minters[minter] = true;
        emit MinterAdded(minter);
    }
    
    function removeMinter(address minter) external onlyOwner {
        minters[minter] = false;
        emit MinterRemoved(minter);
    }
    
    function blacklist(address account) external onlyOwner {
        blacklisted[account] = true;
        emit Blacklisted(account);
    }
    
    function unblacklist(address account) external onlyOwner {
        blacklisted[account] = false;
        emit Unblacklisted(account);
    }
    
    function pause() external onlyOwner {
        _pause();
    }
    
    function unpause() external onlyOwner {
        _unpause();
    }
    
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override whenNotPaused {
        require(!blacklisted[from], "Sender blacklisted");
        require(!blacklisted[to], "Recipient blacklisted");
        super._beforeTokenTransfer(from, to, amount);
    }
}