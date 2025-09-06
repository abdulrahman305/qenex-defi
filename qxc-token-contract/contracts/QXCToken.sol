// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title QENEX Coin (QXC)
 * @dev ERC-20 Token with AI Mining Rewards
 * @author QENEX OS
 */
contract QXCToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    uint256 public totalSupply;
    string public constant name = "QENEX Coin";
    string public constant symbol = "QXC";
    uint8 public constant decimals = 18;
    
    address public owner;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event MiningReward(address indexed miner, uint256 reward, string improvement);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        totalSupply = 1525300000000000000000; // 1525.30 QXC initial supply
        balanceOf[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
    }
    
    function transfer(address to, uint256 amount) public returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        require(to != address(0), "Cannot transfer to zero address");
        
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }
    
    function approve(address spender, uint256 amount) public returns (bool) {
        require(spender != address(0), "Cannot approve zero address");
        
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        require(to != address(0), "Cannot transfer to zero address");
        
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        allowance[from][msg.sender] -= amount;
        
        emit Transfer(from, to, amount);
        return true;
    }
    
    /**
     * @dev Mint new tokens as mining rewards for AI improvements
     * @param miner Address to receive the reward
     * @param reward Amount of QXC to mint
     * @param improvement Description of the AI improvement
     */
    function mintReward(address miner, uint256 reward, string memory improvement) public onlyOwner {
        require(miner != address(0), "Cannot mint to zero address");
        require(reward > 0, "Reward must be positive");
        
        totalSupply += reward;
        balanceOf[miner] += reward;
        
        emit Transfer(address(0), miner, reward);
        emit MiningReward(miner, reward, improvement);
    }
    
    /**
     * @dev Returns the amount of tokens owned by an account
     */
    function getBalance(address account) public view returns (uint256) {
        return balanceOf[account];
    }
    
    /**
     * @dev Returns remaining tokens that spender can withdraw
     */
    function getAllowance(address _owner, address spender) public view returns (uint256) {
        return allowance[_owner][spender];
    }
}