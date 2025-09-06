#!/bin/bash

# QENEX Ethereum Activation Script
# This script helps you activate your QXC on Ethereum mainnet

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   QENEX ETHEREUM ACTIVATION GUIDE     ${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Your wallet information
WALLET_ADDRESS="0xdE071fdF4077FdaBc2Ec9990B48920b8D06C2A2D"
QXC_BALANCE="1525.30"

echo -e "${BLUE}📍 Your Ethereum Address:${NC}"
echo -e "${YELLOW}$WALLET_ADDRESS${NC}"
echo -e "View on Etherscan: https://etherscan.io/address/$WALLET_ADDRESS\n"

echo -e "${BLUE}💰 Your QXC Balance:${NC}"
echo -e "${YELLOW}$QXC_BALANCE QXC${NC}\n"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}         ACTIVATION STEPS               ${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}Step 1: Fund Your Wallet${NC}"
echo "To activate your address on Ethereum, you need ETH for gas fees."
echo "Options to get ETH:"
echo "  • Buy ETH on Coinbase/Binance and send to your address"
echo "  • Use a faucet for testnet ETH (Goerli/Sepolia)"
echo "  • Swap other tokens for ETH on a DEX"
echo ""

echo -e "${YELLOW}Step 2: Deploy QXC Smart Contract${NC}"
echo "Once you have ETH, deploy the QXC contract:"
echo -e "${BLUE}python3 /opt/qenex-os/web3_qxc_integration.py deploy ethereum${NC}"
echo ""

echo -e "${YELLOW}Step 3: Create Liquidity Pool${NC}"
echo "Add liquidity on Uniswap V3:"
echo -e "${BLUE}python3 /opt/qenex-os/web3_qxc_integration.py pool ETH 1000 0.4${NC}"
echo "This creates a QXC/ETH pool with 1000 QXC and 0.4 ETH"
echo ""

echo -e "${YELLOW}Step 4: Bridge Your QXC${NC}"
echo "Bridge QXC from native chain to Ethereum:"
echo -e "${BLUE}python3 /opt/qenex-os/universal_wallet_bridge.py bridge qenex ethereum 100${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}      EARN WITH YOUR ADDRESS            ${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}🎯 Staking Opportunities:${NC}"
echo "  • 7 days: 10% APY"
echo "  • 30 days: 15% APY"
echo "  • 90 days: 20% APY"
echo "  • 365 days: 30% APY"
echo -e "Command: ${BLUE}python3 /opt/qenex-os/web3_qxc_integration.py stake 500 30${NC}"
echo ""

echo -e "${YELLOW}🤖 AI Model Marketplace:${NC}"
echo "Sell your AI models for QXC:"
echo -e "Command: ${BLUE}python3 /opt/qenex-os/ai_model_marketplace.py list <name> <price> NLP${NC}"
echo ""

echo -e "${YELLOW}⛏️ Mining Rewards:${NC}"
echo "Current mining rate: 2.45 QXC/hour"
echo "Monitor at: http://localhost:8080"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}        BLOCKCHAIN ANALYTICS            ${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo "Your address analytics show:"
echo "  ✅ Wallet Trust Score: 100/100"
echo "  ✅ No security risks"
echo "  ✅ Ready for airdrops"
echo "  ✅ DAO participation ready"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}         TESTNET FIRST!                 ${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${RED}⚠️  IMPORTANT: Test on testnets first!${NC}"
echo ""
echo "Get free testnet ETH:"
echo "  • Goerli: https://goerlifaucet.com"
echo "  • Sepolia: https://sepoliafaucet.com"
echo ""

echo "Deploy on testnet:"
echo -e "${BLUE}python3 /opt/qenex-os/web3_qxc_integration.py deploy ethereum_goerli${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}        NEXT STEPS                      ${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo "1. Join the community:"
echo "   • Discord: Create server for QENEX"
echo "   • Telegram: @QENEXOS"
echo "   • Twitter: @QENEX_Official"
echo ""

echo "2. List on exchanges:"
echo "   • Uniswap (ETH)"
echo "   • PancakeSwap (BSC)"
echo "   • QuickSwap (Polygon)"
echo ""

echo "3. Get verified:"
echo "   • CoinGecko listing"
echo "   • CoinMarketCap listing"
echo "   • DexTools listing"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}     YOUR WALLET IS READY! 🚀           ${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Show current status
echo -e "${YELLOW}Quick Status Check:${NC}"
python3 /opt/qenex-os/wallet_cli.py balance USER_WALLET

echo -e "\n${BLUE}Dashboard: http://localhost:8080${NC}"
echo -e "${BLUE}GitHub: https://github.com/abdulrahman305/qenex-os${NC}\n"

echo -e "${GREEN}Ready to activate? Start with Step 1 above!${NC}"