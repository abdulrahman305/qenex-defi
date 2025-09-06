// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";

/**
 * @title QXC Staking V2
 * @author QENEX Team
 * @notice Secure staking contract with dynamic rewards and emergency features
 * @dev Implements staking with compound interest, slashing, and tiered rewards
 */
contract QXCStakingV2 is ReentrancyGuard, Pausable, AccessControl {
    using SafeERC20 for IERC20;
    using Math for uint256;

    // Roles
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");
    bytes32 public constant SLASHER_ROLE = keccak256("SLASHER_ROLE");

    // Structs
    struct Stake {
        uint256 amount;
        uint256 rewardDebt;
        uint256 pendingRewards;
        uint256 lockEndTime;
        uint256 lastUpdateTime;
        uint8 tier; // 0: Flexible, 1: 30 days, 2: 90 days, 3: 180 days
    }

    struct StakingTier {
        uint256 lockDuration;
        uint256 rewardMultiplier; // Basis points (10000 = 100%)
        uint256 minAmount;
        bool active;
    }

    // State variables
    IERC20 public immutable stakingToken;
    uint256 public totalStaked;
    uint256 public totalRewardsDistributed;
    uint256 public rewardPool;
    uint256 public accRewardPerShare;
    uint256 public lastRewardTime;
    uint256 public rewardPerSecond;
    
    mapping(address => Stake) public stakes;
    mapping(uint8 => StakingTier) public tiers;
    mapping(address => bool) public emergencyWithdrawn;
    
    // Constants
    uint256 private constant PRECISION = 1e18;
    uint256 public constant MIN_STAKE_AMOUNT = 10 ether;
    uint256 public constant MAX_REWARD_RATE = 100; // 100% APY max
    uint256 public constant EMERGENCY_WITHDRAW_PENALTY = 2000; // 20%
    
    // Events
    event Staked(address indexed user, uint256 amount, uint8 tier);
    event Unstaked(address indexed user, uint256 amount, uint256 reward);
    event RewardsClaimed(address indexed user, uint256 reward);
    event RewardPoolFunded(uint256 amount);
    event RewardRateUpdated(uint256 oldRate, uint256 newRate);
    event EmergencyWithdraw(address indexed user, uint256 amount);
    event Slashed(address indexed user, uint256 amount);
    event TierUpdated(uint8 tier, uint256 lockDuration, uint256 multiplier);
    
    // Custom errors
    error InsufficientStake();
    error StakeLocked();
    error InvalidTier();
    error TierNotActive();
    error AlreadyEmergencyWithdrawn();
    error RewardRateTooHigh();
    error NoStakeFound();
    error InsufficientRewardPool();

    constructor(address _stakingToken) {
        if (_stakingToken == address(0)) revert();
        stakingToken = IERC20(_stakingToken);
        
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(OPERATOR_ROLE, msg.sender);
        
        // Initialize staking tiers
        _initializeTiers();
        
        lastRewardTime = block.timestamp;
    }

    function _initializeTiers() private {
        // Flexible staking
        tiers[0] = StakingTier({
            lockDuration: 0,
            rewardMultiplier: 10000, // 100%
            minAmount: MIN_STAKE_AMOUNT,
            active: true
        });
        
        // 30 days lock
        tiers[1] = StakingTier({
            lockDuration: 30 days,
            rewardMultiplier: 12500, // 125%
            minAmount: 100 ether,
            active: true
        });
        
        // 90 days lock
        tiers[2] = StakingTier({
            lockDuration: 90 days,
            rewardMultiplier: 15000, // 150%
            minAmount: 500 ether,
            active: true
        });
        
        // 180 days lock
        tiers[3] = StakingTier({
            lockDuration: 180 days,
            rewardMultiplier: 20000, // 200%
            minAmount: 1000 ether,
            active: true
        });
    }

    // Update rewards before any stake changes
    modifier updateReward(address account) {
        _updatePool();
        if (account != address(0)) {
            Stake storage userStake = stakes[account];
            if (userStake.amount > 0) {
                uint256 pending = _calculatePendingReward(account);
                userStake.pendingRewards += pending;
                userStake.rewardDebt = (userStake.amount * accRewardPerShare) / PRECISION;
                userStake.lastUpdateTime = block.timestamp;
            }
        }
        _;
    }

    function stake(uint256 amount, uint8 tier) 
        external 
        nonReentrant 
        whenNotPaused 
        updateReward(msg.sender) 
    {
        if (tier > 3) revert InvalidTier();
        if (!tiers[tier].active) revert TierNotActive();
        
        StakingTier memory stakingTier = tiers[tier];
        if (amount < stakingTier.minAmount) revert InsufficientStake();
        
        Stake storage userStake = stakes[msg.sender];
        
        // If user already has a stake, must be same or higher tier
        if (userStake.amount > 0 && userStake.tier > tier) revert InvalidTier();
        
        // Transfer tokens
        stakingToken.safeTransferFrom(msg.sender, address(this), amount);
        
        // Update stake
        userStake.amount += amount;
        userStake.tier = tier;
        userStake.lockEndTime = block.timestamp + stakingTier.lockDuration;
        userStake.rewardDebt = (userStake.amount * accRewardPerShare) / PRECISION;
        userStake.lastUpdateTime = block.timestamp;
        
        totalStaked += amount;
        
        emit Staked(msg.sender, amount, tier);
    }

    function unstake(uint256 amount) 
        external 
        nonReentrant 
        whenNotPaused 
        updateReward(msg.sender) 
    {
        Stake storage userStake = stakes[msg.sender];
        
        if (userStake.amount < amount) revert InsufficientStake();
        if (block.timestamp < userStake.lockEndTime) revert StakeLocked();
        
        // Calculate total rewards
        uint256 reward = userStake.pendingRewards;
        
        // Update stake
        userStake.amount -= amount;
        userStake.pendingRewards = 0;
        userStake.rewardDebt = (userStake.amount * accRewardPerShare) / PRECISION;
        
        totalStaked -= amount;
        totalRewardsDistributed += reward;
        
        // Transfer tokens and rewards
        stakingToken.safeTransfer(msg.sender, amount + reward);
        
        emit Unstaked(msg.sender, amount, reward);
    }

    function claimRewards() 
        external 
        nonReentrant 
        whenNotPaused 
        updateReward(msg.sender) 
    {
        Stake storage userStake = stakes[msg.sender];
        
        uint256 reward = userStake.pendingRewards;
        if (reward == 0) revert NoStakeFound();
        
        userStake.pendingRewards = 0;
        totalRewardsDistributed += reward;
        
        stakingToken.safeTransfer(msg.sender, reward);
        
        emit RewardsClaimed(msg.sender, reward);
    }

    function emergencyWithdraw() external nonReentrant {
        if (emergencyWithdrawn[msg.sender]) revert AlreadyEmergencyWithdrawn();
        
        Stake storage userStake = stakes[msg.sender];
        if (userStake.amount == 0) revert NoStakeFound();
        
        uint256 amount = userStake.amount;
        uint256 penalty = (amount * EMERGENCY_WITHDRAW_PENALTY) / 10000;
        uint256 withdrawAmount = amount - penalty;
        
        // Clear stake
        totalStaked -= amount;
        delete stakes[msg.sender];
        emergencyWithdrawn[msg.sender] = true;
        
        // Transfer penalty to reward pool
        rewardPool += penalty;
        
        // Transfer remaining to user
        stakingToken.safeTransfer(msg.sender, withdrawAmount);
        
        emit EmergencyWithdraw(msg.sender, withdrawAmount);
    }

    // Admin functions
    function fundRewardPool(uint256 amount) external onlyRole(OPERATOR_ROLE) {
        stakingToken.safeTransferFrom(msg.sender, address(this), amount);
        rewardPool += amount;
        emit RewardPoolFunded(amount);
    }

    function updateRewardRate(uint256 newRate) external onlyRole(OPERATOR_ROLE) {
        if (newRate > MAX_REWARD_RATE) revert RewardRateTooHigh();
        
        _updatePool();
        uint256 oldRate = rewardPerSecond;
        rewardPerSecond = newRate;
        
        emit RewardRateUpdated(oldRate, newRate);
    }

    function updateTier(
        uint8 tier,
        uint256 lockDuration,
        uint256 multiplier,
        uint256 minAmount,
        bool active
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (tier > 3) revert InvalidTier();
        
        tiers[tier] = StakingTier({
            lockDuration: lockDuration,
            rewardMultiplier: multiplier,
            minAmount: minAmount,
            active: active
        });
        
        emit TierUpdated(tier, lockDuration, multiplier);
    }

    function slash(address user, uint256 amount) external onlyRole(SLASHER_ROLE) {
        Stake storage userStake = stakes[user];
        
        if (userStake.amount < amount) {
            amount = userStake.amount;
        }
        
        userStake.amount -= amount;
        totalStaked -= amount;
        rewardPool += amount;
        
        emit Slashed(user, amount);
    }

    function pause() external onlyRole(OPERATOR_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(OPERATOR_ROLE) {
        _unpause();
    }

    // Internal functions
    function _updatePool() private {
        if (block.timestamp <= lastRewardTime) return;
        
        if (totalStaked == 0) {
            lastRewardTime = block.timestamp;
            return;
        }
        
        uint256 timeDelta = block.timestamp - lastRewardTime;
        uint256 reward = timeDelta * rewardPerSecond;
        
        if (reward > rewardPool) {
            reward = rewardPool;
        }
        
        rewardPool -= reward;
        accRewardPerShare += (reward * PRECISION) / totalStaked;
        lastRewardTime = block.timestamp;
    }

    function _calculatePendingReward(address user) private view returns (uint256) {
        Stake memory userStake = stakes[user];
        
        if (userStake.amount == 0) return 0;
        
        uint256 adjustedAccReward = accRewardPerShare;
        
        if (block.timestamp > lastRewardTime && totalStaked > 0) {
            uint256 timeDelta = block.timestamp - lastRewardTime;
            uint256 reward = timeDelta * rewardPerSecond;
            
            if (reward > rewardPool) {
                reward = rewardPool;
            }
            
            adjustedAccReward += (reward * PRECISION) / totalStaked;
        }
        
        uint256 baseReward = (userStake.amount * adjustedAccReward) / PRECISION - userStake.rewardDebt;
        uint256 tierMultiplier = tiers[userStake.tier].rewardMultiplier;
        
        return (baseReward * tierMultiplier) / 10000;
    }

    // View functions
    function getStakeInfo(address user) external view returns (
        uint256 stakedAmount,
        uint256 pendingReward,
        uint256 lockEndTime,
        uint8 tier,
        bool canUnstake
    ) {
        Stake memory userStake = stakes[user];
        stakedAmount = userStake.amount;
        pendingReward = userStake.pendingRewards + _calculatePendingReward(user);
        lockEndTime = userStake.lockEndTime;
        tier = userStake.tier;
        canUnstake = block.timestamp >= userStake.lockEndTime;
    }

    function getTierInfo(uint8 tier) external view returns (
        uint256 lockDuration,
        uint256 rewardMultiplier,
        uint256 minAmount,
        bool active
    ) {
        StakingTier memory stakingTier = tiers[tier];
        return (
            stakingTier.lockDuration,
            stakingTier.rewardMultiplier,
            stakingTier.minAmount,
            stakingTier.active
        );
    }

    function getAPY(uint8 tier) external view returns (uint256) {
        if (totalStaked == 0) return 0;
        
        uint256 yearlyReward = rewardPerSecond * 365 days;
        uint256 baseAPY = (yearlyReward * 10000) / totalStaked;
        uint256 tierMultiplier = tiers[tier].rewardMultiplier;
        
        return (baseAPY * tierMultiplier) / 10000;
    }
}