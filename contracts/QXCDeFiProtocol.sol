// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
}

library Math {
    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
    
    function sqrt(uint256 a) internal pure returns (uint256) {
        if (a == 0) return 0;
        
        uint256 result = 1;
        uint256 x = a;
        
        if (x > 3) {
            result = x / 2 + 1;
            while (result < x) {
                x = result;
                result = (a / x + x) / 2;
            }
        }
        
        return x;
    }
}

contract QXCDeFiProtocol {
    using Math for uint256;
    
    struct Pool {
        address tokenA;
        address tokenB;
        uint256 reserveA;
        uint256 reserveB;
        uint256 totalShares;
        uint256 feeRate; // in basis points (e.g., 30 = 0.3%)
        mapping(address => uint256) shares;
        mapping(address => uint256) feeGrowthA;
        mapping(address => uint256) feeGrowthB;
    }
    
    struct Vault {
        address asset;
        uint256 totalAssets;
        uint256 totalShares;
        uint256 performanceFee;
        uint256 managementFee;
        uint256 lastHarvest;
        mapping(address => uint256) userShares;
    }
    
    struct LendingPool {
        address asset;
        uint256 totalSupply;
        uint256 totalBorrowed;
        uint256 supplyRate;
        uint256 borrowRate;
        uint256 collateralFactor;
        mapping(address => uint256) supplied;
        mapping(address => uint256) borrowed;
        mapping(address => uint256) collateral;
    }
    
    struct FlashLoanRequest {
        address borrower;
        address asset;
        uint256 amount;
        bytes data;
    }
    
    mapping(bytes32 => Pool) public pools;
    mapping(bytes32 => Vault) public vaults;
    mapping(address => LendingPool) public lendingPools;
    
    mapping(address => mapping(address => uint256)) public userCollateral;
    mapping(address => uint256) public flashLoanBalances;
    
    uint256 public constant MINIMUM_LIQUIDITY = 10**3;
    uint256 public constant FEE_DENOMINATOR = 10000;
    uint256 public flashLoanFee = 9; // 0.09%
    
    address public governance;
    address public feeCollector;
    
    event LiquidityAdded(
        address indexed provider,
        bytes32 indexed poolId,
        uint256 amountA,
        uint256 amountB,
        uint256 shares
    );
    
    event LiquidityRemoved(
        address indexed provider,
        bytes32 indexed poolId,
        uint256 amountA,
        uint256 amountB,
        uint256 shares
    );
    
    event Swap(
        address indexed user,
        bytes32 indexed poolId,
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 amountOut
    );
    
    event VaultDeposit(
        address indexed user,
        bytes32 indexed vaultId,
        uint256 assets,
        uint256 shares
    );
    
    event VaultWithdraw(
        address indexed user,
        bytes32 indexed vaultId,
        uint256 assets,
        uint256 shares
    );
    
    event Supplied(
        address indexed user,
        address indexed asset,
        uint256 amount
    );
    
    event Borrowed(
        address indexed user,
        address indexed asset,
        uint256 amount
    );
    
    event Repaid(
        address indexed user,
        address indexed asset,
        uint256 amount
    );
    
    event FlashLoan(
        address indexed borrower,
        address indexed asset,
        uint256 amount,
        uint256 fee
    );
    
    modifier onlyGovernance() {
        require(msg.sender == governance, "Not governance");
        _;
    }
    
    constructor() {
        governance = msg.sender;
        feeCollector = msg.sender;
    }
    
    function createPool(
        address tokenA,
        address tokenB,
        uint256 feeRate
    ) external returns (bytes32) {
        require(tokenA != tokenB, "Same token");
        require(feeRate <= 100, "Fee too high");
        
        bytes32 poolId = keccak256(abi.encodePacked(tokenA, tokenB, feeRate));
        require(pools[poolId].tokenA == address(0), "Pool exists");
        
        Pool storage pool = pools[poolId];
        pool.tokenA = tokenA;
        pool.tokenB = tokenB;
        pool.feeRate = feeRate;
        
        return poolId;
    }
    
    function addLiquidity(
        bytes32 poolId,
        uint256 amountA,
        uint256 amountB,
        uint256 minShares
    ) external returns (uint256 shares) {
        Pool storage pool = pools[poolId];
        require(pool.tokenA != address(0), "Pool not found");
        
        IERC20(pool.tokenA).transferFrom(msg.sender, address(this), amountA);
        IERC20(pool.tokenB).transferFrom(msg.sender, address(this), amountB);
        
        if (pool.totalShares == 0) {
            shares = Math.sqrt(amountA * amountB) - MINIMUM_LIQUIDITY;
            pool.totalShares = MINIMUM_LIQUIDITY;
        } else {
            uint256 shareA = (amountA * pool.totalShares) / pool.reserveA;
            uint256 shareB = (amountB * pool.totalShares) / pool.reserveB;
            shares = Math.min(shareA, shareB);
        }
        
        require(shares >= minShares, "Insufficient shares");
        
        pool.reserveA += amountA;
        pool.reserveB += amountB;
        pool.totalShares += shares;
        pool.shares[msg.sender] += shares;
        
        emit LiquidityAdded(msg.sender, poolId, amountA, amountB, shares);
    }
    
    function removeLiquidity(
        bytes32 poolId,
        uint256 shares,
        uint256 minAmountA,
        uint256 minAmountB
    ) external returns (uint256 amountA, uint256 amountB) {
        Pool storage pool = pools[poolId];
        require(pool.shares[msg.sender] >= shares, "Insufficient shares");
        
        amountA = (shares * pool.reserveA) / pool.totalShares;
        amountB = (shares * pool.reserveB) / pool.totalShares;
        
        require(amountA >= minAmountA, "Insufficient amountA");
        require(amountB >= minAmountB, "Insufficient amountB");
        
        pool.shares[msg.sender] -= shares;
        pool.totalShares -= shares;
        pool.reserveA -= amountA;
        pool.reserveB -= amountB;
        
        IERC20(pool.tokenA).transfer(msg.sender, amountA);
        IERC20(pool.tokenB).transfer(msg.sender, amountB);
        
        emit LiquidityRemoved(msg.sender, poolId, amountA, amountB, shares);
    }
    
    function swap(
        bytes32 poolId,
        address tokenIn,
        uint256 amountIn,
        uint256 minAmountOut
    ) external returns (uint256 amountOut) {
        Pool storage pool = pools[poolId];
        require(pool.tokenA != address(0), "Pool not found");
        require(tokenIn == pool.tokenA || tokenIn == pool.tokenB, "Invalid token");
        
        bool isTokenA = tokenIn == pool.tokenA;
        address tokenOut = isTokenA ? pool.tokenB : pool.tokenA;
        
        uint256 reserveIn = isTokenA ? pool.reserveA : pool.reserveB;
        uint256 reserveOut = isTokenA ? pool.reserveB : pool.reserveA;
        
        uint256 amountInWithFee = amountIn * (FEE_DENOMINATOR - pool.feeRate);
        amountOut = (amountInWithFee * reserveOut) / (reserveIn * FEE_DENOMINATOR + amountInWithFee);
        
        require(amountOut >= minAmountOut, "Insufficient output");
        
        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenOut).transfer(msg.sender, amountOut);
        
        if (isTokenA) {
            pool.reserveA += amountIn;
            pool.reserveB -= amountOut;
        } else {
            pool.reserveB += amountIn;
            pool.reserveA -= amountOut;
        }
        
        emit Swap(msg.sender, poolId, tokenIn, tokenOut, amountIn, amountOut);
    }
    
    function createVault(
        address asset,
        uint256 performanceFee,
        uint256 managementFee
    ) external onlyGovernance returns (bytes32) {
        require(performanceFee <= 2000, "Performance fee too high"); // Max 20%
        require(managementFee <= 200, "Management fee too high"); // Max 2%
        
        bytes32 vaultId = keccak256(abi.encodePacked(asset, block.timestamp));
        
        Vault storage vault = vaults[vaultId];
        vault.asset = asset;
        vault.performanceFee = performanceFee;
        vault.managementFee = managementFee;
        vault.lastHarvest = block.timestamp;
        
        return vaultId;
    }
    
    function depositToVault(bytes32 vaultId, uint256 assets) external returns (uint256 shares) {
        Vault storage vault = vaults[vaultId];
        require(vault.asset != address(0), "Vault not found");
        
        if (vault.totalShares == 0) {
            shares = assets;
        } else {
            shares = (assets * vault.totalShares) / vault.totalAssets;
        }
        
        IERC20(vault.asset).transferFrom(msg.sender, address(this), assets);
        
        vault.totalAssets += assets;
        vault.totalShares += shares;
        vault.userShares[msg.sender] += shares;
        
        emit VaultDeposit(msg.sender, vaultId, assets, shares);
    }
    
    function withdrawFromVault(bytes32 vaultId, uint256 shares) external returns (uint256 assets) {
        Vault storage vault = vaults[vaultId];
        require(vault.userShares[msg.sender] >= shares, "Insufficient shares");
        
        assets = (shares * vault.totalAssets) / vault.totalShares;
        
        vault.userShares[msg.sender] -= shares;
        vault.totalShares -= shares;
        vault.totalAssets -= assets;
        
        IERC20(vault.asset).transfer(msg.sender, assets);
        
        emit VaultWithdraw(msg.sender, vaultId, assets, shares);
    }
    
    function createLendingPool(
        address asset,
        uint256 supplyRate,
        uint256 borrowRate,
        uint256 collateralFactor
    ) external onlyGovernance {
        require(lendingPools[asset].asset == address(0), "Pool exists");
        require(collateralFactor <= FEE_DENOMINATOR, "Invalid collateral factor");
        
        LendingPool storage pool = lendingPools[asset];
        pool.asset = asset;
        pool.supplyRate = supplyRate;
        pool.borrowRate = borrowRate;
        pool.collateralFactor = collateralFactor;
    }
    
    function supply(address asset, uint256 amount) external {
        LendingPool storage pool = lendingPools[asset];
        require(pool.asset != address(0), "Pool not found");
        
        IERC20(asset).transferFrom(msg.sender, address(this), amount);
        
        pool.supplied[msg.sender] += amount;
        pool.totalSupply += amount;
        
        emit Supplied(msg.sender, asset, amount);
    }
    
    function borrow(address asset, uint256 amount) external {
        LendingPool storage pool = lendingPools[asset];
        require(pool.asset != address(0), "Pool not found");
        require(pool.totalSupply - pool.totalBorrowed >= amount, "Insufficient liquidity");
        
        uint256 requiredCollateral = (amount * FEE_DENOMINATOR) / pool.collateralFactor;
        require(getAccountCollateral(msg.sender) >= requiredCollateral, "Insufficient collateral");
        
        pool.borrowed[msg.sender] += amount;
        pool.totalBorrowed += amount;
        
        IERC20(asset).transfer(msg.sender, amount);
        
        emit Borrowed(msg.sender, asset, amount);
    }
    
    function repay(address asset, uint256 amount) external {
        LendingPool storage pool = lendingPools[asset];
        require(pool.borrowed[msg.sender] >= amount, "Excess repayment");
        
        IERC20(asset).transferFrom(msg.sender, address(this), amount);
        
        pool.borrowed[msg.sender] -= amount;
        pool.totalBorrowed -= amount;
        
        emit Repaid(msg.sender, asset, amount);
    }
    
    function flashLoan(
        address asset,
        uint256 amount,
        bytes calldata data
    ) external {
        require(flashLoanBalances[asset] >= amount, "Insufficient liquidity");
        
        uint256 balanceBefore = IERC20(asset).balanceOf(address(this));
        flashLoanBalances[asset] -= amount;
        
        IERC20(asset).transfer(msg.sender, amount);
        
        IFlashLoanReceiver(msg.sender).executeOperation(asset, amount, (amount * flashLoanFee) / FEE_DENOMINATOR, data);
        
        uint256 balanceAfter = IERC20(asset).balanceOf(address(this));
        require(
            balanceAfter >= balanceBefore + (amount * flashLoanFee) / FEE_DENOMINATOR,
            "Flash loan not repaid"
        );
        
        flashLoanBalances[asset] = balanceAfter;
        
        emit FlashLoan(msg.sender, asset, amount, (amount * flashLoanFee) / FEE_DENOMINATOR);
    }
    
    function getAccountCollateral(address account) public view returns (uint256 total) {
        // Simplified collateral calculation
        return userCollateral[account][address(0)];
    }
    
    function addCollateral(address asset, uint256 amount) external {
        IERC20(asset).transferFrom(msg.sender, address(this), amount);
        userCollateral[msg.sender][asset] += amount;
    }
    
    function removeCollateral(address asset, uint256 amount) external {
        require(userCollateral[msg.sender][asset] >= amount, "Insufficient collateral");
        
        userCollateral[msg.sender][asset] -= amount;
        IERC20(asset).transfer(msg.sender, amount);
    }
    
    function setFlashLoanFee(uint256 fee) external onlyGovernance {
        require(fee <= 100, "Fee too high");
        flashLoanFee = fee;
    }
    
    function setFeeCollector(address collector) external onlyGovernance {
        feeCollector = collector;
    }
    
    function setGovernance(address newGovernance) external onlyGovernance {
        governance = newGovernance;
    }
    
    function emergencyPause() external onlyGovernance {
        // Implementation for emergency pause
    }
}

interface IFlashLoanReceiver {
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 fee,
        bytes calldata data
    ) external;
}