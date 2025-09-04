// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Capped.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title QXC Token
 * @author QENEX Team
 * @notice Production-ready QXC token with security features
 * @dev ERC20 token with cap, burn, pause, and access control
 */
contract QXCToken is ERC20, ERC20Burnable, ERC20Capped, AccessControl, Pausable {
    // Roles
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    // Constants
    uint256 public constant INITIAL_SUPPLY = 1525.30 ether;
    uint256 public constant MAX_SUPPLY = 21_000_000 ether;
    
    // State
    bool public tradingEnabled = false;
    mapping(address => bool) public blacklisted;
    
    // Events
    event TradingEnabled();
    event Blacklisted(address indexed account, bool status);
    
    constructor() 
        ERC20("QENEX Coin", "QXC")
        ERC20Capped(MAX_SUPPLY)
    {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
        
        _mint(msg.sender, INITIAL_SUPPLY);
    }

    function mint(address to, uint256 amount) public onlyRole(MINTER_ROLE) {
        _mint(to, amount);
    }

    function pause() public onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() public onlyRole(PAUSER_ROLE) {
        _unpause();
    }
    
    function enableTrading() public onlyRole(DEFAULT_ADMIN_ROLE) {
        tradingEnabled = true;
        emit TradingEnabled();
    }
    
    function setBlacklist(address account, bool status) public onlyRole(DEFAULT_ADMIN_ROLE) {
        blacklisted[account] = status;
        emit Blacklisted(account, status);
    }

    function _update(address from, address to, uint256 amount)
        internal
        override(ERC20, ERC20Capped)
        whenNotPaused
    {
        require(!blacklisted[from] && !blacklisted[to], "Blacklisted");
        
        if (!tradingEnabled && from != address(0) && to != address(0)) {
            require(
                hasRole(DEFAULT_ADMIN_ROLE, from) || hasRole(DEFAULT_ADMIN_ROLE, to),
                "Trading not enabled"
            );
        }
        
        super._update(from, to, amount);
    }
}