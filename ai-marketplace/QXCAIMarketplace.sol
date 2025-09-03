// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract QXCAIMarketplace {
    struct Model {
        string name;
        string ipfsHash;
        uint256 price;
        address creator;
        uint256 usageCount;
    }
    
    mapping(uint256 => Model) public models;
    uint256 public modelCount;
    
    function uploadModel(string memory _name, string memory _ipfsHash, uint256 _price) external {
        modelCount++;
        models[modelCount] = Model(_name, _ipfsHash, _price, msg.sender, 0);
    }
    
    function useModel(uint256 _modelId) external payable {
        Model storage model = models[_modelId];
        require(msg.value >= model.price, "Insufficient payment");
        
        model.usageCount++;
        payable(model.creator).transfer(msg.value * 90 / 100); // 90% to creator
    }
}