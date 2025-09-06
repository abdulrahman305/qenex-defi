// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IUniswapV2Router {
    function addLiquidity(
        address tokenA,
        address tokenB,
        uint amountADesired,
        uint amountBDesired,
        uint amountAMin,
        uint amountBMin,
        address to,
        uint deadline
    ) external returns (uint amountA, uint amountB, uint liquidity);
    
    function removeLiquidity(
        address tokenA,
        address tokenB,
        uint liquidity,
        uint amountAMin,
        uint amountBMin,
        address to,
        uint deadline
    ) external returns (uint amountA, uint amountB);
    
    function swapExactTokensForTokens(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts);
}

interface IUniswapV2Factory {
    function getPair(address tokenA, address tokenB) external view returns (address pair);
    function createPair(address tokenA, address tokenB) external returns (address pair);
}

contract QXCLiquidityProvider is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;
    
    IERC20 public immutable qxcToken;
    IERC20 public immutable usdcToken;
    IUniswapV2Router public immutable uniswapRouter;
    IUniswapV2Factory public immutable uniswapFactory;
    
    address public liquidityPair;
    uint256 public totalLiquidityProvided;
    uint256 public minLiquidityAmount = 1000 * 10**18; // Min 1000 QXC
    uint256 public maxSlippage = 300; // 3%
    
    // Events
    event LiquidityAdded(uint256 qxcAmount, uint256 usdcAmount, uint256 liquidity);
    event LiquidityRemoved(uint256 qxcAmount, uint256 usdcAmount);
    event EmergencyWithdraw(address token, uint256 amount);
    
    constructor(
        address _qxcToken,
        address _usdcToken,
        address _uniswapRouter,
        address _uniswapFactory
    ) Ownable(msg.sender) {
        require(_qxcToken != address(0), "Invalid QXC token");
        require(_usdcToken != address(0), "Invalid USDC token");
        require(_uniswapRouter != address(0), "Invalid router");
        require(_uniswapFactory != address(0), "Invalid factory");
        
        qxcToken = IERC20(_qxcToken);
        usdcToken = IERC20(_usdcToken);
        uniswapRouter = IUniswapV2Router(_uniswapRouter);
        uniswapFactory = IUniswapV2Factory(_uniswapFactory);
        
        // Create or get pair
        liquidityPair = uniswapFactory.getPair(_qxcToken, _usdcToken);
        if (liquidityPair == address(0)) {
            liquidityPair = uniswapFactory.createPair(_qxcToken, _usdcToken);
        }
    }
    
    /**
     * @dev Add initial liquidity to the pool
     */
    function addInitialLiquidity(
        uint256 qxcAmount,
        uint256 usdcAmount
    ) external onlyOwner nonReentrant {
        require(qxcAmount >= minLiquidityAmount, "Below minimum amount");
        require(usdcAmount > 0, "USDC amount required");
        
        // Transfer tokens from owner
        qxcToken.safeTransferFrom(msg.sender, address(this), qxcAmount);
        usdcToken.safeTransferFrom(msg.sender, address(this), usdcAmount);
        
        // Approve router
        qxcToken.approve(address(uniswapRouter), qxcAmount);
        usdcToken.approve(address(uniswapRouter), usdcAmount);
        
        // Add liquidity
        (uint256 amountQXC, uint256 amountUSDC, uint256 liquidity) = uniswapRouter.addLiquidity(
            address(qxcToken),
            address(usdcToken),
            qxcAmount,
            usdcAmount,
            qxcAmount * (10000 - maxSlippage) / 10000,
            usdcAmount * (10000 - maxSlippage) / 10000,
            address(this),
            block.timestamp + 300
        );
        
        totalLiquidityProvided += liquidity;
        
        emit LiquidityAdded(amountQXC, amountUSDC, liquidity);
    }
    
    /**
     * @dev Remove liquidity from the pool
     */
    function removeLiquidity(
        uint256 liquidity
    ) external onlyOwner nonReentrant {
        require(liquidity > 0, "Invalid amount");
        
        IERC20 pair = IERC20(liquidityPair);
        require(pair.balanceOf(address(this)) >= liquidity, "Insufficient LP tokens");
        
        // Approve router
        pair.approve(address(uniswapRouter), liquidity);
        
        // Remove liquidity
        (uint256 amountQXC, uint256 amountUSDC) = uniswapRouter.removeLiquidity(
            address(qxcToken),
            address(usdcToken),
            liquidity,
            0,
            0,
            msg.sender,
            block.timestamp + 300
        );
        
        totalLiquidityProvided -= liquidity;
        
        emit LiquidityRemoved(amountQXC, amountUSDC);
    }
    
    /**
     * @dev Set minimum liquidity amount
     */
    function setMinLiquidityAmount(uint256 _amount) external onlyOwner {
        minLiquidityAmount = _amount;
    }
    
    /**
     * @dev Set maximum slippage
     */
    function setMaxSlippage(uint256 _slippage) external onlyOwner {
        require(_slippage <= 1000, "Slippage too high"); // Max 10%
        maxSlippage = _slippage;
    }
    
    /**
     * @dev Get current LP token balance
     */
    function getLPBalance() external view returns (uint256) {
        return IERC20(liquidityPair).balanceOf(address(this));
    }
    
    /**
     * @dev Emergency withdraw function
     */
    function emergencyWithdraw(address token) external onlyOwner {
        require(token != address(0), "Invalid token");
        
        uint256 balance;
        if (token == address(0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE)) {
            balance = address(this).balance;
            payable(owner()).transfer(balance);
        } else {
            balance = IERC20(token).balanceOf(address(this));
            IERC20(token).safeTransfer(owner(), balance);
        }
        
        emit EmergencyWithdraw(token, balance);
    }
    
    receive() external payable {}
}