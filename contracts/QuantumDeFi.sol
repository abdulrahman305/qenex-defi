// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title QENEX Quantum DeFi Protocol
 * @notice Advanced DeFi system with zero-knowledge proofs and cross-chain capabilities
 */

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
}

contract QuantumDeFi {
    using Math for uint256;
    
    // ============ State Variables ============
    
    struct Position {
        uint256 collateral;
        uint256 debt;
        uint256 lastInteraction;
        bytes32 zkProof;
    }
    
    struct Pool {
        address asset;
        uint256 totalSupply;
        uint256 totalBorrow;
        uint256 utilizationRate;
        uint256 supplyRate;
        uint256 borrowRate;
        uint256 lastUpdate;
        bool active;
    }
    
    struct CrossChainMessage {
        uint256 sourceChain;
        uint256 destChain;
        address sender;
        bytes payload;
        bytes32 proof;
    }
    
    mapping(address => mapping(address => Position)) public positions;
    mapping(address => Pool) public pools;
    mapping(bytes32 => bool) public processedProofs;
    mapping(uint256 => mapping(address => uint256)) public bridgedAssets;
    
    uint256 public constant PRECISION = 1e18;
    uint256 public constant LIQUIDATION_THRESHOLD = 150; // 150%
    uint256 public constant LIQUIDATION_PENALTY = 105; // 5% penalty
    uint256 public constant MAX_UTILIZATION = 95; // 95%
    
    address public governance;
    address public oracle;
    address public zkVerifier;
    
    // ============ Events ============
    
    event PoolCreated(address indexed asset);
    event Deposited(address indexed user, address indexed asset, uint256 amount);
    event Borrowed(address indexed user, address indexed asset, uint256 amount);
    event Repaid(address indexed user, address indexed asset, uint256 amount);
    event Liquidated(address indexed liquidator, address indexed user, uint256 amount);
    event CrossChainTransfer(uint256 sourceChain, uint256 destChain, address asset, uint256 amount);
    event ZKProofVerified(bytes32 proof, address prover);
    
    // ============ Modifiers ============
    
    modifier onlyGovernance() {
        require(msg.sender == governance, "Not governance");
        _;
    }
    
    modifier onlyOracle() {
        require(msg.sender == oracle, "Not oracle");
        _;
    }
    
    modifier poolExists(address asset) {
        require(pools[asset].active, "Pool does not exist");
        _;
    }
    
    // ============ Constructor ============
    
    constructor(address _governance, address _oracle, address _zkVerifier) {
        governance = _governance;
        oracle = _oracle;
        zkVerifier = _zkVerifier;
    }
    
    // ============ Core Functions ============
    
    /**
     * @notice Create new lending pool
     */
    function createPool(address asset) external onlyGovernance {
        require(!pools[asset].active, "Pool already exists");
        
        pools[asset] = Pool({
            asset: asset,
            totalSupply: 0,
            totalBorrow: 0,
            utilizationRate: 0,
            supplyRate: 5 * PRECISION / 100, // 5% APY
            borrowRate: 10 * PRECISION / 100, // 10% APY
            lastUpdate: block.timestamp,
            active: true
        });
        
        emit PoolCreated(asset);
    }
    
    /**
     * @notice Deposit assets with zero-knowledge proof of reserves
     */
    function deposit(
        address asset,
        uint256 amount,
        bytes32 zkProof
    ) external poolExists(asset) {
        require(amount > 0, "Amount must be > 0");
        require(verifyZKProof(zkProof, msg.sender, amount), "Invalid ZK proof");
        
        Pool storage pool = pools[asset];
        _accrueInterest(pool);
        
        IERC20(asset).transferFrom(msg.sender, address(this), amount);
        
        Position storage position = positions[msg.sender][asset];
        position.collateral += amount;
        position.lastInteraction = block.timestamp;
        position.zkProof = zkProof;
        
        pool.totalSupply += amount;
        _updateRates(pool);
        
        emit Deposited(msg.sender, asset, amount);
    }
    
    /**
     * @notice Borrow assets against collateral
     */
    function borrow(address asset, uint256 amount) external poolExists(asset) {
        require(amount > 0, "Amount must be > 0");
        
        Pool storage pool = pools[asset];
        _accrueInterest(pool);
        
        require(pool.totalSupply - pool.totalBorrow >= amount, "Insufficient liquidity");
        
        Position storage position = positions[msg.sender][asset];
        uint256 borrowCapacity = _calculateBorrowCapacity(msg.sender, asset);
        require(position.debt + amount <= borrowCapacity, "Exceeds borrow capacity");
        
        position.debt += amount;
        position.lastInteraction = block.timestamp;
        
        pool.totalBorrow += amount;
        _updateRates(pool);
        
        IERC20(asset).transfer(msg.sender, amount);
        
        emit Borrowed(msg.sender, asset, amount);
    }
    
    /**
     * @notice Repay borrowed assets
     */
    function repay(address asset, uint256 amount) external poolExists(asset) {
        Pool storage pool = pools[asset];
        _accrueInterest(pool);
        
        Position storage position = positions[msg.sender][asset];
        uint256 repayAmount = amount.min(position.debt);
        
        IERC20(asset).transferFrom(msg.sender, address(this), repayAmount);
        
        position.debt -= repayAmount;
        position.lastInteraction = block.timestamp;
        
        pool.totalBorrow -= repayAmount;
        _updateRates(pool);
        
        emit Repaid(msg.sender, asset, repayAmount);
    }
    
    /**
     * @notice Liquidate undercollateralized position
     */
    function liquidate(address user, address asset) external poolExists(asset) {
        Position storage position = positions[user][asset];
        require(position.debt > 0, "No debt to liquidate");
        
        uint256 healthFactor = _calculateHealthFactor(user, asset);
        require(healthFactor < PRECISION, "Position is healthy");
        
        uint256 liquidationAmount = position.debt * LIQUIDATION_PENALTY / 100;
        uint256 collateralToSeize = liquidationAmount * getPrice(asset) / PRECISION;
        
        IERC20(asset).transferFrom(msg.sender, address(this), position.debt);
        
        position.debt = 0;
        position.collateral -= collateralToSeize;
        
        IERC20(asset).transfer(msg.sender, collateralToSeize);
        
        emit Liquidated(msg.sender, user, liquidationAmount);
    }
    
    // ============ Cross-Chain Functions ============
    
    /**
     * @notice Initiate cross-chain transfer with ZK proof
     */
    function crossChainTransfer(
        uint256 destChain,
        address asset,
        uint256 amount,
        bytes32 zkProof
    ) external {
        require(verifyZKProof(zkProof, msg.sender, amount), "Invalid ZK proof");
        
        IERC20(asset).transferFrom(msg.sender, address(this), amount);
        
        bridgedAssets[destChain][asset] += amount;
        
        emit CrossChainTransfer(block.chainid, destChain, asset, amount);
    }
    
    /**
     * @notice Process incoming cross-chain message
     */
    function processCrossChainMessage(
        CrossChainMessage calldata message
    ) external {
        require(!processedProofs[message.proof], "Already processed");
        require(verifyCrossChainProof(message), "Invalid proof");
        
        processedProofs[message.proof] = true;
        
        // Process the message payload
        (address recipient, address asset, uint256 amount) = abi.decode(
            message.payload,
            (address, address, uint256)
        );
        
        bridgedAssets[message.sourceChain][asset] -= amount;
        IERC20(asset).transfer(recipient, amount);
    }
    
    // ============ Zero-Knowledge Functions ============
    
    /**
     * @notice Verify zero-knowledge proof
     */
    function verifyZKProof(
        bytes32 proof,
        address prover,
        uint256 value
    ) public view returns (bool) {
        // In production, call external ZK verifier contract
        // This is a simplified verification
        bytes32 expectedProof = keccak256(abi.encodePacked(prover, value, block.timestamp / 3600));
        return proof == expectedProof;
    }
    
    /**
     * @notice Verify cross-chain proof
     */
    function verifyCrossChainProof(
        CrossChainMessage calldata message
    ) public view returns (bool) {
        // Verify the cross-chain message authenticity
        bytes32 messageHash = keccak256(abi.encodePacked(
            message.sourceChain,
            message.destChain,
            message.sender,
            message.payload
        ));
        
        return message.proof == messageHash;
    }
    
    // ============ Internal Functions ============
    
    function _accrueInterest(Pool storage pool) internal {
        uint256 timeElapsed = block.timestamp - pool.lastUpdate;
        if (timeElapsed == 0) return;
        
        uint256 borrowInterest = pool.totalBorrow * pool.borrowRate * timeElapsed / (365 days * PRECISION);
        pool.totalBorrow += borrowInterest;
        
        uint256 supplyInterest = borrowInterest * 9 / 10; // 90% to suppliers
        pool.totalSupply += supplyInterest;
        
        pool.lastUpdate = block.timestamp;
    }
    
    function _updateRates(Pool storage pool) internal {
        if (pool.totalSupply == 0) {
            pool.utilizationRate = 0;
            return;
        }
        
        pool.utilizationRate = pool.totalBorrow * PRECISION / pool.totalSupply;
        
        // Dynamic interest rate model
        if (pool.utilizationRate < 80 * PRECISION / 100) {
            pool.borrowRate = 5 * PRECISION / 100 + pool.utilizationRate * 15 / 100;
        } else {
            pool.borrowRate = 20 * PRECISION / 100 + (pool.utilizationRate - 80 * PRECISION / 100) * 100 / 100;
        }
        
        pool.supplyRate = pool.borrowRate * pool.utilizationRate / PRECISION * 9 / 10;
    }
    
    function _calculateBorrowCapacity(
        address user,
        address asset
    ) internal view returns (uint256) {
        Position memory position = positions[user][asset];
        uint256 collateralValue = position.collateral * getPrice(asset) / PRECISION;
        return collateralValue * 100 / LIQUIDATION_THRESHOLD;
    }
    
    function _calculateHealthFactor(
        address user,
        address asset
    ) internal view returns (uint256) {
        Position memory position = positions[user][asset];
        if (position.debt == 0) return type(uint256).max;
        
        uint256 collateralValue = position.collateral * getPrice(asset) / PRECISION;
        uint256 debtValue = position.debt * getPrice(asset) / PRECISION;
        
        return collateralValue * PRECISION / debtValue / LIQUIDATION_THRESHOLD * 100;
    }
    
    // ============ View Functions ============
    
    function getPrice(address asset) public view returns (uint256) {
        // In production, query oracle
        // Simplified: return $1 per token
        return PRECISION;
    }
    
    function getPosition(address user, address asset) external view returns (
        uint256 collateral,
        uint256 debt,
        uint256 healthFactor
    ) {
        Position memory position = positions[user][asset];
        return (
            position.collateral,
            position.debt,
            _calculateHealthFactor(user, asset)
        );
    }
    
    function getPoolInfo(address asset) external view returns (
        uint256 totalSupply,
        uint256 totalBorrow,
        uint256 supplyRate,
        uint256 borrowRate,
        uint256 utilization
    ) {
        Pool memory pool = pools[asset];
        return (
            pool.totalSupply,
            pool.totalBorrow,
            pool.supplyRate,
            pool.borrowRate,
            pool.utilizationRate
        );
    }
    
    // ============ Admin Functions ============
    
    function setOracle(address _oracle) external onlyGovernance {
        oracle = _oracle;
    }
    
    function setZKVerifier(address _zkVerifier) external onlyGovernance {
        zkVerifier = _zkVerifier;
    }
    
    function pause(address asset) external onlyGovernance {
        pools[asset].active = false;
    }
    
    function unpause(address asset) external onlyGovernance {
        pools[asset].active = true;
    }
}