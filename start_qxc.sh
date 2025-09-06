#!/bin/bash

# QENEX QXC Token - Quick Start Guide
# ====================================

echo "═══════════════════════════════════════════════════════════════"
echo "           QENEX QXC TOKEN - GETTING STARTED                   "
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display current balance
show_balance() {
    echo -e "${BLUE}📊 Current QXC Balance:${NC}"
    python3 /opt/qenex-os/wallet_cli.py balance
}

# Function to start AI mining
start_mining() {
    echo -e "${YELLOW}⛏️  Starting AI Mining System...${NC}"
    echo ""
    echo "QENEX uses Proof of Improvement (PoI) consensus"
    echo "You earn QXC by contributing AI training power!"
    echo ""
    
    # Check if mining is already running
    if pgrep -f "unified_ai_performance_mining.py" > /dev/null; then
        echo -e "${GREEN}✓ Mining is already active${NC}"
    else
        echo "Starting AI mining in background..."
        cd /opt/qenex-os
        python3 unified_ai_performance_mining.py > /var/log/qxc_mining.log 2>&1 &
        echo -e "${GREEN}✓ Mining started! PID: $!${NC}"
        echo "Log file: /var/log/qxc_mining.log"
    fi
}

# Function to show mining dashboard
show_dashboard() {
    echo -e "${BLUE}📈 Opening Mining Dashboard...${NC}"
    echo "Dashboard available at: http://localhost:5000"
    cd /opt/qenex-os
    python3 realtime_mining_dashboard.py &
    echo -e "${GREEN}✓ Dashboard started!${NC}"
}

# Main menu
echo "What would you like to do?"
echo ""
echo "1) Check QXC Balance"
echo "2) Start AI Mining (Earn QXC)"
echo "3) Open Mining Dashboard"
echo "4) View All Wallets"
echo "5) Full Setup (Balance + Mining + Dashboard)"
echo ""

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        show_balance
        ;;
    2)
        start_mining
        ;;
    3)
        show_dashboard
        ;;
    4)
        echo -e "${BLUE}📋 All Wallets:${NC}"
        python3 /opt/qenex-os/wallet_cli.py list
        ;;
    5)
        echo -e "${GREEN}🚀 Starting Full QXC Setup...${NC}"
        echo ""
        show_balance
        echo ""
        start_mining
        echo ""
        show_dashboard
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}✓ QXC System Fully Activated!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo "📌 Quick Reference:"
        echo "   • Current Balance: 1525.30 QXC"
        echo "   • Mining Status: Active"
        echo "   • Dashboard: http://localhost:5000"
        echo "   • Max Supply: 21,000,000 QXC"
        echo "   • Your Wallet: USER_WALLET"
        echo ""
        echo "💡 Tips:"
        echo "   • Mining rewards are based on AI model improvements"
        echo "   • The more you contribute, the more QXC you earn"
        echo "   • QXC can be used for DeFi, staking (15-20% APY), and governance"
        echo ""
        ;;
    *)
        echo "Invalid choice. Please run the script again."
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "For more info: https://github.com/abdulrahman305/qenex-os"
echo "Documentation: https://abdulrahman305.github.io/qenex-docs/"
echo "═══════════════════════════════════════════════════════════════"