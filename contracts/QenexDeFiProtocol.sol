// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";

/**
 * @title QENEX DeFi Protocol
 * @dev Complete DeFi ecosystem with lending, borrowing, staking, and liquidity pools
 */
contract QenexDeFiProtocol is Ownable, ReentrancyGuard {
    using SafeMath for uint256;
    
    // ============== Data Structures ==============
    
    struct Market {
        address asset;
        uint256 totalSupply;
        uint256 totalBorrow;
        uint256 supplyRate;
        uint256 borrowRate;
        uint256 collateralFactor;
        uint256 reserveFactor;
        uint256 lastUpdateBlock;
        bool isActive;
    }
    
    struct UserAccount {
        mapping(address => uint256) supplied;
        mapping(address => uint256) borrowed;
        uint256 totalCollateralValue;
        uint256 totalBorrowValue;
        uint256 healthFactor;
        uint256 lastActivityBlock;
    }
    
    struct LiquidityPool {
        address tokenA;
        address tokenB;
        uint256 reserveA;
        uint256 reserveB;
        uint256 totalLiquidity;
        uint256 feeRate;
        mapping(address => uint256) liquidityProviders;
    }
    
    struct StakingPool {
        address stakingToken;
        address rewardToken;
        uint256 totalStaked;
        uint256 rewardRate;
        uint256 lastRewardBlock;
        uint256 accRewardPerShare;
        mapping(address => uint256) userStakes;
        mapping(address => uint256) userRewardDebt;
    }
    
    struct FlashLoanRequest {
        address asset;
        uint256 amount;
        address receiver;
        bytes params;
        uint256 fee;
    }
    
    // ============== State Variables ==============
    
    mapping(address => Market) public markets;
    mapping(address => UserAccount) public userAccounts;
    mapping(bytes32 => LiquidityPool) public liquidityPools;
    mapping(address => StakingPool) public stakingPools;
    
    address[] public marketsList;
    bytes32[] public poolsList;
    address[] public stakingPoolsList;
    
    uint256 public constant PRECISION = 1e18;
    uint256 public constant MAX_MARKETS = 100;
    uint256 public constant MIN_HEALTH_FACTOR = 1.2e18;
    uint256 public constant LIQUIDATION_BONUS = 1.05e18;
    uint256 public constant FLASH_LOAN_FEE = 9; // 0.09%
    
    address public treasuryAddress;
    address public oracleAddress;
    bool public protocolPaused;
    
    // ============== Events ==============
    
    event MarketAdded(address indexed asset, uint256 collateralFactor);
    event Supply(address indexed user, address indexed asset, uint256 amount);
    event Withdraw(address indexed user, address indexed asset, uint256 amount);
    event Borrow(address indexed user, address indexed asset, uint256 amount);
    event Repay(address indexed user, address indexed asset, uint256 amount);
    event Liquidation(address indexed liquidator, address indexed borrower, address asset, uint256 amount);
    event PoolCreated(bytes32 indexed poolId, address tokenA, address tokenB);
    event LiquidityAdded(bytes32 indexed poolId, address indexed provider, uint256 amountA, uint256 amountB);
    event LiquidityRemoved(bytes32 indexed poolId, address indexed provider, uint256 liquidity);
    event Swap(bytes32 indexed poolId, address indexed trader, address tokenIn, uint256 amountIn, uint256 amountOut);
    event Stake(address indexed pool, address indexed user, uint256 amount);
    event Unstake(address indexed pool, address indexed user, uint256 amount);
    event RewardClaimed(address indexed pool, address indexed user, uint256 reward);
    event FlashLoan(address indexed receiver, address indexed asset, uint256 amount, uint256 fee);
    
    // ============== Modifiers ==============
    
    modifier whenNotPaused() {
        require(!protocolPaused, "Protocol is paused");
        _;
    }
    
    modifier marketExists(address asset) {
        require(markets[asset].isActive, "Market does not exist");
        _;
    }
    
    modifier onlyOracle() {
        require(msg.sender == oracleAddress, "Only oracle");
        _;
    }
    
    // ============== Constructor ==============
    
    constructor(address _treasury, address _oracle) {
        treasuryAddress = _treasury;
        oracleAddress = _oracle;
    }
    
    // ============== Lending & Borrowing Functions ==============
    
    function addMarket(
        address asset,
        uint256 collateralFactor,
        uint256 reserveFactor
    ) external onlyOwner {
        require(marketsList.length < MAX_MARKETS, "Max markets reached");
        require(!markets[asset].isActive, "Market already exists");
        require(collateralFactor <= PRECISION, "Invalid collateral factor");
        
        markets[asset] = Market({
            asset: asset,
            totalSupply: 0,
            totalBorrow: 0,
            supplyRate: 5e16, // 5% APR
            borrowRate: 10e16, // 10% APR
            collateralFactor: collateralFactor,
            reserveFactor: reserveFactor,
            lastUpdateBlock: block.number,
            isActive: true
        });
        
        marketsList.push(asset);
        emit MarketAdded(asset, collateralFactor);
    }
    
    function supply(address asset, uint256 amount) 
        external 
        whenNotPaused 
        marketExists(asset) 
        nonReentrant 
    {
        require(amount > 0, "Amount must be greater than 0");
        
        Market storage market = markets[asset];
        UserAccount storage account = userAccounts[msg.sender];
        
        // Transfer tokens from user
        IERC20(asset).transferFrom(msg.sender, address(this), amount);
        
        // Update market state
        _accrueInterest(asset);
        
        // Update user balance
        account.supplied[asset] = account.supplied[asset].add(amount);
        market.totalSupply = market.totalSupply.add(amount);
        
        // Update collateral value
        _updateUserCollateral(msg.sender);
        
        emit Supply(msg.sender, asset, amount);
    }
    
    function withdraw(address asset, uint256 amount) 
        external 
        whenNotPaused 
        marketExists(asset) 
        nonReentrant 
    {
        Market storage market = markets[asset];
        UserAccount storage account = userAccounts[msg.sender];
        
        require(account.supplied[asset] >= amount, "Insufficient balance");
        
        // Update market state
        _accrueInterest(asset);
        
        // Check if withdrawal maintains health factor
        account.supplied[asset] = account.supplied[asset].sub(amount);
        _updateUserCollateral(msg.sender);
        
        require(_checkHealthFactor(msg.sender), "Withdrawal would cause undercollateralization");
        
        // Update market totals
        market.totalSupply = market.totalSupply.sub(amount);
        
        // Transfer tokens to user
        IERC20(asset).transfer(msg.sender, amount);
        
        emit Withdraw(msg.sender, asset, amount);
    }
    
    function borrow(address asset, uint256 amount) 
        external 
        whenNotPaused 
        marketExists(asset) 
        nonReentrant 
    {
        Market storage market = markets[asset];
        UserAccount storage account = userAccounts[msg.sender];
        
        require(market.totalSupply >= market.totalBorrow.add(amount), "Insufficient liquidity");
        
        // Update market state
        _accrueInterest(asset);
        
        // Update user borrow
        account.borrowed[asset] = account.borrowed[asset].add(amount);
        market.totalBorrow = market.totalBorrow.add(amount);
        
        // Check health factor
        _updateUserCollateral(msg.sender);
        require(_checkHealthFactor(msg.sender), "Insufficient collateral");
        
        // Transfer tokens to user
        IERC20(asset).transfer(msg.sender, amount);
        
        emit Borrow(msg.sender, asset, amount);
    }
    
    function repay(address asset, uint256 amount) 
        external 
        whenNotPaused 
        marketExists(asset) 
        nonReentrant 
    {
        Market storage market = markets[asset];
        UserAccount storage account = userAccounts[msg.sender];
        
        uint256 borrowBalance = account.borrowed[asset];
        require(borrowBalance > 0, "No borrow to repay");
        
        uint256 repayAmount = amount > borrowBalance ? borrowBalance : amount;
        
        // Transfer tokens from user
        IERC20(asset).transferFrom(msg.sender, address(this), repayAmount);
        
        // Update market state
        _accrueInterest(asset);
        
        // Update balances
        account.borrowed[asset] = account.borrowed[asset].sub(repayAmount);
        market.totalBorrow = market.totalBorrow.sub(repayAmount);
        
        // Update collateral
        _updateUserCollateral(msg.sender);
        
        emit Repay(msg.sender, asset, repayAmount);
    }
    
    function liquidate(address borrower, address asset, uint256 amount) 
        external 
        whenNotPaused 
        marketExists(asset) 
        nonReentrant 
    {
        UserAccount storage borrowerAccount = userAccounts[borrower];
        
        // Check if borrower is undercollateralized
        _updateUserCollateral(borrower);
        require(borrowerAccount.healthFactor < MIN_HEALTH_FACTOR, "Borrower not liquidatable");
        
        uint256 borrowBalance = borrowerAccount.borrowed[asset];
        require(borrowBalance > 0, "No borrow to liquidate");
        
        uint256 liquidateAmount = amount > borrowBalance ? borrowBalance : amount;
        
        // Transfer repay amount from liquidator
        IERC20(asset).transferFrom(msg.sender, address(this), liquidateAmount);
        
        // Calculate collateral to seize (with bonus)
        uint256 seizeAmount = liquidateAmount.mul(LIQUIDATION_BONUS).div(PRECISION);
        
        // Transfer seized collateral to liquidator
        // (Implementation would need to determine which collateral to seize)
        
        // Update borrower's debt
        borrowerAccount.borrowed[asset] = borrowerAccount.borrowed[asset].sub(liquidateAmount);
        markets[asset].totalBorrow = markets[asset].totalBorrow.sub(liquidateAmount);
        
        emit Liquidation(msg.sender, borrower, asset, liquidateAmount);
    }
    
    // ============== AMM & Liquidity Pool Functions ==============
    
    function createPool(address tokenA, address tokenB, uint256 feeRate) 
        external 
        onlyOwner 
    {
        require(tokenA != tokenB, "Identical tokens");
        require(feeRate <= 1000, "Fee too high"); // Max 10%
        
        bytes32 poolId = keccak256(abi.encodePacked(tokenA, tokenB));
        require(liquidityPools[poolId].tokenA == address(0), "Pool already exists");
        
        liquidityPools[poolId] = LiquidityPool({
            tokenA: tokenA,
            tokenB: tokenB,
            reserveA: 0,
            reserveB: 0,
            totalLiquidity: 0,
            feeRate: feeRate
        });
        
        poolsList.push(poolId);
        emit PoolCreated(poolId, tokenA, tokenB);
    }
    
    function addLiquidity(
        bytes32 poolId,
        uint256 amountA,
        uint256 amountB,
        uint256 minLiquidity
    ) external whenNotPaused nonReentrant returns (uint256 liquidity) {
        LiquidityPool storage pool = liquidityPools[poolId];
        require(pool.tokenA != address(0), "Pool does not exist");
        
        // Transfer tokens
        IERC20(pool.tokenA).transferFrom(msg.sender, address(this), amountA);
        IERC20(pool.tokenB).transferFrom(msg.sender, address(this), amountB);
        
        if (pool.totalLiquidity == 0) {
            // First liquidity provider
            liquidity = _sqrt(amountA.mul(amountB));
        } else {
            // Calculate proportional liquidity
            uint256 liquidityA = amountA.mul(pool.totalLiquidity).div(pool.reserveA);
            uint256 liquidityB = amountB.mul(pool.totalLiquidity).div(pool.reserveB);
            liquidity = liquidityA < liquidityB ? liquidityA : liquidityB;
        }
        
        require(liquidity >= minLiquidity, "Insufficient liquidity minted");
        
        // Update pool state
        pool.reserveA = pool.reserveA.add(amountA);
        pool.reserveB = pool.reserveB.add(amountB);
        pool.totalLiquidity = pool.totalLiquidity.add(liquidity);
        pool.liquidityProviders[msg.sender] = pool.liquidityProviders[msg.sender].add(liquidity);
        
        emit LiquidityAdded(poolId, msg.sender, amountA, amountB);
        return liquidity;
    }
    
    function removeLiquidity(
        bytes32 poolId,
        uint256 liquidity,
        uint256 minAmountA,
        uint256 minAmountB
    ) external whenNotPaused nonReentrant returns (uint256 amountA, uint256 amountB) {
        LiquidityPool storage pool = liquidityPools[poolId];
        require(pool.liquidityProviders[msg.sender] >= liquidity, "Insufficient liquidity");
        
        // Calculate token amounts
        amountA = liquidity.mul(pool.reserveA).div(pool.totalLiquidity);
        amountB = liquidity.mul(pool.reserveB).div(pool.totalLiquidity);
        
        require(amountA >= minAmountA && amountB >= minAmountB, "Insufficient amounts");
        
        // Update pool state
        pool.liquidityProviders[msg.sender] = pool.liquidityProviders[msg.sender].sub(liquidity);
        pool.totalLiquidity = pool.totalLiquidity.sub(liquidity);
        pool.reserveA = pool.reserveA.sub(amountA);
        pool.reserveB = pool.reserveB.sub(amountB);
        
        // Transfer tokens
        IERC20(pool.tokenA).transfer(msg.sender, amountA);
        IERC20(pool.tokenB).transfer(msg.sender, amountB);
        
        emit LiquidityRemoved(poolId, msg.sender, liquidity);
        return (amountA, amountB);
    }
    
    function swap(
        bytes32 poolId,
        address tokenIn,
        uint256 amountIn,
        uint256 minAmountOut
    ) external whenNotPaused nonReentrant returns (uint256 amountOut) {
        LiquidityPool storage pool = liquidityPools[poolId];
        require(pool.tokenA != address(0), "Pool does not exist");
        require(tokenIn == pool.tokenA || tokenIn == pool.tokenB, "Invalid token");
        
        bool isTokenA = tokenIn == pool.tokenA;
        uint256 reserveIn = isTokenA ? pool.reserveA : pool.reserveB;
        uint256 reserveOut = isTokenA ? pool.reserveB : pool.reserveA;
        
        // Calculate output amount (constant product formula with fee)
        uint256 amountInWithFee = amountIn.mul(10000 - pool.feeRate);
        amountOut = amountInWithFee.mul(reserveOut).div(reserveIn.mul(10000).add(amountInWithFee));
        
        require(amountOut >= minAmountOut, "Insufficient output amount");
        
        // Transfer tokens
        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        IERC20(isTokenA ? pool.tokenB : pool.tokenA).transfer(msg.sender, amountOut);
        
        // Update reserves
        if (isTokenA) {
            pool.reserveA = pool.reserveA.add(amountIn);
            pool.reserveB = pool.reserveB.sub(amountOut);
        } else {
            pool.reserveB = pool.reserveB.add(amountIn);
            pool.reserveA = pool.reserveA.sub(amountOut);
        }
        
        emit Swap(poolId, msg.sender, tokenIn, amountIn, amountOut);
        return amountOut;
    }
    
    // ============== Staking Functions ==============
    
    function createStakingPool(
        address stakingToken,
        address rewardToken,
        uint256 rewardRate
    ) external onlyOwner {
        require(stakingPools[stakingToken].stakingToken == address(0), "Pool already exists");
        
        stakingPools[stakingToken] = StakingPool({
            stakingToken: stakingToken,
            rewardToken: rewardToken,
            totalStaked: 0,
            rewardRate: rewardRate,
            lastRewardBlock: block.number,
            accRewardPerShare: 0
        });
        
        stakingPoolsList.push(stakingToken);
    }
    
    function stake(address poolToken, uint256 amount) 
        external 
        whenNotPaused 
        nonReentrant 
    {
        StakingPool storage pool = stakingPools[poolToken];
        require(pool.stakingToken != address(0), "Pool does not exist");
        
        _updatePool(poolToken);
        
        if (pool.userStakes[msg.sender] > 0) {
            uint256 pending = pool.userStakes[msg.sender]
                .mul(pool.accRewardPerShare)
                .div(PRECISION)
                .sub(pool.userRewardDebt[msg.sender]);
            
            if (pending > 0) {
                IERC20(pool.rewardToken).transfer(msg.sender, pending);
            }
        }
        
        IERC20(pool.stakingToken).transferFrom(msg.sender, address(this), amount);
        
        pool.userStakes[msg.sender] = pool.userStakes[msg.sender].add(amount);
        pool.totalStaked = pool.totalStaked.add(amount);
        pool.userRewardDebt[msg.sender] = pool.userStakes[msg.sender]
            .mul(pool.accRewardPerShare)
            .div(PRECISION);
        
        emit Stake(poolToken, msg.sender, amount);
    }
    
    function unstake(address poolToken, uint256 amount) 
        external 
        whenNotPaused 
        nonReentrant 
    {
        StakingPool storage pool = stakingPools[poolToken];
        require(pool.userStakes[msg.sender] >= amount, "Insufficient stake");
        
        _updatePool(poolToken);
        
        uint256 pending = pool.userStakes[msg.sender]
            .mul(pool.accRewardPerShare)
            .div(PRECISION)
            .sub(pool.userRewardDebt[msg.sender]);
        
        pool.userStakes[msg.sender] = pool.userStakes[msg.sender].sub(amount);
        pool.totalStaked = pool.totalStaked.sub(amount);
        pool.userRewardDebt[msg.sender] = pool.userStakes[msg.sender]
            .mul(pool.accRewardPerShare)
            .div(PRECISION);
        
        IERC20(pool.stakingToken).transfer(msg.sender, amount);
        
        if (pending > 0) {
            IERC20(pool.rewardToken).transfer(msg.sender, pending);
            emit RewardClaimed(poolToken, msg.sender, pending);
        }
        
        emit Unstake(poolToken, msg.sender, amount);
    }
    
    // ============== Flash Loan Functions ==============
    
    function flashLoan(
        address receiver,
        address asset,
        uint256 amount,
        bytes calldata params
    ) external whenNotPaused nonReentrant {
        uint256 balanceBefore = IERC20(asset).balanceOf(address(this));
        require(balanceBefore >= amount, "Insufficient liquidity");
        
        uint256 fee = amount.mul(FLASH_LOAN_FEE).div(10000);
        
        // Transfer requested amount
        IERC20(asset).transfer(receiver, amount);
        
        // Call receiver's execute function
        IFlashLoanReceiver(receiver).executeOperation(asset, amount, fee, params);
        
        // Verify repayment
        uint256 balanceAfter = IERC20(asset).balanceOf(address(this));
        require(balanceAfter >= balanceBefore.add(fee), "Flash loan not repaid");
        
        // Transfer fee to treasury
        IERC20(asset).transfer(treasuryAddress, fee);
        
        emit FlashLoan(receiver, asset, amount, fee);
    }
    
    // ============== Internal Functions ==============
    
    function _accrueInterest(address asset) internal {
        Market storage market = markets[asset];
        
        uint256 blockDelta = block.number - market.lastUpdateBlock;
        if (blockDelta == 0) return;
        
        // Simple interest accrual (can be made more sophisticated)
        uint256 borrowInterest = market.totalBorrow
            .mul(market.borrowRate)
            .mul(blockDelta)
            .div(2102400); // Blocks per year (approximate)
        
        market.totalBorrow = market.totalBorrow.add(borrowInterest);
        market.lastUpdateBlock = block.number;
    }
    
    function _updateUserCollateral(address user) internal {
        UserAccount storage account = userAccounts[user];
        
        uint256 totalCollateral = 0;
        uint256 totalBorrow = 0;
        
        for (uint256 i = 0; i < marketsList.length; i++) {
            address asset = marketsList[i];
            Market memory market = markets[asset];
            
            if (account.supplied[asset] > 0) {
                uint256 assetValue = _getAssetValue(asset, account.supplied[asset]);
                totalCollateral = totalCollateral.add(
                    assetValue.mul(market.collateralFactor).div(PRECISION)
                );
            }
            
            if (account.borrowed[asset] > 0) {
                totalBorrow = totalBorrow.add(_getAssetValue(asset, account.borrowed[asset]));
            }
        }
        
        account.totalCollateralValue = totalCollateral;
        account.totalBorrowValue = totalBorrow;
        
        if (totalBorrow > 0) {
            account.healthFactor = totalCollateral.mul(PRECISION).div(totalBorrow);
        } else {
            account.healthFactor = type(uint256).max;
        }
    }
    
    function _checkHealthFactor(address user) internal view returns (bool) {
        return userAccounts[user].healthFactor >= MIN_HEALTH_FACTOR;
    }
    
    function _getAssetValue(address asset, uint256 amount) internal view returns (uint256) {
        // In production, this would query an oracle for real prices
        // For now, return amount (assuming 1:1 with USD)
        return amount;
    }
    
    function _updatePool(address poolToken) internal {
        StakingPool storage pool = stakingPools[poolToken];
        
        if (block.number <= pool.lastRewardBlock) {
            return;
        }
        
        if (pool.totalStaked == 0) {
            pool.lastRewardBlock = block.number;
            return;
        }
        
        uint256 blockDelta = block.number - pool.lastRewardBlock;
        uint256 reward = blockDelta.mul(pool.rewardRate);
        
        pool.accRewardPerShare = pool.accRewardPerShare.add(
            reward.mul(PRECISION).div(pool.totalStaked)
        );
        pool.lastRewardBlock = block.number;
    }
    
    function _sqrt(uint256 y) internal pure returns (uint256 z) {
        if (y > 3) {
            z = y;
            uint256 x = y / 2 + 1;
            while (x < z) {
                z = x;
                x = (y / x + x) / 2;
            }
        } else if (y != 0) {
            z = 1;
        }
    }
    
    // ============== Admin Functions ==============
    
    function pause() external onlyOwner {
        protocolPaused = true;
    }
    
    function unpause() external onlyOwner {
        protocolPaused = false;
    }
    
    function updateOracle(address newOracle) external onlyOwner {
        oracleAddress = newOracle;
    }
    
    function updateTreasury(address newTreasury) external onlyOwner {
        treasuryAddress = newTreasury;
    }
    
    function emergencyWithdraw(address token) external onlyOwner {
        uint256 balance = IERC20(token).balanceOf(address(this));
        IERC20(token).transfer(owner(), balance);
    }
}

interface IFlashLoanReceiver {
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        bytes calldata params
    ) external;
}