// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title QXC Governance
 * @notice Decentralized governance system for protocol decisions
 * @dev Implements quadratic voting and time-locked execution
 */

interface IERC20 {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
}

contract QXCGovernance {
    // Core state
    IERC20 public immutable qxcToken;
    uint256 public proposalCount;
    mapping(uint256 => Proposal) public proposals;
    mapping(address => mapping(uint256 => VoteInfo)) public votes;
    mapping(address => uint256) public votingPower;
    mapping(address => uint256) public delegatedTo;
    
    // Proposal structure
    struct Proposal {
        address proposer;
        string title;
        string description;
        ProposalType proposalType;
        address target;
        uint256 value;
        bytes callData;
        uint256 startTime;
        uint256 endTime;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        bool executed;
        bool canceled;
        uint256 executionTime;
    }
    
    struct VoteInfo {
        bool hasVoted;
        uint8 support; // 0 = Against, 1 = For, 2 = Abstain
        uint256 votes;
    }
    
    enum ProposalType {
        ParameterChange,
        FundTransfer,
        ContractUpgrade,
        Emergency
    }
    
    // Governance parameters
    uint256 public constant PROPOSAL_THRESHOLD = 1000 * 10**18; // 1000 QXC to propose
    uint256 public constant QUORUM = 4; // 4% of total supply
    uint256 public constant VOTING_PERIOD = 3 days;
    uint256 public constant EXECUTION_DELAY = 2 days;
    uint256 public constant EMERGENCY_DELAY = 6 hours;
    
    // Access control
    address public owner;
    mapping(address => bool) public guardians;
    
    // Events
    event ProposalCreated(uint256 indexed proposalId, address indexed proposer, string title);
    event VoteCast(address indexed voter, uint256 indexed proposalId, uint8 support, uint256 votes);
    event ProposalExecuted(uint256 indexed proposalId);
    event ProposalCanceled(uint256 indexed proposalId);
    event DelegateChanged(address indexed delegator, address indexed delegate);
    event GuardianAdded(address indexed guardian);
    event GuardianRemoved(address indexed guardian);
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    modifier onlyGuardian() {
        require(guardians[msg.sender], "Not guardian");
        _;
    }
    
    constructor(address _qxcToken) {
        require(_qxcToken != address(0), "Invalid token");
        qxcToken = IERC20(_qxcToken);
        owner = msg.sender;
        guardians[msg.sender] = true;
    }
    
    /**
     * @notice Create a new proposal
     * @param title Proposal title
     * @param description Detailed description
     * @param proposalType Type of proposal
     * @param target Target contract address
     * @param value ETH value to send
     * @param callData Encoded function call
     */
    function propose(
        string memory title,
        string memory description,
        ProposalType proposalType,
        address target,
        uint256 value,
        bytes memory callData
    ) external returns (uint256 proposalId) {
        require(
            qxcToken.balanceOf(msg.sender) >= PROPOSAL_THRESHOLD,
            "Insufficient QXC balance"
        );
        require(bytes(title).length > 0, "Empty title");
        require(bytes(description).length > 0, "Empty description");
        
        proposalId = ++proposalCount;
        
        proposals[proposalId] = Proposal({
            proposer: msg.sender,
            title: title,
            description: description,
            proposalType: proposalType,
            target: target,
            value: value,
            callData: callData,
            startTime: block.timestamp,
            endTime: block.timestamp + VOTING_PERIOD,
            forVotes: 0,
            againstVotes: 0,
            abstainVotes: 0,
            executed: false,
            canceled: false,
            executionTime: 0
        });
        
        emit ProposalCreated(proposalId, msg.sender, title);
    }
    
    /**
     * @notice Cast vote on a proposal
     * @param proposalId Proposal ID
     * @param support Vote type (0 = Against, 1 = For, 2 = Abstain)
     */
    function castVote(uint256 proposalId, uint8 support) external {
        Proposal storage proposal = proposals[proposalId];
        require(proposal.proposer != address(0), "Invalid proposal");
        require(block.timestamp >= proposal.startTime, "Voting not started");
        require(block.timestamp < proposal.endTime, "Voting ended");
        require(!votes[msg.sender][proposalId].hasVoted, "Already voted");
        require(support <= 2, "Invalid vote type");
        
        uint256 votingWeight = getVotingPower(msg.sender);
        require(votingWeight > 0, "No voting power");
        
        // Use quadratic voting for fairness
        uint256 voteWeight = sqrt(votingWeight);
        
        votes[msg.sender][proposalId] = VoteInfo({
            hasVoted: true,
            support: support,
            votes: voteWeight
        });
        
        if (support == 0) {
            proposal.againstVotes += voteWeight;
        } else if (support == 1) {
            proposal.forVotes += voteWeight;
        } else {
            proposal.abstainVotes += voteWeight;
        }
        
        emit VoteCast(msg.sender, proposalId, support, voteWeight);
    }
    
    /**
     * @notice Execute a passed proposal
     * @param proposalId Proposal ID
     */
    function execute(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];
        require(!proposal.executed, "Already executed");
        require(!proposal.canceled, "Proposal canceled");
        require(block.timestamp >= proposal.endTime, "Voting not ended");
        
        // Check if proposal passed
        require(proposal.forVotes > proposal.againstVotes, "Proposal failed");
        
        // Check quorum
        uint256 totalVotes = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;
        uint256 totalSupply = qxcToken.balanceOf(address(this));
        require(totalVotes * 100 >= totalSupply * QUORUM, "Quorum not reached");
        
        // Check execution delay
        uint256 delay = proposal.proposalType == ProposalType.Emergency ? 
            EMERGENCY_DELAY : EXECUTION_DELAY;
        
        if (proposal.executionTime == 0) {
            proposal.executionTime = block.timestamp + delay;
            return;
        }
        
        require(block.timestamp >= proposal.executionTime, "Execution delay not met");
        
        proposal.executed = true;
        
        // Execute proposal
        if (proposal.target != address(0) && proposal.callData.length > 0) {
            (bool success,) = proposal.target.call{value: proposal.value}(proposal.callData);
            require(success, "Execution failed");
        }
        
        emit ProposalExecuted(proposalId);
    }
    
    /**
     * @notice Cancel a proposal (guardian only)
     * @param proposalId Proposal ID
     */
    function cancelProposal(uint256 proposalId) external onlyGuardian {
        Proposal storage proposal = proposals[proposalId];
        require(!proposal.executed, "Already executed");
        require(!proposal.canceled, "Already canceled");
        
        proposal.canceled = true;
        emit ProposalCanceled(proposalId);
    }
    
    /**
     * @notice Delegate voting power
     * @param delegate Address to delegate to
     */
    function delegateVotes(address delegate) external {
        require(delegate != address(0), "Invalid delegate");
        require(delegate != msg.sender, "Cannot delegate to self");
        
        address currentDelegate = address(uint160(delegatedTo[msg.sender]));
        if (currentDelegate != address(0)) {
            votingPower[currentDelegate] -= qxcToken.balanceOf(msg.sender);
        }
        
        delegatedTo[msg.sender] = uint256(uint160(delegate));
        votingPower[delegate] += qxcToken.balanceOf(msg.sender);
        
        emit DelegateChanged(msg.sender, delegate);
    }
    
    /**
     * @notice Get voting power of an address
     * @param account Address to check
     */
    function getVotingPower(address account) public view returns (uint256) {
        uint256 delegated = votingPower[account];
        uint256 balance = qxcToken.balanceOf(account);
        
        // If user has delegated their votes, they can't vote
        if (delegatedTo[account] != 0) {
            return delegated;
        }
        
        return balance + delegated;
    }
    
    /**
     * @notice Check if proposal passed
     * @param proposalId Proposal ID
     */
    function proposalPassed(uint256 proposalId) external view returns (bool) {
        Proposal memory proposal = proposals[proposalId];
        
        if (proposal.executed || proposal.canceled) return false;
        if (block.timestamp < proposal.endTime) return false;
        if (proposal.forVotes <= proposal.againstVotes) return false;
        
        uint256 totalVotes = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;
        uint256 totalSupply = qxcToken.balanceOf(address(this));
        
        return totalVotes * 100 >= totalSupply * QUORUM;
    }
    
    /**
     * @notice Add guardian
     * @param guardian Address to add
     */
    function addGuardian(address guardian) external onlyOwner {
        require(guardian != address(0), "Invalid guardian");
        require(!guardians[guardian], "Already guardian");
        guardians[guardian] = true;
        emit GuardianAdded(guardian);
    }
    
    /**
     * @notice Remove guardian
     * @param guardian Address to remove
     */
    function removeGuardian(address guardian) external onlyOwner {
        require(guardians[guardian], "Not guardian");
        guardians[guardian] = false;
        emit GuardianRemoved(guardian);
    }
    
    /**
     * @notice Get proposal details
     * @param proposalId Proposal ID
     */
    function getProposal(uint256 proposalId) external view returns (
        address proposer,
        string memory title,
        uint256 forVotes,
        uint256 againstVotes,
        uint256 endTime,
        bool executed,
        bool canceled
    ) {
        Proposal memory proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.title,
            proposal.forVotes,
            proposal.againstVotes,
            proposal.endTime,
            proposal.executed,
            proposal.canceled
        );
    }
    
    // Helper function for quadratic voting
    function sqrt(uint256 y) internal pure returns (uint256 z) {
        if (y > 3) {
            z = y;
            uint256 x = y / 2 + 1;
            while (x < z) {
                z = x;
                x = (y / x + x) / 2;
            }
        } else if (y != 0) {
            z = 1;
        }
    }
    
    // Receive ETH for treasury
    receive() external payable {}
}