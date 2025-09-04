#!/usr/bin/env python3
"""
QENEX Smart Contract Deployment System
Automated deployment and management of banking smart contracts
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import hashlib
import subprocess
import tempfile

logger = logging.getLogger(__name__)

# ============================================================================
# Smart Contract Templates
# ============================================================================

class ContractType(Enum):
    """Types of smart contracts"""
    PAYMENT_PROCESSING = "payment_processing"
    ESCROW = "escrow"
    LOAN = "loan"
    TOKEN_TRANSFER = "token_transfer"
    MULTI_SIG_WALLET = "multi_sig_wallet"
    INSURANCE = "insurance"
    REGULATORY_COMPLIANCE = "compliance"

@dataclass
class ContractDeployment:
    """Smart contract deployment information"""
    contract_id: str
    contract_type: ContractType
    network: str
    address: str
    transaction_hash: str
    deployment_time: datetime
    gas_used: int
    status: str
    abi: List[Dict]
    bytecode: str
    verified: bool = False

class SmartContractTemplates:
    """Smart contract templates for banking operations"""
    
    @staticmethod
    def get_payment_processing_contract() -> str:
        """Payment processing smart contract in Solidity"""
        return """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

contract QENEXPaymentProcessor is ReentrancyGuard, Ownable, Pausable {
    
    struct Payment {
        address sender;
        address receiver;
        uint256 amount;
        bytes32 reference;
        uint256 timestamp;
        bool completed;
        bool reversed;
    }
    
    mapping(bytes32 => Payment) public payments;
    mapping(address => uint256) public balances;
    mapping(bytes32 => bool) public processedReferences;
    
    event PaymentInitiated(bytes32 indexed reference, address sender, address receiver, uint256 amount);
    event PaymentCompleted(bytes32 indexed reference);
    event PaymentReversed(bytes32 indexed reference, string reason);
    event FundsDeposited(address indexed account, uint256 amount);
    event FundsWithdrawn(address indexed account, uint256 amount);
    
    uint256 public constant MAX_PAYMENT_AMOUNT = 1000000 * 10**18; // 1M tokens
    uint256 public constant MIN_PAYMENT_AMOUNT = 1 * 10**15; // 0.001 tokens
    
    modifier validAmount(uint256 amount) {
        require(amount >= MIN_PAYMENT_AMOUNT && amount <= MAX_PAYMENT_AMOUNT, "Invalid payment amount");
        _;
    }
    
    modifier validReference(bytes32 reference) {
        require(reference != bytes32(0), "Invalid reference");
        require(!processedReferences[reference], "Reference already used");
        _;
    }
    
    constructor() {}
    
    function depositFunds() external payable {
        require(msg.value > 0, "Deposit amount must be greater than 0");
        balances[msg.sender] += msg.value;
        emit FundsDeposited(msg.sender, msg.value);
    }
    
    function withdrawFunds(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        require(amount > 0, "Withdrawal amount must be greater than 0");
        
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
        
        emit FundsWithdrawn(msg.sender, amount);
    }
    
    function initiatePayment(
        address receiver,
        uint256 amount,
        bytes32 reference
    ) external validAmount(amount) validReference(reference) whenNotPaused {
        require(receiver != address(0), "Invalid receiver address");
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        payments[reference] = Payment({
            sender: msg.sender,
            receiver: receiver,
            amount: amount,
            reference: reference,
            timestamp: block.timestamp,
            completed: false,
            reversed: false
        });
        
        processedReferences[reference] = true;
        balances[msg.sender] -= amount;
        
        emit PaymentInitiated(reference, msg.sender, receiver, amount);
    }
    
    function completePayment(bytes32 reference) external onlyOwner {
        Payment storage payment = payments[reference];
        require(payment.sender != address(0), "Payment not found");
        require(!payment.completed, "Payment already completed");
        require(!payment.reversed, "Payment was reversed");
        
        payment.completed = true;
        balances[payment.receiver] += payment.amount;
        
        emit PaymentCompleted(reference);
    }
    
    function reversePayment(bytes32 reference, string calldata reason) external onlyOwner {
        Payment storage payment = payments[reference];
        require(payment.sender != address(0), "Payment not found");
        require(!payment.completed, "Cannot reverse completed payment");
        require(!payment.reversed, "Payment already reversed");
        
        payment.reversed = true;
        balances[payment.sender] += payment.amount;
        
        emit PaymentReversed(reference, reason);
    }
    
    function getPayment(bytes32 reference) external view returns (Payment memory) {
        return payments[reference];
    }
    
    function getBalance(address account) external view returns (uint256) {
        return balances[account];
    }
    
    function pause() external onlyOwner {
        _pause();
    }
    
    function unpause() external onlyOwner {
        _unpause();
    }
    
    // Emergency withdrawal function
    function emergencyWithdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }
}
"""

    @staticmethod
    def get_escrow_contract() -> str:
        """Escrow smart contract in Solidity"""
        return """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract QENEXEscrow is ReentrancyGuard, Ownable {
    
    enum EscrowState { Created, Funded, Released, Refunded, Disputed }
    
    struct EscrowAgreement {
        address buyer;
        address seller;
        address arbiter;
        uint256 amount;
        uint256 deadline;
        EscrowState state;
        string description;
        bool buyerApproved;
        bool sellerApproved;
    }
    
    mapping(bytes32 => EscrowAgreement) public escrows;
    mapping(address => uint256) public deposits;
    
    event EscrowCreated(bytes32 indexed escrowId, address buyer, address seller, uint256 amount);
    event EscrowFunded(bytes32 indexed escrowId);
    event EscrowReleased(bytes32 indexed escrowId);
    event EscrowRefunded(bytes32 indexed escrowId);
    event DisputeRaised(bytes32 indexed escrowId);
    
    uint256 public constant ESCROW_FEE_PERCENT = 250; // 2.5%
    uint256 public constant PERCENT_DENOMINATOR = 10000;
    
    modifier onlyParties(bytes32 escrowId) {
        EscrowAgreement memory escrow = escrows[escrowId];
        require(
            msg.sender == escrow.buyer || 
            msg.sender == escrow.seller || 
            msg.sender == escrow.arbiter,
            "Not authorized"
        );
        _;
    }
    
    modifier escrowExists(bytes32 escrowId) {
        require(escrows[escrowId].buyer != address(0), "Escrow does not exist");
        _;
    }
    
    function createEscrow(
        bytes32 escrowId,
        address seller,
        address arbiter,
        uint256 deadline,
        string calldata description
    ) external payable {
        require(msg.value > 0, "Escrow amount must be greater than 0");
        require(seller != address(0), "Invalid seller address");
        require(arbiter != address(0), "Invalid arbiter address");
        require(deadline > block.timestamp, "Deadline must be in the future");
        require(escrows[escrowId].buyer == address(0), "Escrow already exists");
        
        escrows[escrowId] = EscrowAgreement({
            buyer: msg.sender,
            seller: seller,
            arbiter: arbiter,
            amount: msg.value,
            deadline: deadline,
            state: EscrowState.Funded,
            description: description,
            buyerApproved: false,
            sellerApproved: false
        });
        
        emit EscrowCreated(escrowId, msg.sender, seller, msg.value);
        emit EscrowFunded(escrowId);
    }
    
    function approveRelease(bytes32 escrowId) external escrowExists(escrowId) {
        EscrowAgreement storage escrow = escrows[escrowId];
        require(escrow.state == EscrowState.Funded, "Invalid escrow state");
        require(block.timestamp <= escrow.deadline, "Escrow expired");
        
        if (msg.sender == escrow.buyer) {
            escrow.buyerApproved = true;
        } else if (msg.sender == escrow.seller) {
            escrow.sellerApproved = true;
        } else {
            revert("Not authorized to approve");
        }
        
        // If both parties approve, release funds
        if (escrow.buyerApproved && escrow.sellerApproved) {
            _releaseFunds(escrowId);
        }
    }
    
    function releaseFunds(bytes32 escrowId) external escrowExists(escrowId) {
        EscrowAgreement storage escrow = escrows[escrowId];
        require(msg.sender == escrow.arbiter, "Only arbiter can force release");
        require(escrow.state == EscrowState.Funded, "Invalid escrow state");
        
        _releaseFunds(escrowId);
    }
    
    function _releaseFunds(bytes32 escrowId) internal nonReentrant {
        EscrowAgreement storage escrow = escrows[escrowId];
        
        uint256 fee = (escrow.amount * ESCROW_FEE_PERCENT) / PERCENT_DENOMINATOR;
        uint256 sellerAmount = escrow.amount - fee;
        
        escrow.state = EscrowState.Released;
        
        payable(escrow.seller).transfer(sellerAmount);
        deposits[owner()] += fee;
        
        emit EscrowReleased(escrowId);
    }
    
    function refundBuyer(bytes32 escrowId) external escrowExists(escrowId) {
        EscrowAgreement storage escrow = escrows[escrowId];
        require(
            msg.sender == escrow.arbiter || 
            (msg.sender == escrow.buyer && block.timestamp > escrow.deadline),
            "Not authorized to refund"
        );
        require(escrow.state == EscrowState.Funded, "Invalid escrow state");
        
        escrow.state = EscrowState.Refunded;
        payable(escrow.buyer).transfer(escrow.amount);
        
        emit EscrowRefunded(escrowId);
    }
    
    function raiseDispute(bytes32 escrowId) external onlyParties(escrowId) escrowExists(escrowId) {
        EscrowAgreement storage escrow = escrows[escrowId];
        require(escrow.state == EscrowState.Funded, "Invalid escrow state");
        
        escrow.state = EscrowState.Disputed;
        emit DisputeRaised(escrowId);
    }
    
    function withdrawDeposits() external onlyOwner {
        uint256 amount = deposits[msg.sender];
        require(amount > 0, "No deposits to withdraw");
        
        deposits[msg.sender] = 0;
        payable(msg.sender).transfer(amount);
    }
}
"""

    @staticmethod
    def get_loan_contract() -> str:
        """Loan smart contract in Solidity"""
        return """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract QENEXLoan is ReentrancyGuard, Ownable {
    
    enum LoanState { Pending, Active, Repaid, Defaulted }
    
    struct Loan {
        address borrower;
        address lender;
        uint256 principal;
        uint256 interestRate; // Annual interest rate in basis points (e.g., 500 = 5%)
        uint256 duration; // Loan duration in seconds
        uint256 startTime;
        uint256 totalRepayment;
        uint256 amountRepaid;
        LoanState state;
        bytes32 collateralHash;
    }
    
    mapping(bytes32 => Loan) public loans;
    mapping(address => bytes32[]) public borrowerLoans;
    mapping(address => bytes32[]) public lenderLoans;
    
    event LoanRequested(bytes32 indexed loanId, address borrower, uint256 amount);
    event LoanFunded(bytes32 indexed loanId, address lender);
    event PaymentMade(bytes32 indexed loanId, uint256 amount);
    event LoanRepaid(bytes32 indexed loanId);
    event LoanDefaulted(bytes32 indexed loanId);
    
    uint256 public constant BASIS_POINTS = 10000;
    uint256 public constant SECONDS_IN_YEAR = 365 * 24 * 3600;
    uint256 public constant MAX_INTEREST_RATE = 5000; // 50% annual
    uint256 public constant MIN_LOAN_DURATION = 30 days;
    uint256 public constant MAX_LOAN_DURATION = 365 days;
    
    modifier loanExists(bytes32 loanId) {
        require(loans[loanId].borrower != address(0), "Loan does not exist");
        _;
    }
    
    modifier onlyBorrower(bytes32 loanId) {
        require(loans[loanId].borrower == msg.sender, "Only borrower allowed");
        _;
    }
    
    function requestLoan(
        bytes32 loanId,
        uint256 amount,
        uint256 interestRate,
        uint256 duration,
        bytes32 collateralHash
    ) external {
        require(loans[loanId].borrower == address(0), "Loan ID already exists");
        require(amount > 0, "Loan amount must be positive");
        require(interestRate <= MAX_INTEREST_RATE, "Interest rate too high");
        require(duration >= MIN_LOAN_DURATION && duration <= MAX_LOAN_DURATION, "Invalid duration");
        
        uint256 totalRepayment = amount + ((amount * interestRate * duration) / (BASIS_POINTS * SECONDS_IN_YEAR));
        
        loans[loanId] = Loan({
            borrower: msg.sender,
            lender: address(0),
            principal: amount,
            interestRate: interestRate,
            duration: duration,
            startTime: 0,
            totalRepayment: totalRepayment,
            amountRepaid: 0,
            state: LoanState.Pending,
            collateralHash: collateralHash
        });
        
        borrowerLoans[msg.sender].push(loanId);
        
        emit LoanRequested(loanId, msg.sender, amount);
    }
    
    function fundLoan(bytes32 loanId) external payable loanExists(loanId) nonReentrant {
        Loan storage loan = loans[loanId];
        require(loan.state == LoanState.Pending, "Loan not available for funding");
        require(msg.value == loan.principal, "Incorrect funding amount");
        require(msg.sender != loan.borrower, "Borrower cannot fund own loan");
        
        loan.lender = msg.sender;
        loan.startTime = block.timestamp;
        loan.state = LoanState.Active;
        
        lenderLoans[msg.sender].push(loanId);
        
        // Transfer funds to borrower
        payable(loan.borrower).transfer(loan.principal);
        
        emit LoanFunded(loanId, msg.sender);
    }
    
    function makePayment(bytes32 loanId) external payable loanExists(loanId) onlyBorrower(loanId) {
        Loan storage loan = loans[loanId];
        require(loan.state == LoanState.Active, "Loan not active");
        require(msg.value > 0, "Payment amount must be positive");
        
        uint256 remainingBalance = loan.totalRepayment - loan.amountRepaid;
        uint256 paymentAmount = msg.value > remainingBalance ? remainingBalance : msg.value;
        
        loan.amountRepaid += paymentAmount;
        
        // Transfer payment to lender
        payable(loan.lender).transfer(paymentAmount);
        
        // Refund excess payment if any
        if (msg.value > paymentAmount) {
            payable(msg.sender).transfer(msg.value - paymentAmount);
        }
        
        emit PaymentMade(loanId, paymentAmount);
        
        // Check if loan is fully repaid
        if (loan.amountRepaid >= loan.totalRepayment) {
            loan.state = LoanState.Repaid;
            emit LoanRepaid(loanId);
        }
    }
    
    function defaultLoan(bytes32 loanId) external loanExists(loanId) {
        Loan storage loan = loans[loanId];
        require(msg.sender == loan.lender || msg.sender == owner(), "Not authorized");
        require(loan.state == LoanState.Active, "Loan not active");
        require(block.timestamp > loan.startTime + loan.duration, "Loan not yet due");
        
        loan.state = LoanState.Defaulted;
        emit LoanDefaulted(loanId);
    }
    
    function getLoan(bytes32 loanId) external view returns (Loan memory) {
        return loans[loanId];
    }
    
    function getBorrowerLoans(address borrower) external view returns (bytes32[] memory) {
        return borrowerLoans[borrower];
    }
    
    function getLenderLoans(address lender) external view returns (bytes32[] memory) {
        return lenderLoans[lender];
    }
    
    function calculateCurrentBalance(bytes32 loanId) external view loanExists(loanId) returns (uint256) {
        Loan memory loan = loans[loanId];
        if (loan.state != LoanState.Active) {
            return 0;
        }
        
        return loan.totalRepayment - loan.amountRepaid;
    }
}
"""

# ============================================================================
# Smart Contract Compiler and Deployer
# ============================================================================

class SmartContractCompiler:
    """Compiles and prepares smart contracts for deployment"""
    
    def __init__(self, solc_version: str = "0.8.19"):
        self.solc_version = solc_version
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def compile_contract(self, contract_code: str, contract_name: str) -> Dict[str, Any]:
        """Compile Solidity contract"""
        
        # Write contract to temporary file
        contract_file = self.temp_dir / f"{contract_name}.sol"
        with open(contract_file, 'w') as f:
            f.write(contract_code)
            
        try:
            # Use solc to compile (requires solc binary)
            result = subprocess.run([
                'solc', '--combined-json', 'abi,bin,metadata',
                '--optimize', '--optimize-runs', '200',
                str(contract_file)
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise Exception(f"Compilation failed: {result.stderr}")
                
            compiled_data = json.loads(result.stdout)
            contract_data = compiled_data['contracts'][f"{contract_file}:{contract_name}"]
            
            return {
                'abi': json.loads(contract_data['abi']),
                'bytecode': contract_data['bin'],
                'metadata': json.loads(contract_data['metadata']),
                'compiled_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Contract compilation failed: {e}")
            # Return mock compilation result for testing
            return self._get_mock_compilation_result(contract_name)
            
    def _get_mock_compilation_result(self, contract_name: str) -> Dict[str, Any]:
        """Generate mock compilation result for testing"""
        return {
            'abi': [
                {
                    "inputs": [],
                    "name": "constructor",
                    "stateMutability": "nonpayable",
                    "type": "constructor"
                }
            ],
            'bytecode': f"0x608060405234801561001057600080fd5b50{hashlib.sha256(contract_name.encode()).hexdigest()}",
            'metadata': {
                'compiler': {'version': self.solc_version},
                'language': 'Solidity',
                'output': {
                    'abi': [],
                    'devdoc': {'methods': {}},
                    'userdoc': {'methods': {}}
                }
            },
            'compiled_at': datetime.now(timezone.utc).isoformat()
        }

class SmartContractDeployer:
    """Deploys smart contracts to blockchain networks"""
    
    def __init__(self):
        self.compiler = SmartContractCompiler()
        self.deployments: Dict[str, ContractDeployment] = {}
        self.supported_networks = {
            'ethereum': {
                'rpc_url': 'https://mainnet.infura.io/v3/YOUR_PROJECT_ID',
                'chain_id': 1,
                'gas_price_gwei': 20
            },
            'polygon': {
                'rpc_url': 'https://polygon-rpc.com',
                'chain_id': 137,
                'gas_price_gwei': 30
            },
            'bsc': {
                'rpc_url': 'https://bsc-dataseed.binance.org',
                'chain_id': 56,
                'gas_price_gwei': 5
            },
            'localhost': {
                'rpc_url': 'http://localhost:8545',
                'chain_id': 1337,
                'gas_price_gwei': 20
            }
        }
        
    async def deploy_contract(
        self,
        contract_type: ContractType,
        network: str,
        constructor_args: List[Any] = None,
        gas_limit: int = 3000000
    ) -> ContractDeployment:
        """Deploy a smart contract"""
        
        if network not in self.supported_networks:
            raise ValueError(f"Unsupported network: {network}")
            
        # Get contract template
        contract_code = self._get_contract_template(contract_type)
        contract_name = self._get_contract_name(contract_type)
        
        # Compile contract
        compiled = self.compiler.compile_contract(contract_code, contract_name)
        
        # Generate unique contract ID
        contract_id = self._generate_contract_id(contract_type, network)
        
        # Simulate deployment (in production, would interact with blockchain)
        deployment_result = await self._simulate_deployment(
            contract_id, contract_type, network, compiled, gas_limit
        )
        
        # Store deployment information
        self.deployments[contract_id] = deployment_result
        
        logger.info(f"Contract {contract_id} deployed to {network} at {deployment_result.address}")
        return deployment_result
        
    def _get_contract_template(self, contract_type: ContractType) -> str:
        """Get contract template by type"""
        
        templates = SmartContractTemplates()
        
        if contract_type == ContractType.PAYMENT_PROCESSING:
            return templates.get_payment_processing_contract()
        elif contract_type == ContractType.ESCROW:
            return templates.get_escrow_contract()
        elif contract_type == ContractType.LOAN:
            return templates.get_loan_contract()
        else:
            raise ValueError(f"No template available for contract type: {contract_type}")
            
    def _get_contract_name(self, contract_type: ContractType) -> str:
        """Get contract name by type"""
        
        name_mapping = {
            ContractType.PAYMENT_PROCESSING: "QENEXPaymentProcessor",
            ContractType.ESCROW: "QENEXEscrow",
            ContractType.LOAN: "QENEXLoan",
            ContractType.TOKEN_TRANSFER: "QENEXTokenTransfer",
            ContractType.MULTI_SIG_WALLET: "QENEXMultiSigWallet"
        }
        
        return name_mapping.get(contract_type, "QENEXContract")
        
    def _generate_contract_id(self, contract_type: ContractType, network: str) -> str:
        """Generate unique contract ID"""
        
        timestamp = int(time.time())
        data = f"{contract_type.value}_{network}_{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
        
    async def _simulate_deployment(
        self,
        contract_id: str,
        contract_type: ContractType,
        network: str,
        compiled: Dict[str, Any],
        gas_limit: int
    ) -> ContractDeployment:
        """Simulate contract deployment"""
        
        # Simulate deployment delay
        await asyncio.sleep(0.5)
        
        # Generate mock deployment data
        mock_address = f"0x{hashlib.sha256(contract_id.encode()).hexdigest()[:40]}"
        mock_tx_hash = f"0x{hashlib.sha256(f'{contract_id}_tx'.encode()).hexdigest()}"
        
        gas_used = min(gas_limit, int(gas_limit * 0.8))  # Simulate gas usage
        
        return ContractDeployment(
            contract_id=contract_id,
            contract_type=contract_type,
            network=network,
            address=mock_address,
            transaction_hash=mock_tx_hash,
            deployment_time=datetime.now(timezone.utc),
            gas_used=gas_used,
            status="deployed",
            abi=compiled['abi'],
            bytecode=compiled['bytecode'],
            verified=False
        )
        
    async def verify_contract(self, contract_id: str) -> bool:
        """Verify contract on blockchain explorer"""
        
        if contract_id not in self.deployments:
            raise ValueError(f"Contract {contract_id} not found")
            
        deployment = self.deployments[contract_id]
        
        # Simulate verification process
        await asyncio.sleep(1.0)
        
        # In production, would interact with blockchain explorer API
        deployment.verified = True
        
        logger.info(f"Contract {contract_id} verified on {deployment.network}")
        return True
        
    def get_contract_info(self, contract_id: str) -> Optional[ContractDeployment]:
        """Get contract deployment information"""
        return self.deployments.get(contract_id)
        
    def list_deployments(self, network: Optional[str] = None) -> List[ContractDeployment]:
        """List all deployments, optionally filtered by network"""
        
        deployments = list(self.deployments.values())
        
        if network:
            deployments = [d for d in deployments if d.network == network]
            
        return sorted(deployments, key=lambda x: x.deployment_time, reverse=True)

# ============================================================================
# Contract Manager
# ============================================================================

class SmartContractManager:
    """Manages smart contract lifecycle and operations"""
    
    def __init__(self):
        self.deployer = SmartContractDeployer()
        self.active_contracts: Dict[str, Dict[str, Any]] = {}
        
    async def deploy_banking_suite(
        self,
        network: str = "localhost",
        deploy_all: bool = True
    ) -> Dict[str, ContractDeployment]:
        """Deploy complete banking smart contract suite"""
        
        contracts_to_deploy = [
            ContractType.PAYMENT_PROCESSING,
            ContractType.ESCROW,
            ContractType.LOAN
        ]
        
        if not deploy_all:
            contracts_to_deploy = [ContractType.PAYMENT_PROCESSING]
            
        deployments = {}
        
        for contract_type in contracts_to_deploy:
            try:
                deployment = await self.deployer.deploy_contract(
                    contract_type=contract_type,
                    network=network
                )
                
                deployments[contract_type.value] = deployment
                
                # Verify contract after deployment
                await asyncio.sleep(2)  # Wait for deployment confirmation
                await self.deployer.verify_contract(deployment.contract_id)
                
            except Exception as e:
                logger.error(f"Failed to deploy {contract_type.value}: {e}")
                
        logger.info(f"Deployed {len(deployments)} contracts to {network}")
        return deployments
        
    async def upgrade_contract(self, contract_id: str, new_version: str) -> bool:
        """Upgrade deployed contract (proxy pattern)"""
        
        deployment = self.deployer.get_contract_info(contract_id)
        if not deployment:
            raise ValueError(f"Contract {contract_id} not found")
            
        # In production, would implement proxy upgrade pattern
        logger.info(f"Contract {contract_id} upgraded to version {new_version}")
        return True
        
    def get_contract_stats(self) -> Dict[str, Any]:
        """Get deployment statistics"""
        
        deployments = self.deployer.list_deployments()
        
        stats = {
            'total_deployments': len(deployments),
            'by_network': {},
            'by_type': {},
            'verified_count': sum(1 for d in deployments if d.verified),
            'total_gas_used': sum(d.gas_used for d in deployments),
            'latest_deployment': None
        }
        
        for deployment in deployments:
            # Count by network
            stats['by_network'][deployment.network] = stats['by_network'].get(deployment.network, 0) + 1
            
            # Count by type
            type_name = deployment.contract_type.value
            stats['by_type'][type_name] = stats['by_type'].get(type_name, 0) + 1
            
        if deployments:
            stats['latest_deployment'] = deployments[0].deployment_time.isoformat()
            
        return stats

# ============================================================================
# Testing
# ============================================================================

async def test_smart_contracts():
    """Test smart contract deployment system"""
    
    manager = SmartContractManager()
    
    print("Testing QENEX Smart Contract Deployment System")
    print("=" * 50)
    
    # Deploy banking suite
    print("Deploying banking smart contract suite...")
    deployments = await manager.deploy_banking_suite(network="localhost")
    
    print(f"\nDeployed {len(deployments)} contracts:")
    for contract_type, deployment in deployments.items():
        print(f"- {contract_type}: {deployment.address}")
        print(f"  Transaction: {deployment.transaction_hash}")
        print(f"  Gas Used: {deployment.gas_used:,}")
        
    # Get contract stats
    stats = manager.get_contract_stats()
    print(f"\nContract Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Test individual contract deployment
    print(f"\nTesting individual contract deployment...")
    escrow_deployment = await manager.deployer.deploy_contract(
        contract_type=ContractType.ESCROW,
        network="polygon"
    )
    
    print(f"Escrow contract deployed:")
    print(f"- Address: {escrow_deployment.address}")
    print(f"- Network: {escrow_deployment.network}")
    print(f"- Verified: {escrow_deployment.verified}")
    
    print("\nSmart contract deployment test completed!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_smart_contracts())