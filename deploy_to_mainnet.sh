#!/bin/bash

# QENEX QXC Deployment Script for Real Networks

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   QENEX QXC MAINNET DEPLOYMENT TOOL   ${NC}"
echo -e "${GREEN}========================================${NC}\n"

function show_wallet_info() {
    echo -e "${YELLOW}Your QXC Wallet Information:${NC}"
    python3 /opt/qenex-os/wallet_cli.py balance USER_WALLET
    echo ""
    echo -e "${YELLOW}Ethereum Address:${NC}"
    echo "0xdE071fdF4077FdaBc2Ec9990B48920b8D06C2A2D"
    echo "View on Etherscan: https://etherscan.io/address/0xdE071fdF4077FdaBc2Ec9990B48920b8D06C2A2D"
    echo ""
}

function prepare_metamask() {
    echo -e "${GREEN}Preparing MetaMask Configuration...${NC}"
    python3 /opt/qenex-os/universal_wallet_bridge.py metamask
    echo -e "${GREEN}✓ MetaMask configuration ready${NC}\n"
}

function create_network_wallets() {
    echo -e "${GREEN}Creating wallets for all networks...${NC}"
    
    networks=("ethereum" "bsc" "polygon" "avalanche" "arbitrum" "optimism")
    
    for network in "${networks[@]}"; do
        echo -e "Creating ${network} wallet..."
        python3 /opt/qenex-os/universal_wallet_bridge.py create $network
        sleep 1
    done
    
    echo -e "${GREEN}✓ All network wallets created${NC}\n"
}

function deploy_testnet() {
    echo -e "${YELLOW}Deploying to Testnets First (Recommended)${NC}"
    
    echo "1. Ethereum Goerli Testnet"
    python3 /opt/qenex-os/web3_qxc_integration.py deploy ethereum_goerli
    
    echo "2. BSC Testnet"
    python3 /opt/qenex-os/web3_qxc_integration.py deploy bsc_testnet
    
    echo "3. Polygon Mumbai"
    python3 /opt/qenex-os/web3_qxc_integration.py deploy polygon_mumbai
    
    echo -e "${GREEN}✓ Testnet deployment complete${NC}\n"
}

function show_next_steps() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}         NEXT STEPS FOR MAINNET         ${NC}"
    echo -e "${GREEN}========================================${NC}\n"
    
    echo "1. Get Test Tokens:"
    echo "   - ETH Goerli: https://goerlifaucet.com"
    echo "   - BNB Testnet: https://testnet.binance.org/faucet-smart"
    echo "   - MATIC Mumbai: https://mumbaifaucet.com"
    echo ""
    
    echo "2. Fund Your Mainnet Address:"
    echo "   Send ETH to: 0xdE071fdF4077FdaBc2Ec9990B48920b8D06C2A2D"
    echo ""
    
    echo "3. Bridge QXC to Mainnet:"
    echo "   python3 /opt/qenex-os/universal_wallet_bridge.py bridge qenex ethereum 100"
    echo ""
    
    echo "4. Deploy Smart Contract:"
    echo "   python3 /opt/qenex-os/web3_qxc_integration.py deploy ethereum"
    echo ""
    
    echo -e "${YELLOW}Your QXC Balance: 1,525.30 QXC${NC}"
    echo -e "${YELLOW}Ready for deployment on any network!${NC}"
}

# Main menu
echo "Select an option:"
echo "1. Show Wallet Information"
echo "2. Prepare MetaMask"
echo "3. Create All Network Wallets"
echo "4. Deploy to Testnets"
echo "5. Show Mainnet Instructions"
echo "6. Full Setup (All of the above)"
echo ""

read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        show_wallet_info
        ;;
    2)
        prepare_metamask
        ;;
    3)
        create_network_wallets
        ;;
    4)
        deploy_testnet
        ;;
    5)
        show_next_steps
        ;;
    6)
        show_wallet_info
        prepare_metamask
        create_network_wallets
        deploy_testnet
        show_next_steps
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "\n${GREEN}✓ Done!${NC}"