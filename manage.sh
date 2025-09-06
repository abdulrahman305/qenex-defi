#!/bin/bash
# QENEX OS Management Script

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function header() {
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}       QENEX OS Management Console          ${NC}"
    echo -e "${GREEN}============================================${NC}"
}

function status() {
    header
    echo -e "\n${YELLOW}System Status:${NC}"
    
    # Check processes
    echo -e "\n${YELLOW}Running Processes:${NC}"
    ps aux | grep -E "qenex|mining|wallet" | grep -v grep | wc -l | xargs echo "QENEX Processes:"
    
    # Check resources
    echo -e "\n${YELLOW}Resource Usage:${NC}"
    free -h | grep Mem | awk '{print "Memory: " $3 " / " $2 " (" int($3/$2 * 100) "%)"}'
    df -h / | tail -1 | awk '{print "Disk: " $3 " / " $2 " (" $5 ")"}'
    
    # Check services
    echo -e "\n${YELLOW}Service Status:${NC}"
    curl -s http://localhost:5000 > /dev/null 2>&1 && echo "✓ Monitoring Dashboard: Running" || echo "✗ Monitoring Dashboard: Stopped"
    curl -s http://localhost:8000 > /dev/null 2>&1 && echo "✓ API Server: Running" || echo "✗ API Server: Stopped"
    ps aux | grep -q "[q]enex_core_integrated" && echo "✓ Core System: Running" || echo "✗ Core System: Stopped"
}

function start() {
    header
    echo -e "${GREEN}Starting QENEX OS...${NC}\n"
    
    # Stop old processes first
    stop_quiet
    
    # Start core system
    echo "Starting core system..."
    cd /opt/qenex-os
    python3 qenex_core_integrated.py > /var/log/qenex-core.log 2>&1 &
    
    # Start monitoring
    echo "Starting monitoring dashboard..."
    python3 monitoring_dashboard.py > /var/log/qenex-monitor.log 2>&1 &
    
    sleep 3
    echo -e "\n${GREEN}QENEX OS started successfully!${NC}"
    echo "Dashboard: http://localhost:5000"
}

function stop() {
    header
    echo -e "${RED}Stopping QENEX OS...${NC}\n"
    
    pkill -f "qenex_core_integrated"
    pkill -f "monitoring_dashboard"
    pkill -f "unified_qxc_system"
    pkill -f "real_ai_mining"
    pkill -f "unified_wallet_system"
    pkill -f "hierarchical_wallet_system"
    pkill -f "unified_ai_performance_mining"
    pkill -f "cumulative_distributed_model"
    
    echo -e "${GREEN}All QENEX processes stopped.${NC}"
}

function stop_quiet() {
    pkill -f "qenex_core_integrated" 2>/dev/null
    pkill -f "monitoring_dashboard" 2>/dev/null
    pkill -f "unified_qxc_system" 2>/dev/null
    pkill -f "real_ai_mining" 2>/dev/null
    pkill -f "unified_wallet_system" 2>/dev/null
    pkill -f "hierarchical_wallet_system" 2>/dev/null
    pkill -f "unified_ai_performance_mining" 2>/dev/null
    pkill -f "cumulative_distributed_model" 2>/dev/null
}

function restart() {
    stop
    sleep 2
    start
}

function logs() {
    header
    echo -e "${YELLOW}Recent logs:${NC}\n"
    
    if [ -f /var/log/qenex-core.log ]; then
        echo "=== Core System Logs ==="
        tail -20 /var/log/qenex-core.log
    fi
    
    if [ -f /var/log/qenex-monitor.log ]; then
        echo -e "\n=== Monitor Logs ==="
        tail -20 /var/log/qenex-monitor.log
    fi
}

function cleanup() {
    header
    echo -e "${YELLOW}Cleaning up duplicate processes...${NC}\n"
    
    # Kill duplicate agents
    pkill -f "monitor_agent.py"
    pkill -f "security_agent.py"
    pkill -f "automation_agent.py"
    pkill -f "optimizer_agent.py"
    
    # Kill other duplicates
    pkill -f "autonomous_coordination_system"
    pkill -f "autonomous_system_controller"
    pkill -f "comprehensive_defense_system"
    
    echo -e "${GREEN}Cleanup complete!${NC}"
}

function install() {
    header
    echo -e "${YELLOW}Installing dependencies...${NC}\n"
    
    pip3 install -q numpy psutil cryptography 2>/dev/null
    pip3 install -q flask flask-cors flask-socketio 2>/dev/null
    
    echo -e "${GREEN}Dependencies installed!${NC}"
}

function help() {
    header
    echo -e "\nUsage: $0 {start|stop|restart|status|logs|cleanup|install|help}"
    echo ""
    echo "Commands:"
    echo "  start    - Start QENEX OS core system"
    echo "  stop     - Stop all QENEX processes"
    echo "  restart  - Restart the system"
    echo "  status   - Show system status"
    echo "  logs     - Show recent logs"
    echo "  cleanup  - Clean up duplicate processes"
    echo "  install  - Install dependencies"
    echo "  help     - Show this help message"
}

# Main script logic
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    cleanup)
        cleanup
        ;;
    install)
        install
        ;;
    help)
        help
        ;;
    *)
        help
        exit 1
        ;;
esac

exit 0