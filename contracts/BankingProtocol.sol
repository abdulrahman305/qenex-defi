// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title BankingProtocol
 * @dev Decentralized banking protocol for institutional DeFi
 */
contract BankingProtocol is ReentrancyGuard, AccessControl, Pausable {
    bytes32 public constant BANKER_ROLE = keccak256("BANKER_ROLE");
    bytes32 public constant COMPLIANCE_ROLE = keccak256("COMPLIANCE_ROLE");
    
    struct Account {
        uint256 balance;
        uint256 creditLimit;
        uint256 interestRate;
        bool isActive;
        bool kycVerified;
    }
    
    struct Transaction {
        address from;
        address to;
        uint256 amount;
        uint256 timestamp;
        string reference;
        TransactionStatus status;
    }
    
    enum TransactionStatus {
        Pending,
        Processing,
        Completed,
        Failed,
        Reversed
    }
    
    mapping(address => Account) public accounts;
    mapping(bytes32 => Transaction) public transactions;
    mapping(address => bool) public sanctionsList;
    
    uint256 public totalDeposits;
    uint256 public totalLoans;
    uint256 public reserveRatio = 200; // 20% in basis points
    
    event AccountOpened(address indexed account, uint256 creditLimit);
    event Deposit(address indexed account, uint256 amount);
    event Withdrawal(address indexed account, uint256 amount);
    event Transfer(bytes32 indexed transactionId, address from, address to, uint256 amount);
    event LoanIssued(address indexed borrower, uint256 amount, uint256 rate);
    event LoanRepaid(address indexed borrower, uint256 amount);
    
    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(BANKER_ROLE, msg.sender);
        _grantRole(COMPLIANCE_ROLE, msg.sender);
    }
    
    /**
     * @dev Open a new banking account
     */
    function openAccount(
        address _account,
        uint256 _creditLimit,
        uint256 _interestRate
    ) external onlyRole(BANKER_ROLE) {
        require(!accounts[_account].isActive, "Account already exists");
        require(!sanctionsList[_account], "Address is sanctioned");
        
        accounts[_account] = Account({
            balance: 0,
            creditLimit: _creditLimit,
            interestRate: _interestRate,
            isActive: true,
            kycVerified: false
        });
        
        emit AccountOpened(_account, _creditLimit);
    }
    
    /**
     * @dev Verify KYC for an account
     */
    function verifyKYC(address _account) external onlyRole(COMPLIANCE_ROLE) {
        require(accounts[_account].isActive, "Account does not exist");
        accounts[_account].kycVerified = true;
    }
    
    /**
     * @dev Deposit funds into account
     */
    function deposit() external payable nonReentrant whenNotPaused {
        require(accounts[msg.sender].isActive, "Account not active");
        require(accounts[msg.sender].kycVerified, "KYC not verified");
        require(msg.value > 0, "Invalid amount");
        
        accounts[msg.sender].balance += msg.value;
        totalDeposits += msg.value;
        
        emit Deposit(msg.sender, msg.value);
    }
    
    /**
     * @dev Withdraw funds from account
     */
    function withdraw(uint256 _amount) external nonReentrant whenNotPaused {
        require(accounts[msg.sender].isActive, "Account not active");
        require(accounts[msg.sender].balance >= _amount, "Insufficient balance");
        require(_checkReserveRatio(_amount), "Reserve ratio violated");
        
        accounts[msg.sender].balance -= _amount;
        totalDeposits -= _amount;
        
        (bool success, ) = msg.sender.call{value: _amount}("");
        require(success, "Transfer failed");
        
        emit Withdrawal(msg.sender, _amount);
    }
    
    /**
     * @dev Transfer funds between accounts
     */
    function transfer(
        address _to,
        uint256 _amount,
        string memory _reference
    ) external nonReentrant whenNotPaused returns (bytes32) {
        require(accounts[msg.sender].isActive, "Sender account not active");
        require(accounts[_to].isActive, "Receiver account not active");
        require(accounts[msg.sender].balance >= _amount, "Insufficient balance");
        require(!sanctionsList[msg.sender] && !sanctionsList[_to], "Sanctioned address");
        
        bytes32 txId = keccak256(abi.encodePacked(msg.sender, _to, _amount, block.timestamp));
        
        transactions[txId] = Transaction({
            from: msg.sender,
            to: _to,
            amount: _amount,
            timestamp: block.timestamp,
            reference: _reference,
            status: TransactionStatus.Processing
        });
        
        // Execute transfer
        accounts[msg.sender].balance -= _amount;
        accounts[_to].balance += _amount;
        
        transactions[txId].status = TransactionStatus.Completed;
        
        emit Transfer(txId, msg.sender, _to, _amount);
        
        return txId;
    }
    
    /**
     * @dev Issue a loan to borrower
     */
    function issueLoan(
        address _borrower,
        uint256 _amount
    ) external onlyRole(BANKER_ROLE) nonReentrant whenNotPaused {
        require(accounts[_borrower].isActive, "Borrower account not active");
        require(accounts[_borrower].kycVerified, "KYC not verified");
        require(_amount <= accounts[_borrower].creditLimit, "Exceeds credit limit");
        require(_checkLiquidityForLoan(_amount), "Insufficient liquidity");
        
        accounts[_borrower].balance += _amount;
        totalLoans += _amount;
        
        emit LoanIssued(_borrower, _amount, accounts[_borrower].interestRate);
    }
    
    /**
     * @dev Repay a loan
     */
    function repayLoan(uint256 _amount) external nonReentrant whenNotPaused {
        require(accounts[msg.sender].isActive, "Account not active");
        require(_amount > 0, "Invalid amount");
        
        // Calculate interest
        uint256 interest = (_amount * accounts[msg.sender].interestRate) / 10000;
        uint256 totalRepayment = _amount + interest;
        
        require(accounts[msg.sender].balance >= totalRepayment, "Insufficient balance");
        
        accounts[msg.sender].balance -= totalRepayment;
        totalLoans -= _amount;
        
        emit LoanRepaid(msg.sender, _amount);
    }
    
    /**
     * @dev Add address to sanctions list
     */
    function addToSanctionsList(address _address) external onlyRole(COMPLIANCE_ROLE) {
        sanctionsList[_address] = true;
    }
    
    /**
     * @dev Remove address from sanctions list
     */
    function removeFromSanctionsList(address _address) external onlyRole(COMPLIANCE_ROLE) {
        sanctionsList[_address] = false;
    }
    
    /**
     * @dev Check if reserve ratio is maintained
     */
    function _checkReserveRatio(uint256 _withdrawalAmount) private view returns (bool) {
        uint256 remainingDeposits = totalDeposits - _withdrawalAmount;
        uint256 requiredReserves = (totalLoans * reserveRatio) / 1000;
        return remainingDeposits >= requiredReserves;
    }
    
    /**
     * @dev Check if sufficient liquidity exists for loan
     */
    function _checkLiquidityForLoan(uint256 _loanAmount) private view returns (bool) {
        uint256 availableLiquidity = address(this).balance;
        uint256 requiredReserves = ((totalLoans + _loanAmount) * reserveRatio) / 1000;
        return availableLiquidity >= requiredReserves;
    }
    
    /**
     * @dev Update reserve ratio
     */
    function updateReserveRatio(uint256 _newRatio) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_newRatio >= 100 && _newRatio <= 500, "Invalid ratio");
        reserveRatio = _newRatio;
    }
    
    /**
     * @dev Emergency pause
     */
    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }
    
    /**
     * @dev Unpause
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
    
    /**
     * @dev Get account details
     */
    function getAccountDetails(address _account) external view returns (
        uint256 balance,
        uint256 creditLimit,
        uint256 interestRate,
        bool isActive,
        bool kycVerified
    ) {
        Account memory acc = accounts[_account];
        return (
            acc.balance,
            acc.creditLimit,
            acc.interestRate,
            acc.isActive,
            acc.kycVerified
        );
    }
    
    /**
     * @dev Get transaction details
     */
    function getTransaction(bytes32 _txId) external view returns (
        address from,
        address to,
        uint256 amount,
        uint256 timestamp,
        string memory reference,
        TransactionStatus status
    ) {
        Transaction memory tx = transactions[_txId];
        return (
            tx.from,
            tx.to,
            tx.amount,
            tx.timestamp,
            tx.reference,
            tx.status
        );
    }
    
    /**
     * @dev Get protocol statistics
     */
    function getProtocolStats() external view returns (
        uint256 deposits,
        uint256 loans,
        uint256 liquidity,
        uint256 utilization
    ) {
        uint256 liquidityAmount = address(this).balance;
        uint256 utilizationRate = totalDeposits > 0 ? (totalLoans * 10000) / totalDeposits : 0;
        
        return (
            totalDeposits,
            totalLoans,
            liquidityAmount,
            utilizationRate
        );
    }
}