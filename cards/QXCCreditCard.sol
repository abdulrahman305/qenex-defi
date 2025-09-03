// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract QXCCreditCard {
    struct Card {
        uint256 creditLimit;
        uint256 balance;
        uint256 cashback;
        bool isActive;
    }
    
    mapping(address => Card) public cards;
    mapping(address => bool) public merchants;
    
    function issueCard(address _user, uint256 _limit) external {
        cards[_user] = Card(_limit, 0, 0, true);
    }
    
    function spend(uint256 _amount) external {
        Card storage card = cards[msg.sender];
        require(card.isActive, "Card inactive");
        require(card.balance + _amount <= card.creditLimit, "Exceeds limit");
        
        card.balance += _amount;
        card.cashback += _amount * 2 / 100; // 2% cashback
    }
    
    function payBill() external payable {
        Card storage card = cards[msg.sender];
        require(msg.value >= card.balance, "Insufficient payment");
        
        card.balance = 0;
        if (msg.value > card.balance) {
            payable(msg.sender).transfer(msg.value - card.balance);
        }
    }
}