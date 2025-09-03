// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title QXC Multi-Chain Bridge
 * @dev Bridge QXC tokens across Ethereum, Polygon, BSC, and Arbitrum
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function burn(uint256 amount) external;
    function mint(address to, uint256 amount) external;
}

contract QXCBridge {
    IERC20 public qxcToken;
    
    enum Chain { Ethereum, Polygon, BSC, Arbitrum, Optimism }
    
    struct BridgeRequest {
        address user;
        uint256 amount;
        Chain sourceChain;
        Chain targetChain;
        uint256 timestamp;
        bytes32 txHash;
        bool completed;
    }
    
    mapping(bytes32 => BridgeRequest) public bridgeRequests;
    mapping(Chain => uint256) public chainBalances;
    mapping(address => bool) public validators;
    
    uint256 public bridgeFee = 0.001 ether; // Bridge fee in ETH
    uint256 public minBridgeAmount = 10 * 10**18; // 10 QXC minimum
    
    event BridgeInitiated(
        bytes32 indexed requestId,
        address user,
        uint256 amount,
        Chain sourceChain,
        Chain targetChain
    );
    
    event BridgeCompleted(bytes32 indexed requestId, address user, uint256 amount);
    
    modifier onlyValidator() {
        require(validators[msg.sender], "Not a validator");
        _;
    }
    
    constructor(address _qxcToken) {
        qxcToken = IERC20(_qxcToken);
        validators[msg.sender] = true;
    }
    
    /**
     * @dev Initiate bridge transfer
     */
    function bridge(
        uint256 amount,
        Chain targetChain
    ) external payable returns (bytes32) {
        require(msg.value >= bridgeFee, "Insufficient bridge fee");
        require(amount >= minBridgeAmount, "Below minimum amount");
        require(targetChain != Chain.Ethereum, "Already on Ethereum");
        
        // Transfer QXC to bridge
        require(qxcToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        
        // Create bridge request
        bytes32 requestId = keccak256(
            abi.encodePacked(msg.sender, amount, block.timestamp)
        );
        
        bridgeRequests[requestId] = BridgeRequest({
            user: msg.sender,
            amount: amount,
            sourceChain: Chain.Ethereum,
            targetChain: targetChain,
            timestamp: block.timestamp,
            txHash: requestId,
            completed: false
        });
        
        emit BridgeInitiated(requestId, msg.sender, amount, Chain.Ethereum, targetChain);
        
        return requestId;
    }
    
    /**
     * @dev Complete bridge transfer (called by validators)
     */
    function completeBridge(bytes32 requestId) external onlyValidator {
        BridgeRequest storage request = bridgeRequests[requestId];
        require(!request.completed, "Already completed");
        
        request.completed = true;
        
        // In production, this would mint on target chain
        // For demo, we transfer back to user
        require(qxcToken.transfer(request.user, request.amount), "Transfer failed");
        
        emit BridgeCompleted(requestId, request.user, request.amount);
    }
    
    /**
     * @dev Add validator
     */
    function addValidator(address validator) external onlyValidator {
        validators[validator] = true;
    }
    
    /**
     * @dev Get bridge status
     */
    function getBridgeStatus(bytes32 requestId) external view returns (
        address user,
        uint256 amount,
        Chain targetChain,
        bool completed
    ) {
        BridgeRequest memory request = bridgeRequests[requestId];
        return (
            request.user,
            request.amount,
            request.targetChain,
            request.completed
        );
    }
    
    /**
     * @dev Withdraw bridge fees (admin only)
     */
    function withdrawFees() external onlyValidator {
        payable(msg.sender).transfer(address(this).balance);
    }
}