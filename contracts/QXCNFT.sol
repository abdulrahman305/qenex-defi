// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title QXC NFT Marketplace
 * @dev NFT marketplace for AI-generated art using QENEX OS
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

interface IERC721 {
    function ownerOf(uint256 tokenId) external view returns (address);
    function transferFrom(address from, address to, uint256 tokenId) external;
}

contract QXCNFT {
    IERC20 public qxcToken;
    
    struct NFT {
        uint256 tokenId;
        address creator;
        string name;
        string aiModel;
        string ipfsHash;
        uint256 mintTime;
        uint256 royaltyPercentage;
    }
    
    struct Listing {
        uint256 nftId;
        address seller;
        uint256 price;
        bool active;
    }
    
    mapping(uint256 => NFT) public nfts;
    mapping(uint256 => Listing) public listings;
    mapping(address => uint256[]) public creatorNFTs;
    mapping(address => uint256) public creatorEarnings;
    
    uint256 public nextTokenId = 1;
    uint256 public marketplaceFee = 25; // 2.5%
    uint256 public totalVolume;
    
    event NFTMinted(uint256 indexed tokenId, address creator, string name);
    event NFTListed(uint256 indexed tokenId, address seller, uint256 price);
    event NFTSold(uint256 indexed tokenId, address buyer, address seller, uint256 price);
    event RoyaltyPaid(address creator, uint256 amount);
    
    constructor(address _qxcToken) {
        qxcToken = IERC20(_qxcToken);
    }
    
    /**
     * @dev Mint AI-generated NFT
     */
    function mintNFT(
        string memory name,
        string memory aiModel,
        string memory ipfsHash,
        uint256 royaltyPercentage
    ) external returns (uint256) {
        require(royaltyPercentage <= 100, "Royalty too high"); // Max 10%
        
        uint256 tokenId = nextTokenId++;
        
        nfts[tokenId] = NFT({
            tokenId: tokenId,
            creator: msg.sender,
            name: name,
            aiModel: aiModel,
            ipfsHash: ipfsHash,
            mintTime: block.timestamp,
            royaltyPercentage: royaltyPercentage
        });
        
        creatorNFTs[msg.sender].push(tokenId);
        
        emit NFTMinted(tokenId, msg.sender, name);
        return tokenId;
    }
    
    /**
     * @dev List NFT for sale
     */
    function listNFT(uint256 tokenId, uint256 price) external {
        require(nfts[tokenId].creator == msg.sender || 
                listings[tokenId].seller == msg.sender, "Not owner");
        require(price > 0, "Invalid price");
        
        listings[tokenId] = Listing({
            nftId: tokenId,
            seller: msg.sender,
            price: price,
            active: true
        });
        
        emit NFTListed(tokenId, msg.sender, price);
    }
    
    /**
     * @dev Buy NFT with QXC
     */
    function buyNFT(uint256 tokenId) external {
        Listing storage listing = listings[tokenId];
        require(listing.active, "Not for sale");
        
        NFT memory nft = nfts[tokenId];
        uint256 price = listing.price;
        
        // Calculate fees
        uint256 marketFee = (price * marketplaceFee) / 1000;
        uint256 royalty = (price * nft.royaltyPercentage) / 1000;
        uint256 sellerAmount = price - marketFee - royalty;
        
        // Transfer QXC
        require(qxcToken.transferFrom(msg.sender, listing.seller, sellerAmount), "Payment failed");
        
        if (royalty > 0 && nft.creator != listing.seller) {
            require(qxcToken.transferFrom(msg.sender, nft.creator, royalty), "Royalty failed");
            creatorEarnings[nft.creator] += royalty;
            emit RoyaltyPaid(nft.creator, royalty);
        }
        
        // Update listing
        listing.active = false;
        address previousOwner = listing.seller;
        listing.seller = msg.sender;
        
        totalVolume += price;
        
        emit NFTSold(tokenId, msg.sender, previousOwner, price);
    }
    
    /**
     * @dev Cancel listing
     */
    function cancelListing(uint256 tokenId) external {
        require(listings[tokenId].seller == msg.sender, "Not seller");
        listings[tokenId].active = false;
    }
    
    /**
     * @dev Get NFT details
     */
    function getNFT(uint256 tokenId) external view returns (
        address creator,
        string memory name,
        string memory aiModel,
        string memory ipfsHash,
        uint256 price,
        bool forSale
    ) {
        NFT memory nft = nfts[tokenId];
        Listing memory listing = listings[tokenId];
        
        return (
            nft.creator,
            nft.name,
            nft.aiModel,
            nft.ipfsHash,
            listing.price,
            listing.active
        );
    }
    
    /**
     * @dev Get creator's NFTs
     */
    function getCreatorNFTs(address creator) external view returns (uint256[] memory) {
        return creatorNFTs[creator];
    }
    
    /**
     * @dev Get marketplace statistics
     */
    function getMarketStats() external view returns (
        uint256 totalNFTs,
        uint256 _totalVolume,
        uint256 activeListings
    ) {
        totalNFTs = nextTokenId - 1;
        _totalVolume = totalVolume;
        
        // Count active listings
        for (uint256 i = 1; i < nextTokenId; i++) {
            if (listings[i].active) {
                activeListings++;
            }
        }
    }
}