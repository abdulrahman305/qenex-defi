// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * QXC Token - Complete Contract
 * All features in one simple file
 */

contract QXCToken {
    string public name = "QENEX Coin";
    string public symbol = "QXC";
    uint8 public decimals = 18;
    uint256 public totalSupply = 1525.30 ether;
    
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    // Staking
    mapping(address => uint256) public staked;
    mapping(address => uint256) public stakingTime;
    uint256 public constant STAKING_RATE = 15; // 15% APY
    
    // Events
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount, uint256 reward);
    
    constructor() {
        balanceOf[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
    }
    
    function transfer(address to, uint256 amount) public returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        
        emit Transfer(msg.sender, to, amount);
        return true;
    }
    
    function approve(address spender, uint256 amount) public returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        allowance[from][msg.sender] -= amount;
        
        emit Transfer(from, to, amount);
        return true;
    }
    
    // Staking Functions
    function stake(uint256 amount) public {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        
        balanceOf[msg.sender] -= amount;
        staked[msg.sender] += amount;
        stakingTime[msg.sender] = block.timestamp;
        
        emit Staked(msg.sender, amount);
    }
    
    function unstake() public {
        uint256 stakedAmount = staked[msg.sender];
        require(stakedAmount > 0, "No staked tokens");
        
        uint256 stakingDuration = block.timestamp - stakingTime[msg.sender];
        uint256 reward = (stakedAmount * STAKING_RATE * stakingDuration) / (365 days * 100);
        
        staked[msg.sender] = 0;
        balanceOf[msg.sender] += stakedAmount + reward;
        totalSupply += reward; // Mint rewards
        
        emit Unstaked(msg.sender, stakedAmount, reward);
    }
    
    function getStakingReward(address user) public view returns (uint256) {
        if (staked[user] == 0) return 0;
        
        uint256 stakingDuration = block.timestamp - stakingTime[user];
        return (staked[user] * STAKING_RATE * stakingDuration) / (365 days * 100);
    }
    
    // Utility Functions
    function getBalance(address account) public view returns (uint256) {
        return balanceOf[account];
    }
    
    function getTotalStaked() public view returns (uint256) {
        return staked[msg.sender];
    }
}