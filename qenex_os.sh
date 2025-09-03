#!/bin/bash
# QENEX AI OS - Main Control Interface
# Unified operating system management

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# QENEX OS Configuration
QENEX_VERSION="3.0.0"
QENEX_ROOT="/opt/qenex-os"
QENEX_OLD="/opt/qenex"

# Display main menu
show_main_menu() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                     QENEX AI OS v3.0.0                        ║
║                Intelligent Operating System                    ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    echo -e "${WHITE}System Control Panel${NC}"
    echo -e "${WHITE}═══════════════════${NC}"
    echo ""
    echo -e "${CYAN}1.${NC} Boot QENEX OS"
    echo -e "${CYAN}2.${NC} System Status"
    echo -e "${CYAN}3.${NC} Security Center"
    echo -e "${CYAN}4.${NC} AI Control Panel"
    echo -e "${CYAN}5.${NC} Service Manager"
    echo -e "${CYAN}6.${NC} Network Configuration"
    echo -e "${CYAN}7.${NC} System Monitoring"
    echo -e "${CYAN}8.${NC} Incident Response"
    echo -e "${CYAN}9.${NC} System Recovery"
    echo -e "${CYAN}10.${NC} Shutdown System"
    echo ""
    echo -e "${CYAN}0.${NC} Exit"
    echo ""
    read -p "Select option: " choice
}

# Boot system
boot_system() {
    echo -e "${CYAN}Booting QENEX AI OS...${NC}"
    chmod +x "$QENEX_ROOT/init/qenex_init.sh"
    "$QENEX_ROOT/init/qenex_init.sh" boot
}

# System status
system_status() {
    clear
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    SYSTEM STATUS                       ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    
    # OS Info
    echo -e "${WHITE}Operating System:${NC}"
    echo -e "  Version: QENEX AI OS v$QENEX_VERSION"
    echo -e "  Kernel: $(uname -r)"
    echo -e "  Uptime: $(uptime -p)"
    echo ""
    
    # Hardware
    echo -e "${WHITE}Hardware:${NC}"
    echo -e "  CPU: $(nproc) cores @ $(cat /proc/cpuinfo | grep "MHz" | head -1 | awk '{print $4}') MHz"
    echo -e "  Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
    echo -e "  Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 " used)"}')"
    echo ""
    
    # Services
    echo -e "${WHITE}Core Services:${NC}"
    
    # Check kernel
    if pgrep -f "qenex_core.py" > /dev/null; then
        echo -e "  QENEX Kernel: ${GREEN}● Active${NC}"
    else
        echo -e "  QENEX Kernel: ${RED}○ Inactive${NC}"
    fi
    
    # Check Security Guardian
    if pgrep -f "security_guardian.sh" > /dev/null; then
        echo -e "  Security Guardian: ${GREEN}● Active${NC}"
    else
        echo -e "  Security Guardian: ${RED}○ Inactive${NC}"
    fi
    
    # Check AI Monitor
    if pgrep -f "ai_security_trainer.py" > /dev/null; then
        echo -e "  AI Monitor: ${GREEN}● Active${NC}"
    else
        echo -e "  AI Monitor: ${RED}○ Inactive${NC}"
    fi
    
    # Network
    echo ""
    echo -e "${WHITE}Network:${NC}"
    echo -e "  IP Address: $(hostname -I | awk '{print $1}')"
    echo -e "  Active Connections: $(ss -tun | wc -l)"
    echo -e "  Firewall Rules: $(iptables -L -n 2>/dev/null | grep -c DROP || echo 0)"
    
    # Security
    echo ""
    echo -e "${WHITE}Security Status:${NC}"
    threat_level=$([ -f "/var/log/qenex-os/alerts.json" ] && tail -1 /var/log/qenex-os/alerts.json 2>/dev/null | grep -o '"level":"[^"]*"' | cut -d'"' -f4 || echo "NORMAL")
    
    case "$threat_level" in
        CRITICAL)
            echo -e "  Threat Level: ${RED}● CRITICAL${NC}"
            ;;
        HIGH)
            echo -e "  Threat Level: ${YELLOW}● HIGH${NC}"
            ;;
        *)
            echo -e "  Threat Level: ${GREEN}● NORMAL${NC}"
            ;;
    esac
    
    incidents=$(ls /opt/qenex/incident_response/evidence 2>/dev/null | wc -l || echo 0)
    echo -e "  Recent Incidents: $incidents"
    
    echo ""
    read -p "Press Enter to continue..."
}

# Security Center
security_center() {
    clear
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                   SECURITY CENTER                      ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    
    echo -e "${WHITE}1.${NC} View Security Report"
    echo -e "${WHITE}2.${NC} Run Security Scan"
    echo -e "${WHITE}3.${NC} Configure Firewall"
    echo -e "${WHITE}4.${NC} View Threat Log"
    echo -e "${WHITE}5.${NC} Emergency Lockdown"
    echo -e "${WHITE}6.${NC} Back to Main Menu"
    echo ""
    
    read -p "Select option: " sec_choice
    
    case $sec_choice in
        1)
            if [ -f "/opt/qenex/security_guardian.sh" ]; then
                /opt/qenex/security_guardian.sh report
            fi
            ;;
        2)
            echo -e "${CYAN}Running security scan...${NC}"
            if [ -f "/opt/qenex/security_guardian.sh" ]; then
                /opt/qenex/security_guardian.sh check
            fi
            ;;
        3)
            echo -e "${CYAN}Current firewall rules:${NC}"
            iptables -L -n -v
            ;;
        4)
            echo -e "${CYAN}Recent threats:${NC}"
            tail -20 /var/log/qenex/security_alerts.log 2>/dev/null || echo "No recent threats"
            ;;
        5)
            echo -e "${RED}ACTIVATING EMERGENCY LOCKDOWN${NC}"
            # Block all incoming except SSH from specific IP
            iptables -P INPUT DROP
            iptables -A INPUT -i lo -j ACCEPT
            iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
            echo -e "${GREEN}Lockdown activated${NC}"
            ;;
        6)
            return
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    security_center
}

# AI Control Panel
ai_control() {
    clear
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                   AI CONTROL PANEL                     ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    
    # AI Status
    if [ -f "/opt/qenex/ai_security_trainer.py" ]; then
        accuracy=$(python3 /opt/qenex/ai_security_trainer.py accuracy 2>/dev/null | grep -oP '\d+\.?\d*' || echo "0")
        echo -e "${WHITE}AI Model Status:${NC}"
        echo -e "  Model Accuracy: ${YELLOW}${accuracy}%${NC}"
        echo -e "  Training Mode: ${GREEN}Active${NC}"
        echo ""
    fi
    
    echo -e "${WHITE}1.${NC} Start AI Monitoring"
    echo -e "${WHITE}2.${NC} Analyze Current Threats"
    echo -e "${WHITE}3.${NC} Train AI Model"
    echo -e "${WHITE}4.${NC} View AI Report"
    echo -e "${WHITE}5.${NC} Configure AI Settings"
    echo -e "${WHITE}6.${NC} Back to Main Menu"
    echo ""
    
    read -p "Select option: " ai_choice
    
    case $ai_choice in
        1)
            echo -e "${CYAN}Starting AI monitoring...${NC}"
            python3 /opt/qenex/ai_security_trainer.py monitor &
            echo -e "${GREEN}AI monitoring started${NC}"
            ;;
        2)
            python3 /opt/qenex/ai_security_trainer.py analyze
            ;;
        3)
            echo -e "${CYAN}Training AI model...${NC}"
            python3 /opt/qenex/ai_security_trainer.py train
            ;;
        4)
            python3 /opt/qenex/ai_security_trainer.py report
            ;;
        5)
            echo -e "${CYAN}AI Configuration${NC}"
            echo "Auto-training: Enabled"
            echo "Threat detection: Enabled"
            echo "Learning rate: Adaptive"
            ;;
        6)
            return
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    ai_control
}

# Service Manager
service_manager() {
    clear
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                   SERVICE MANAGER                      ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    
    echo -e "${WHITE}Services:${NC}"
    echo ""
    
    # List services
    services=(
        "qenex-kernel:QENEX AI Kernel:qenex_core.py"
        "security-guardian:Security Guardian:security_guardian.sh"
        "ai-monitor:AI Monitor:ai_security_trainer.py"
        "incident-response:Incident Response:incident_response_playbook.sh"
        "web-api:Web API:web_api.py"
    )
    
    for service in "${services[@]}"; do
        IFS=':' read -r svc_id svc_name svc_process <<< "$service"
        
        if pgrep -f "$svc_process" > /dev/null 2>&1; then
            echo -e "  ${GREEN}●${NC} $svc_name"
        else
            echo -e "  ${RED}○${NC} $svc_name"
        fi
    done
    
    echo ""
    echo -e "${WHITE}Actions:${NC}"
    echo -e "${WHITE}1.${NC} Start All Services"
    echo -e "${WHITE}2.${NC} Stop All Services"
    echo -e "${WHITE}3.${NC} Restart All Services"
    echo -e "${WHITE}4.${NC} View Service Logs"
    echo -e "${WHITE}5.${NC} Back to Main Menu"
    echo ""
    
    read -p "Select option: " svc_choice
    
    case $svc_choice in
        1)
            echo -e "${CYAN}Starting all services...${NC}"
            "$QENEX_ROOT/init/qenex_init.sh" boot
            ;;
        2)
            echo -e "${YELLOW}Stopping all services...${NC}"
            pkill -f "qenex_core.py" 2>/dev/null || true
            pkill -f "security_guardian.sh" 2>/dev/null || true
            pkill -f "ai_security_trainer.py" 2>/dev/null || true
            echo -e "${GREEN}Services stopped${NC}"
            ;;
        3)
            echo -e "${CYAN}Restarting all services...${NC}"
            $0 service_manager 2
            sleep 2
            $0 service_manager 1
            ;;
        4)
            echo -e "${CYAN}Service Logs:${NC}"
            tail -20 /var/log/qenex-os/kernel.log 2>/dev/null
            ;;
        5)
            return
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    service_manager
}

# System monitoring
system_monitoring() {
    clear
    while true; do
        clear
        echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${CYAN}                  SYSTEM MONITORING                      ${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
        echo ""
        
        # CPU
        cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
        echo -e "${WHITE}CPU Usage:${NC} ${cpu_usage}%"
        
        # Memory
        mem_usage=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
        echo -e "${WHITE}Memory Usage:${NC} ${mem_usage}%"
        
        # Disk
        disk_usage=$(df -h / | tail -1 | awk '{print $5}')
        echo -e "${WHITE}Disk Usage:${NC} ${disk_usage}"
        
        # Network
        connections=$(ss -tun | wc -l)
        echo -e "${WHITE}Network Connections:${NC} $connections"
        
        # Processes
        processes=$(ps aux | wc -l)
        echo -e "${WHITE}Running Processes:${NC} $processes"
        
        # Load Average
        load_avg=$(uptime | awk -F'load average:' '{print $2}')
        echo -e "${WHITE}Load Average:${NC}$load_avg"
        
        echo ""
        echo -e "${WHITE}Top Processes:${NC}"
        ps aux | head -6 | tail -5
        
        echo ""
        echo -e "${YELLOW}Press Ctrl+C to exit${NC}"
        sleep 5
    done
}

# Incident Response
incident_response() {
    clear
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                 INCIDENT RESPONSE                       ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ -f "/opt/qenex/incident_response_playbook.sh" ]; then
        /opt/qenex/incident_response_playbook.sh
    else
        echo -e "${RED}Incident Response system not found${NC}"
    fi
    
    echo ""
    read -p "Press Enter to continue..."
}

# System Recovery
system_recovery() {
    clear
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                  SYSTEM RECOVERY                        ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    
    echo -e "${WHITE}Recovery Options:${NC}"
    echo -e "${WHITE}1.${NC} Restore Default Configuration"
    echo -e "${WHITE}2.${NC} Clear Threat Database"
    echo -e "${WHITE}3.${NC} Reset AI Models"
    echo -e "${WHITE}4.${NC} Emergency Mode"
    echo -e "${WHITE}5.${NC} Full System Reset"
    echo -e "${WHITE}6.${NC} Back to Main Menu"
    echo ""
    
    read -p "Select option: " rec_choice
    
    case $rec_choice in
        1)
            echo -e "${CYAN}Restoring default configuration...${NC}"
            rm -f "$QENEX_ROOT/config/system.json"
            echo -e "${GREEN}Configuration restored${NC}"
            ;;
        2)
            echo -e "${CYAN}Clearing threat database...${NC}"
            rm -f /var/log/qenex-os/alerts.json
            rm -f /var/log/qenex/security_alerts.log
            echo -e "${GREEN}Threat database cleared${NC}"
            ;;
        3)
            echo -e "${CYAN}Resetting AI models...${NC}"
            rm -f "$QENEX_ROOT/ai-models/"*.pkl
            echo -e "${GREEN}AI models reset${NC}"
            ;;
        4)
            echo -e "${YELLOW}Entering emergency mode...${NC}"
            "$QENEX_ROOT/init/qenex_init.sh" emergency
            ;;
        5)
            echo -e "${RED}WARNING: This will reset the entire system!${NC}"
            read -p "Are you sure? (yes/no): " confirm
            if [ "$confirm" = "yes" ]; then
                rm -rf "$QENEX_ROOT/runtime/"*
                rm -rf "$QENEX_ROOT/config/"*
                rm -rf /var/log/qenex-os/*
                echo -e "${GREEN}System reset complete${NC}"
            fi
            ;;
        6)
            return
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    system_recovery
}

# Shutdown system
shutdown_system() {
    echo -e "${YELLOW}Shutting down QENEX AI OS...${NC}"
    
    # Stop all services
    echo -e "${CYAN}Stopping services...${NC}"
    pkill -f "qenex_core.py" 2>/dev/null || true
    pkill -f "security_guardian.sh" 2>/dev/null || true
    pkill -f "ai_security_trainer.py" 2>/dev/null || true
    pkill -f "web_api.py" 2>/dev/null || true
    
    echo -e "${GREEN}QENEX AI OS shutdown complete${NC}"
    exit 0
}

# Install/Update QENEX OS
install_qenex_os() {
    echo -e "${CYAN}Installing QENEX AI OS v3.0.0...${NC}"
    
    # Create directory structure
    mkdir -p "$QENEX_ROOT"/{kernel,init,services,modules,config,runtime,ai-models,security}
    mkdir -p /var/log/qenex-os
    
    # Set permissions
    chmod 755 "$QENEX_ROOT"
    chmod +x "$QENEX_ROOT"/*.sh 2>/dev/null || true
    chmod +x "$QENEX_ROOT"/*/*.sh 2>/dev/null || true
    chmod +x "$QENEX_ROOT"/*/*.py 2>/dev/null || true
    
    # Create symlink for qenex-os command
    ln -sf "$0" /usr/local/bin/qenex-os 2>/dev/null || true
    
    echo -e "${GREEN}QENEX AI OS installed successfully!${NC}"
    echo -e "${CYAN}Run 'qenex-os' to start${NC}"
}

# Main execution
main() {
    # Check if installation needed
    if [ ! -d "$QENEX_ROOT/kernel" ]; then
        install_qenex_os
    fi
    
    while true; do
        show_main_menu
        
        case $choice in
            1) boot_system ;;
            2) system_status ;;
            3) security_center ;;
            4) ai_control ;;
            5) service_manager ;;
            6) config_network ;;
            7) system_monitoring ;;
            8) incident_response ;;
            9) system_recovery ;;
            10) shutdown_system ;;
            0) exit 0 ;;
            *) echo -e "${RED}Invalid option${NC}" ;;
        esac
    done
}

# Handle command line arguments
case "$1" in
    boot)
        boot_system
        ;;
    status)
        system_status
        ;;
    install)
        install_qenex_os
        ;;
    *)
        main
        ;;
esac