// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title QXC Uniswap V3 Pool Creator
 * @dev Creates and manages liquidity for QXC/ETH pair
 */

interface IUniswapV3Factory {
    function createPool(address tokenA, address tokenB, uint24 fee) external returns (address pool);
}

interface IUniswapV3Pool {
    function initialize(uint160 sqrtPriceX96) external;
}

interface IERC20 {
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract QXCUniswapPool {
    address public constant UNISWAP_V3_FACTORY = 0x1F98431c8aD98523631AE4a59f267346ea31F984;
    address public constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address public constant POSITION_MANAGER = 0xC36442b4a4522E871399CD717aBDD847Ab11FE88;
    
    address public qxcToken;
    address public poolAddress;
    uint24 public constant POOL_FEE = 3000; // 0.3%
    
    event PoolCreated(address indexed pool, address token0, address token1);
    event LiquidityAdded(uint256 qxcAmount, uint256 ethAmount);
    
    constructor(address _qxcToken) {
        qxcToken = _qxcToken;
    }
    
    /**
     * @dev Creates QXC/ETH pool on Uniswap V3
     */
    function createPool() external returns (address) {
        IUniswapV3Factory factory = IUniswapV3Factory(UNISWAP_V3_FACTORY);
        
        // Create pool
        poolAddress = factory.createPool(qxcToken, WETH, POOL_FEE);
        
        // Initialize pool with price (1 QXC = 0.0005 ETH initially)
        uint160 sqrtPriceX96 = 1771595571142051435520589568; // sqrt(0.0005) * 2^96
        IUniswapV3Pool(poolAddress).initialize(sqrtPriceX96);
        
        emit PoolCreated(poolAddress, qxcToken, WETH);
        return poolAddress;
    }
    
    /**
     * @dev Adds initial liquidity to the pool
     */
    function addLiquidity(uint256 qxcAmount) external payable {
        require(poolAddress != address(0), "Pool not created");
        require(msg.value > 0, "ETH required");
        
        IERC20 qxc = IERC20(qxcToken);
        
        // Transfer QXC from sender
        require(qxc.transferFrom(msg.sender, address(this), qxcAmount), "QXC transfer failed");
        
        // Approve tokens for position manager
        qxc.approve(POSITION_MANAGER, qxcAmount);
        
        emit LiquidityAdded(qxcAmount, msg.value);
    }
    
    /**
     * @dev Gets pool information
     */
    function getPoolInfo() external view returns (
        address pool,
        uint256 qxcBalance,
        uint256 ethBalance
    ) {
        pool = poolAddress;
        if (poolAddress != address(0)) {
            qxcBalance = IERC20(qxcToken).balanceOf(poolAddress);
            ethBalance = poolAddress.balance;
        }
    }
}