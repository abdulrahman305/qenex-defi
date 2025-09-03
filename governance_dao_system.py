#!/usr/bin/env python3
"""
QENEX Governance DAO System
Decentralized governance with QXC voting
"""

import json
import time
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('GovernanceDAO')

class ProposalStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"

@dataclass
class Proposal:
    id: str
    title: str
    description: str
    proposer: str
    category: str
    status: ProposalStatus
    yes_votes: float
    no_votes: float
    abstain_votes: float
    start_time: float
    end_time: float
    execution_time: Optional[float]
    actions: List[Dict]
    quorum_required: float
    pass_threshold: float

class GovernanceDAO:
    """Decentralized Autonomous Organization for QENEX"""
    
    def __init__(self):
        self.dao_dir = Path('/opt/qenex-os/dao')
        self.dao_dir.mkdir(exist_ok=True)
        self.proposals_db = self.dao_dir / 'proposals.json'
        self.votes_db = self.dao_dir / 'votes.json'
        self.treasury_db = self.dao_dir / 'treasury.json'
        
        self.proposals = self._load_proposals()
        self.votes = self._load_votes()
        self.treasury = self._load_treasury()
        
        # DAO Configuration
        self.config = {
            'voting_period': 7 * 24 * 3600,  # 7 days
            'execution_delay': 2 * 24 * 3600,  # 2 days timelock
            'proposal_threshold': 100.0,  # 100 QXC to create proposal
            'quorum': 0.1,  # 10% of total supply
            'pass_threshold': 0.5,  # 50% majority
        }
        
    def _load_proposals(self) -> Dict[str, Proposal]:
        """Load proposals from database"""
        if self.proposals_db.exists():
            with open(self.proposals_db, 'r') as f:
                data = json.load(f)
                return {k: Proposal(**v) for k, v in data.items()}
        return {}
        
    def _load_votes(self) -> Dict:
        """Load voting records"""
        if self.votes_db.exists():
            with open(self.votes_db, 'r') as f:
                return json.load(f)
        return {}
        
    def _load_treasury(self) -> Dict:
        """Load treasury data"""
        if self.treasury_db.exists():
            with open(self.treasury_db, 'r') as f:
                return json.load(f)
        return {
            'balance': 100000.0,  # 100k QXC treasury
            'allocations': {},
            'spending_history': []
        }
        
    def create_proposal(self, data: Dict) -> Proposal:
        """Create a new governance proposal"""
        
        proposal_id = hashlib.sha256(
            f"{data['title']}_{time.time()}".encode()
        ).hexdigest()[:16]
        
        proposal = Proposal(
            id=proposal_id,
            title=data['title'],
            description=data['description'],
            proposer=data['proposer'],
            category=data.get('category', 'general'),
            status=ProposalStatus.PENDING,
            yes_votes=0,
            no_votes=0,
            abstain_votes=0,
            start_time=time.time(),
            end_time=time.time() + self.config['voting_period'],
            execution_time=None,
            actions=data.get('actions', []),
            quorum_required=self.config['quorum'],
            pass_threshold=self.config['pass_threshold']
        )
        
        self.proposals[proposal_id] = proposal
        self._save_proposals()
        
        logger.info(f"Created proposal: {proposal.title}")
        return proposal
        
    def vote(self, proposal_id: str, voter: str, vote_type: str, weight: float) -> bool:
        """Cast a vote on a proposal"""
        
        if proposal_id not in self.proposals:
            return False
            
        proposal = self.proposals[proposal_id]
        
        # Check if voting is active
        if proposal.status != ProposalStatus.ACTIVE:
            return False
            
        if time.time() > proposal.end_time:
            return False
            
        # Record vote
        vote_key = f"{proposal_id}_{voter}"
        if vote_key in self.votes:
            # Remove previous vote
            prev_vote = self.votes[vote_key]
            if prev_vote['type'] == 'yes':
                proposal.yes_votes -= prev_vote['weight']
            elif prev_vote['type'] == 'no':
                proposal.no_votes -= prev_vote['weight']
            else:
                proposal.abstain_votes -= prev_vote['weight']
                
        # Add new vote
        if vote_type == 'yes':
            proposal.yes_votes += weight
        elif vote_type == 'no':
            proposal.no_votes += weight
        else:
            proposal.abstain_votes += weight
            
        self.votes[vote_key] = {
            'proposal_id': proposal_id,
            'voter': voter,
            'type': vote_type,
            'weight': weight,
            'timestamp': time.time()
        }
        
        self.proposals[proposal_id] = proposal
        self._save_proposals()
        self._save_votes()
        
        return True
        
    def finalize_proposal(self, proposal_id: str) -> str:
        """Finalize voting and determine outcome"""
        
        if proposal_id not in self.proposals:
            return "Proposal not found"
            
        proposal = self.proposals[proposal_id]
        
        if time.time() < proposal.end_time:
            return "Voting still active"
            
        total_votes = proposal.yes_votes + proposal.no_votes + proposal.abstain_votes
        total_supply = 1000000000  # 1B QXC total supply
        
        # Check quorum
        if total_votes < (total_supply * proposal.quorum_required):
            proposal.status = ProposalStatus.REJECTED
            result = "Rejected: Quorum not met"
        else:
            # Check pass threshold
            if proposal.yes_votes > (total_votes * proposal.pass_threshold):
                proposal.status = ProposalStatus.PASSED
                proposal.execution_time = time.time() + self.config['execution_delay']
                result = "Passed"
            else:
                proposal.status = ProposalStatus.REJECTED
                result = "Rejected: Threshold not met"
                
        self.proposals[proposal_id] = proposal
        self._save_proposals()
        
        return result
        
    def execute_proposal(self, proposal_id: str) -> bool:
        """Execute a passed proposal"""
        
        if proposal_id not in self.proposals:
            return False
            
        proposal = self.proposals[proposal_id]
        
        if proposal.status != ProposalStatus.PASSED:
            return False
            
        if time.time() < proposal.execution_time:
            return False  # Still in timelock
            
        # Execute actions
        for action in proposal.actions:
            self._execute_action(action, proposal)
            
        proposal.status = ProposalStatus.EXECUTED
        self.proposals[proposal_id] = proposal
        self._save_proposals()
        
        logger.info(f"Executed proposal: {proposal.title}")
        return True
        
    def _execute_action(self, action: Dict, proposal: Proposal):
        """Execute a specific proposal action"""
        
        action_type = action.get('type')
        
        if action_type == 'treasury_transfer':
            amount = action.get('amount', 0)
            recipient = action.get('recipient')
            
            if self.treasury['balance'] >= amount:
                self.treasury['balance'] -= amount
                self.treasury['spending_history'].append({
                    'proposal_id': proposal.id,
                    'amount': amount,
                    'recipient': recipient,
                    'timestamp': time.time()
                })
                self._save_treasury()
                
        elif action_type == 'parameter_change':
            param = action.get('parameter')
            value = action.get('value')
            
            if param in self.config:
                self.config[param] = value
                
        elif action_type == 'grant_allocation':
            project = action.get('project')
            amount = action.get('amount')
            
            self.treasury['allocations'][project] = amount
            self._save_treasury()
            
    def get_treasury_status(self) -> Dict:
        """Get current treasury status"""
        return {
            'balance': self.treasury['balance'],
            'allocations': self.treasury['allocations'],
            'recent_spending': self.treasury['spending_history'][-10:]
        }
        
    def _save_proposals(self):
        """Save proposals to database"""
        data = {}
        for k, v in self.proposals.items():
            proposal_dict = v.__dict__.copy()
            proposal_dict['status'] = proposal_dict['status'].value
            data[k] = proposal_dict
            
        with open(self.proposals_db, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
    def _save_votes(self):
        """Save votes to database"""
        with open(self.votes_db, 'w') as f:
            json.dump(self.votes, f, indent=2)
            
    def _save_treasury(self):
        """Save treasury data"""
        with open(self.treasury_db, 'w') as f:
            json.dump(self.treasury, f, indent=2)

def main():
    """CLI interface for DAO"""
    import sys
    
    dao = GovernanceDAO()
    
    if len(sys.argv) < 2:
        print("\nQENEX Governance DAO")
        print("="*40)
        print("\nCommands:")
        print("  propose <title> <description>  - Create proposal")
        print("  vote <proposal_id> <yes/no>    - Vote on proposal")
        print("  status <proposal_id>           - Check proposal status")
        print("  treasury                       - View treasury")
        print("  active                         - List active proposals")
        return
        
    command = sys.argv[1].lower()
    
    if command == 'treasury':
        status = dao.get_treasury_status()
        print(f"\n💰 Treasury Balance: {status['balance']:.2f} QXC")
        print(f"Allocations: {len(status['allocations'])}")
        print(f"Recent spending: {len(status['recent_spending'])} transactions")
        
    elif command == 'active':
        active = [p for p in dao.proposals.values() 
                 if p.status == ProposalStatus.ACTIVE]
        print(f"\n📋 Active Proposals: {len(active)}")
        for proposal in active:
            print(f"- {proposal.id[:8]}: {proposal.title}")
            print(f"  Yes: {proposal.yes_votes:.0f} | No: {proposal.no_votes:.0f}")

if __name__ == '__main__':
    main()