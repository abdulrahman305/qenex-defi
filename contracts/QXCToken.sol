// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Snapshot.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title QXC Token
 * @dev QENEX native token with advanced DeFi capabilities
 */
contract QXCToken is 
    ERC20, 
    ERC20Burnable, 
    ERC20Snapshot, 
    AccessControl, 
    Pausable, 
    ERC20Permit, 
    ERC20Votes,
    ReentrancyGuard 
{
    bytes32 public constant SNAPSHOT_ROLE = keccak256("SNAPSHOT_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant GOVERNOR_ROLE = keccak256("GOVERNOR_ROLE");

    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18; // 1 billion tokens
    uint256 public constant INITIAL_SUPPLY = 100_000_000 * 10**18; // 100 million initial
    
    // Tokenomics
    uint256 public constant LIQUIDITY_ALLOCATION = 20; // 20%
    uint256 public constant STAKING_REWARDS_ALLOCATION = 30; // 30%
    uint256 public constant DEVELOPMENT_ALLOCATION = 15; // 15%
    uint256 public constant COMMUNITY_ALLOCATION = 35; // 35%
    
    // Fee structure
    uint256 public transferFeeRate = 10; // 0.1% = 10 basis points
    uint256 public constant MAX_FEE_RATE = 100; // 1% maximum
    address public feeCollector;
    
    // Staking
    mapping(address => uint256) public stakedBalance;
    mapping(address => uint256) public stakingTimestamp;
    uint256 public totalStaked;
    uint256 public stakingAPY = 500; // 5% APY = 500 basis points
    
    // Governance
    mapping(uint256 => Proposal) public proposals;
    uint256 public proposalCount;
    uint256 public constant PROPOSAL_THRESHOLD = 1_000_000 * 10**18; // 1M tokens to propose
    uint256 public constant VOTING_PERIOD = 3 days;
    
    struct Proposal {
        uint256 id;
        address proposer;
        string description;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 startTime;
        uint256 endTime;
        bool executed;
        mapping(address => bool) hasVoted;
    }
    
    // Events
    event TokensStaked(address indexed user, uint256 amount);
    event TokensUnstaked(address indexed user, uint256 amount);
    event RewardsClaimed(address indexed user, uint256 amount);
    event ProposalCreated(uint256 indexed proposalId, address proposer, string description);
    event VoteCast(uint256 indexed proposalId, address voter, bool support, uint256 votes);
    event ProposalExecuted(uint256 indexed proposalId);
    event FeeCollected(address from, address to, uint256 amount);
    
    constructor() 
        ERC20("QENEX Token", "QXC") 
        ERC20Permit("QENEX Token") 
    {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(SNAPSHOT_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(GOVERNOR_ROLE, msg.sender);
        
        feeCollector = msg.sender;
        
        // Mint initial supply
        _mint(msg.sender, INITIAL_SUPPLY);
    }
    
    /**
     * @dev Pause token transfers
     */
    function pause() public onlyRole(PAUSER_ROLE) {
        _pause();
    }
    
    /**
     * @dev Unpause token transfers
     */
    function unpause() public onlyRole(PAUSER_ROLE) {
        _unpause();
    }
    
    /**
     * @dev Create a snapshot for governance
     */
    function snapshot() public onlyRole(SNAPSHOT_ROLE) returns (uint256) {
        return _snapshot();
    }
    
    /**
     * @dev Mint new tokens (up to max supply)
     */
    function mint(address to, uint256 amount) public onlyRole(MINTER_ROLE) {
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(to, amount);
    }
    
    /**
     * @dev Stake tokens for rewards
     */
    function stake(uint256 amount) external nonReentrant whenNotPaused {
        require(amount > 0, "Cannot stake 0");
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");
        
        // Claim pending rewards first
        if (stakedBalance[msg.sender] > 0) {
            _claimRewards(msg.sender);
        }
        
        _transfer(msg.sender, address(this), amount);
        stakedBalance[msg.sender] += amount;
        stakingTimestamp[msg.sender] = block.timestamp;
        totalStaked += amount;
        
        emit TokensStaked(msg.sender, amount);
    }
    
    /**
     * @dev Unstake tokens
     */
    function unstake(uint256 amount) external nonReentrant {
        require(amount > 0, "Cannot unstake 0");
        require(stakedBalance[msg.sender] >= amount, "Insufficient staked balance");
        
        // Claim rewards
        _claimRewards(msg.sender);
        
        stakedBalance[msg.sender] -= amount;
        totalStaked -= amount;
        
        _transfer(address(this), msg.sender, amount);
        
        emit TokensUnstaked(msg.sender, amount);
    }
    
    /**
     * @dev Calculate staking rewards
     */
    function calculateRewards(address account) public view returns (uint256) {
        if (stakedBalance[account] == 0) {
            return 0;
        }
        
        uint256 stakingDuration = block.timestamp - stakingTimestamp[account];
        uint256 rewards = (stakedBalance[account] * stakingAPY * stakingDuration) / (365 days * 10000);
        
        return rewards;
    }
    
    /**
     * @dev Claim staking rewards
     */
    function claimRewards() external nonReentrant {
        _claimRewards(msg.sender);
    }
    
    function _claimRewards(address account) private {
        uint256 rewards = calculateRewards(account);
        if (rewards > 0) {
            stakingTimestamp[account] = block.timestamp;
            _mint(account, rewards);
            emit RewardsClaimed(account, rewards);
        }
    }
    
    /**
     * @dev Create a governance proposal
     */
    function createProposal(string memory description) external returns (uint256) {
        require(getVotes(msg.sender) >= PROPOSAL_THRESHOLD, "Insufficient voting power");
        
        uint256 proposalId = proposalCount++;
        Proposal storage proposal = proposals[proposalId];
        proposal.id = proposalId;
        proposal.proposer = msg.sender;
        proposal.description = description;
        proposal.startTime = block.timestamp;
        proposal.endTime = block.timestamp + VOTING_PERIOD;
        
        emit ProposalCreated(proposalId, msg.sender, description);
        
        return proposalId;
    }
    
    /**
     * @dev Vote on a proposal
     */
    function vote(uint256 proposalId, bool support) external {
        Proposal storage proposal = proposals[proposalId];
        require(block.timestamp >= proposal.startTime, "Voting not started");
        require(block.timestamp <= proposal.endTime, "Voting ended");
        require(!proposal.hasVoted[msg.sender], "Already voted");
        
        uint256 votes = getVotes(msg.sender);
        require(votes > 0, "No voting power");
        
        proposal.hasVoted[msg.sender] = true;
        
        if (support) {
            proposal.forVotes += votes;
        } else {
            proposal.againstVotes += votes;
        }
        
        emit VoteCast(proposalId, msg.sender, support, votes);
    }
    
    /**
     * @dev Execute a successful proposal
     */
    function executeProposal(uint256 proposalId) external onlyRole(GOVERNOR_ROLE) {
        Proposal storage proposal = proposals[proposalId];
        require(block.timestamp > proposal.endTime, "Voting not ended");
        require(!proposal.executed, "Already executed");
        require(proposal.forVotes > proposal.againstVotes, "Proposal failed");
        
        proposal.executed = true;
        
        // Execute proposal logic here
        // This is a placeholder for actual governance actions
        
        emit ProposalExecuted(proposalId);
    }
    
    /**
     * @dev Set transfer fee rate
     */
    function setTransferFeeRate(uint256 _feeRate) external onlyRole(GOVERNOR_ROLE) {
        require(_feeRate <= MAX_FEE_RATE, "Fee too high");
        transferFeeRate = _feeRate;
    }
    
    /**
     * @dev Set fee collector address
     */
    function setFeeCollector(address _feeCollector) external onlyRole(GOVERNOR_ROLE) {
        require(_feeCollector != address(0), "Invalid address");
        feeCollector = _feeCollector;
    }
    
    /**
     * @dev Set staking APY
     */
    function setStakingAPY(uint256 _apy) external onlyRole(GOVERNOR_ROLE) {
        require(_apy <= 2000, "APY too high"); // Max 20%
        stakingAPY = _apy;
    }
    
    /**
     * @dev Override transfer to include fees
     */
    function _transfer(
        address from,
        address to,
        uint256 amount
    ) internal override whenNotPaused {
        // Skip fees for certain transfers
        if (from == address(this) || to == address(this) || 
            hasRole(GOVERNOR_ROLE, from) || hasRole(GOVERNOR_ROLE, to)) {
            super._transfer(from, to, amount);
            return;
        }
        
        uint256 fee = (amount * transferFeeRate) / 10000;
        uint256 netAmount = amount - fee;
        
        if (fee > 0) {
            super._transfer(from, feeCollector, fee);
            emit FeeCollected(from, to, fee);
        }
        
        super._transfer(from, to, netAmount);
    }
    
    // Required overrides
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Snapshot) {
        super._beforeTokenTransfer(from, to, amount);
    }
    
    function _afterTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._afterTokenTransfer(from, to, amount);
    }
    
    function _mint(address to, uint256 amount) internal override(ERC20, ERC20Votes) {
        super._mint(to, amount);
    }
    
    function _burn(address account, uint256 amount) internal override(ERC20, ERC20Votes) {
        super._burn(account, amount);
    }
}