// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
}

contract QXCMetaverseLand is ERC721, Ownable, ReentrancyGuard {
    using Counters for Counters.Counter;
    Counters.Counter private _tokenIds;
    
    struct Land {
        int256 x;
        int256 y;
        uint256 size; // 1 = small, 2 = medium, 3 = large
        uint256 price;
        bool isForSale;
        string metadataURI;
        uint256 lastDevelopmentTime;
        uint256 developmentLevel;
    }
    
    mapping(uint256 => Land) public lands;
    mapping(int256 => mapping(int256 => uint256)) public coordinateToTokenId;
    mapping(address => uint256[]) public ownerLands;
    
    IERC20 public qxcToken;
    uint256 public constant LAND_BASE_PRICE = 1000 * 10**18; // 1000 QXC
    
    event LandMinted(uint256 tokenId, int256 x, int256 y, address owner);
    event LandListedForSale(uint256 tokenId, uint256 price);
    event LandSold(uint256 tokenId, address from, address to, uint256 price);
    event LandDeveloped(uint256 tokenId, uint256 newLevel);
    
    constructor(address _qxcToken) ERC721("QXC Metaverse Land", "QXCLAND") {
        qxcToken = IERC20(_qxcToken);
    }
    
    function mintLand(int256 _x, int256 _y, uint256 _size) external nonReentrant {
        require(_size >= 1 && _size <= 3, "Invalid land size");
        require(coordinateToTokenId[_x][_y] == 0, "Land already exists");
        
        uint256 price = LAND_BASE_PRICE * _size;
        require(qxcToken.transferFrom(msg.sender, address(this), price), "Payment failed");
        
        _tokenIds.increment();
        uint256 newTokenId = _tokenIds.current();
        
        lands[newTokenId] = Land({
            x: _x,
            y: _y,
            size: _size,
            price: price,
            isForSale: false,
            metadataURI: "",
            lastDevelopmentTime: block.timestamp,
            developmentLevel: 0
        });
        
        coordinateToTokenId[_x][_y] = newTokenId;
        ownerLands[msg.sender].push(newTokenId);
        
        _safeMint(msg.sender, newTokenId);
        emit LandMinted(newTokenId, _x, _y, msg.sender);
    }
    
    function listLandForSale(uint256 _tokenId, uint256 _price) external {
        require(ownerOf(_tokenId) == msg.sender, "Not the owner");
        lands[_tokenId].isForSale = true;
        lands[_tokenId].price = _price;
        emit LandListedForSale(_tokenId, _price);
    }
    
    function buyLand(uint256 _tokenId) external nonReentrant {
        Land storage land = lands[_tokenId];
        require(land.isForSale, "Land not for sale");
        
        address previousOwner = ownerOf(_tokenId);
        require(qxcToken.transferFrom(msg.sender, previousOwner, land.price), "Payment failed");
        
        _transfer(previousOwner, msg.sender, _tokenId);
        land.isForSale = false;
        
        emit LandSold(_tokenId, previousOwner, msg.sender, land.price);
    }
    
    function developLand(uint256 _tokenId) external {
        require(ownerOf(_tokenId) == msg.sender, "Not the owner");
        Land storage land = lands[_tokenId];
        
        uint256 developmentCost = (land.developmentLevel + 1) * 500 * 10**18;
        require(qxcToken.transferFrom(msg.sender, address(this), developmentCost), "Payment failed");
        
        land.developmentLevel++;
        land.lastDevelopmentTime = block.timestamp;
        
        emit LandDeveloped(_tokenId, land.developmentLevel);
    }
}

contract QXCMetaverseItems is ERC1155, Ownable, ReentrancyGuard {
    using Counters for Counters.Counter;
    Counters.Counter private _itemIds;
    
    struct Item {
        string name;
        string category; // "avatar", "building", "vehicle", "accessory"
        uint256 price;
        uint256 maxSupply;
        uint256 currentSupply;
        bool isActive;
        uint256 rarity; // 1 = common, 2 = rare, 3 = epic, 4 = legendary
    }
    
    mapping(uint256 => Item) public items;
    mapping(address => mapping(uint256 => uint256)) public userInventory;
    
    IERC20 public qxcToken;
    
    event ItemCreated(uint256 itemId, string name, string category);
    event ItemPurchased(uint256 itemId, address buyer, uint256 amount);
    event ItemTraded(uint256 itemId, address from, address to, uint256 amount);
    
    constructor(address _qxcToken) ERC1155("https://qxc-metaverse.com/api/item/{id}") {
        qxcToken = IERC20(_qxcToken);
    }
    
    function createItem(
        string memory _name,
        string memory _category,
        uint256 _price,
        uint256 _maxSupply,
        uint256 _rarity
    ) external onlyOwner {
        _itemIds.increment();
        uint256 newItemId = _itemIds.current();
        
        items[newItemId] = Item({
            name: _name,
            category: _category,
            price: _price,
            maxSupply: _maxSupply,
            currentSupply: 0,
            isActive: true,
            rarity: _rarity
        });
        
        emit ItemCreated(newItemId, _name, _category);
    }
    
    function purchaseItem(uint256 _itemId, uint256 _amount) external nonReentrant {
        Item storage item = items[_itemId];
        require(item.isActive, "Item not active");
        require(item.currentSupply + _amount <= item.maxSupply, "Exceeds max supply");
        
        uint256 totalCost = item.price * _amount;
        require(qxcToken.transferFrom(msg.sender, address(this), totalCost), "Payment failed");
        
        item.currentSupply += _amount;
        userInventory[msg.sender][_itemId] += _amount;
        _mint(msg.sender, _itemId, _amount, "");
        
        emit ItemPurchased(_itemId, msg.sender, _amount);
    }
}

contract QXCMetaverseWorld is Ownable, ReentrancyGuard {
    struct World {
        string name;
        string description;
        address creator;
        uint256 maxPlayers;
        uint256 entryFee;
        bool isPublic;
        mapping(address => bool) hasAccess;
        mapping(address => uint256) playerScores;
    }
    
    struct Player {
        string username;
        uint256 level;
        uint256 experience;
        uint256 qxcBalance;
        uint256[] ownedLands;
        uint256[] ownedItems;
        uint256 lastActivityTime;
    }
    
    mapping(uint256 => World) public worlds;
    mapping(address => Player) public players;
    mapping(string => bool) public usernameExists;
    
    uint256 public worldCounter;
    IERC20 public qxcToken;
    QXCMetaverseLand public landContract;
    QXCMetaverseItems public itemsContract;
    
    event WorldCreated(uint256 worldId, string name, address creator);
    event PlayerJoined(address player, uint256 worldId);
    event ExperienceGained(address player, uint256 amount);
    event LevelUp(address player, uint256 newLevel);
    
    constructor(
        address _qxcToken,
        address _landContract,
        address _itemsContract
    ) {
        qxcToken = IERC20(_qxcToken);
        landContract = QXCMetaverseLand(_landContract);
        itemsContract = QXCMetaverseItems(_itemsContract);
    }
    
    function createPlayer(string memory _username) external {
        require(!usernameExists[_username], "Username taken");
        require(bytes(players[msg.sender].username).length == 0, "Player already exists");
        
        players[msg.sender] = Player({
            username: _username,
            level: 1,
            experience: 0,
            qxcBalance: 100 * 10**18, // 100 QXC welcome bonus
            ownedLands: new uint256[](0),
            ownedItems: new uint256[](0),
            lastActivityTime: block.timestamp
        });
        
        usernameExists[_username] = true;
        qxcToken.transfer(msg.sender, 100 * 10**18);
    }
    
    function createWorld(
        string memory _name,
        string memory _description,
        uint256 _maxPlayers,
        uint256 _entryFee,
        bool _isPublic
    ) external {
        worldCounter++;
        World storage newWorld = worlds[worldCounter];
        newWorld.name = _name;
        newWorld.description = _description;
        newWorld.creator = msg.sender;
        newWorld.maxPlayers = _maxPlayers;
        newWorld.entryFee = _entryFee;
        newWorld.isPublic = _isPublic;
        
        emit WorldCreated(worldCounter, _name, msg.sender);
    }
    
    function enterWorld(uint256 _worldId) external nonReentrant {
        World storage world = worlds[_worldId];
        require(world.isPublic || world.hasAccess[msg.sender], "No access");
        
        if (world.entryFee > 0) {
            require(qxcToken.transferFrom(msg.sender, world.creator, world.entryFee), "Entry fee failed");
        }
        
        emit PlayerJoined(msg.sender, _worldId);
    }
    
    function gainExperience(address _player, uint256 _amount) external onlyOwner {
        Player storage player = players[_player];
        player.experience += _amount;
        
        uint256 requiredExp = player.level * 1000;
        if (player.experience >= requiredExp) {
            player.level++;
            player.experience -= requiredExp;
            emit LevelUp(_player, player.level);
        }
        
        emit ExperienceGained(_player, _amount);
    }
}

contract QXCMetaverseEconomy is Ownable, ReentrancyGuard {
    struct Quest {
        string name;
        string description;
        uint256 rewardQXC;
        uint256 rewardExp;
        uint256 requiredLevel;
        bool isActive;
        mapping(address => bool) completed;
    }
    
    struct Trade {
        address seller;
        uint256 itemId;
        uint256 amount;
        uint256 pricePerItem;
        bool isActive;
    }
    
    mapping(uint256 => Quest) public quests;
    mapping(uint256 => Trade) public trades;
    mapping(address => uint256) public playerEarnings;
    
    uint256 public questCounter;
    uint256 public tradeCounter;
    uint256 public constant TRADING_FEE = 25; // 2.5%
    
    IERC20 public qxcToken;
    QXCMetaverseWorld public worldContract;
    QXCMetaverseItems public itemsContract;
    
    event QuestCreated(uint256 questId, string name);
    event QuestCompleted(address player, uint256 questId);
    event TradeCreated(uint256 tradeId, address seller, uint256 itemId);
    event TradeExecuted(uint256 tradeId, address buyer);
    
    constructor(
        address _qxcToken,
        address _worldContract,
        address _itemsContract
    ) {
        qxcToken = IERC20(_qxcToken);
        worldContract = QXCMetaverseWorld(_worldContract);
        itemsContract = QXCMetaverseItems(_itemsContract);
    }
    
    function createQuest(
        string memory _name,
        string memory _description,
        uint256 _rewardQXC,
        uint256 _rewardExp,
        uint256 _requiredLevel
    ) external onlyOwner {
        questCounter++;
        Quest storage newQuest = quests[questCounter];
        newQuest.name = _name;
        newQuest.description = _description;
        newQuest.rewardQXC = _rewardQXC;
        newQuest.rewardExp = _rewardExp;
        newQuest.requiredLevel = _requiredLevel;
        newQuest.isActive = true;
        
        emit QuestCreated(questCounter, _name);
    }
    
    function completeQuest(uint256 _questId) external {
        Quest storage quest = quests[_questId];
        require(quest.isActive, "Quest not active");
        require(!quest.completed[msg.sender], "Already completed");
        
        (,uint256 playerLevel,,,,,) = worldContract.players(msg.sender);
        require(playerLevel >= quest.requiredLevel, "Level too low");
        
        quest.completed[msg.sender] = true;
        playerEarnings[msg.sender] += quest.rewardQXC;
        
        if (quest.rewardQXC > 0) {
            qxcToken.transfer(msg.sender, quest.rewardQXC);
        }
        
        if (quest.rewardExp > 0) {
            worldContract.gainExperience(msg.sender, quest.rewardExp);
        }
        
        emit QuestCompleted(msg.sender, _questId);
    }
    
    function createTrade(uint256 _itemId, uint256 _amount, uint256 _pricePerItem) external {
        require(itemsContract.balanceOf(msg.sender, _itemId) >= _amount, "Insufficient items");
        
        tradeCounter++;
        trades[tradeCounter] = Trade({
            seller: msg.sender,
            itemId: _itemId,
            amount: _amount,
            pricePerItem: _pricePerItem,
            isActive: true
        });
        
        itemsContract.safeTransferFrom(msg.sender, address(this), _itemId, _amount, "");
        emit TradeCreated(tradeCounter, msg.sender, _itemId);
    }
    
    function executeTrade(uint256 _tradeId) external nonReentrant {
        Trade storage trade = trades[_tradeId];
        require(trade.isActive, "Trade not active");
        require(trade.seller != msg.sender, "Cannot buy own trade");
        
        uint256 totalPrice = trade.pricePerItem * trade.amount;
        uint256 fee = (totalPrice * TRADING_FEE) / 1000;
        uint256 sellerPayment = totalPrice - fee;
        
        require(qxcToken.transferFrom(msg.sender, trade.seller, sellerPayment), "Payment failed");
        require(qxcToken.transferFrom(msg.sender, address(this), fee), "Fee payment failed");
        
        itemsContract.safeTransferFrom(address(this), msg.sender, trade.itemId, trade.amount, "");
        trade.isActive = false;
        
        emit TradeExecuted(_tradeId, msg.sender);
    }
}