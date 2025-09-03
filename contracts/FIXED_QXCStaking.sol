// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title QXC Staking Platform - Security Hardened
 * @dev Stake QXC tokens to earn rewards with comprehensive security measures
 */
contract QXCStaking is ReentrancyGuard, Pausable, Ownable {
    using SafeERC20 for IERC20;
    
    IERC20 public immutable qxcToken;
    
    struct Stake {
        uint256 amount;
        uint256 timestamp;
        uint256 rewardsClaimed;
        uint256 lastRewardCalculation;
    }
    
    mapping(address => Stake) public stakes;
    mapping(address => uint256) public pendingRewards;
    
    uint256 public totalStaked;
    uint256 public rewardRate = 15; // 15% APY
    uint256 public minStakeAmount = 100 * 10**18; // 100 QXC minimum
    uint256 public maxStakeAmount = 1000000 * 10**18; // 1M QXC maximum per user
    uint256 public lockupPeriod = 7 days; // Minimum staking period
    
    // Security: Track reward pool separately
    uint256 public rewardPool;
    uint256 public constant MAX_REWARD_RATE = 50; // Maximum 50% APY
    
    event Staked(address indexed user, uint256 amount, uint256 timestamp);
    event Unstaked(address indexed user, uint256 amount, uint256 reward);
    event RewardsClaimed(address indexed user, uint256 amount);
    event RewardRateUpdated(uint256 oldRate, uint256 newRate);
    event RewardPoolFunded(uint256 amount);
    event EmergencyWithdraw(address indexed user, uint256 amount);
    
    constructor(address _qxcToken) {
        require(_qxcToken != address(0), "Invalid token address");
        qxcToken = IERC20(_qxcToken);
    }
    
    /**
     * @dev Stake QXC tokens with enhanced security checks
     */
    function stake(uint256 amount) external nonReentrant whenNotPaused {
        require(amount >= minStakeAmount, "Below minimum stake");
        require(amount <= maxStakeAmount, "Exceeds maximum stake");
        
        address user = msg.sender;
        Stake storage userStake = stakes[user];
        
        // Check total stake doesn't exceed max
        require(
            userStake.amount + amount <= maxStakeAmount,
            "Total stake exceeds maximum"
        );
        
        // Calculate and store pending rewards before updating stake
        if (userStake.amount > 0) {
            uint256 reward = _calculateRewards(user);
            pendingRewards[user] += reward;
            userStake.lastRewardCalculation = block.timestamp;
        }
        
        // Update stake
        userStake.amount += amount;
        userStake.timestamp = block.timestamp;
        totalStaked += amount;
        
        // Transfer tokens using SafeERC20
        qxcToken.safeTransferFrom(user, address(this), amount);
        
        emit Staked(user, amount, block.timestamp);
    }
    
    /**
     * @dev Unstake QXC tokens with lockup period check
     */
    function unstake(uint256 amount) external nonReentrant whenNotPaused {
        address user = msg.sender;
        Stake storage userStake = stakes[user];
        
        require(userStake.amount >= amount, "Insufficient stake");
        require(
            block.timestamp >= userStake.timestamp + lockupPeriod,
            "Stake still locked"
        );
        
        // Calculate all pending rewards
        uint256 rewards = pendingRewards[user] + _calculateRewards(user);
        require(rewardPool >= rewards, "Insufficient reward pool");
        
        // Update state BEFORE external calls
        userStake.amount -= amount;
        userStake.lastRewardCalculation = block.timestamp;
        totalStaked -= amount;
        pendingRewards[user] = 0;
        rewardPool -= rewards;
        
        // Transfer tokens and rewards
        uint256 totalTransfer = amount + rewards;
        qxcToken.safeTransfer(user, totalTransfer);
        
        emit Unstaked(user, amount, rewards);
    }
    
    /**
     * @dev Claim staking rewards without unstaking
     */
    function claimRewards() external nonReentrant whenNotPaused {
        address user = msg.sender;
        Stake storage userStake = stakes[user];
        
        uint256 rewards = pendingRewards[user] + _calculateRewards(user);
        require(rewards > 0, "No rewards available");
        require(rewardPool >= rewards, "Insufficient reward pool");
        
        // Update state BEFORE external call
        pendingRewards[user] = 0;
        userStake.lastRewardCalculation = block.timestamp;
        userStake.rewardsClaimed += rewards;
        rewardPool -= rewards;
        
        // Transfer rewards
        qxcToken.safeTransfer(user, rewards);
        
        emit RewardsClaimed(user, rewards);
    }
    
    /**
     * @dev Emergency withdraw without rewards (penalty situation)
     */
    function emergencyWithdraw() external nonReentrant {
        address user = msg.sender;
        Stake storage userStake = stakes[user];
        uint256 amount = userStake.amount;
        
        require(amount > 0, "No stake to withdraw");
        
        // Reset user stake
        userStake.amount = 0;
        userStake.timestamp = 0;
        userStake.lastRewardCalculation = 0;
        totalStaked -= amount;
        pendingRewards[user] = 0;
        
        // Transfer only principal (no rewards)
        qxcToken.safeTransfer(user, amount);
        
        emit EmergencyWithdraw(user, amount);
    }
    
    /**
     * @dev Calculate pending rewards with overflow protection
     */
    function _calculateRewards(address user) private view returns (uint256) {
        Stake memory userStake = stakes[user];
        if (userStake.amount == 0) return 0;
        
        uint256 timeElapsed = block.timestamp - userStake.lastRewardCalculation;
        if (timeElapsed == 0) return 0;
        
        // Prevent overflow with safe math
        uint256 annualReward = (userStake.amount * rewardRate) / 100;
        uint256 reward = (annualReward * timeElapsed) / 365 days;
        
        return reward;
    }
    
    /**
     * @dev Get user's total pending rewards
     */
    function getPendingRewards(address user) external view returns (uint256) {
        return pendingRewards[user] + _calculateRewards(user);
    }
    
    /**
     * @dev Get user staking info
     */
    function getUserInfo(address user) external view returns (
        uint256 stakedAmount,
        uint256 pendingReward,
        uint256 totalClaimed,
        uint256 stakingTime,
        bool canUnstake
    ) {
        Stake memory userStake = stakes[user];
        stakedAmount = userStake.amount;
        pendingReward = pendingRewards[user] + _calculateRewards(user);
        totalClaimed = userStake.rewardsClaimed;
        stakingTime = userStake.timestamp;
        canUnstake = block.timestamp >= userStake.timestamp + lockupPeriod;
    }
    
    // ========== ADMIN FUNCTIONS ==========
    
    /**
     * @dev Fund the reward pool
     */
    function fundRewardPool(uint256 amount) external onlyOwner {
        require(amount > 0, "Invalid amount");
        
        rewardPool += amount;
        qxcToken.safeTransferFrom(msg.sender, address(this), amount);
        
        emit RewardPoolFunded(amount);
    }
    
    /**
     * @dev Update reward rate with maximum cap
     */
    function updateRewardRate(uint256 newRate) external onlyOwner {
        require(newRate <= MAX_REWARD_RATE, "Rate exceeds maximum");
        
        uint256 oldRate = rewardRate;
        rewardRate = newRate;
        
        emit RewardRateUpdated(oldRate, newRate);
    }
    
    /**
     * @dev Update minimum stake amount
     */
    function updateMinStake(uint256 newMinimum) external onlyOwner {
        require(newMinimum > 0, "Invalid minimum");
        minStakeAmount = newMinimum;
    }
    
    /**
     * @dev Pause contract in emergency
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    /**
     * @dev Unpause contract
     */
    function unpause() external onlyOwner {
        _unpause();
    }
    
    /**
     * @dev Get platform statistics
     */
    function getStats() external view returns (
        uint256 _totalStaked,
        uint256 _rewardRate,
        uint256 _minStake,
        uint256 _maxStake,
        uint256 _rewardPool,
        uint256 _lockupPeriod
    ) {
        return (
            totalStaked,
            rewardRate,
            minStakeAmount,
            maxStakeAmount,
            rewardPool,
            lockupPeriod
        );
    }
}