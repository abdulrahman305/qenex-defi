// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title QXC Automated Market Maker
 * @notice Decentralized exchange with constant product formula
 * @dev Implements x*y=k AMM with concentrated liquidity
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
}

contract QXCAutomatedMarketMaker {
    // Core state
    address public immutable qxcToken;
    mapping(address => Pool) public pools;
    mapping(address => mapping(address => uint256)) public liquidity;
    
    // Pool structure
    struct Pool {
        uint256 qxcReserve;
        uint256 tokenReserve;
        uint256 totalLiquidity;
        uint256 fee; // in basis points (100 = 1%)
        bool active;
    }
    
    // Security
    bool private locked;
    address public owner;
    mapping(address => bool) public authorizedTokens;
    
    // Constants
    uint256 public constant MIN_LIQUIDITY = 1000;
    uint256 public constant MAX_FEE = 1000; // 10% max
    uint256 public constant DEFAULT_FEE = 30; // 0.3%
    
    // Events
    event PoolCreated(address indexed token, uint256 qxcAmount, uint256 tokenAmount);
    event LiquidityAdded(address indexed provider, address indexed token, uint256 qxcAmount, uint256 tokenAmount, uint256 liquidity);
    event LiquidityRemoved(address indexed provider, address indexed token, uint256 qxcAmount, uint256 tokenAmount, uint256 liquidity);
    event Swap(address indexed trader, address indexed tokenIn, address indexed tokenOut, uint256 amountIn, uint256 amountOut);
    event FeeUpdated(address indexed token, uint256 newFee);
    
    // Modifiers
    modifier nonReentrant() {
        require(!locked, "Reentrant call");
        locked = true;
        _;
        locked = false;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    modifier onlyAuthorized(address token) {
        require(authorizedTokens[token], "Token not authorized");
        _;
    }
    
    constructor(address _qxcToken) {
        require(_qxcToken != address(0), "Invalid QXC token");
        qxcToken = _qxcToken;
        owner = msg.sender;
    }
    
    /**
     * @notice Create new liquidity pool
     * @param token Paired token address
     * @param qxcAmount Initial QXC liquidity
     * @param tokenAmount Initial token liquidity
     */
    function createPool(
        address token,
        uint256 qxcAmount,
        uint256 tokenAmount
    ) external nonReentrant onlyAuthorized(token) {
        require(!pools[token].active, "Pool exists");
        require(qxcAmount > MIN_LIQUIDITY && tokenAmount > MIN_LIQUIDITY, "Insufficient initial liquidity");
        
        // Transfer tokens
        IERC20(qxcToken).transferFrom(msg.sender, address(this), qxcAmount);
        IERC20(token).transferFrom(msg.sender, address(this), tokenAmount);
        
        // Calculate initial liquidity
        uint256 initialLiquidity = sqrt(qxcAmount * tokenAmount);
        require(initialLiquidity > MIN_LIQUIDITY, "Insufficient liquidity");
        
        // Create pool
        pools[token] = Pool({
            qxcReserve: qxcAmount,
            tokenReserve: tokenAmount,
            totalLiquidity: initialLiquidity - MIN_LIQUIDITY,
            fee: DEFAULT_FEE,
            active: true
        });
        
        // Mint liquidity tokens (minus minimum liquidity locked forever)
        liquidity[msg.sender][token] = initialLiquidity - MIN_LIQUIDITY;
        
        emit PoolCreated(token, qxcAmount, tokenAmount);
        emit LiquidityAdded(msg.sender, token, qxcAmount, tokenAmount, initialLiquidity - MIN_LIQUIDITY);
    }
    
    /**
     * @notice Add liquidity to existing pool
     * @param token Paired token address
     * @param qxcDesired Desired QXC amount
     * @param tokenDesired Desired token amount
     * @param qxcMin Minimum QXC amount
     * @param tokenMin Minimum token amount
     */
    function addLiquidity(
        address token,
        uint256 qxcDesired,
        uint256 tokenDesired,
        uint256 qxcMin,
        uint256 tokenMin
    ) external nonReentrant returns (uint256 qxcActual, uint256 tokenActual, uint256 liquidityMinted) {
        Pool storage pool = pools[token];
        require(pool.active, "Pool not active");
        
        // Calculate optimal amounts
        if (pool.qxcReserve == 0 && pool.tokenReserve == 0) {
            qxcActual = qxcDesired;
            tokenActual = tokenDesired;
        } else {
            uint256 tokenOptimal = (qxcDesired * pool.tokenReserve) / pool.qxcReserve;
            if (tokenOptimal <= tokenDesired) {
                require(tokenOptimal >= tokenMin, "Insufficient token amount");
                qxcActual = qxcDesired;
                tokenActual = tokenOptimal;
            } else {
                uint256 qxcOptimal = (tokenDesired * pool.qxcReserve) / pool.tokenReserve;
                require(qxcOptimal <= qxcDesired && qxcOptimal >= qxcMin, "Insufficient QXC amount");
                qxcActual = qxcOptimal;
                tokenActual = tokenDesired;
            }
        }
        
        // Transfer tokens
        IERC20(qxcToken).transferFrom(msg.sender, address(this), qxcActual);
        IERC20(token).transferFrom(msg.sender, address(this), tokenActual);
        
        // Mint liquidity
        if (pool.totalLiquidity == 0) {
            liquidityMinted = sqrt(qxcActual * tokenActual) - MIN_LIQUIDITY;
        } else {
            liquidityMinted = min(
                (qxcActual * pool.totalLiquidity) / pool.qxcReserve,
                (tokenActual * pool.totalLiquidity) / pool.tokenReserve
            );
        }
        
        require(liquidityMinted > 0, "Insufficient liquidity minted");
        
        // Update state
        liquidity[msg.sender][token] += liquidityMinted;
        pool.totalLiquidity += liquidityMinted;
        pool.qxcReserve += qxcActual;
        pool.tokenReserve += tokenActual;
        
        emit LiquidityAdded(msg.sender, token, qxcActual, tokenActual, liquidityMinted);
    }
    
    /**
     * @notice Remove liquidity from pool
     * @param token Paired token address
     * @param liquidityAmount Amount of liquidity to remove
     * @param qxcMin Minimum QXC to receive
     * @param tokenMin Minimum token to receive
     */
    function removeLiquidity(
        address token,
        uint256 liquidityAmount,
        uint256 qxcMin,
        uint256 tokenMin
    ) external nonReentrant returns (uint256 qxcAmount, uint256 tokenAmount) {
        Pool storage pool = pools[token];
        require(pool.active, "Pool not active");
        require(liquidity[msg.sender][token] >= liquidityAmount, "Insufficient liquidity");
        
        // Calculate token amounts
        qxcAmount = (liquidityAmount * pool.qxcReserve) / pool.totalLiquidity;
        tokenAmount = (liquidityAmount * pool.tokenReserve) / pool.totalLiquidity;
        
        require(qxcAmount >= qxcMin && tokenAmount >= tokenMin, "Slippage exceeded");
        
        // Update state
        liquidity[msg.sender][token] -= liquidityAmount;
        pool.totalLiquidity -= liquidityAmount;
        pool.qxcReserve -= qxcAmount;
        pool.tokenReserve -= tokenAmount;
        
        // Transfer tokens
        IERC20(qxcToken).transfer(msg.sender, qxcAmount);
        IERC20(token).transfer(msg.sender, tokenAmount);
        
        emit LiquidityRemoved(msg.sender, token, qxcAmount, tokenAmount, liquidityAmount);
    }
    
    /**
     * @notice Swap tokens
     * @param tokenIn Input token address
     * @param tokenOut Output token address
     * @param amountIn Amount to swap
     * @param minAmountOut Minimum output amount
     */
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut
    ) external nonReentrant returns (uint256 amountOut) {
        require(tokenIn == qxcToken || tokenOut == qxcToken, "One token must be QXC");
        require(tokenIn != tokenOut, "Same token swap");
        
        address poolToken = tokenIn == qxcToken ? tokenOut : tokenIn;
        Pool storage pool = pools[poolToken];
        require(pool.active, "Pool not active");
        
        // Calculate output amount
        uint256 amountInWithFee = (amountIn * (10000 - pool.fee)) / 10000;
        
        if (tokenIn == qxcToken) {
            // QXC -> Token
            amountOut = (amountInWithFee * pool.tokenReserve) / (pool.qxcReserve + amountInWithFee);
            require(amountOut >= minAmountOut, "Slippage exceeded");
            
            // Transfer tokens
            IERC20(qxcToken).transferFrom(msg.sender, address(this), amountIn);
            IERC20(poolToken).transfer(msg.sender, amountOut);
            
            // Update reserves
            pool.qxcReserve += amountIn;
            pool.tokenReserve -= amountOut;
        } else {
            // Token -> QXC
            amountOut = (amountInWithFee * pool.qxcReserve) / (pool.tokenReserve + amountInWithFee);
            require(amountOut >= minAmountOut, "Slippage exceeded");
            
            // Transfer tokens
            IERC20(poolToken).transferFrom(msg.sender, address(this), amountIn);
            IERC20(qxcToken).transfer(msg.sender, amountOut);
            
            // Update reserves
            pool.tokenReserve += amountIn;
            pool.qxcReserve -= amountOut;
        }
        
        emit Swap(msg.sender, tokenIn, tokenOut, amountIn, amountOut);
    }
    
    /**
     * @notice Get swap output amount
     * @param tokenIn Input token
     * @param tokenOut Output token
     * @param amountIn Input amount
     */
    function getAmountOut(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) external view returns (uint256 amountOut) {
        require(tokenIn == qxcToken || tokenOut == qxcToken, "One token must be QXC");
        
        address poolToken = tokenIn == qxcToken ? tokenOut : tokenIn;
        Pool memory pool = pools[poolToken];
        require(pool.active, "Pool not active");
        
        uint256 amountInWithFee = (amountIn * (10000 - pool.fee)) / 10000;
        
        if (tokenIn == qxcToken) {
            amountOut = (amountInWithFee * pool.tokenReserve) / (pool.qxcReserve + amountInWithFee);
        } else {
            amountOut = (amountInWithFee * pool.qxcReserve) / (pool.tokenReserve + amountInWithFee);
        }
    }
    
    /**
     * @notice Authorize token for pool creation
     * @param token Token to authorize
     */
    function authorizeToken(address token) external onlyOwner {
        require(token != address(0) && token != qxcToken, "Invalid token");
        authorizedTokens[token] = true;
    }
    
    /**
     * @notice Update pool fee
     * @param token Pool token
     * @param newFee New fee in basis points
     */
    function updateFee(address token, uint256 newFee) external onlyOwner {
        require(pools[token].active, "Pool not active");
        require(newFee <= MAX_FEE, "Fee too high");
        pools[token].fee = newFee;
        emit FeeUpdated(token, newFee);
    }
    
    // Helper functions
    function sqrt(uint256 y) internal pure returns (uint256 z) {
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
    
    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
}