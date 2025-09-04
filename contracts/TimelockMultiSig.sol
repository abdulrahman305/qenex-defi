// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Timelock Multi-Signature Wallet
 * @notice Production-ready multi-sig with timelock
 * @dev 2-of-3 signatures with 48-hour timelock for critical operations
 */
contract TimelockMultiSig {
    // Constants
    uint256 public constant TIMELOCK_DURATION = 48 hours;
    uint256 public constant EMERGENCY_TIMELOCK = 24 hours;
    uint256 public constant MIN_SIGNERS = 3;
    uint256 public constant REQUIRED_SIGNATURES = 2;
    
    // Events
    event TransactionQueued(uint256 indexed txId, address indexed target, uint256 eta);
    event TransactionExecuted(uint256 indexed txId);
    event TransactionCancelled(uint256 indexed txId);
    event SignerAdded(address indexed signer);
    event SignerRemoved(address indexed signer);
    event EmergencyUsed(uint256 indexed txId);
    
    // State
    mapping(address => bool) public isSigner;
    address[] public signers;
    
    struct Transaction {
        address target;
        bytes data;
        uint256 value;
        uint256 eta; // Estimated time of arrival (execution time)
        bool executed;
        bool cancelled;
        uint256 signatures;
        mapping(address => bool) signed;
        bool isEmergency;
    }
    
    mapping(uint256 => Transaction) public transactions;
    uint256 public transactionCount;
    
    // Circuit breaker
    bool public emergencyStop = false;
    uint256 public lastEmergencyTime;
    
    modifier onlySigner() {
        require(isSigner[msg.sender], "Not a signer");
        _;
    }
    
    modifier notEmergency() {
        require(!emergencyStop, "Emergency stop active");
        _;
    }
    
    constructor(address[] memory _signers) {
        require(_signers.length >= MIN_SIGNERS, "Not enough signers");
        
        for (uint256 i = 0; i < _signers.length; i++) {
            require(_signers[i] != address(0), "Invalid signer");
            require(!isSigner[_signers[i]], "Duplicate signer");
            
            isSigner[_signers[i]] = true;
            signers.push(_signers[i]);
        }
    }
    
    function queueTransaction(
        address target,
        bytes memory data,
        uint256 value,
        bool isEmergency
    ) 
        external 
        onlySigner 
        notEmergency 
        returns (uint256) 
    {
        uint256 txId = transactionCount++;
        Transaction storage tx = transactions[txId];
        
        tx.target = target;
        tx.data = data;
        tx.value = value;
        tx.isEmergency = isEmergency;
        tx.signatures = 1;
        tx.signed[msg.sender] = true;
        
        // Set timelock
        uint256 delay = isEmergency ? EMERGENCY_TIMELOCK : TIMELOCK_DURATION;
        tx.eta = block.timestamp + delay;
        
        emit TransactionQueued(txId, target, tx.eta);
        return txId;
    }
    
    function signTransaction(uint256 txId) 
        external 
        onlySigner 
        notEmergency 
    {
        Transaction storage tx = transactions[txId];
        require(tx.target != address(0), "Transaction does not exist");
        require(!tx.executed, "Already executed");
        require(!tx.cancelled, "Cancelled");
        require(!tx.signed[msg.sender], "Already signed");
        
        tx.signed[msg.sender] = true;
        tx.signatures++;
        
        // Auto-execute if ready
        if (tx.signatures >= REQUIRED_SIGNATURES && block.timestamp >= tx.eta) {
            _executeTransaction(txId);
        }
    }
    
    function executeTransaction(uint256 txId) 
        external 
        notEmergency 
    {
        Transaction storage tx = transactions[txId];
        require(tx.signatures >= REQUIRED_SIGNATURES, "Not enough signatures");
        require(block.timestamp >= tx.eta, "Timelock not expired");
        
        _executeTransaction(txId);
    }
    
    function _executeTransaction(uint256 txId) private {
        Transaction storage tx = transactions[txId];
        require(!tx.executed, "Already executed");
        require(!tx.cancelled, "Cancelled");
        
        tx.executed = true;
        
        if (tx.isEmergency) {
            lastEmergencyTime = block.timestamp;
            emit EmergencyUsed(txId);
        }
        
        (bool success,) = tx.target.call{value: tx.value}(tx.data);
        require(success, "Transaction failed");
        
        emit TransactionExecuted(txId);
    }
    
    function cancelTransaction(uint256 txId) 
        external 
        onlySigner 
    {
        Transaction storage tx = transactions[txId];
        require(!tx.executed, "Already executed");
        require(tx.signatures >= REQUIRED_SIGNATURES, "Need more signatures to cancel");
        
        tx.cancelled = true;
        emit TransactionCancelled(txId);
    }
    
    function triggerEmergencyStop() 
        external 
        onlySigner 
    {
        require(!emergencyStop, "Already stopped");
        emergencyStop = true;
        lastEmergencyTime = block.timestamp;
    }
    
    function releaseEmergencyStop() 
        external 
        onlySigner 
    {
        require(emergencyStop, "Not stopped");
        require(
            block.timestamp >= lastEmergencyTime + EMERGENCY_TIMELOCK,
            "Emergency cooldown active"
        );
        emergencyStop = false;
    }
    
    function getTransaction(uint256 txId) 
        external 
        view 
        returns (
            address target,
            bytes memory data,
            uint256 value,
            uint256 eta,
            bool executed,
            bool cancelled,
            uint256 signatures,
            bool isEmergency
        ) 
    {
        Transaction storage tx = transactions[txId];
        return (
            tx.target,
            tx.data,
            tx.value,
            tx.eta,
            tx.executed,
            tx.cancelled,
            tx.signatures,
            tx.isEmergency
        );
    }
    
    function getSigners() external view returns (address[] memory) {
        return signers;
    }
    
    receive() external payable {}
}