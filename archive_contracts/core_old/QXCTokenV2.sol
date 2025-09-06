// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Snapshot.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Capped.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title QXC Token V2
 * @author QENEX Team
 * @notice Production-ready QXC token with comprehensive security features
 * @dev Implements ERC20 with minting caps, burning, governance, and emergency features
 */
contract QXCTokenV2 is 
    ERC20,
    ERC20Burnable,
    ERC20Snapshot,
    ERC20Permit,
    ERC20Votes,
    ERC20Capped,
    AccessControl,
    Pausable,
    ReentrancyGuard
{
    // Roles
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant SNAPSHOT_ROLE = keccak256("SNAPSHOT_ROLE");
    bytes32 public constant BLACKLIST_ROLE = keccak256("BLACKLIST_ROLE");

    // Constants
    uint256 public constant INITIAL_SUPPLY = 1525.30 ether;
    uint256 public constant MAX_SUPPLY = 21_000_000 ether;
    uint256 public constant MAX_TRANSACTION_AMOUNT = 1_000_000 ether;
    
    // State variables
    mapping(address => bool) public blacklisted;
    mapping(address => uint256) public lastTransactionTime;
    uint256 public minTimeBetweenTransactions = 1; // seconds
    bool public tradingEnabled = false;
    address public treasury;
    
    // Fee configuration (basis points, 100 = 1%)
    uint256 public transferFee = 0; // Default 0%
    uint256 public constant MAX_FEE = 500; // Max 5%
    
    // Events
    event Blacklisted(address indexed account);
    event Unblacklisted(address indexed account);
    event TradingEnabled();
    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);
    event TransferFeeUpdated(uint256 oldFee, uint256 newFee);
    event EmergencyWithdraw(address indexed recipient, uint256 amount);
    
    // Custom errors
    error BlacklistedAddress(address account);
    error TradingNotEnabled();
    error TransactionTooLarge(uint256 amount);
    error TransactionTooFrequent();
    error InvalidAddress();
    error FeeTooHigh();

    constructor(address _treasury) 
        ERC20("QENEX Coin", "QXC")
        ERC20Permit("QENEX Coin")
        ERC20Capped(MAX_SUPPLY)
    {
        if (_treasury == address(0)) revert InvalidAddress();
        
        treasury = _treasury;
        
        // Setup roles
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
        _grantRole(SNAPSHOT_ROLE, msg.sender);
        _grantRole(BLACKLIST_ROLE, msg.sender);
        
        // Mint initial supply
        _mint(msg.sender, INITIAL_SUPPLY);
    }

    // Core overrides with security checks
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Snapshot) whenNotPaused {
        // Blacklist check
        if (blacklisted[from]) revert BlacklistedAddress(from);
        if (blacklisted[to]) revert BlacklistedAddress(to);
        
        // Trading check (exclude minting and burning)
        if (!tradingEnabled && from != address(0) && to != address(0)) {
            if (!hasRole(DEFAULT_ADMIN_ROLE, from) && !hasRole(DEFAULT_ADMIN_ROLE, to)) {
                revert TradingNotEnabled();
            }
        }
        
        // Transaction size check
        if (amount > MAX_TRANSACTION_AMOUNT) {
            if (!hasRole(DEFAULT_ADMIN_ROLE, from)) {
                revert TransactionTooLarge(amount);
            }
        }
        
        // Rate limiting
        if (from != address(0) && to != address(0)) {
            if (block.timestamp < lastTransactionTime[from] + minTimeBetweenTransactions) {
                revert TransactionTooFrequent();
            }
            lastTransactionTime[from] = block.timestamp;
        }
        
        super._beforeTokenTransfer(from, to, amount);
    }

    function _afterTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._afterTokenTransfer(from, to, amount);
        
        // Apply transfer fee if configured
        if (transferFee > 0 && from != address(0) && to != address(0)) {
            uint256 fee = (amount * transferFee) / 10000;
            if (fee > 0 && to != treasury) {
                _transfer(to, treasury, fee);
            }
        }
    }

    // Minting function with role check
    function mint(address to, uint256 amount) public onlyRole(MINTER_ROLE) {
        _mint(to, amount);
    }

    // Snapshot function for governance
    function snapshot() public onlyRole(SNAPSHOT_ROLE) returns (uint256) {
        return _snapshot();
    }

    // Pause functions
    function pause() public onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() public onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    // Blacklist functions
    function blacklist(address account) public onlyRole(BLACKLIST_ROLE) {
        if (account == address(0)) revert InvalidAddress();
        if (hasRole(DEFAULT_ADMIN_ROLE, account)) revert InvalidAddress();
        
        blacklisted[account] = true;
        emit Blacklisted(account);
    }

    function unblacklist(address account) public onlyRole(BLACKLIST_ROLE) {
        blacklisted[account] = false;
        emit Unblacklisted(account);
    }

    // Trading control
    function enableTrading() public onlyRole(DEFAULT_ADMIN_ROLE) {
        tradingEnabled = true;
        emit TradingEnabled();
    }

    // Treasury management
    function updateTreasury(address newTreasury) public onlyRole(DEFAULT_ADMIN_ROLE) {
        if (newTreasury == address(0)) revert InvalidAddress();
        
        address oldTreasury = treasury;
        treasury = newTreasury;
        emit TreasuryUpdated(oldTreasury, newTreasury);
    }

    // Fee management
    function updateTransferFee(uint256 newFee) public onlyRole(DEFAULT_ADMIN_ROLE) {
        if (newFee > MAX_FEE) revert FeeTooHigh();
        
        uint256 oldFee = transferFee;
        transferFee = newFee;
        emit TransferFeeUpdated(oldFee, newFee);
    }

    // Rate limiting configuration
    function updateRateLimit(uint256 seconds_) public onlyRole(DEFAULT_ADMIN_ROLE) {
        minTimeBetweenTransactions = seconds_;
    }

    // Emergency functions
    function emergencyWithdraw(address token, uint256 amount) 
        public 
        onlyRole(DEFAULT_ADMIN_ROLE)
        nonReentrant 
    {
        if (token == address(0)) {
            // Withdraw ETH
            payable(msg.sender).transfer(amount);
        } else {
            // Withdraw ERC20
            IERC20(token).transfer(msg.sender, amount);
        }
        emit EmergencyWithdraw(msg.sender, amount);
    }

    // Required overrides
    function _mint(address to, uint256 amount) 
        internal 
        override(ERC20, ERC20Capped, ERC20Votes) 
    {
        super._mint(to, amount);
    }

    function _burn(address account, uint256 amount) 
        internal 
        override(ERC20, ERC20Votes) 
    {
        super._burn(account, amount);
    }

    // View functions
    function getCirculatingSupply() public view returns (uint256) {
        return totalSupply() - balanceOf(address(0)) - balanceOf(treasury);
    }

    // Receive function to accept ETH
    receive() external payable {}
}