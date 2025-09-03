// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title QXC Unified Protocol
 * @notice Comprehensive solution for global financial inclusion
 * @dev Integrates identity, payments, lending, and yield generation
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
}

/**
 * @title Decentralized Identity System
 * @notice Self-sovereign identity with privacy preservation
 */
contract QXCIdentity {
    struct Identity {
        bytes32 didHash;  // Decentralized identifier
        uint256 trustScore;  // 0-1000 credit score
        uint256 verificationLevel;  // 0: none, 1: basic, 2: advanced, 3: institutional
        mapping(string => bytes32) credentials;  // Encrypted credentials
        mapping(address => bool) authorizedViewers;  // Who can view identity
        uint256 createdAt;
        uint256 lastUpdated;
    }
    
    mapping(address => Identity) public identities;
    mapping(bytes32 => address) public didToAddress;
    
    event IdentityCreated(address indexed user, bytes32 did);
    event TrustScoreUpdated(address indexed user, uint256 newScore);
    event CredentialAdded(address indexed user, string credentialType);
    
    function createIdentity(bytes32 _didHash) external {
        require(identities[msg.sender].createdAt == 0, "Identity exists");
        
        Identity storage id = identities[msg.sender];
        id.didHash = _didHash;
        id.trustScore = 100;  // Start with basic score
        id.verificationLevel = 0;
        id.createdAt = block.timestamp;
        id.lastUpdated = block.timestamp;
        
        didToAddress[_didHash] = msg.sender;
        emit IdentityCreated(msg.sender, _didHash);
    }
    
    function updateTrustScore(address user, uint256 score) external {
        // In production, only authorized oracles can update
        require(score <= 1000, "Invalid score");
        identities[user].trustScore = score;
        emit TrustScoreUpdated(user, score);
    }
    
    function getTrustScore(address user) external view returns (uint256) {
        return identities[user].trustScore;
    }
}

/**
 * @title Universal Payment System
 * @notice Instant, low-cost global transfers
 */
contract QXCPayments {
    IERC20 public qxcToken;
    
    struct Payment {
        address sender;
        address recipient;
        uint256 amount;
        string currency;  // Support multiple currencies
        uint256 exchangeRate;
        uint256 fee;
        uint256 timestamp;
        string memo;
    }
    
    mapping(bytes32 => Payment) public payments;
    mapping(address => uint256) public balances;
    
    uint256 public constant BASE_FEE = 1;  // 0.001 QXC base fee
    uint256 public totalVolume;
    uint256 public totalFees;
    
    event PaymentSent(
        bytes32 indexed paymentId,
        address indexed sender,
        address indexed recipient,
        uint256 amount
    );
    
    constructor(address _qxcToken) {
        qxcToken = IERC20(_qxcToken);
    }
    
    function sendPayment(
        address recipient,
        uint256 amount,
        string memory currency,
        string memory memo
    ) external returns (bytes32) {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Invalid amount");
        
        uint256 fee = calculateFee(amount);
        uint256 total = amount + fee;
        
        require(qxcToken.transferFrom(msg.sender, address(this), total), "Transfer failed");
        require(qxcToken.transfer(recipient, amount), "Transfer failed");
        
        bytes32 paymentId = keccak256(abi.encode(msg.sender, recipient, amount, block.timestamp));
        
        payments[paymentId] = Payment({
            sender: msg.sender,
            recipient: recipient,
            amount: amount,
            currency: currency,
            exchangeRate: 1,  // Would integrate oracle for real rates
            fee: fee,
            timestamp: block.timestamp,
            memo: memo
        });
        
        totalVolume += amount;
        totalFees += fee;
        
        emit PaymentSent(paymentId, msg.sender, recipient, amount);
        return paymentId;
    }
    
    function calculateFee(uint256 amount) public pure returns (uint256) {
        // Ultra-low fees: 0.001% or minimum 0.001 QXC
        uint256 calculatedFee = amount / 100000;
        return calculatedFee > BASE_FEE ? calculatedFee : BASE_FEE;
    }
}

/**
 * @title AI-Powered Lending Platform
 * @notice Undercollateralized loans based on trust scores
 */
contract QXCLending {
    IERC20 public qxcToken;
    QXCIdentity public identitySystem;
    
    struct Loan {
        address borrower;
        uint256 amount;
        uint256 interestRate;  // Annual rate in basis points
        uint256 duration;  // In seconds
        uint256 startTime;
        uint256 amountRepaid;
        bool isActive;
        uint256 collateral;  // Can be 0 for trusted users
    }
    
    mapping(uint256 => Loan) public loans;
    mapping(address => uint256[]) public userLoans;
    uint256 public loanCounter;
    
    uint256 public totalLent;
    uint256 public totalRepaid;
    uint256 public defaultRate;  // Basis points
    
    event LoanIssued(
        uint256 indexed loanId,
        address indexed borrower,
        uint256 amount,
        uint256 interestRate
    );
    event LoanRepaid(uint256 indexed loanId, uint256 amount);
    event LoanDefaulted(uint256 indexed loanId);
    
    constructor(address _qxcToken, address _identitySystem) {
        qxcToken = IERC20(_qxcToken);
        identitySystem = QXCIdentity(_identitySystem);
    }
    
    function requestLoan(uint256 amount, uint256 duration) external returns (uint256) {
        uint256 trustScore = identitySystem.getTrustScore(msg.sender);
        require(trustScore > 0, "No identity");
        
        // Calculate interest based on trust score
        uint256 interestRate = calculateInterestRate(trustScore);
        
        // Determine collateral requirement
        uint256 collateralRequired = calculateCollateral(amount, trustScore);
        
        if (collateralRequired > 0) {
            require(
                qxcToken.transferFrom(msg.sender, address(this), collateralRequired),
                "Collateral transfer failed"
            );
        }
        
        loanCounter++;
        loans[loanCounter] = Loan({
            borrower: msg.sender,
            amount: amount,
            interestRate: interestRate,
            duration: duration,
            startTime: block.timestamp,
            amountRepaid: 0,
            isActive: true,
            collateral: collateralRequired
        });
        
        userLoans[msg.sender].push(loanCounter);
        totalLent += amount;
        
        require(qxcToken.transfer(msg.sender, amount), "Loan transfer failed");
        
        emit LoanIssued(loanCounter, msg.sender, amount, interestRate);
        return loanCounter;
    }
    
    function repayLoan(uint256 loanId, uint256 amount) external {
        Loan storage loan = loans[loanId];
        require(loan.isActive, "Loan not active");
        require(msg.sender == loan.borrower, "Not borrower");
        
        uint256 totalDue = calculateTotalDue(loanId);
        uint256 repayAmount = amount > totalDue - loan.amountRepaid ? 
                              totalDue - loan.amountRepaid : amount;
        
        require(
            qxcToken.transferFrom(msg.sender, address(this), repayAmount),
            "Repayment failed"
        );
        
        loan.amountRepaid += repayAmount;
        totalRepaid += repayAmount;
        
        if (loan.amountRepaid >= totalDue) {
            loan.isActive = false;
            
            // Return collateral if any
            if (loan.collateral > 0) {
                qxcToken.transfer(msg.sender, loan.collateral);
            }
            
            // Improve trust score for successful repayment
            identitySystem.updateTrustScore(
                msg.sender,
                identitySystem.getTrustScore(msg.sender) + 10
            );
        }
        
        emit LoanRepaid(loanId, repayAmount);
    }
    
    function calculateInterestRate(uint256 trustScore) public pure returns (uint256) {
        // Higher trust = lower interest
        // 950-1000: 5% APR
        // 800-949: 10% APR
        // 600-799: 15% APR
        // 400-599: 20% APR
        // Below 400: 25% APR
        
        if (trustScore >= 950) return 500;  // 5%
        if (trustScore >= 800) return 1000; // 10%
        if (trustScore >= 600) return 1500; // 15%
        if (trustScore >= 400) return 2000; // 20%
        return 2500; // 25%
    }
    
    function calculateCollateral(uint256 amount, uint256 trustScore) public pure returns (uint256) {
        // Higher trust = lower collateral
        if (trustScore >= 900) return 0;  // No collateral
        if (trustScore >= 700) return amount * 20 / 100;  // 20%
        if (trustScore >= 500) return amount * 50 / 100;  // 50%
        return amount;  // 100% collateral
    }
    
    function calculateTotalDue(uint256 loanId) public view returns (uint256) {
        Loan memory loan = loans[loanId];
        uint256 timeElapsed = block.timestamp - loan.startTime;
        uint256 interest = loan.amount * loan.interestRate * timeElapsed / (365 days * 10000);
        return loan.amount + interest;
    }
}

/**
 * @title Supply Chain Finance
 * @notice Real-time invoice factoring and trade finance
 */
contract QXCSupplyChain {
    IERC20 public qxcToken;
    
    struct Invoice {
        address supplier;
        address buyer;
        uint256 amount;
        uint256 dueDate;
        bool isPaid;
        bool isFactored;
        address factorProvider;
        uint256 advanceRate;  // Percentage advanced immediately
    }
    
    mapping(bytes32 => Invoice) public invoices;
    mapping(address => bytes32[]) public supplierInvoices;
    mapping(address => bytes32[]) public buyerInvoices;
    
    event InvoiceCreated(bytes32 indexed invoiceId, address supplier, address buyer, uint256 amount);
    event InvoiceFactored(bytes32 indexed invoiceId, address factor, uint256 advanceAmount);
    event InvoicePaid(bytes32 indexed invoiceId);
    
    constructor(address _qxcToken) {
        qxcToken = IERC20(_qxcToken);
    }
    
    function createInvoice(
        address buyer,
        uint256 amount,
        uint256 dueDate
    ) external returns (bytes32) {
        bytes32 invoiceId = keccak256(abi.encode(msg.sender, buyer, amount, block.timestamp));
        
        invoices[invoiceId] = Invoice({
            supplier: msg.sender,
            buyer: buyer,
            amount: amount,
            dueDate: dueDate,
            isPaid: false,
            isFactored: false,
            factorProvider: address(0),
            advanceRate: 0
        });
        
        supplierInvoices[msg.sender].push(invoiceId);
        buyerInvoices[buyer].push(invoiceId);
        
        emit InvoiceCreated(invoiceId, msg.sender, buyer, amount);
        return invoiceId;
    }
    
    function factorInvoice(bytes32 invoiceId, uint256 advanceRate) external {
        Invoice storage invoice = invoices[invoiceId];
        require(!invoice.isPaid, "Already paid");
        require(!invoice.isFactored, "Already factored");
        require(advanceRate <= 95, "Advance rate too high");
        
        uint256 advanceAmount = invoice.amount * advanceRate / 100;
        uint256 fee = invoice.amount * 2 / 100;  // 2% factoring fee
        uint256 payment = advanceAmount - fee;
        
        require(qxcToken.transfer(invoice.supplier, payment), "Payment failed");
        
        invoice.isFactored = true;
        invoice.factorProvider = msg.sender;
        invoice.advanceRate = advanceRate;
        
        emit InvoiceFactored(invoiceId, msg.sender, advanceAmount);
    }
    
    function payInvoice(bytes32 invoiceId) external {
        Invoice storage invoice = invoices[invoiceId];
        require(msg.sender == invoice.buyer, "Not buyer");
        require(!invoice.isPaid, "Already paid");
        
        address payTo = invoice.isFactored ? invoice.factorProvider : invoice.supplier;
        uint256 payAmount = invoice.amount;
        
        if (invoice.isFactored) {
            // If factored, pay the remaining amount to supplier
            uint256 remaining = invoice.amount * (100 - invoice.advanceRate) / 100;
            require(qxcToken.transferFrom(msg.sender, invoice.supplier, remaining), "Transfer failed");
            payAmount -= remaining;
        }
        
        require(qxcToken.transferFrom(msg.sender, payTo, payAmount), "Payment failed");
        invoice.isPaid = true;
        
        emit InvoicePaid(invoiceId);
    }
}

/**
 * @title Yield Optimization Engine
 * @notice Automated strategies for maximum returns
 */
contract QXCYieldOptimizer {
    IERC20 public qxcToken;
    
    struct Strategy {
        string name;
        uint256 targetAPY;
        uint256 riskLevel;  // 1-10
        uint256 minDeposit;
        uint256 totalDeposits;
        bool isActive;
    }
    
    struct UserPosition {
        uint256 strategyId;
        uint256 amount;
        uint256 startTime;
        uint256 lastHarvest;
        uint256 earned;
    }
    
    mapping(uint256 => Strategy) public strategies;
    mapping(address => UserPosition[]) public userPositions;
    uint256 public strategyCounter;
    
    event Deposited(address indexed user, uint256 strategyId, uint256 amount);
    event Withdrawn(address indexed user, uint256 strategyId, uint256 amount);
    event Harvested(address indexed user, uint256 earned);
    
    constructor(address _qxcToken) {
        qxcToken = IERC20(_qxcToken);
        _initializeStrategies();
    }
    
    function _initializeStrategies() internal {
        // Conservative strategy
        strategies[1] = Strategy({
            name: "Stable Yield",
            targetAPY: 800,  // 8%
            riskLevel: 2,
            minDeposit: 1e18,  // 1 QXC
            totalDeposits: 0,
            isActive: true
        });
        
        // Balanced strategy
        strategies[2] = Strategy({
            name: "Balanced Growth",
            targetAPY: 1500,  // 15%
            riskLevel: 5,
            minDeposit: 10e18,  // 10 QXC
            totalDeposits: 0,
            isActive: true
        });
        
        // Aggressive strategy
        strategies[3] = Strategy({
            name: "High Yield",
            targetAPY: 3000,  // 30%
            riskLevel: 8,
            minDeposit: 100e18,  // 100 QXC
            totalDeposits: 0,
            isActive: true
        });
        
        strategyCounter = 3;
    }
    
    function deposit(uint256 strategyId, uint256 amount) external {
        Strategy storage strategy = strategies[strategyId];
        require(strategy.isActive, "Strategy not active");
        require(amount >= strategy.minDeposit, "Below minimum");
        
        require(qxcToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        
        userPositions[msg.sender].push(UserPosition({
            strategyId: strategyId,
            amount: amount,
            startTime: block.timestamp,
            lastHarvest: block.timestamp,
            earned: 0
        }));
        
        strategy.totalDeposits += amount;
        
        emit Deposited(msg.sender, strategyId, amount);
    }
    
    function withdraw(uint256 positionIndex) external {
        require(positionIndex < userPositions[msg.sender].length, "Invalid position");
        
        UserPosition storage position = userPositions[msg.sender][positionIndex];
        uint256 earned = calculateEarnings(msg.sender, positionIndex);
        uint256 total = position.amount + earned;
        
        strategies[position.strategyId].totalDeposits -= position.amount;
        
        // Remove position
        userPositions[msg.sender][positionIndex] = 
            userPositions[msg.sender][userPositions[msg.sender].length - 1];
        userPositions[msg.sender].pop();
        
        require(qxcToken.transfer(msg.sender, total), "Transfer failed");
        
        emit Withdrawn(msg.sender, position.strategyId, total);
    }
    
    function harvest(uint256 positionIndex) external {
        require(positionIndex < userPositions[msg.sender].length, "Invalid position");
        
        UserPosition storage position = userPositions[msg.sender][positionIndex];
        uint256 earned = calculateEarnings(msg.sender, positionIndex);
        
        position.earned += earned;
        position.lastHarvest = block.timestamp;
        
        require(qxcToken.transfer(msg.sender, earned), "Transfer failed");
        
        emit Harvested(msg.sender, earned);
    }
    
    function calculateEarnings(address user, uint256 positionIndex) public view returns (uint256) {
        UserPosition memory position = userPositions[user][positionIndex];
        Strategy memory strategy = strategies[position.strategyId];
        
        uint256 timeElapsed = block.timestamp - position.lastHarvest;
        uint256 earnings = position.amount * strategy.targetAPY * timeElapsed / (365 days * 10000);
        
        return earnings;
    }
}

/**
 * @title Unified Protocol Controller
 * @notice Main entry point for all protocol interactions
 */
contract QXCUnifiedProtocol {
    QXCIdentity public identitySystem;
    QXCPayments public paymentSystem;
    QXCLending public lendingSystem;
    QXCSupplyChain public supplyChainSystem;
    QXCYieldOptimizer public yieldSystem;
    
    address public governance;
    
    event SystemDeployed(address indexed deployer);
    
    constructor(address _qxcToken) {
        governance = msg.sender;
        
        // Deploy all subsystems
        identitySystem = new QXCIdentity();
        paymentSystem = new QXCPayments(_qxcToken);
        lendingSystem = new QXCLending(_qxcToken, address(identitySystem));
        supplyChainSystem = new QXCSupplyChain(_qxcToken);
        yieldSystem = new QXCYieldOptimizer(_qxcToken);
        
        emit SystemDeployed(msg.sender);
    }
    
    // Unified interface for all protocol functions
    function getSystemAddresses() external view returns (
        address identity,
        address payments,
        address lending,
        address supplyChain,
        address yield
    ) {
        return (
            address(identitySystem),
            address(paymentSystem),
            address(lendingSystem),
            address(supplyChainSystem),
            address(yieldSystem)
        );
    }
}