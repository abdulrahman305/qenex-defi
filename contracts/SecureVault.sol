// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";

/**
 * @title SecureVault
 * @dev High-security vault for institutional asset management
 */
contract SecureVault is ReentrancyGuard, Ownable {
    using SafeERC20 for IERC20;
    using SafeMath for uint256;
    
    struct Deposit {
        address token;
        uint256 amount;
        uint256 timestamp;
        uint256 lockUntil;
        bool withdrawn;
    }
    
    struct WithdrawalRequest {
        address requester;
        address token;
        uint256 amount;
        uint256 timestamp;
        uint256 executeAfter;
        bool executed;
        bool cancelled;
        bytes32 approvalHash;
    }
    
    // User deposits
    mapping(address => mapping(address => uint256)) public balances;
    mapping(address => Deposit[]) public deposits;
    
    // Withdrawal requests
    mapping(bytes32 => WithdrawalRequest) public withdrawalRequests;
    bytes32[] public pendingWithdrawals;
    
    // Security settings
    uint256 public constant WITHDRAWAL_DELAY = 24 hours;
    uint256 public constant MAX_WITHDRAWAL_PERCENTAGE = 25; // 25% max per withdrawal
    uint256 public emergencyWithdrawalFee = 500; // 5% in basis points
    
    // Multi-signature settings
    mapping(address => bool) public signers;
    uint256 public requiredSignatures = 2;
    mapping(bytes32 => mapping(address => bool)) public approvals;
    
    // Vault statistics
    uint256 public totalValueLocked;
    mapping(address => uint256) public tokenBalances;
    
    // Events
    event Deposited(address indexed user, address indexed token, uint256 amount, uint256 lockUntil);
    event WithdrawalRequested(bytes32 indexed requestId, address indexed user, address token, uint256 amount);
    event WithdrawalApproved(bytes32 indexed requestId, address indexed signer);
    event WithdrawalExecuted(bytes32 indexed requestId, address indexed user, uint256 amount);
    event WithdrawalCancelled(bytes32 indexed requestId);
    event SignerAdded(address indexed signer);
    event SignerRemoved(address indexed signer);
    event EmergencyWithdrawal(address indexed user, address indexed token, uint256 amount, uint256 fee);
    
    modifier onlySigner() {
        require(signers[msg.sender], "Not a signer");
        _;
    }
    
    constructor() {
        signers[msg.sender] = true;
    }
    
    /**
     * @dev Deposit tokens into the vault
     * @param token Token address (use address(0) for ETH)
     * @param amount Amount to deposit
     * @param lockDays Number of days to lock the deposit
     */
    function deposit(
        address token,
        uint256 amount,
        uint256 lockDays
    ) external payable nonReentrant {
        require(amount > 0, "Amount must be greater than 0");
        require(lockDays <= 365, "Lock period too long");
        
        uint256 lockUntil = block.timestamp + (lockDays * 1 days);
        
        if (token == address(0)) {
            // ETH deposit
            require(msg.value == amount, "Incorrect ETH amount");
            balances[msg.sender][address(0)] = balances[msg.sender][address(0)].add(amount);
            tokenBalances[address(0)] = tokenBalances[address(0)].add(amount);
        } else {
            // ERC20 deposit
            IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
            balances[msg.sender][token] = balances[msg.sender][token].add(amount);
            tokenBalances[token] = tokenBalances[token].add(amount);
        }
        
        deposits[msg.sender].push(Deposit({
            token: token,
            amount: amount,
            timestamp: block.timestamp,
            lockUntil: lockUntil,
            withdrawn: false
        }));
        
        totalValueLocked = totalValueLocked.add(amount);
        
        emit Deposited(msg.sender, token, amount, lockUntil);
    }
    
    /**
     * @dev Request withdrawal (time-delayed for security)
     * @param token Token address
     * @param amount Amount to withdraw
     */
    function requestWithdrawal(
        address token,
        uint256 amount
    ) external nonReentrant returns (bytes32) {
        require(amount > 0, "Amount must be greater than 0");
        require(balances[msg.sender][token] >= amount, "Insufficient balance");
        
        // Check withdrawal limit (25% of balance)
        uint256 maxWithdrawal = balances[msg.sender][token].mul(MAX_WITHDRAWAL_PERCENTAGE).div(100);
        require(amount <= maxWithdrawal, "Exceeds maximum withdrawal limit");
        
        // Check if deposits are unlocked
        uint256 unlockedBalance = getUnlockedBalance(msg.sender, token);
        require(unlockedBalance >= amount, "Insufficient unlocked balance");
        
        bytes32 requestId = keccak256(
            abi.encodePacked(msg.sender, token, amount, block.timestamp)
        );
        
        withdrawalRequests[requestId] = WithdrawalRequest({
            requester: msg.sender,
            token: token,
            amount: amount,
            timestamp: block.timestamp,
            executeAfter: block.timestamp + WITHDRAWAL_DELAY,
            executed: false,
            cancelled: false,
            approvalHash: bytes32(0)
        });
        
        pendingWithdrawals.push(requestId);
        
        emit WithdrawalRequested(requestId, msg.sender, token, amount);
        
        return requestId;
    }
    
    /**
     * @dev Approve withdrawal request (multi-sig)
     * @param requestId Withdrawal request ID
     */
    function approveWithdrawal(bytes32 requestId) external onlySigner {
        WithdrawalRequest storage request = withdrawalRequests[requestId];
        require(request.amount > 0, "Request not found");
        require(!request.executed, "Already executed");
        require(!request.cancelled, "Request cancelled");
        require(!approvals[requestId][msg.sender], "Already approved");
        
        approvals[requestId][msg.sender] = true;
        
        emit WithdrawalApproved(requestId, msg.sender);
        
        // Check if enough approvals
        uint256 approvalCount = 0;
        for (uint256 i = 0; i < getSignerCount(); i++) {
            if (approvals[requestId][getSignerAt(i)]) {
                approvalCount++;
            }
        }
        
        if (approvalCount >= requiredSignatures) {
            request.approvalHash = keccak256(abi.encodePacked(requestId, approvalCount));
        }
    }
    
    /**
     * @dev Execute approved withdrawal after delay
     * @param requestId Withdrawal request ID
     */
    function executeWithdrawal(bytes32 requestId) external nonReentrant {
        WithdrawalRequest storage request = withdrawalRequests[requestId];
        require(request.amount > 0, "Request not found");
        require(request.requester == msg.sender, "Not the requester");
        require(!request.executed, "Already executed");
        require(!request.cancelled, "Request cancelled");
        require(block.timestamp >= request.executeAfter, "Withdrawal delay not met");
        require(request.approvalHash != bytes32(0), "Not enough approvals");
        
        request.executed = true;
        
        // Update balances
        balances[msg.sender][request.token] = balances[msg.sender][request.token].sub(request.amount);
        tokenBalances[request.token] = tokenBalances[request.token].sub(request.amount);
        totalValueLocked = totalValueLocked.sub(request.amount);
        
        // Transfer funds
        if (request.token == address(0)) {
            // Transfer ETH
            (bool success, ) = msg.sender.call{value: request.amount}("");
            require(success, "ETH transfer failed");
        } else {
            // Transfer ERC20
            IERC20(request.token).safeTransfer(msg.sender, request.amount);
        }
        
        emit WithdrawalExecuted(requestId, msg.sender, request.amount);
    }
    
    /**
     * @dev Cancel withdrawal request
     * @param requestId Withdrawal request ID
     */
    function cancelWithdrawal(bytes32 requestId) external {
        WithdrawalRequest storage request = withdrawalRequests[requestId];
        require(request.amount > 0, "Request not found");
        require(request.requester == msg.sender, "Not the requester");
        require(!request.executed, "Already executed");
        require(!request.cancelled, "Already cancelled");
        
        request.cancelled = true;
        
        emit WithdrawalCancelled(requestId);
    }
    
    /**
     * @dev Emergency withdrawal with fee
     * @param token Token address
     */
    function emergencyWithdraw(address token) external nonReentrant {
        uint256 balance = balances[msg.sender][token];
        require(balance > 0, "No balance");
        
        uint256 fee = balance.mul(emergencyWithdrawalFee).div(10000);
        uint256 withdrawAmount = balance.sub(fee);
        
        balances[msg.sender][token] = 0;
        tokenBalances[token] = tokenBalances[token].sub(balance);
        totalValueLocked = totalValueLocked.sub(balance);
        
        // Mark all deposits as withdrawn
        Deposit[] storage userDeposits = deposits[msg.sender];
        for (uint256 i = 0; i < userDeposits.length; i++) {
            if (userDeposits[i].token == token && !userDeposits[i].withdrawn) {
                userDeposits[i].withdrawn = true;
            }
        }
        
        // Transfer funds minus fee
        if (token == address(0)) {
            (bool success, ) = msg.sender.call{value: withdrawAmount}("");
            require(success, "ETH transfer failed");
        } else {
            IERC20(token).safeTransfer(msg.sender, withdrawAmount);
        }
        
        emit EmergencyWithdrawal(msg.sender, token, withdrawAmount, fee);
    }
    
    /**
     * @dev Get unlocked balance for user
     * @param user User address
     * @param token Token address
     */
    function getUnlockedBalance(address user, address token) public view returns (uint256) {
        uint256 unlocked = 0;
        Deposit[] memory userDeposits = deposits[user];
        
        for (uint256 i = 0; i < userDeposits.length; i++) {
            if (userDeposits[i].token == token 
                && !userDeposits[i].withdrawn 
                && block.timestamp >= userDeposits[i].lockUntil) {
                unlocked = unlocked.add(userDeposits[i].amount);
            }
        }
        
        return unlocked;
    }
    
    /**
     * @dev Add signer for multi-sig
     * @param signer Signer address
     */
    function addSigner(address signer) external onlyOwner {
        require(signer != address(0), "Invalid address");
        require(!signers[signer], "Already a signer");
        
        signers[signer] = true;
        
        emit SignerAdded(signer);
    }
    
    /**
     * @dev Remove signer
     * @param signer Signer address
     */
    function removeSigner(address signer) external onlyOwner {
        require(signers[signer], "Not a signer");
        
        signers[signer] = false;
        
        emit SignerRemoved(signer);
    }
    
    /**
     * @dev Update required signatures
     * @param required Number of required signatures
     */
    function updateRequiredSignatures(uint256 required) external onlyOwner {
        require(required > 0 && required <= getSignerCount(), "Invalid requirement");
        requiredSignatures = required;
    }
    
    /**
     * @dev Update emergency withdrawal fee
     * @param fee Fee in basis points (100 = 1%)
     */
    function updateEmergencyFee(uint256 fee) external onlyOwner {
        require(fee <= 1000, "Fee too high"); // Max 10%
        emergencyWithdrawalFee = fee;
    }
    
    /**
     * @dev Get signer count
     */
    function getSignerCount() private view returns (uint256) {
        // Simplified - in production, maintain a list
        return 3;
    }
    
    /**
     * @dev Get signer at index
     */
    function getSignerAt(uint256 index) private view returns (address) {
        // Simplified - in production, maintain a list
        if (index == 0) return owner();
        return address(0);
    }
    
    /**
     * @dev Get user's deposit history
     * @param user User address
     */
    function getUserDeposits(address user) external view returns (Deposit[] memory) {
        return deposits[user];
    }
    
    /**
     * @dev Get pending withdrawals count
     */
    function getPendingWithdrawalsCount() external view returns (uint256) {
        uint256 count = 0;
        for (uint256 i = 0; i < pendingWithdrawals.length; i++) {
            WithdrawalRequest memory request = withdrawalRequests[pendingWithdrawals[i]];
            if (!request.executed && !request.cancelled) {
                count++;
            }
        }
        return count;
    }
    
    /**
     * @dev Get vault statistics
     */
    function getVaultStats() external view returns (
        uint256 tvl,
        uint256 ethBalance,
        uint256 withdrawalsPending
    ) {
        return (
            totalValueLocked,
            tokenBalances[address(0)],
            this.getPendingWithdrawalsCount()
        );
    }
    
    receive() external payable {
        // Accept ETH deposits
    }
}