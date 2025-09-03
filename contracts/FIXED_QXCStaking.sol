// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title QXC Staking - FIXED VERSION
 * @notice Secure staking contract with reentrancy protection
 * @dev Implements checks-effects-interactions pattern
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract QXCStaking {
    IERC20 public immutable qxcToken;
    address public owner;
    
    // Staking parameters
    uint256 public constant REWARD_RATE = 15; // 15% APY
    uint256 public constant MIN_STAKE = 10 * 10**18; // Minimum 10 QXC
    uint256 public constant LOCK_PERIOD = 7 days; // Minimum lock period
    
    // Staking state
    struct Stake {
        uint256 amount;
        uint256 timestamp;
        uint256 rewardsClaimed;
        uint256 lastClaimTime;
    }
    
    mapping(address => Stake) public stakes;
    uint256 public totalStaked;
    uint256 public rewardPool;
    
    // Security
    bool private locked;
    bool public paused;
    
    // Events
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount, uint256 reward);
    event RewardsClaimed(address indexed user, uint256 amount);
    event RewardPoolFunded(uint256 amount);
    event EmergencyWithdraw(address indexed user, uint256 amount);
    
    // Modifiers
    modifier nonReentrant() {
        require(!locked, "Reentrant call");
        locked = true;
        _;
        locked = false;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    modifier whenNotPaused() {
        require(!paused, "Contract paused");
        _;
    }
    
    constructor(address _token) {
        require(_token != address(0), "Invalid token");
        qxcToken = IERC20(_token);
        owner = msg.sender;
    }
    
    /**
     * @notice Stake QXC tokens
     * @param amount Amount to stake
     */
    function stake(uint256 amount) external nonReentrant whenNotPaused {
        require(amount >= MIN_STAKE, "Below minimum stake");
        require(qxcToken.balanceOf(msg.sender) >= amount, "Insufficient balance");
        
        // Calculate pending rewards before updating stake
        if (stakes[msg.sender].amount > 0) {
            _claimRewards(msg.sender);
        }
        
        // Effects
        stakes[msg.sender].amount += amount;
        stakes[msg.sender].timestamp = block.timestamp;
        stakes[msg.sender].lastClaimTime = block.timestamp;
        totalStaked += amount;
        
        // Interactions
        require(qxcToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        
        emit Staked(msg.sender, amount);
    }
    
    /**
     * @notice Unstake tokens and claim rewards
     */
    function unstake() external nonReentrant whenNotPaused {
        Stake storage userStake = stakes[msg.sender];
        require(userStake.amount > 0, "No stake");
        require(block.timestamp >= userStake.timestamp + LOCK_PERIOD, "Lock period active");
        
        uint256 amount = userStake.amount;
        uint256 reward = calculateReward(msg.sender);
        
        // Check reward pool has sufficient funds
        if (reward > rewardPool) {
            reward = rewardPool; // Cap reward at available pool
        }
        
        // Effects
        totalStaked -= amount;
        rewardPool -= reward;
        delete stakes[msg.sender];
        
        // Interactions
        require(qxcToken.transfer(msg.sender, amount + reward), "Transfer failed");
        
        emit Unstaked(msg.sender, amount, reward);
    }
    
    /**
     * @notice Claim accumulated rewards without unstaking
     */
    function claimRewards() external nonReentrant whenNotPaused {
        require(stakes[msg.sender].amount > 0, "No stake");
        _claimRewards(msg.sender);
    }
    
    /**
     * @notice Internal function to claim rewards
     */
    function _claimRewards(address user) private {
        uint256 reward = calculateReward(user);
        
        if (reward > 0) {
            // Check reward pool has sufficient funds
            if (reward > rewardPool) {
                reward = rewardPool; // Cap reward at available pool
            }
            
            // Effects
            stakes[user].rewardsClaimed += reward;
            stakes[user].lastClaimTime = block.timestamp;
            rewardPool -= reward;
            
            // Interactions
            require(qxcToken.transfer(user, reward), "Reward transfer failed");
            
            emit RewardsClaimed(user, reward);
        }
    }
    
    /**
     * @notice Calculate pending rewards for a user
     */
    function calculateReward(address user) public view returns (uint256) {
        Stake memory userStake = stakes[user];
        if (userStake.amount == 0) return 0;
        
        uint256 stakingDuration = block.timestamp - userStake.lastClaimTime;
        uint256 annualReward = (userStake.amount * REWARD_RATE) / 100;
        uint256 reward = (annualReward * stakingDuration) / 365 days;
        
        return reward;
    }
    
    /**
     * @notice Fund the reward pool
     * @param amount Amount to add to reward pool
     */
    function fundRewardPool(uint256 amount) external onlyOwner {
        require(amount > 0, "Invalid amount");
        require(qxcToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        
        rewardPool += amount;
        emit RewardPoolFunded(amount);
    }
    
    /**
     * @notice Emergency withdraw without rewards (only if paused)
     */
    function emergencyWithdraw() external nonReentrant {
        require(paused, "Not emergency");
        
        Stake storage userStake = stakes[msg.sender];
        require(userStake.amount > 0, "No stake");
        
        uint256 amount = userStake.amount;
        
        // Effects
        totalStaked -= amount;
        delete stakes[msg.sender];
        
        // Interactions
        require(qxcToken.transfer(msg.sender, amount), "Transfer failed");
        
        emit EmergencyWithdraw(msg.sender, amount);
    }
    
    /**
     * @notice Pause contract (emergency only)
     */
    function pause() external onlyOwner {
        paused = true;
    }
    
    /**
     * @notice Unpause contract
     */
    function unpause() external onlyOwner {
        paused = false;
    }
    
    /**
     * @notice Get staking info for a user
     */
    function getStakeInfo(address user) external view returns (
        uint256 stakedAmount,
        uint256 pendingReward,
        uint256 stakingTime,
        bool canUnstake
    ) {
        Stake memory userStake = stakes[user];
        stakedAmount = userStake.amount;
        pendingReward = calculateReward(user);
        stakingTime = userStake.timestamp;
        canUnstake = block.timestamp >= userStake.timestamp + LOCK_PERIOD;
    }
}