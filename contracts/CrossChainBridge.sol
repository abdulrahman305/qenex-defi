// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/**
 * @title CrossChainBridge
 * @dev Cross-chain asset bridge for multi-blockchain interoperability
 */
contract CrossChainBridge is ReentrancyGuard, Ownable {
    using ECDSA for bytes32;
    
    struct BridgeRequest {
        address sender;
        address recipient;
        uint256 amount;
        uint256 chainId;
        uint256 nonce;
        bytes32 txHash;
        bool processed;
    }
    
    struct ChainConfig {
        bool isActive;
        uint256 minAmount;
        uint256 maxAmount;
        uint256 fee;
        address validator;
    }
    
    mapping(uint256 => ChainConfig) public supportedChains;
    mapping(bytes32 => BridgeRequest) public bridgeRequests;
    mapping(address => uint256) public nonces;
    mapping(address => bool) public validators;
    
    uint256 public constant MIN_CONFIRMATIONS = 3;
    uint256 public bridgeFee = 10; // 0.1% in basis points
    uint256 public totalBridged;
    uint256 public totalFees;
    
    event BridgeInitiated(
        bytes32 indexed requestId,
        address indexed sender,
        uint256 amount,
        uint256 targetChain
    );
    
    event BridgeCompleted(
        bytes32 indexed requestId,
        address indexed recipient,
        uint256 amount
    );
    
    event ChainAdded(uint256 indexed chainId, address validator);
    event ValidatorUpdated(address indexed validator, bool status);
    
    modifier onlyValidator() {
        require(validators[msg.sender], "Not a validator");
        _;
    }
    
    constructor() {
        validators[msg.sender] = true;
    }
    
    /**
     * @dev Add support for a new blockchain
     */
    function addSupportedChain(
        uint256 _chainId,
        uint256 _minAmount,
        uint256 _maxAmount,
        uint256 _fee,
        address _validator
    ) external onlyOwner {
        require(_chainId != block.chainid, "Cannot add current chain");
        require(_validator != address(0), "Invalid validator");
        
        supportedChains[_chainId] = ChainConfig({
            isActive: true,
            minAmount: _minAmount,
            maxAmount: _maxAmount,
            fee: _fee,
            validator: _validator
        });
        
        validators[_validator] = true;
        
        emit ChainAdded(_chainId, _validator);
    }
    
    /**
     * @dev Initiate bridge transfer to another chain
     */
    function bridgeAssets(
        uint256 _targetChainId,
        address _recipient
    ) external payable nonReentrant returns (bytes32) {
        ChainConfig memory config = supportedChains[_targetChainId];
        require(config.isActive, "Chain not supported");
        require(msg.value >= config.minAmount, "Amount too low");
        require(msg.value <= config.maxAmount, "Amount too high");
        
        uint256 fee = (msg.value * config.fee) / 10000;
        uint256 amountAfterFee = msg.value - fee;
        
        bytes32 requestId = keccak256(
            abi.encodePacked(
                msg.sender,
                _recipient,
                amountAfterFee,
                _targetChainId,
                nonces[msg.sender]++,
                block.timestamp
            )
        );
        
        bridgeRequests[requestId] = BridgeRequest({
            sender: msg.sender,
            recipient: _recipient,
            amount: amountAfterFee,
            chainId: _targetChainId,
            nonce: nonces[msg.sender],
            txHash: bytes32(0),
            processed: false
        });
        
        totalBridged += amountAfterFee;
        totalFees += fee;
        
        emit BridgeInitiated(requestId, msg.sender, amountAfterFee, _targetChainId);
        
        return requestId;
    }
    
    /**
     * @dev Complete bridge transfer from another chain
     */
    function completeBridge(
        bytes32 _requestId,
        address _recipient,
        uint256 _amount,
        uint256 _sourceChainId,
        bytes memory _signature
    ) external onlyValidator nonReentrant {
        require(!bridgeRequests[_requestId].processed, "Already processed");
        require(supportedChains[_sourceChainId].isActive, "Chain not supported");
        
        // Verify signature
        bytes32 messageHash = keccak256(
            abi.encodePacked(_requestId, _recipient, _amount, _sourceChainId)
        );
        address signer = messageHash.toEthSignedMessageHash().recover(_signature);
        require(validators[signer], "Invalid signature");
        
        bridgeRequests[_requestId].processed = true;
        
        // Transfer funds
        (bool success, ) = _recipient.call{value: _amount}("");
        require(success, "Transfer failed");
        
        emit BridgeCompleted(_requestId, _recipient, _amount);
    }
    
    /**
     * @dev Update validator status
     */
    function updateValidator(address _validator, bool _status) external onlyOwner {
        validators[_validator] = _status;
        emit ValidatorUpdated(_validator, _status);
    }
    
    /**
     * @dev Update bridge fee
     */
    function updateBridgeFee(uint256 _fee) external onlyOwner {
        require(_fee <= 100, "Fee too high"); // Max 1%
        bridgeFee = _fee;
    }
    
    /**
     * @dev Withdraw accumulated fees
     */
    function withdrawFees() external onlyOwner {
        uint256 amount = totalFees;
        totalFees = 0;
        
        (bool success, ) = owner().call{value: amount}("");
        require(success, "Withdrawal failed");
    }
    
    /**
     * @dev Emergency pause for a specific chain
     */
    function pauseChain(uint256 _chainId) external onlyOwner {
        supportedChains[_chainId].isActive = false;
    }
    
    /**
     * @dev Resume operations for a specific chain
     */
    function resumeChain(uint256 _chainId) external onlyOwner {
        require(supportedChains[_chainId].validator != address(0), "Chain not configured");
        supportedChains[_chainId].isActive = true;
    }
    
    /**
     * @dev Get bridge request details
     */
    function getBridgeRequest(bytes32 _requestId) external view returns (
        address sender,
        address recipient,
        uint256 amount,
        uint256 chainId,
        bool processed
    ) {
        BridgeRequest memory request = bridgeRequests[_requestId];
        return (
            request.sender,
            request.recipient,
            request.amount,
            request.chainId,
            request.processed
        );
    }
    
    /**
     * @dev Get chain configuration
     */
    function getChainConfig(uint256 _chainId) external view returns (
        bool isActive,
        uint256 minAmount,
        uint256 maxAmount,
        uint256 fee,
        address validator
    ) {
        ChainConfig memory config = supportedChains[_chainId];
        return (
            config.isActive,
            config.minAmount,
            config.maxAmount,
            config.fee,
            config.validator
        );
    }
    
    /**
     * @dev Get bridge statistics
     */
    function getBridgeStats() external view returns (
        uint256 bridged,
        uint256 fees,
        uint256 balance
    ) {
        return (
            totalBridged,
            totalFees,
            address(this).balance
        );
    }
    
    receive() external payable {}
}