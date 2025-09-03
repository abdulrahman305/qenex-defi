// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title QXC Launchpad - ICO/IDO Platform
 * @dev Launch new projects with QXC
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract QXCLaunchpad {
    IERC20 public qxcToken;
    
    struct Project {
        address tokenAddress;
        address creator;
        string name;
        string symbol;
        uint256 hardCap;
        uint256 softCap;
        uint256 raised;
        uint256 rate; // tokens per QXC
        uint256 startTime;
        uint256 endTime;
        bool finalized;
        bool cancelled;
        mapping(address => uint256) contributions;
    }
    
    struct Tier {
        string name;
        uint256 minStake;
        uint256 allocationMultiplier;
        uint256 guaranteedAllocation;
    }
    
    mapping(uint256 => Project) public projects;
    mapping(address => uint256) public userStakes;
    mapping(uint256 => Tier) public tiers;
    
    uint256 public projectCount;
    uint256 public platformFee = 100; // 10%
    uint256 public minStakeForLaunch = 10000 * 10**18; // 10,000 QXC
    
    event ProjectCreated(uint256 indexed projectId, string name, address creator);
    event Contributed(uint256 indexed projectId, address contributor, uint256 amount);
    event ProjectFinalized(uint256 indexed projectId, uint256 totalRaised);
    event TokensClaimed(uint256 indexed projectId, address user, uint256 amount);
    
    constructor(address _qxcToken) {
        qxcToken = IERC20(_qxcToken);
        
        // Initialize tiers
        tiers[0] = Tier("Bronze", 100 * 10**18, 1, 100 * 10**18);
        tiers[1] = Tier("Silver", 500 * 10**18, 2, 500 * 10**18);
        tiers[2] = Tier("Gold", 1000 * 10**18, 5, 1000 * 10**18);
        tiers[3] = Tier("Platinum", 5000 * 10**18, 10, 5000 * 10**18);
    }
    
    /**
     * @dev Create new IDO project
     */
    function createProject(
        address tokenAddress,
        string memory name,
        string memory symbol,
        uint256 hardCap,
        uint256 softCap,
        uint256 rate,
        uint256 duration
    ) external returns (uint256) {
        require(qxcToken.balanceOf(msg.sender) >= minStakeForLaunch, "Insufficient QXC stake");
        require(hardCap > softCap, "Invalid caps");
        require(rate > 0, "Invalid rate");
        
        projectCount++;
        Project storage project = projects[projectCount];
        project.tokenAddress = tokenAddress;
        project.creator = msg.sender;
        project.name = name;
        project.symbol = symbol;
        project.hardCap = hardCap;
        project.softCap = softCap;
        project.rate = rate;
        project.startTime = block.timestamp;
        project.endTime = block.timestamp + duration;
        
        emit ProjectCreated(projectCount, name, msg.sender);
        return projectCount;
    }
    
    /**
     * @dev Contribute to IDO
     */
    function contribute(uint256 projectId, uint256 amount) external {
        Project storage project = projects[projectId];
        require(block.timestamp >= project.startTime, "Not started");
        require(block.timestamp <= project.endTime, "Ended");
        require(!project.finalized && !project.cancelled, "Not active");
        require(project.raised + amount <= project.hardCap, "Exceeds hard cap");
        
        // Check tier allocation
        uint256 userTier = getUserTier(msg.sender);
        uint256 maxAllocation = getMaxAllocation(userTier, project.hardCap);
        require(project.contributions[msg.sender] + amount <= maxAllocation, "Exceeds allocation");
        
        require(qxcToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        
        project.contributions[msg.sender] += amount;
        project.raised += amount;
        
        emit Contributed(projectId, msg.sender, amount);
    }
    
    /**
     * @dev Finalize IDO and distribute funds
     */
    function finalizeProject(uint256 projectId) external {
        Project storage project = projects[projectId];
        require(msg.sender == project.creator, "Not creator");
        require(block.timestamp > project.endTime, "Not ended");
        require(!project.finalized && !project.cancelled, "Already finalized");
        
        if (project.raised >= project.softCap) {
            project.finalized = true;
            
            // Transfer funds to creator minus platform fee
            uint256 fee = (project.raised * platformFee) / 1000;
            uint256 creatorAmount = project.raised - fee;
            
            require(qxcToken.transfer(project.creator, creatorAmount), "Transfer failed");
            
            emit ProjectFinalized(projectId, project.raised);
        } else {
            // Refund if soft cap not reached
            project.cancelled = true;
        }
    }
    
    /**
     * @dev Claim tokens or refund
     */
    function claim(uint256 projectId) external {
        Project storage project = projects[projectId];
        uint256 contribution = project.contributions[msg.sender];
        require(contribution > 0, "No contribution");
        
        project.contributions[msg.sender] = 0;
        
        if (project.finalized) {
            // Calculate and transfer tokens
            uint256 tokenAmount = contribution * project.rate;
            IERC20(project.tokenAddress).transfer(msg.sender, tokenAmount);
            emit TokensClaimed(projectId, msg.sender, tokenAmount);
        } else if (project.cancelled) {
            // Refund QXC
            require(qxcToken.transfer(msg.sender, contribution), "Refund failed");
        }
    }
    
    /**
     * @dev Stake QXC for tier benefits
     */
    function stake(uint256 amount) external {
        require(qxcToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        userStakes[msg.sender] += amount;
    }
    
    /**
     * @dev Get user tier based on stake
     */
    function getUserTier(address user) public view returns (uint256) {
        uint256 staked = userStakes[user];
        if (staked >= tiers[3].minStake) return 3; // Platinum
        if (staked >= tiers[2].minStake) return 2; // Gold
        if (staked >= tiers[1].minStake) return 1; // Silver
        if (staked >= tiers[0].minStake) return 0; // Bronze
        return 0; // Default
    }
    
    /**
     * @dev Get maximum allocation based on tier
     */
    function getMaxAllocation(uint256 tier, uint256 hardCap) public view returns (uint256) {
        Tier memory userTier = tiers[tier];
        return userTier.guaranteedAllocation + (hardCap * userTier.allocationMultiplier / 100);
    }
}