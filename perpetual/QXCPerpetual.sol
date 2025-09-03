// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract QXCPerpetual {
    struct Position {
        int256 size;
        uint256 margin;
        uint256 entryPrice;
        uint256 lastFunding;
    }
    
    mapping(address => Position) public positions;
    uint256 public fundingRate = 1; // 0.01%
    
    function openPosition(int256 _size, uint256 _leverage) external payable {
        require(msg.value > 0, "No margin");
        uint256 notional = uint256(abs(_size)) * _leverage;
        
        positions[msg.sender] = Position(_size, msg.value, getMarkPrice(), block.timestamp);
    }
    
    function closePosition() external {
        Position storage pos = positions[msg.sender];
        int256 pnl = calculatePnL(msg.sender);
        
        delete positions[msg.sender];
        
        if (pnl > 0) {
            payable(msg.sender).transfer(pos.margin + uint256(pnl));
        } else if (pos.margin > uint256(-pnl)) {
            payable(msg.sender).transfer(pos.margin - uint256(-pnl));
        }
    }
    
    function calculatePnL(address _trader) public view returns (int256) {
        Position memory pos = positions[_trader];
        uint256 currentPrice = getMarkPrice();
        return pos.size * int256(currentPrice - pos.entryPrice) / 1e18;
    }
    
    function getMarkPrice() public pure returns (uint256) {
        return 1000 * 1e18; // Placeholder
    }
    
    function abs(int256 x) private pure returns (int256) {
        return x >= 0 ? x : -x;
    }
}