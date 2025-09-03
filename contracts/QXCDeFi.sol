// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title QXC DeFi Lending & Borrowing Protocol
 * @dev Decentralized lending platform for QXC tokens
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract QXCDeFi {
    IERC20 public qxcToken;
    
    struct Deposit {
        uint256 amount;
        uint256 timestamp;
        uint256 interestEarned;
    }
    
    struct Loan {
        uint256 amount;
        uint256 collateral;
        uint256 timestamp;
        uint256 interestRate;
        bool active;
    }
    
    mapping(address => Deposit) public deposits;
    mapping(address => Loan) public loans;
    
    uint256 public totalDeposited;
    uint256 public totalBorrowed;
    uint256 public depositAPY = 8; // 8% APY for deposits
    uint256 public borrowAPR = 12; // 12% APR for loans
    uint256 public collateralRatio = 150; // 150% collateralization required
    
    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount, uint256 interest);
    event Borrowed(address indexed user, uint256 amount, uint256 collateral);
    event LoanRepaid(address indexed user, uint256 amount, uint256 interest);
    event Liquidated(address indexed user, uint256 collateral);
    
    constructor(address _qxcToken) {
        qxcToken = IERC20(_qxcToken);
    }
    
    /**
     * @dev Deposit QXC to earn interest
     */
    function deposit(uint256 amount) external {
        require(amount > 0, "Amount must be positive");
        require(qxcToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        
        // Calculate pending interest before updating deposit
        if (deposits[msg.sender].amount > 0) {
            uint256 interest = calculateDepositInterest(msg.sender);
            deposits[msg.sender].interestEarned += interest;
        }
        
        deposits[msg.sender].amount += amount;
        deposits[msg.sender].timestamp = block.timestamp;
        totalDeposited += amount;
        
        emit Deposited(msg.sender, amount);
    }
    
    /**
     * @dev Withdraw deposited QXC plus interest
     */
    function withdraw(uint256 amount) external {
        Deposit storage userDeposit = deposits[msg.sender];
        require(userDeposit.amount >= amount, "Insufficient balance");
        
        uint256 interest = calculateDepositInterest(msg.sender) + userDeposit.interestEarned;
        userDeposit.amount -= amount;
        userDeposit.timestamp = block.timestamp;
        userDeposit.interestEarned = 0;
        totalDeposited -= amount;
        
        uint256 totalAmount = amount + interest;
        require(qxcToken.transfer(msg.sender, totalAmount), "Transfer failed");
        
        emit Withdrawn(msg.sender, amount, interest);
    }
    
    /**
     * @dev Borrow QXC against collateral
     */
    function borrow(uint256 amount) external payable {
        require(amount > 0, "Amount must be positive");
        require(!loans[msg.sender].active, "Existing loan active");
        
        // Calculate required collateral in ETH
        uint256 requiredCollateral = (amount * collateralRatio) / 100;
        require(msg.value >= requiredCollateral / 1e15, "Insufficient collateral"); // Simplified price
        
        loans[msg.sender] = Loan({
            amount: amount,
            collateral: msg.value,
            timestamp: block.timestamp,
            interestRate: borrowAPR,
            active: true
        });
        
        totalBorrowed += amount;
        require(qxcToken.transfer(msg.sender, amount), "Transfer failed");
        
        emit Borrowed(msg.sender, amount, msg.value);
    }
    
    /**
     * @dev Repay loan with interest
     */
    function repayLoan() external {
        Loan storage userLoan = loans[msg.sender];
        require(userLoan.active, "No active loan");
        
        uint256 interest = calculateLoanInterest(msg.sender);
        uint256 totalRepayment = userLoan.amount + interest;
        
        require(qxcToken.transferFrom(msg.sender, address(this), totalRepayment), "Transfer failed");
        
        // Return collateral
        uint256 collateral = userLoan.collateral;
        userLoan.active = false;
        userLoan.amount = 0;
        userLoan.collateral = 0;
        totalBorrowed -= userLoan.amount;
        
        payable(msg.sender).transfer(collateral);
        
        emit LoanRepaid(msg.sender, userLoan.amount, interest);
    }
    
    /**
     * @dev Liquidate undercollateralized loan
     */
    function liquidate(address borrower) external {
        Loan storage userLoan = loans[borrower];
        require(userLoan.active, "No active loan");
        
        // Check if loan is undercollateralized (simplified)
        uint256 collateralValue = userLoan.collateral * 1e15; // Simplified ETH price
        uint256 loanValue = userLoan.amount;
        
        require(collateralValue < (loanValue * 120) / 100, "Not liquidatable");
        
        // Liquidator repays the loan and gets collateral at discount
        require(qxcToken.transferFrom(msg.sender, address(this), userLoan.amount), "Transfer failed");
        
        uint256 collateral = userLoan.collateral;
        userLoan.active = false;
        userLoan.amount = 0;
        userLoan.collateral = 0;
        totalBorrowed -= userLoan.amount;
        
        // Give 90% of collateral to liquidator (10% penalty)
        payable(msg.sender).transfer((collateral * 90) / 100);
        
        emit Liquidated(borrower, collateral);
    }
    
    /**
     * @dev Calculate deposit interest
     */
    function calculateDepositInterest(address user) public view returns (uint256) {
        Deposit memory userDeposit = deposits[user];
        if (userDeposit.amount == 0) return 0;
        
        uint256 timeElapsed = block.timestamp - userDeposit.timestamp;
        uint256 annualInterest = (userDeposit.amount * depositAPY) / 100;
        return (annualInterest * timeElapsed) / 365 days;
    }
    
    /**
     * @dev Calculate loan interest
     */
    function calculateLoanInterest(address user) public view returns (uint256) {
        Loan memory userLoan = loans[user];
        if (!userLoan.active) return 0;
        
        uint256 timeElapsed = block.timestamp - userLoan.timestamp;
        uint256 annualInterest = (userLoan.amount * userLoan.interestRate) / 100;
        return (annualInterest * timeElapsed) / 365 days;
    }
    
    /**
     * @dev Get protocol statistics
     */
    function getProtocolStats() external view returns (
        uint256 _totalDeposited,
        uint256 _totalBorrowed,
        uint256 _depositAPY,
        uint256 _borrowAPR,
        uint256 utilization
    ) {
        _totalDeposited = totalDeposited;
        _totalBorrowed = totalBorrowed;
        _depositAPY = depositAPY;
        _borrowAPR = borrowAPR;
        utilization = totalDeposited > 0 ? (totalBorrowed * 100) / totalDeposited : 0;
    }
}