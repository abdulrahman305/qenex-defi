// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
}

interface IKYCRegistry {
    function isVerified(address account) external view returns (bool);
    function getKYCLevel(address account) external view returns (uint256);
}

contract QXCInstitutionalGateway is AccessControl, ReentrancyGuard, Pausable {
    using SafeMath for uint256;
    
    bytes32 public constant INSTITUTION_ROLE = keccak256("INSTITUTION_ROLE");
    bytes32 public constant COMPLIANCE_ROLE = keccak256("COMPLIANCE_ROLE");
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");
    
    struct Institution {
        string name;
        address wallet;
        uint256 tier; // 1 = Basic, 2 = Professional, 3 = Prime
        uint256 dailyLimit;
        uint256 monthlyLimit;
        uint256 totalVolume;
        bool isActive;
        uint256 registeredAt;
        mapping(address => bool) authorizedTraders;
    }
    
    struct Order {
        uint256 id;
        address institution;
        OrderType orderType;
        uint256 amount;
        uint256 price;
        uint256 executedAmount;
        OrderStatus status;
        uint256 createdAt;
        uint256 executedAt;
    }
    
    struct CustodyAccount {
        uint256 qxcBalance;
        uint256 usdBalance;
        uint256 lockedQXC;
        uint256 lockedUSD;
        mapping(address => uint256) subAccountBalances;
    }
    
    enum OrderType { BUY, SELL }
    enum OrderStatus { PENDING, PARTIAL, FILLED, CANCELLED }
    
    mapping(address => Institution) public institutions;
    mapping(uint256 => Order) public orders;
    mapping(address => CustodyAccount) public custodyAccounts;
    mapping(address => uint256[]) public institutionOrders;
    
    uint256 public orderCounter;
    uint256 public totalCustodyQXC;
    uint256 public totalCustodyUSD;
    
    IERC20 public qxcToken;
    IKYCRegistry public kycRegistry;
    
    // Tier requirements
    uint256 public constant BASIC_TIER_MIN = 100000 * 10**18; // 100k QXC
    uint256 public constant PRO_TIER_MIN = 1000000 * 10**18; // 1M QXC
    uint256 public constant PRIME_TIER_MIN = 10000000 * 10**18; // 10M QXC
    
    // Fee structure (basis points)
    uint256 public constant BASIC_FEE = 50; // 0.5%
    uint256 public constant PRO_FEE = 30; // 0.3%
    uint256 public constant PRIME_FEE = 10; // 0.1%
    
    event InstitutionRegistered(address indexed institution, string name, uint256 tier);
    event OrderPlaced(uint256 indexed orderId, address indexed institution, OrderType orderType, uint256 amount);
    event OrderExecuted(uint256 indexed orderId, uint256 executedAmount, uint256 price);
    event OrderCancelled(uint256 indexed orderId);
    event Deposit(address indexed institution, uint256 amount, string asset);
    event Withdrawal(address indexed institution, uint256 amount, string asset);
    event TraderAuthorized(address indexed institution, address indexed trader);
    
    constructor(address _qxcToken, address _kycRegistry) {
        qxcToken = IERC20(_qxcToken);
        kycRegistry = IKYCRegistry(_kycRegistry);
        
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _setupRole(COMPLIANCE_ROLE, msg.sender);
        _setupRole(OPERATOR_ROLE, msg.sender);
    }
    
    modifier onlyInstitution() {
        require(institutions[msg.sender].isActive, "Not an active institution");
        _;
    }
    
    modifier onlyVerifiedKYC() {
        require(kycRegistry.isVerified(msg.sender), "KYC not verified");
        _;
    }
    
    function registerInstitution(
        string memory _name,
        address _wallet,
        uint256 _initialDeposit
    ) external onlyVerifiedKYC nonReentrant {
        require(!institutions[_wallet].isActive, "Already registered");
        require(_initialDeposit >= BASIC_TIER_MIN, "Insufficient initial deposit");
        
        uint256 tier = 1;
        if (_initialDeposit >= PRIME_TIER_MIN) {
            tier = 3;
        } else if (_initialDeposit >= PRO_TIER_MIN) {
            tier = 2;
        }
        
        Institution storage inst = institutions[_wallet];
        inst.name = _name;
        inst.wallet = _wallet;
        inst.tier = tier;
        inst.dailyLimit = tier * 1000000 * 10**18; // 1M, 2M, or 3M QXC
        inst.monthlyLimit = tier * 30000000 * 10**18; // 30M, 60M, or 90M QXC
        inst.isActive = true;
        inst.registeredAt = block.timestamp;
        
        require(qxcToken.transferFrom(msg.sender, address(this), _initialDeposit), "Transfer failed");
        
        custodyAccounts[_wallet].qxcBalance = _initialDeposit;
        totalCustodyQXC = totalCustodyQXC.add(_initialDeposit);
        
        _setupRole(INSTITUTION_ROLE, _wallet);
        
        emit InstitutionRegistered(_wallet, _name, tier);
        emit Deposit(_wallet, _initialDeposit, "QXC");
    }
    
    function authorizeTrader(address _trader) external onlyInstitution {
        institutions[msg.sender].authorizedTraders[_trader] = true;
        emit TraderAuthorized(msg.sender, _trader);
    }
    
    function revokeTrader(address _trader) external onlyInstitution {
        institutions[msg.sender].authorizedTraders[_trader] = false;
    }
    
    function depositQXC(uint256 _amount) external onlyInstitution nonReentrant {
        require(qxcToken.transferFrom(msg.sender, address(this), _amount), "Transfer failed");
        
        custodyAccounts[msg.sender].qxcBalance = custodyAccounts[msg.sender].qxcBalance.add(_amount);
        totalCustodyQXC = totalCustodyQXC.add(_amount);
        
        emit Deposit(msg.sender, _amount, "QXC");
    }
    
    function withdrawQXC(uint256 _amount) external onlyInstitution nonReentrant {
        CustodyAccount storage account = custodyAccounts[msg.sender];
        uint256 availableBalance = account.qxcBalance.sub(account.lockedQXC);
        require(availableBalance >= _amount, "Insufficient balance");
        
        account.qxcBalance = account.qxcBalance.sub(_amount);
        totalCustodyQXC = totalCustodyQXC.sub(_amount);
        
        require(qxcToken.transfer(msg.sender, _amount), "Transfer failed");
        
        emit Withdrawal(msg.sender, _amount, "QXC");
    }
    
    function placeOrder(
        OrderType _orderType,
        uint256 _amount,
        uint256 _price
    ) external onlyInstitution nonReentrant returns (uint256) {
        Institution storage inst = institutions[msg.sender];
        require(inst.totalVolume.add(_amount) <= inst.monthlyLimit, "Exceeds monthly limit");
        
        if (_orderType == OrderType.SELL) {
            CustodyAccount storage account = custodyAccounts[msg.sender];
            require(account.qxcBalance.sub(account.lockedQXC) >= _amount, "Insufficient QXC");
            account.lockedQXC = account.lockedQXC.add(_amount);
        }
        
        orderCounter++;
        Order storage order = orders[orderCounter];
        order.id = orderCounter;
        order.institution = msg.sender;
        order.orderType = _orderType;
        order.amount = _amount;
        order.price = _price;
        order.status = OrderStatus.PENDING;
        order.createdAt = block.timestamp;
        
        institutionOrders[msg.sender].push(orderCounter);
        
        emit OrderPlaced(orderCounter, msg.sender, _orderType, _amount);
        
        return orderCounter;
    }
    
    function executeOrder(uint256 _orderId, uint256 _executionAmount) 
        external 
        onlyRole(OPERATOR_ROLE) 
        nonReentrant 
    {
        Order storage order = orders[_orderId];
        require(order.status == OrderStatus.PENDING || order.status == OrderStatus.PARTIAL, "Invalid order status");
        require(_executionAmount <= order.amount.sub(order.executedAmount), "Exceeds order amount");
        
        order.executedAmount = order.executedAmount.add(_executionAmount);
        
        if (order.executedAmount == order.amount) {
            order.status = OrderStatus.FILLED;
            order.executedAt = block.timestamp;
        } else {
            order.status = OrderStatus.PARTIAL;
        }
        
        // Calculate fees
        uint256 fee = calculateFee(order.institution, _executionAmount);
        uint256 netAmount = _executionAmount.sub(fee);
        
        CustodyAccount storage account = custodyAccounts[order.institution];
        
        if (order.orderType == OrderType.SELL) {
            account.lockedQXC = account.lockedQXC.sub(_executionAmount);
            account.qxcBalance = account.qxcBalance.sub(_executionAmount);
            account.usdBalance = account.usdBalance.add(netAmount.mul(order.price).div(10**18));
        } else {
            // For buy orders, assume USD was already deposited
            account.qxcBalance = account.qxcBalance.add(netAmount);
        }
        
        institutions[order.institution].totalVolume = institutions[order.institution].totalVolume.add(_executionAmount);
        
        emit OrderExecuted(_orderId, _executionAmount, order.price);
    }
    
    function cancelOrder(uint256 _orderId) external nonReentrant {
        Order storage order = orders[_orderId];
        require(order.institution == msg.sender, "Not order owner");
        require(order.status == OrderStatus.PENDING || order.status == OrderStatus.PARTIAL, "Cannot cancel");
        
        if (order.orderType == OrderType.SELL) {
            uint256 remainingAmount = order.amount.sub(order.executedAmount);
            custodyAccounts[msg.sender].lockedQXC = custodyAccounts[msg.sender].lockedQXC.sub(remainingAmount);
        }
        
        order.status = OrderStatus.CANCELLED;
        
        emit OrderCancelled(_orderId);
    }
    
    function calculateFee(address _institution, uint256 _amount) public view returns (uint256) {
        uint256 tier = institutions[_institution].tier;
        uint256 feeRate = BASIC_FEE;
        
        if (tier == 2) {
            feeRate = PRO_FEE;
        } else if (tier == 3) {
            feeRate = PRIME_FEE;
        }
        
        return _amount.mul(feeRate).div(10000);
    }
    
    function upgradeTier() external onlyInstitution nonReentrant {
        Institution storage inst = institutions[msg.sender];
        uint256 balance = custodyAccounts[msg.sender].qxcBalance;
        
        uint256 newTier = inst.tier;
        if (balance >= PRIME_TIER_MIN && inst.tier < 3) {
            newTier = 3;
        } else if (balance >= PRO_TIER_MIN && inst.tier < 2) {
            newTier = 2;
        }
        
        require(newTier > inst.tier, "Cannot upgrade");
        
        inst.tier = newTier;
        inst.dailyLimit = newTier * 1000000 * 10**18;
        inst.monthlyLimit = newTier * 30000000 * 10**18;
    }
    
    function getInstitutionOrders(address _institution) external view returns (uint256[] memory) {
        return institutionOrders[_institution];
    }
    
    function getCustodyBalance(address _institution) external view returns (uint256 qxc, uint256 usd) {
        CustodyAccount storage account = custodyAccounts[_institution];
        return (account.qxcBalance, account.usdBalance);
    }
}

contract InstitutionalSettlement is AccessControl, ReentrancyGuard {
    using SafeMath for uint256;
    
    struct Settlement {
        uint256 id;
        address buyer;
        address seller;
        uint256 amount;
        uint256 price;
        SettlementStatus status;
        uint256 settlementTime;
        bytes32 txHash;
    }
    
    enum SettlementStatus { PENDING, SETTLING, COMPLETED, FAILED }
    
    mapping(uint256 => Settlement) public settlements;
    uint256 public settlementCounter;
    
    QXCInstitutionalGateway public gateway;
    
    event SettlementInitiated(uint256 indexed settlementId, address buyer, address seller);
    event SettlementCompleted(uint256 indexed settlementId);
    event SettlementFailed(uint256 indexed settlementId, string reason);
    
    constructor(address _gateway) {
        gateway = QXCInstitutionalGateway(_gateway);
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }
    
    function initiateSettlement(
        address _buyer,
        address _seller,
        uint256 _amount,
        uint256 _price
    ) external returns (uint256) {
        settlementCounter++;
        
        Settlement storage settlement = settlements[settlementCounter];
        settlement.id = settlementCounter;
        settlement.buyer = _buyer;
        settlement.seller = _seller;
        settlement.amount = _amount;
        settlement.price = _price;
        settlement.status = SettlementStatus.PENDING;
        settlement.settlementTime = block.timestamp + 3600; // T+1 hour for demo
        
        emit SettlementInitiated(settlementCounter, _buyer, _seller);
        
        return settlementCounter;
    }
    
    function executeSettlement(uint256 _settlementId) external nonReentrant {
        Settlement storage settlement = settlements[_settlementId];
        require(settlement.status == SettlementStatus.PENDING, "Invalid status");
        require(block.timestamp >= settlement.settlementTime, "Too early");
        
        settlement.status = SettlementStatus.SETTLING;
        
        // Actual settlement logic would go here
        // This would integrate with traditional banking rails
        
        settlement.status = SettlementStatus.COMPLETED;
        settlement.txHash = keccak256(abi.encodePacked(_settlementId, block.timestamp));
        
        emit SettlementCompleted(_settlementId);
    }
}

contract InstitutionalReporting is AccessControl {
    struct Report {
        uint256 id;
        address institution;
        ReportType reportType;
        uint256 startDate;
        uint256 endDate;
        string dataHash; // IPFS hash of the full report
        bool isGenerated;
    }
    
    enum ReportType { DAILY, MONTHLY, QUARTERLY, ANNUAL, REGULATORY }
    
    mapping(uint256 => Report) public reports;
    mapping(address => uint256[]) public institutionReports;
    uint256 public reportCounter;
    
    event ReportGenerated(uint256 indexed reportId, address institution, ReportType reportType);
    
    constructor() {
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }
    
    function generateReport(
        address _institution,
        ReportType _type,
        uint256 _startDate,
        uint256 _endDate
    ) external returns (uint256) {
        reportCounter++;
        
        Report storage report = reports[reportCounter];
        report.id = reportCounter;
        report.institution = _institution;
        report.reportType = _type;
        report.startDate = _startDate;
        report.endDate = _endDate;
        report.isGenerated = true;
        
        // Generate report data hash (would include actual data processing)
        report.dataHash = string(abi.encodePacked("QXC_REPORT_", uint2str(reportCounter)));
        
        institutionReports[_institution].push(reportCounter);
        
        emit ReportGenerated(reportCounter, _institution, _type);
        
        return reportCounter;
    }
    
    function uint2str(uint256 _i) internal pure returns (string memory) {
        if (_i == 0) return "0";
        uint256 j = _i;
        uint256 length;
        while (j != 0) {
            length++;
            j /= 10;
        }
        bytes memory bstr = new bytes(length);
        uint256 k = length;
        while (_i != 0) {
            k = k - 1;
            uint8 temp = (48 + uint8(_i - _i / 10 * 10));
            bytes1 b1 = bytes1(temp);
            bstr[k] = b1;
            _i /= 10;
        }
        return string(bstr);
    }
}