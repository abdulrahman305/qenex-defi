// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title QXC Staking
 * @author QENEX Team
 * @notice Staking contract with rewards
 * @dev Simple staking implementation with security features
 */
contract QXCStaking is ReentrancyGuard, Ownable, Pausable {
    using SafeERC20 for IERC20;
    
    IERC20 public immutable stakingToken;
    
    struct Stake {
        uint256 amount;
        uint256 timestamp;
        uint256 rewardsClaimed;
    }
    
    mapping(address => Stake) public stakes;
    uint256 public totalStaked;
    uint256 public rewardRate = 15; // 15% APY
    uint256 public constant SECONDS_IN_YEAR = 365 days;
    
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount, uint256 reward);
    event RewardsClaimed(address indexed user, uint256 reward);
    event RewardRateUpdated(uint256 newRate);
    
    constructor(address _token) Ownable(msg.sender) {
        require(_token != address(0), "Invalid token");
        stakingToken = IERC20(_token);
    }
    
    function stake(uint256 amount) external nonReentrant whenNotPaused {
        require(amount > 0, "Amount must be > 0");
        
        // Claim pending rewards first
        if (stakes[msg.sender].amount > 0) {
            _claimRewards(msg.sender);
        }
        
        stakingToken.safeTransferFrom(msg.sender, address(this), amount);
        
        stakes[msg.sender].amount += amount;
        stakes[msg.sender].timestamp = block.timestamp;
        totalStaked += amount;
        
        emit Staked(msg.sender, amount);
    }
    
    function unstake() external nonReentrant whenNotPaused {
        Stake memory userStake = stakes[msg.sender];
        require(userStake.amount > 0, "No stake found");
        
        uint256 reward = _calculateReward(msg.sender);
        uint256 totalAmount = userStake.amount + reward;
        
        // Reset stake
        delete stakes[msg.sender];
        totalStaked -= userStake.amount;
        
        // Transfer tokens and rewards
        stakingToken.safeTransfer(msg.sender, totalAmount);
        
        emit Unstaked(msg.sender, userStake.amount, reward);
    }
    
    function claimRewards() external nonReentrant whenNotPaused {
        _claimRewards(msg.sender);
    }
    
    function _claimRewards(address user) private {
        uint256 reward = _calculateReward(user);
        if (reward > 0) {
            stakes[user].rewardsClaimed += reward;
            stakes[user].timestamp = block.timestamp;
            stakingToken.safeTransfer(user, reward);
            emit RewardsClaimed(user, reward);
        }
    }
    
    function _calculateReward(address user) private view returns (uint256) {
        Stake memory userStake = stakes[user];
        if (userStake.amount == 0) return 0;
        
        uint256 duration = block.timestamp - userStake.timestamp;
        uint256 reward = (userStake.amount * rewardRate * duration) / (100 * SECONDS_IN_YEAR);
        
        return reward;
    }
    
    function getPendingReward(address user) external view returns (uint256) {
        return _calculateReward(user);
    }
    
    function updateRewardRate(uint256 newRate) external onlyOwner {
        require(newRate <= 100, "Rate too high");
        rewardRate = newRate;
        emit RewardRateUpdated(newRate);
    }
    
    function pause() external onlyOwner {
        _pause();
    }
    
    function unpause() external onlyOwner {
        _unpause();
    }
    
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner(), amount);
    }
}