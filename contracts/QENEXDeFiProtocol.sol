// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

/**
 * @title QENEX DeFi Protocol
 * @notice Advanced decentralized finance protocol with lending, borrowing, and yield farming
 * @dev Enterprise-grade DeFi infrastructure with comprehensive risk management
 */
contract QENEXDeFiProtocol is ReentrancyGuard, AccessControl, Pausable {
    using SafeERC20 for IERC20;
    using SafeMath for uint256;

    // Roles
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");
    bytes32 public constant RISK_MANAGER_ROLE = keccak256("RISK_MANAGER_ROLE");
    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE");
    bytes32 public constant LIQUIDATOR_ROLE = keccak256("LIQUIDATOR_ROLE");

    // Market parameters
    uint256 public constant PRECISION = 1e18;
    uint256 public constant MAX_MARKETS = 50;
    uint256 public constant LIQUIDATION_BONUS = 105; // 5% bonus
    uint256 public constant CLOSE_FACTOR = 50; // Can liquidate 50% at a time
    
    // Market structure
    struct Market {
        IERC20 token;
        uint256 totalSupply;
        uint256 totalBorrows;
        uint256 supplyIndex;
        uint256 borrowIndex;
        uint256 supplyRate;
        uint256 borrowRate;
        uint256 collateralFactor; // % that can be borrowed against
        uint256 liquidationThreshold; // % at which liquidation occurs
        uint256 reserveFactor; // % of interest that goes to reserves
        uint256 lastUpdateTimestamp;
        bool isActive;
        bool canBeCollateral;
        AggregatorV3Interface priceFeed;
    }

    // User account structure
    struct UserAccount {
        mapping(address => uint256) suppliedAmounts;
        mapping(address => uint256) borrowedAmounts;
        mapping(address => bool) usedAsCollateral;
        uint256 totalCollateralValue;
        uint256 totalBorrowValue;
        uint256 healthFactor;
        uint256 lastUpdateTimestamp;
    }

    // Yield farming pool structure
    struct YieldPool {
        IERC20 stakingToken;
        IERC20 rewardToken;
        uint256 totalStaked;
        uint256 rewardRate;
        uint256 rewardPerTokenStored;
        uint256 lastUpdateTime;
        uint256 periodFinish;
        uint256 rewardsDuration;
        mapping(address => uint256) userRewardPerTokenPaid;
        mapping(address => uint256) rewards;
        mapping(address => uint256) balances;
    }

    // Flash loan structure
    struct FlashLoanData {
        address borrower;
        address asset;
        uint256 amount;
        uint256 fee;
        bytes params;
    }

    // State variables
    mapping(address => Market) public markets;
    mapping(address => UserAccount) public userAccounts;
    mapping(uint256 => YieldPool) public yieldPools;
    address[] public marketsList;
    uint256 public poolCounter;
    
    // Protocol parameters
    uint256 public flashLoanFee = 9; // 0.09%
    uint256 public constant FLASH_LOAN_FEE_PRECISION = 10000;
    address public treasury;
    uint256 public totalReserves;
    
    // Risk parameters
    uint256 public globalCollateralRatio = 150; // 150% minimum
    uint256 public maxLTV = 80; // 80% maximum loan-to-value
    
    // Events
    event MarketAdded(address indexed token, uint256 collateralFactor);
    event Supply(address indexed user, address indexed token, uint256 amount);
    event Withdraw(address indexed user, address indexed token, uint256 amount);
    event Borrow(address indexed user, address indexed token, uint256 amount);
    event Repay(address indexed user, address indexed token, uint256 amount);
    event Liquidation(
        address indexed liquidator,
        address indexed borrower,
        address indexed collateralAsset,
        uint256 debtAmount,
        uint256 collateralAmount
    );
    event FlashLoan(
        address indexed borrower,
        address indexed asset,
        uint256 amount,
        uint256 fee
    );
    event YieldPoolCreated(uint256 indexed poolId, address stakingToken, address rewardToken);
    event Staked(uint256 indexed poolId, address indexed user, uint256 amount);
    event Unstaked(uint256 indexed poolId, address indexed user, uint256 amount);
    event RewardPaid(uint256 indexed poolId, address indexed user, uint256 reward);
    event InterestAccrued(address indexed token, uint256 supplyInterest, uint256 borrowInterest);
    event ReservesWithdrawn(address indexed token, uint256 amount, address to);

    // Modifiers
    modifier marketExists(address token) {
        require(markets[token].isActive, "Market does not exist");
        _;
    }

    modifier updateReward(uint256 poolId, address account) {
        YieldPool storage pool = yieldPools[poolId];
        pool.rewardPerTokenStored = rewardPerToken(poolId);
        pool.lastUpdateTime = lastTimeRewardApplicable(poolId);
        if (account != address(0)) {
            pool.rewards[account] = earned(poolId, account);
            pool.userRewardPerTokenPaid[account] = pool.rewardPerTokenStored;
        }
        _;
    }

    constructor(address _treasury) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(GOVERNANCE_ROLE, msg.sender);
        _grantRole(RISK_MANAGER_ROLE, msg.sender);
        treasury = _treasury;
    }

    /**
     * @notice Add a new lending market
     */
    function addMarket(
        address token,
        uint256 collateralFactor,
        uint256 liquidationThreshold,
        uint256 reserveFactor,
        address priceFeed
    ) external onlyRole(GOVERNANCE_ROLE) {
        require(!markets[token].isActive, "Market already exists");
        require(marketsList.length < MAX_MARKETS, "Max markets reached");
        require(collateralFactor <= 90, "Collateral factor too high");
        require(liquidationThreshold > collateralFactor, "Invalid thresholds");

        markets[token] = Market({
            token: IERC20(token),
            totalSupply: 0,
            totalBorrows: 0,
            supplyIndex: PRECISION,
            borrowIndex: PRECISION,
            supplyRate: 0,
            borrowRate: 0,
            collateralFactor: collateralFactor,
            liquidationThreshold: liquidationThreshold,
            reserveFactor: reserveFactor,
            lastUpdateTimestamp: block.timestamp,
            isActive: true,
            canBeCollateral: collateralFactor > 0,
            priceFeed: AggregatorV3Interface(priceFeed)
        });

        marketsList.push(token);
        emit MarketAdded(token, collateralFactor);
    }

    /**
     * @notice Supply assets to the protocol
     */
    function supply(address token, uint256 amount) 
        external 
        nonReentrant 
        whenNotPaused 
        marketExists(token) 
    {
        require(amount > 0, "Amount must be greater than 0");
        
        Market storage market = markets[token];
        UserAccount storage account = userAccounts[msg.sender];
        
        // Update interest
        _accrueInterest(token);
        
        // Transfer tokens from user
        market.token.safeTransferFrom(msg.sender, address(this), amount);
        
        // Update user balance
        account.suppliedAmounts[token] = account.suppliedAmounts[token].add(amount);
        
        // Update market totals
        market.totalSupply = market.totalSupply.add(amount);
        
        // Enable as collateral by default if eligible
        if (market.canBeCollateral && !account.usedAsCollateral[token]) {
            account.usedAsCollateral[token] = true;
        }
        
        // Update user health factor
        _updateUserHealth(msg.sender);
        
        emit Supply(msg.sender, token, amount);
    }

    /**
     * @notice Withdraw supplied assets
     */
    function withdraw(address token, uint256 amount) 
        external 
        nonReentrant 
        whenNotPaused 
        marketExists(token) 
    {
        Market storage market = markets[token];
        UserAccount storage account = userAccounts[msg.sender];
        
        require(account.suppliedAmounts[token] >= amount, "Insufficient balance");
        
        // Update interest
        _accrueInterest(token);
        
        // Update user balance
        account.suppliedAmounts[token] = account.suppliedAmounts[token].sub(amount);
        
        // Check health factor after withdrawal
        _updateUserHealth(msg.sender);
        require(account.healthFactor >= PRECISION, "Withdrawal would cause undercollateralization");
        
        // Update market totals
        market.totalSupply = market.totalSupply.sub(amount);
        
        // Transfer tokens to user
        market.token.safeTransfer(msg.sender, amount);
        
        emit Withdraw(msg.sender, token, amount);
    }

    /**
     * @notice Borrow assets from the protocol
     */
    function borrow(address token, uint256 amount) 
        external 
        nonReentrant 
        whenNotPaused 
        marketExists(token) 
    {
        Market storage market = markets[token];
        UserAccount storage account = userAccounts[msg.sender];
        
        require(amount > 0, "Amount must be greater than 0");
        require(market.totalSupply.sub(market.totalBorrows) >= amount, "Insufficient liquidity");
        
        // Update interest
        _accrueInterest(token);
        
        // Update user balance
        account.borrowedAmounts[token] = account.borrowedAmounts[token].add(amount);
        
        // Update market totals
        market.totalBorrows = market.totalBorrows.add(amount);
        
        // Check health factor after borrowing
        _updateUserHealth(msg.sender);
        require(account.healthFactor >= PRECISION, "Insufficient collateral");
        
        // Transfer tokens to user
        market.token.safeTransfer(msg.sender, amount);
        
        emit Borrow(msg.sender, token, amount);
    }

    /**
     * @notice Repay borrowed assets
     */
    function repay(address token, uint256 amount) 
        external 
        nonReentrant 
        whenNotPaused 
        marketExists(token) 
    {
        Market storage market = markets[token];
        UserAccount storage account = userAccounts[msg.sender];
        
        uint256 borrowBalance = account.borrowedAmounts[token];
        require(borrowBalance > 0, "No debt to repay");
        
        // Update interest
        _accrueInterest(token);
        
        // Cap repayment at actual debt
        uint256 repayAmount = amount > borrowBalance ? borrowBalance : amount;
        
        // Transfer tokens from user
        market.token.safeTransferFrom(msg.sender, address(this), repayAmount);
        
        // Update user balance
        account.borrowedAmounts[token] = account.borrowedAmounts[token].sub(repayAmount);
        
        // Update market totals
        market.totalBorrows = market.totalBorrows.sub(repayAmount);
        
        // Update user health factor
        _updateUserHealth(msg.sender);
        
        emit Repay(msg.sender, token, repayAmount);
    }

    /**
     * @notice Liquidate an undercollateralized position
     */
    function liquidate(
        address borrower,
        address debtToken,
        address collateralToken,
        uint256 debtAmount
    ) external nonReentrant whenNotPaused {
        UserAccount storage account = userAccounts[borrower];
        
        // Update health factors
        _updateUserHealth(borrower);
        
        // Check if position is liquidatable
        require(account.healthFactor < PRECISION, "Position is healthy");
        
        // Calculate liquidation amounts
        uint256 maxLiquidation = account.borrowedAmounts[debtToken].mul(CLOSE_FACTOR).div(100);
        uint256 actualDebtAmount = debtAmount > maxLiquidation ? maxLiquidation : debtAmount;
        
        // Calculate collateral to seize (with bonus)
        uint256 collateralPrice = _getPrice(collateralToken);
        uint256 debtPrice = _getPrice(debtToken);
        uint256 collateralAmount = actualDebtAmount.mul(debtPrice).mul(LIQUIDATION_BONUS)
            .div(collateralPrice).div(100);
        
        require(account.suppliedAmounts[collateralToken] >= collateralAmount, 
                "Insufficient collateral");
        
        // Transfer debt from liquidator
        markets[debtToken].token.safeTransferFrom(msg.sender, address(this), actualDebtAmount);
        
        // Update borrower's debt
        account.borrowedAmounts[debtToken] = account.borrowedAmounts[debtToken].sub(actualDebtAmount);
        markets[debtToken].totalBorrows = markets[debtToken].totalBorrows.sub(actualDebtAmount);
        
        // Transfer collateral to liquidator
        account.suppliedAmounts[collateralToken] = account.suppliedAmounts[collateralToken]
            .sub(collateralAmount);
        markets[collateralToken].totalSupply = markets[collateralToken].totalSupply.sub(collateralAmount);
        markets[collateralToken].token.safeTransfer(msg.sender, collateralAmount);
        
        // Update health factors
        _updateUserHealth(borrower);
        
        emit Liquidation(msg.sender, borrower, collateralToken, actualDebtAmount, collateralAmount);
    }

    /**
     * @notice Flash loan implementation
     */
    function flashLoan(
        address asset,
        uint256 amount,
        bytes calldata params
    ) external nonReentrant whenNotPaused marketExists(asset) {
        Market storage market = markets[asset];
        uint256 balanceBefore = market.token.balanceOf(address(this));
        
        require(amount <= balanceBefore, "Insufficient liquidity");
        
        // Calculate fee
        uint256 fee = amount.mul(flashLoanFee).div(FLASH_LOAN_FEE_PRECISION);
        
        // Transfer funds to borrower
        market.token.safeTransfer(msg.sender, amount);
        
        // Execute borrower's code
        IFlashLoanReceiver(msg.sender).executeOperation(asset, amount, fee, params);
        
        // Check that funds are returned with fee
        uint256 balanceAfter = market.token.balanceOf(address(this));
        require(balanceAfter >= balanceBefore.add(fee), "Flash loan not repaid");
        
        // Add fee to reserves
        totalReserves = totalReserves.add(fee);
        
        emit FlashLoan(msg.sender, asset, amount, fee);
    }

    /**
     * @notice Create a yield farming pool
     */
    function createYieldPool(
        address stakingToken,
        address rewardToken,
        uint256 rewardRate,
        uint256 rewardsDuration
    ) external onlyRole(GOVERNANCE_ROLE) returns (uint256) {
        poolCounter++;
        
        YieldPool storage pool = yieldPools[poolCounter];
        pool.stakingToken = IERC20(stakingToken);
        pool.rewardToken = IERC20(rewardToken);
        pool.rewardRate = rewardRate;
        pool.rewardsDuration = rewardsDuration;
        pool.lastUpdateTime = block.timestamp;
        pool.periodFinish = block.timestamp.add(rewardsDuration);
        
        emit YieldPoolCreated(poolCounter, stakingToken, rewardToken);
        return poolCounter;
    }

    /**
     * @notice Stake tokens in yield pool
     */
    function stake(uint256 poolId, uint256 amount) 
        external 
        nonReentrant 
        whenNotPaused 
        updateReward(poolId, msg.sender) 
    {
        require(amount > 0, "Cannot stake 0");
        YieldPool storage pool = yieldPools[poolId];
        
        pool.balances[msg.sender] = pool.balances[msg.sender].add(amount);
        pool.totalStaked = pool.totalStaked.add(amount);
        
        pool.stakingToken.safeTransferFrom(msg.sender, address(this), amount);
        
        emit Staked(poolId, msg.sender, amount);
    }

    /**
     * @notice Unstake tokens from yield pool
     */
    function unstake(uint256 poolId, uint256 amount) 
        external 
        nonReentrant 
        whenNotPaused 
        updateReward(poolId, msg.sender) 
    {
        require(amount > 0, "Cannot withdraw 0");
        YieldPool storage pool = yieldPools[poolId];
        require(pool.balances[msg.sender] >= amount, "Insufficient balance");
        
        pool.balances[msg.sender] = pool.balances[msg.sender].sub(amount);
        pool.totalStaked = pool.totalStaked.sub(amount);
        
        pool.stakingToken.safeTransfer(msg.sender, amount);
        
        emit Unstaked(poolId, msg.sender, amount);
    }

    /**
     * @notice Claim yield farming rewards
     */
    function claimReward(uint256 poolId) 
        external 
        nonReentrant 
        updateReward(poolId, msg.sender) 
    {
        YieldPool storage pool = yieldPools[poolId];
        uint256 reward = pool.rewards[msg.sender];
        
        if (reward > 0) {
            pool.rewards[msg.sender] = 0;
            pool.rewardToken.safeTransfer(msg.sender, reward);
            emit RewardPaid(poolId, msg.sender, reward);
        }
    }

    // Internal functions

    function _accrueInterest(address token) internal {
        Market storage market = markets[token];
        
        uint256 timeDelta = block.timestamp.sub(market.lastUpdateTimestamp);
        if (timeDelta == 0) return;
        
        // Calculate utilization rate
        uint256 utilization = market.totalBorrows.mul(PRECISION)
            .div(market.totalSupply.add(1)); // Add 1 to prevent division by zero
        
        // Calculate interest rates (simplified model)
        market.borrowRate = utilization.mul(20).div(100); // Up to 20% APR at full utilization
        market.supplyRate = market.borrowRate.mul(utilization).div(PRECISION)
            .mul(100 - market.reserveFactor).div(100);
        
        // Calculate interest accrued
        uint256 borrowInterest = market.totalBorrows.mul(market.borrowRate)
            .mul(timeDelta).div(365 days).div(PRECISION);
        uint256 supplyInterest = market.totalSupply.mul(market.supplyRate)
            .mul(timeDelta).div(365 days).div(PRECISION);
        
        // Update totals
        market.totalBorrows = market.totalBorrows.add(borrowInterest);
        market.totalSupply = market.totalSupply.add(supplyInterest);
        
        // Update reserves
        uint256 reserveAmount = borrowInterest.mul(market.reserveFactor).div(100);
        totalReserves = totalReserves.add(reserveAmount);
        
        market.lastUpdateTimestamp = block.timestamp;
        
        emit InterestAccrued(token, supplyInterest, borrowInterest);
    }

    function _updateUserHealth(address user) internal {
        UserAccount storage account = userAccounts[user];
        
        uint256 totalCollateralValue = 0;
        uint256 totalBorrowValue = 0;
        
        // Calculate total collateral value
        for (uint256 i = 0; i < marketsList.length; i++) {
            address token = marketsList[i];
            if (account.usedAsCollateral[token] && account.suppliedAmounts[token] > 0) {
                uint256 price = _getPrice(token);
                uint256 collateralValue = account.suppliedAmounts[token].mul(price).div(PRECISION);
                totalCollateralValue = totalCollateralValue.add(
                    collateralValue.mul(markets[token].collateralFactor).div(100)
                );
            }
        }
        
        // Calculate total borrow value
        for (uint256 i = 0; i < marketsList.length; i++) {
            address token = marketsList[i];
            if (account.borrowedAmounts[token] > 0) {
                uint256 price = _getPrice(token);
                uint256 borrowValue = account.borrowedAmounts[token].mul(price).div(PRECISION);
                totalBorrowValue = totalBorrowValue.add(borrowValue);
            }
        }
        
        account.totalCollateralValue = totalCollateralValue;
        account.totalBorrowValue = totalBorrowValue;
        
        // Calculate health factor
        if (totalBorrowValue == 0) {
            account.healthFactor = type(uint256).max;
        } else {
            account.healthFactor = totalCollateralValue.mul(PRECISION).div(totalBorrowValue);
        }
        
        account.lastUpdateTimestamp = block.timestamp;
    }

    function _getPrice(address token) internal view returns (uint256) {
        Market memory market = markets[token];
        if (address(market.priceFeed) != address(0)) {
            (, int256 price, , , ) = market.priceFeed.latestRoundData();
            return uint256(price).mul(PRECISION).div(10**8); // Chainlink uses 8 decimals
        }
        return PRECISION; // Default to $1 if no price feed
    }

    // Yield farming helper functions

    function lastTimeRewardApplicable(uint256 poolId) public view returns (uint256) {
        YieldPool storage pool = yieldPools[poolId];
        return block.timestamp < pool.periodFinish ? block.timestamp : pool.periodFinish;
    }

    function rewardPerToken(uint256 poolId) public view returns (uint256) {
        YieldPool storage pool = yieldPools[poolId];
        if (pool.totalStaked == 0) {
            return pool.rewardPerTokenStored;
        }
        return pool.rewardPerTokenStored.add(
            lastTimeRewardApplicable(poolId)
                .sub(pool.lastUpdateTime)
                .mul(pool.rewardRate)
                .mul(PRECISION)
                .div(pool.totalStaked)
        );
    }

    function earned(uint256 poolId, address account) public view returns (uint256) {
        YieldPool storage pool = yieldPools[poolId];
        return pool.balances[account]
            .mul(rewardPerToken(poolId).sub(pool.userRewardPerTokenPaid[account]))
            .div(PRECISION)
            .add(pool.rewards[account]);
    }

    // Admin functions

    function withdrawReserves(address token, uint256 amount) 
        external 
        onlyRole(GOVERNANCE_ROLE) 
    {
        require(amount <= totalReserves, "Insufficient reserves");
        totalReserves = totalReserves.sub(amount);
        IERC20(token).safeTransfer(treasury, amount);
        emit ReservesWithdrawn(token, amount, treasury);
    }

    function updateRiskParameters(
        uint256 _globalCollateralRatio,
        uint256 _maxLTV
    ) external onlyRole(RISK_MANAGER_ROLE) {
        globalCollateralRatio = _globalCollateralRatio;
        maxLTV = _maxLTV;
    }

    function pause() external onlyRole(RISK_MANAGER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(RISK_MANAGER_ROLE) {
        _unpause();
    }

    // View functions

    function getUserAccountData(address user) external view returns (
        uint256 totalCollateralValue,
        uint256 totalBorrowValue,
        uint256 availableBorrow,
        uint256 healthFactor
    ) {
        UserAccount storage account = userAccounts[user];
        totalCollateralValue = account.totalCollateralValue;
        totalBorrowValue = account.totalBorrowValue;
        availableBorrow = totalCollateralValue.mul(maxLTV).div(100).sub(totalBorrowValue);
        healthFactor = account.healthFactor;
    }

    function getMarketData(address token) external view returns (
        uint256 totalSupply,
        uint256 totalBorrows,
        uint256 supplyRate,
        uint256 borrowRate,
        uint256 utilizationRate
    ) {
        Market storage market = markets[token];
        totalSupply = market.totalSupply;
        totalBorrows = market.totalBorrows;
        supplyRate = market.supplyRate;
        borrowRate = market.borrowRate;
        utilizationRate = totalBorrows.mul(PRECISION).div(totalSupply.add(1));
    }
}

// Flash loan receiver interface
interface IFlashLoanReceiver {
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 fee,
        bytes calldata params
    ) external;
}