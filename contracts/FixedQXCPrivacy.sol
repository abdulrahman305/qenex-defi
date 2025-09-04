// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title Fixed QXC Privacy Contract
 * @notice CORRECTED VERSION - Fixes critical vulnerabilities
 * @dev Educational implementation - NOT FOR PRODUCTION
 */
contract FixedQXCPrivacy is ReentrancyGuard, Ownable, Pausable {
    
    // Fixed deposit amount to prevent accounting errors
    uint256 public constant DEPOSIT_AMOUNT = 1 ether;
    
    // Track deposits and withdrawals properly
    mapping(bytes32 => bool) public nullifierUsed;
    mapping(bytes32 => uint256) public commitmentDeposits;
    uint256 public totalDeposited;
    uint256 public totalWithdrawn;
    
    // Events
    event Deposit(bytes32 indexed commitment, uint256 amount, uint256 timestamp);
    event Withdrawal(bytes32 indexed nullifier, address indexed recipient, uint256 amount);
    
    constructor() Ownable(msg.sender) {}
    
    /**
     * @notice Deposit funds with a commitment
     * @param _commitment Hash commitment for later withdrawal
     */
    function deposit(bytes32 _commitment) external payable nonReentrant whenNotPaused {
        require(msg.value == DEPOSIT_AMOUNT, "Must deposit exactly 1 ETH");
        require(_commitment != bytes32(0), "Invalid commitment");
        require(commitmentDeposits[_commitment] == 0, "Commitment already used");
        
        commitmentDeposits[_commitment] = msg.value;
        totalDeposited += msg.value;
        
        emit Deposit(_commitment, msg.value, block.timestamp);
    }
    
    /**
     * @notice Withdraw funds with proof
     * @param _nullifier Nullifier to prevent double spending
     * @param _commitment Original commitment
     * @param _recipient Recipient address
     * 
     * NOTE: In production, this would require actual ZK proof verification
     * This is a simplified version for educational purposes
     */
    function withdraw(
        bytes32 _nullifier,
        bytes32 _commitment,
        address payable _recipient
    ) external nonReentrant whenNotPaused {
        require(_nullifier != bytes32(0), "Invalid nullifier");
        require(_commitment != bytes32(0), "Invalid commitment");
        require(_recipient != address(0), "Invalid recipient");
        require(!nullifierUsed[_nullifier], "Nullifier already used");
        require(commitmentDeposits[_commitment] > 0, "No deposit found");
        
        // In production: Verify ZK proof here
        // require(verifyProof(_nullifier, _commitment, proof), "Invalid proof");
        
        // For educational version, just check nullifier matches commitment hash
        require(
            keccak256(abi.encodePacked(_commitment, _recipient)) == _nullifier,
            "Invalid nullifier for commitment"
        );
        
        uint256 amount = commitmentDeposits[_commitment];
        require(address(this).balance >= amount, "Insufficient contract balance");
        
        // Effects before interactions (checks-effects-interactions pattern)
        nullifierUsed[_nullifier] = true;
        commitmentDeposits[_commitment] = 0;
        totalWithdrawn += amount;
        
        // Transfer funds
        (bool success, ) = _recipient.call{value: amount}("");
        require(success, "Transfer failed");
        
        emit Withdrawal(_nullifier, _recipient, amount);
    }
    
    /**
     * @notice Get contract statistics
     */
    function getStats() external view returns (
        uint256 balance,
        uint256 deposited,
        uint256 withdrawn
    ) {
        return (
            address(this).balance,
            totalDeposited,
            totalWithdrawn
        );
    }
    
    /**
     * @notice Emergency withdrawal for owner
     * @dev Only for emergency recovery - breaks privacy
     */
    function emergencyWithdraw() external onlyOwner {
        _pause();
        uint256 balance = address(this).balance;
        (bool success, ) = payable(owner()).call{value: balance}("");
        require(success, "Emergency withdrawal failed");
    }
    
    // Admin functions
    function pause() external onlyOwner {
        _pause();
    }
    
    function unpause() external onlyOwner {
        _unpause();
    }
}