// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Capped.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title QXC Token - Production Version
 * @notice Production-ready ERC20 with security features
 * @dev Minimalist implementation with essential security
 */
contract QXCTokenProduction is ERC20, ERC20Burnable, ERC20Capped, AccessControl, Pausable {
    // Roles
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    
    // Constants
    uint256 public constant INITIAL_SUPPLY = 1525.30 ether;
    uint256 public constant MAX_SUPPLY = 21_000_000 ether;
    uint256 public constant MAX_TRANSFER_AMOUNT = 100_000 ether;
    
    // State
    bool public tradingEnabled = false;
    mapping(address => bool) public blacklisted;
    mapping(address => uint256) public lastTransferTime;
    uint256 public constant TRANSFER_COOLDOWN = 1 minutes;
    
    // Multi-sig controller
    address public multiSigController;
    
    // Events
    event TradingEnabled(uint256 timestamp);
    event Blacklisted(address indexed account, bool status);
    event MultiSigUpdated(address indexed newController);
    
    modifier onlyMultiSig() {
        require(msg.sender == multiSigController, "Only multi-sig");
        _;
    }
    
    modifier tradingActive() {
        require(tradingEnabled || hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "Trading disabled");
        _;
    }
    
    modifier notBlacklisted(address from, address to) {
        require(!blacklisted[from] && !blacklisted[to], "Blacklisted");
        _;
    }
    
    modifier rateLimited(address from) {
        require(
            block.timestamp >= lastTransferTime[from] + TRANSFER_COOLDOWN ||
            hasRole(DEFAULT_ADMIN_ROLE, from),
            "Rate limited"
        );
        _;
    }
    
    constructor(address _multiSig) 
        ERC20("QENEX Coin", "QXC") 
        ERC20Capped(MAX_SUPPLY) 
    {
        require(_multiSig != address(0), "Invalid multi-sig");
        multiSigController = _multiSig;
        
        // Grant initial roles to multi-sig
        _grantRole(DEFAULT_ADMIN_ROLE, _multiSig);
        _grantRole(MINTER_ROLE, _multiSig);
        _grantRole(PAUSER_ROLE, _multiSig);
        
        // Mint initial supply to multi-sig
        _mint(_multiSig, INITIAL_SUPPLY);
    }
    
    function mint(address to, uint256 amount) 
        external 
        onlyRole(MINTER_ROLE) 
        whenNotPaused 
    {
        require(amount <= MAX_TRANSFER_AMOUNT, "Amount too large");
        _mint(to, amount);
    }
    
    function enableTrading() 
        external 
        onlyMultiSig 
    {
        require(!tradingEnabled, "Already enabled");
        tradingEnabled = true;
        emit TradingEnabled(block.timestamp);
    }
    
    function setBlacklist(address account, bool status) 
        external 
        onlyRole(DEFAULT_ADMIN_ROLE) 
    {
        blacklisted[account] = status;
        emit Blacklisted(account, status);
    }
    
    function updateMultiSig(address newController) 
        external 
        onlyMultiSig 
    {
        require(newController != address(0), "Invalid address");
        
        // Revoke roles from old controller
        _revokeRole(DEFAULT_ADMIN_ROLE, multiSigController);
        _revokeRole(MINTER_ROLE, multiSigController);
        _revokeRole(PAUSER_ROLE, multiSigController);
        
        // Grant roles to new controller
        _grantRole(DEFAULT_ADMIN_ROLE, newController);
        _grantRole(MINTER_ROLE, newController);
        _grantRole(PAUSER_ROLE, newController);
        
        multiSigController = newController;
        emit MultiSigUpdated(newController);
    }
    
    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }
    
    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }
    
    // Override transfers with security checks
    function _update(
        address from,
        address to,
        uint256 amount
    ) 
        internal 
        override(ERC20, ERC20Capped)
        whenNotPaused
    {
        // Check trading status
        require(tradingEnabled || hasRole(DEFAULT_ADMIN_ROLE, from), "Trading disabled");
        
        // Check blacklist
        require(!blacklisted[from] && !blacklisted[to], "Blacklisted");
        
        // Check rate limit
        require(
            block.timestamp >= lastTransferTime[from] + TRANSFER_COOLDOWN ||
            hasRole(DEFAULT_ADMIN_ROLE, from),
            "Rate limited"
        );
        
        // Check transfer amount
        require(amount <= MAX_TRANSFER_AMOUNT, "Transfer limit exceeded");
        
        // Update rate limit
        if (from != address(0)) {
            lastTransferTime[from] = block.timestamp;
        }
        
        super._update(from, to, amount);
    }
}