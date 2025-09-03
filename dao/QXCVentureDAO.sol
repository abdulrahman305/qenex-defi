// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract QXCVentureDAO {
    struct Proposal {
        string project;
        uint256 fundingAmount;
        uint256 yesVotes;
        uint256 noVotes;
        uint256 endTime;
        bool executed;
    }
    
    mapping(uint256 => Proposal) public proposals;
    mapping(address => uint256) public votingPower;
    uint256 public proposalCount;
    
    function createProposal(string memory _project, uint256 _amount) external {
        proposalCount++;
        proposals[proposalCount] = Proposal(_project, _amount, 0, 0, block.timestamp + 7 days, false);
    }
    
    function vote(uint256 _proposalId, bool _support) external {
        Proposal storage proposal = proposals[_proposalId];
        require(block.timestamp < proposal.endTime, "Voting ended");
        
        if (_support) {
            proposal.yesVotes += votingPower[msg.sender];
        } else {
            proposal.noVotes += votingPower[msg.sender];
        }
    }
    
    function execute(uint256 _proposalId) external {
        Proposal storage proposal = proposals[_proposalId];
        require(block.timestamp > proposal.endTime, "Voting ongoing");
        require(!proposal.executed, "Already executed");
        require(proposal.yesVotes > proposal.noVotes, "Rejected");
        
        proposal.executed = true;
        // Transfer funds to project
    }
}