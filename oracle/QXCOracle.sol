// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract QXCOracle {
    mapping(string => uint256) public prices;
    mapping(address => bool) public feeders;
    
    modifier onlyFeeder() {
        require(feeders[msg.sender], "Not authorized");
        _;
    }
    
    constructor() {
        feeders[msg.sender] = true;
    }
    
    function updatePrice(string memory _pair, uint256 _price) external onlyFeeder {
        prices[_pair] = _price;
    }
    
    function getPrice(string memory _pair) external view returns (uint256) {
        require(prices[_pair] > 0, "No price");
        return prices[_pair];
    }
}