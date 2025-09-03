// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract QXCPrivacy {
    mapping(bytes32 => bool) private nullifiers;
    mapping(bytes32 => bytes32) private commitments;
    
    event Deposit(bytes32 commitment);
    event Withdraw(bytes32 nullifier);
    
    function deposit(bytes32 _commitment) external payable {
        commitments[_commitment] = _commitment;
        emit Deposit(_commitment);
    }
    
    function withdraw(bytes32 _nullifier, bytes zkProof) external {
        require(!nullifiers[_nullifier], "Already spent");
        // Verify ZK proof here
        nullifiers[_nullifier] = true;
        payable(msg.sender).transfer(1 ether);
        emit Withdraw(_nullifier);
    }
}