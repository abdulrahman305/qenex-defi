// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Capped.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title SecureQXCToken
 * @dev Production-ready token with all security features
 */
contract SecureQXCToken is ERC20Capped, Pausable, AccessControl, ReentrancyGuard {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    
    uint256 public constant INITIAL_SUPPLY = 1525.30 ether;
    uint256 public constant MAX_SUPPLY = 21_000_000 ether;
    
    constructor() 
        ERC20("QENEX Coin", "QXC") 
        ERC20Capped(MAX_SUPPLY) 
    {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
        
        _mint(msg.sender, INITIAL_SUPPLY);
    }
    
    function mint(address to, uint256 amount) 
        public 
        onlyRole(MINTER_ROLE) 
        whenNotPaused 
    {
        _mint(to, amount);
    }
    
    function pause() public onlyRole(PAUSER_ROLE) {
        _pause();
    }
    
    function unpause() public onlyRole(PAUSER_ROLE) {
        _unpause();
    }
    
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override whenNotPaused {
        super._beforeTokenTransfer(from, to, amount);
    }
}

/**
 * @title SecureStaking
 * @dev Secure staking with reentrancy protection
 */
contract SecureStaking is ReentrancyGuard, Pausable, AccessControl {
    IERC20 public immutable stakingToken;
    
    uint256 public constant REWARD_RATE = 15; // 15% APY
    uint256 public constant LOCK_PERIOD = 7 days;
    
    struct Stake {
        uint256 amount;
        uint256 timestamp;
        uint256 rewardsClaimed;
    }
    
    mapping(address => Stake) public stakes;
    
    constructor(address _token) {
        stakingToken = IERC20(_token);
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }
    
    function stake(uint256 amount) external nonReentrant whenNotPaused {
        require(amount > 0, "Cannot stake 0");
        
        // Calculate pending rewards first
        if (stakes[msg.sender].amount > 0) {
            _claimRewards();
        }
        
        // Effects
        stakes[msg.sender].amount += amount;
        stakes[msg.sender].timestamp = block.timestamp;
        
        // Interactions (CEI pattern)
        require(stakingToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");
    }
    
    function unstake() external nonReentrant whenNotPaused {
        Stake storage userStake = stakes[msg.sender];
        require(userStake.amount > 0, "No stake");
        require(block.timestamp >= userStake.timestamp + LOCK_PERIOD, "Still locked");
        
        uint256 amount = userStake.amount;
        uint256 reward = _calculateReward(msg.sender);
        
        // Effects first (CEI pattern)
        delete stakes[msg.sender];
        
        // Interactions last
        require(stakingToken.transfer(msg.sender, amount + reward), "Transfer failed");
    }
    
    function _calculateReward(address user) private view returns (uint256) {
        Stake memory userStake = stakes[user];
        if (userStake.amount == 0) return 0;
        
        uint256 stakingDuration = block.timestamp - userStake.timestamp;
        return (userStake.amount * REWARD_RATE * stakingDuration) / (365 days * 100);
    }
    
    function _claimRewards() private {
        uint256 reward = _calculateReward(msg.sender);
        if (reward > 0) {
            stakes[msg.sender].rewardsClaimed += reward;
            require(stakingToken.transfer(msg.sender, reward), "Reward transfer failed");
        }
    }
}