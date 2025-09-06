// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract QXCInsurance {
    struct Policy {
        uint256 coverage;
        uint256 premium;
        uint256 expiry;
        bool claimed;
    }
    
    mapping(address => Policy) public policies;
    uint256 public poolBalance;
    
    function buyInsurance(uint256 _coverage) external payable {
        uint256 premium = _coverage / 100; // 1% premium
        require(msg.value >= premium, "Insufficient premium");
        
        policies[msg.sender] = Policy(_coverage, premium, block.timestamp + 365 days, false);
        poolBalance += msg.value;
    }
    
    function claim(uint256 _amount) external {
        Policy storage policy = policies[msg.sender];
        require(policy.expiry > block.timestamp, "Expired");
        require(!policy.claimed, "Already claimed");
        require(_amount <= policy.coverage, "Exceeds coverage");
        
        policy.claimed = true;
        payable(msg.sender).transfer(_amount);
    }
}