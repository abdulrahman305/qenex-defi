// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title QXC Staking - Minimalist Fixed Version
 * @notice Simple staking with sustainable rewards
 * @dev Rewards must be funded separately by owner
 */
contract QXCStakingFixed is ReentrancyGuard, Ownable, Pausable {
    using SafeERC20 for IERC20;
    
    IERC20 public immutable stakingToken;
    
    struct Stake {
        uint256 amount;
        uint256 timestamp;
    }
    
    mapping(address => Stake) public stakes;
    uint256 public totalStaked;
    uint256 public rewardRate = 10; // 10% APY (reduced from 15%)
    uint256 public rewardPool; // Separate reward pool
    uint256 public constant SECONDS_IN_YEAR = 365 days;
    uint256 public constant MIN_STAKE_DURATION = 7 days; // Minimum stake period
    
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount, uint256 reward);
    event RewardsDeposited(uint256 amount);
    event EmergencyWithdraw(address indexed user, uint256 amount);
    
    constructor(address _token) Ownable(msg.sender) {
        require(_token != address(0), "Invalid token");
        stakingToken = IERC20(_token);
    }
    
    // Owner must fund rewards separately
    function depositRewards(uint256 amount) external onlyOwner {
        require(amount > 0, "Amount must be > 0");
        stakingToken.safeTransferFrom(msg.sender, address(this), amount);
        rewardPool += amount;
        emit RewardsDeposited(amount);
    }
    
    function stake(uint256 amount) external nonReentrant whenNotPaused {
        require(amount >= 100 * 10**18, "Minimum 100 tokens");
        require(amount <= 10000 * 10**18, "Maximum 10000 tokens");
        
        // Only one stake per address for simplicity
        require(stakes[msg.sender].amount == 0, "Already staking");
        
        stakingToken.safeTransferFrom(msg.sender, address(this), amount);
        
        stakes[msg.sender] = Stake({
            amount: amount,
            timestamp: block.timestamp
        });
        
        totalStaked += amount;
        emit Staked(msg.sender, amount);
    }
    
    function unstake() external nonReentrant whenNotPaused {
        Stake memory userStake = stakes[msg.sender];
        require(userStake.amount > 0, "No stake found");
        require(
            block.timestamp >= userStake.timestamp + MIN_STAKE_DURATION,
            "Minimum stake period not met"
        );
        
        uint256 reward = calculateReward(msg.sender);
        
        // Check reward pool has enough funds
        if (reward > rewardPool) {
            reward = rewardPool; // Cap at available rewards
        }
        
        // Update state
        delete stakes[msg.sender];
        totalStaked -= userStake.amount;
        rewardPool -= reward;
        
        // Transfer principal + rewards
        uint256 totalAmount = userStake.amount + reward;
        stakingToken.safeTransfer(msg.sender, totalAmount);
        
        emit Unstaked(msg.sender, userStake.amount, reward);
    }
    
    // Emergency withdraw without rewards
    function emergencyWithdraw() external nonReentrant {
        Stake memory userStake = stakes[msg.sender];
        require(userStake.amount > 0, "No stake found");
        
        uint256 amount = userStake.amount;
        delete stakes[msg.sender];
        totalStaked -= amount;
        
        stakingToken.safeTransfer(msg.sender, amount);
        emit EmergencyWithdraw(msg.sender, amount);
    }
    
    function calculateReward(address user) public view returns (uint256) {
        Stake memory userStake = stakes[user];
        if (userStake.amount == 0) return 0;
        
        uint256 duration = block.timestamp - userStake.timestamp;
        if (duration < MIN_STAKE_DURATION) return 0;
        
        // Simple interest calculation (not compound)
        uint256 reward = (userStake.amount * rewardRate * duration) / (100 * SECONDS_IN_YEAR);
        
        // Cap reward at 50% of stake amount
        uint256 maxReward = userStake.amount / 2;
        if (reward > maxReward) {
            reward = maxReward;
        }
        
        return reward;
    }
    
    // View functions
    function getStakeInfo(address user) external view returns (
        uint256 amount,
        uint256 timestamp,
        uint256 pendingReward,
        bool canUnstake
    ) {
        Stake memory userStake = stakes[user];
        amount = userStake.amount;
        timestamp = userStake.timestamp;
        pendingReward = calculateReward(user);
        canUnstake = block.timestamp >= userStake.timestamp + MIN_STAKE_DURATION;
    }
    
    function getContractInfo() external view returns (
        uint256 _totalStaked,
        uint256 _rewardPool,
        uint256 _rewardRate
    ) {
        return (totalStaked, rewardPool, rewardRate);
    }
    
    // Admin functions
    function pause() external onlyOwner {
        _pause();
    }
    
    function unpause() external onlyOwner {
        _unpause();
    }
}