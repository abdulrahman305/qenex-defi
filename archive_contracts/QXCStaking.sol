// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title QXC Staking Platform
 * @dev Stake QXC tokens to earn rewards from AI mining
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract QXCStaking {
    IERC20 public qxcToken;
    
    struct Stake {
        uint256 amount;
        uint256 timestamp;
        uint256 rewardsClaimed;
    }
    
    mapping(address => Stake) public stakes;
    mapping(address => uint256) public rewards;
    
    uint256 public totalStaked;
    uint256 public rewardRate = 15; // 15% APY
    uint256 public minStakeAmount = 100 * 10**18; // 100 QXC minimum
    
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event RewardsClaimed(address indexed user, uint256 amount);
    
    constructor(address _qxcToken) {
        qxcToken = IERC20(_qxcToken);
    }
    
    /**
     * @dev Stake QXC tokens
     */
    function stake(uint256 amount) external {
        require(amount >= minStakeAmount, "Below minimum stake");
        require(qxcToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        
        // Calculate pending rewards before updating stake
        if (stakes[msg.sender].amount > 0) {
            rewards[msg.sender] += calculateRewards(msg.sender);
        }
        
        stakes[msg.sender].amount += amount;
        stakes[msg.sender].timestamp = block.timestamp;
        totalStaked += amount;
        
        emit Staked(msg.sender, amount);
    }
    
    /**
     * @dev Unstake QXC tokens
     */
    function unstake(uint256 amount) external {
        require(stakes[msg.sender].amount >= amount, "Insufficient stake");
        
        // Calculate rewards before unstaking
        rewards[msg.sender] += calculateRewards(msg.sender);
        
        stakes[msg.sender].amount -= amount;
        stakes[msg.sender].timestamp = block.timestamp;
        totalStaked -= amount;
        
        require(qxcToken.transfer(msg.sender, amount), "Transfer failed");
        
        emit Unstaked(msg.sender, amount);
    }
    
    /**
     * @dev Claim staking rewards
     */
    function claimRewards() external {
        uint256 reward = rewards[msg.sender] + calculateRewards(msg.sender);
        require(reward > 0, "No rewards available");
        
        rewards[msg.sender] = 0;
        stakes[msg.sender].timestamp = block.timestamp;
        stakes[msg.sender].rewardsClaimed += reward;
        
        require(qxcToken.transfer(msg.sender, reward), "Transfer failed");
        
        emit RewardsClaimed(msg.sender, reward);
    }
    
    /**
     * @dev Calculate pending rewards
     */
    function calculateRewards(address user) public view returns (uint256) {
        Stake memory userStake = stakes[user];
        if (userStake.amount == 0) return 0;
        
        uint256 stakingDuration = block.timestamp - userStake.timestamp;
        uint256 annualReward = (userStake.amount * rewardRate) / 100;
        uint256 reward = (annualReward * stakingDuration) / 365 days;
        
        return reward;
    }
    
    /**
     * @dev Get user staking info
     */
    function getUserInfo(address user) external view returns (
        uint256 stakedAmount,
        uint256 pendingRewards,
        uint256 totalClaimed,
        uint256 stakingTime
    ) {
        stakedAmount = stakes[user].amount;
        pendingRewards = rewards[user] + calculateRewards(user);
        totalClaimed = stakes[user].rewardsClaimed;
        stakingTime = stakes[user].timestamp;
    }
    
    /**
     * @dev Get platform statistics
     */
    function getStats() external view returns (
        uint256 _totalStaked,
        uint256 _rewardRate,
        uint256 _minStake
    ) {
        _totalStaked = totalStaked;
        _rewardRate = rewardRate;
        _minStake = minStakeAmount;
    }
}