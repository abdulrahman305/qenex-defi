// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title QXC Token - FIXED VERSION
 * @notice Secure ERC-20 token with proper safety mechanisms
 * @dev All critical vulnerabilities have been addressed
 */
contract QXCToken {
    // Token metadata
    string public constant name = "QENEX Coin";
    string public constant symbol = "QXC";
    uint8 public constant decimals = 18;
    
    // Supply management with proper limits
    uint256 public totalSupply;
    uint256 public constant MAX_SUPPLY = 21_000_000 * 10**18; // 21 million max
    uint256 public constant INITIAL_SUPPLY = 1525.30 * 10**18; // 1525.30 initial
    
    // Ownership and roles
    address public owner;
    mapping(address => bool) public minters;
    bool public mintingEnabled = true;
    
    // Balances and allowances
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    // Security features
    mapping(address => bool) public blacklisted;
    bool public paused = false;
    
    // Events
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event MinterAdded(address indexed minter);
    event MinterRemoved(address indexed minter);
    event Blacklisted(address indexed account);
    event Unblacklisted(address indexed account);
    event Paused();
    event Unpaused();
    event MintingDisabled();
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    modifier onlyMinter() {
        require(minters[msg.sender], "Not minter");
        _;
    }
    
    modifier whenNotPaused() {
        require(!paused, "Contract paused");
        _;
    }
    
    modifier notBlacklisted(address account) {
        require(!blacklisted[account], "Account blacklisted");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        minters[msg.sender] = true;
        totalSupply = INITIAL_SUPPLY;
        balanceOf[msg.sender] = INITIAL_SUPPLY;
        emit Transfer(address(0), msg.sender, INITIAL_SUPPLY);
    }
    
    // Core ERC-20 functions with security checks
    function transfer(address to, uint256 amount) 
        public 
        whenNotPaused 
        notBlacklisted(msg.sender) 
        notBlacklisted(to) 
        returns (bool) 
    {
        require(to != address(0), "Invalid recipient");
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        
        unchecked {
            balanceOf[msg.sender] -= amount;
            balanceOf[to] += amount;
        }
        
        emit Transfer(msg.sender, to, amount);
        return true;
    }
    
    function approve(address spender, uint256 amount) 
        public 
        whenNotPaused 
        returns (bool) 
    {
        require(spender != address(0), "Invalid spender");
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) 
        public 
        whenNotPaused 
        notBlacklisted(from) 
        notBlacklisted(to) 
        returns (bool) 
    {
        require(to != address(0), "Invalid recipient");
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        
        unchecked {
            balanceOf[from] -= amount;
            balanceOf[to] += amount;
            allowance[from][msg.sender] -= amount;
        }
        
        emit Transfer(from, to, amount);
        return true;
    }
    
    // Minting with proper controls
    function mint(address to, uint256 amount) 
        public 
        onlyMinter 
        whenNotPaused 
        notBlacklisted(to) 
    {
        require(mintingEnabled, "Minting disabled");
        require(to != address(0), "Invalid recipient");
        require(totalSupply + amount <= MAX_SUPPLY, "Exceeds max supply");
        
        totalSupply += amount;
        balanceOf[to] += amount;
        
        emit Transfer(address(0), to, amount);
    }
    
    // Burning mechanism
    function burn(uint256 amount) public whenNotPaused {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        
        unchecked {
            balanceOf[msg.sender] -= amount;
            totalSupply -= amount;
        }
        
        emit Transfer(msg.sender, address(0), amount);
    }
    
    // Admin functions with proper access control
    function addMinter(address minter) public onlyOwner {
        require(minter != address(0), "Invalid minter");
        require(!minters[minter], "Already minter");
        minters[minter] = true;
        emit MinterAdded(minter);
    }
    
    function removeMinter(address minter) public onlyOwner {
        require(minters[minter], "Not minter");
        minters[minter] = false;
        emit MinterRemoved(minter);
    }
    
    function blacklist(address account) public onlyOwner {
        require(account != owner, "Cannot blacklist owner");
        require(!blacklisted[account], "Already blacklisted");
        blacklisted[account] = true;
        emit Blacklisted(account);
    }
    
    function unblacklist(address account) public onlyOwner {
        require(blacklisted[account], "Not blacklisted");
        blacklisted[account] = false;
        emit Unblacklisted(account);
    }
    
    function pause() public onlyOwner {
        require(!paused, "Already paused");
        paused = true;
        emit Paused();
    }
    
    function unpause() public onlyOwner {
        require(paused, "Not paused");
        paused = false;
        emit Unpaused();
    }
    
    function disableMinting() public onlyOwner {
        require(mintingEnabled, "Already disabled");
        mintingEnabled = false;
        emit MintingDisabled();
    }
    
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Invalid owner");
        owner = newOwner;
    }
}