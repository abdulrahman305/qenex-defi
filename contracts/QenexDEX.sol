// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract QenexDEX is ReentrancyGuard, Ownable {
    struct Pool {
        address token0;
        address token1;
        uint256 reserve0;
        uint256 reserve1;
        uint256 totalSupply;
        mapping(address => uint256) balanceOf;
    }
    
    mapping(bytes32 => Pool) public pools;
    bytes32[] public poolKeys;
    
    event PoolCreated(bytes32 indexed poolKey, address token0, address token1);
    event Swap(address indexed user, address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut);
    event LiquidityAdded(bytes32 indexed poolKey, address indexed provider, uint256 amount0, uint256 amount1);
    
    function createPool(address token0, address token1) external returns (bytes32) {
        require(token0 != token1, "Identical tokens");
        require(token0 != address(0) && token1 != address(0), "Zero address");
        
        bytes32 poolKey = keccak256(abi.encodePacked(token0, token1));
        require(pools[poolKey].token0 == address(0), "Pool exists");
        
        pools[poolKey].token0 = token0;
        pools[poolKey].token1 = token1;
        poolKeys.push(poolKey);
        
        emit PoolCreated(poolKey, token0, token1);
        return poolKey;
    }
    
    function addLiquidity(
        bytes32 poolKey,
        uint256 amount0,
        uint256 amount1
    ) external nonReentrant returns (uint256 liquidity) {
        Pool storage pool = pools[poolKey];
        require(pool.token0 != address(0), "Pool not found");
        
        IERC20(pool.token0).transferFrom(msg.sender, address(this), amount0);
        IERC20(pool.token1).transferFrom(msg.sender, address(this), amount1);
        
        if (pool.totalSupply == 0) {
            liquidity = sqrt(amount0 * amount1);
        } else {
            liquidity = min(
                (amount0 * pool.totalSupply) / pool.reserve0,
                (amount1 * pool.totalSupply) / pool.reserve1
            );
        }
        
        require(liquidity > 0, "Insufficient liquidity minted");
        
        pool.balanceOf[msg.sender] += liquidity;
        pool.totalSupply += liquidity;
        pool.reserve0 += amount0;
        pool.reserve1 += amount1;
        
        emit LiquidityAdded(poolKey, msg.sender, amount0, amount1);
    }
    
    function swap(
        bytes32 poolKey,
        address tokenIn,
        uint256 amountIn,
        uint256 minAmountOut
    ) external nonReentrant returns (uint256 amountOut) {
        Pool storage pool = pools[poolKey];
        require(pool.token0 != address(0), "Pool not found");
        require(tokenIn == pool.token0 || tokenIn == pool.token1, "Invalid token");
        
        bool isToken0 = tokenIn == pool.token0;
        (uint256 reserveIn, uint256 reserveOut) = isToken0 
            ? (pool.reserve0, pool.reserve1) 
            : (pool.reserve1, pool.reserve0);
        
        uint256 amountInWithFee = amountIn * 997; // 0.3% fee
        amountOut = (amountInWithFee * reserveOut) / (reserveIn * 1000 + amountInWithFee);
        
        require(amountOut >= minAmountOut, "Insufficient output");
        
        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        
        address tokenOut = isToken0 ? pool.token1 : pool.token0;
        IERC20(tokenOut).transfer(msg.sender, amountOut);
        
        if (isToken0) {
            pool.reserve0 += amountIn;
            pool.reserve1 -= amountOut;
        } else {
            pool.reserve1 += amountIn;
            pool.reserve0 -= amountOut;
        }
        
        emit Swap(msg.sender, tokenIn, tokenOut, amountIn, amountOut);
    }
    
    function sqrt(uint256 x) internal pure returns (uint256) {
        if (x == 0) return 0;
        uint256 z = (x + 1) / 2;
        uint256 y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
        return y;
    }
    
    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
}
