// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Simple Multi-Signature Wallet
 * @notice Minimal 2-of-3 multisig for critical functions
 * @dev Simplified implementation - no complex features
 */
contract SimpleMultiSig {
    // Events
    event TransactionProposed(uint256 indexed txId, address indexed proposer, address target, bytes data);
    event TransactionApproved(uint256 indexed txId, address indexed approver);
    event TransactionExecuted(uint256 indexed txId);
    event SignerAdded(address indexed signer);
    event SignerRemoved(address indexed signer);
    
    // State
    mapping(address => bool) public isSigner;
    address[] public signers;
    uint256 public requiredSignatures = 2;
    
    struct Transaction {
        address target;
        bytes data;
        uint256 value;
        bool executed;
        uint256 approvals;
        mapping(address => bool) approved;
    }
    
    mapping(uint256 => Transaction) public transactions;
    uint256 public transactionCount;
    
    modifier onlySigner() {
        require(isSigner[msg.sender], "Not a signer");
        _;
    }
    
    modifier txExists(uint256 txId) {
        require(txId < transactionCount, "Transaction does not exist");
        _;
    }
    
    modifier notExecuted(uint256 txId) {
        require(!transactions[txId].executed, "Transaction already executed");
        _;
    }
    
    constructor(address[] memory _signers) {
        require(_signers.length >= 3, "Need at least 3 signers");
        
        for (uint256 i = 0; i < _signers.length; i++) {
            require(_signers[i] != address(0), "Invalid signer");
            require(!isSigner[_signers[i]], "Duplicate signer");
            
            isSigner[_signers[i]] = true;
            signers.push(_signers[i]);
        }
    }
    
    function proposeTransaction(
        address target,
        bytes memory data,
        uint256 value
    ) external onlySigner returns (uint256) {
        uint256 txId = transactionCount++;
        
        Transaction storage tx = transactions[txId];
        tx.target = target;
        tx.data = data;
        tx.value = value;
        tx.executed = false;
        tx.approvals = 1;
        tx.approved[msg.sender] = true;
        
        emit TransactionProposed(txId, msg.sender, target, data);
        return txId;
    }
    
    function approveTransaction(uint256 txId) 
        external 
        onlySigner 
        txExists(txId) 
        notExecuted(txId) 
    {
        Transaction storage tx = transactions[txId];
        require(!tx.approved[msg.sender], "Already approved");
        
        tx.approved[msg.sender] = true;
        tx.approvals++;
        
        emit TransactionApproved(txId, msg.sender);
        
        // Auto-execute if enough approvals
        if (tx.approvals >= requiredSignatures) {
            executeTransaction(txId);
        }
    }
    
    function executeTransaction(uint256 txId) 
        public 
        txExists(txId) 
        notExecuted(txId) 
    {
        Transaction storage tx = transactions[txId];
        require(tx.approvals >= requiredSignatures, "Not enough approvals");
        
        tx.executed = true;
        
        (bool success,) = tx.target.call{value: tx.value}(tx.data);
        require(success, "Transaction failed");
        
        emit TransactionExecuted(txId);
    }
    
    function getTransaction(uint256 txId) external view returns (
        address target,
        bytes memory data,
        uint256 value,
        bool executed,
        uint256 approvals
    ) {
        Transaction storage tx = transactions[txId];
        return (tx.target, tx.data, tx.value, tx.executed, tx.approvals);
    }
    
    function getSigners() external view returns (address[] memory) {
        return signers;
    }
    
    receive() external payable {}
}