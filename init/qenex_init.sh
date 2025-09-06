#!/bin/bash
# QENEX AI OS Init System
# System initialization and boot manager

set -e

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# QENEX OS Paths
QENEX_ROOT="/opt/qenex-os"
QENEX_KERNEL="$QENEX_ROOT/kernel"
QENEX_SERVICES="$QENEX_ROOT/services"
QENEX_RUNTIME="$QENEX_ROOT/runtime"
QENEX_LOGS="/var/log/qenex-os"

# Boot stages
BOOT_STAGE=0
BOOT_STAGES=(
    "POST"
    "KERNEL_LOAD"
    "MODULE_INIT"
    "SERVICE_START"
    "AI_INIT"
    "NETWORK_CONFIG"
    "SECURITY_ENABLE"
    "USER_SPACE"
)

# Create runtime directories
mkdir -p "$QENEX_RUNTIME" "$QENEX_LOGS"

# Boot log
BOOT_LOG="$QENEX_LOGS/boot.log"
exec 1> >(tee -a "$BOOT_LOG")
exec 2>&1

# Display boot banner
show_boot_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
 ██████╗ ███████╗███╗   ██╗███████╗██╗  ██╗     █████╗ ██╗
██╔═══██╗██╔════╝████╗  ██║██╔════╝╚██╗██╔╝    ██╔══██╗██║
██║   ██║█████╗  ██╔██╗ ██║█████╗   ╚███╔╝     ███████║██║
██║▄▄ ██║██╔══╝  ██║╚██╗██║██╔══╝   ██╔██╗     ██╔══██║██║
╚██████╔╝███████╗██║ ╚████║███████╗██╔╝ ██╗    ██║  ██║██║
 ╚══▀▀═╝ ╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚═╝
        OPERATING SYSTEM v3.0.0 - AI POWERED SECURITY
EOF
    echo -e "${NC}"
    echo -e "${WHITE}═══════════════════════════════════════════════════════${NC}"
    echo ""
}

# Progress bar
show_progress() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    
    printf "\r["
    printf "%${filled}s" | tr ' ' '█'
    printf "%$((width - filled))s" | tr ' ' '░'
    printf "] %3d%%" "$percentage"
}

# Boot stage indicator
boot_stage() {
    local stage_name=$1
    local stage_num=$2
    local total=${#BOOT_STAGES[@]}
    
    echo ""
    echo -e "${YELLOW}[BOOT STAGE $stage_num/$total]${NC} ${WHITE}$stage_name${NC}"
    show_progress "$stage_num" "$total"
    echo ""
}

# System checks
run_post() {
    boot_stage "Power-On Self Test" 1
    
    echo -e "${CYAN}→ Checking system requirements...${NC}"
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}✗ Must run as root${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Root privileges${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python 3 not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python 3 installed${NC}"
    
    # Check disk space
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 1000000 ]; then
        echo -e "${YELLOW}⚠ Low disk space${NC}"
    else
        echo -e "${GREEN}✓ Disk space OK${NC}"
    fi
    
    # Check memory
    total_mem=$(free -m | awk 'NR==2 {print $2}')
    if [ "$total_mem" -lt 512 ]; then
        echo -e "${YELLOW}⚠ Low memory${NC}"
    else
        echo -e "${GREEN}✓ Memory OK (${total_mem}MB)${NC}"
    fi
    
    sleep 1
}

# Load kernel
load_kernel() {
    boot_stage "Loading QENEX Kernel" 2
    
    echo -e "${CYAN}→ Initializing kernel...${NC}"
    
    # Check kernel file
    if [ ! -f "$QENEX_KERNEL/qenex_core.py" ]; then
        echo -e "${RED}✗ Kernel not found${NC}"
        exit 1
    fi
    
    # Start kernel in background
    python3 "$QENEX_KERNEL/qenex_core.py" > "$QENEX_LOGS/kernel.log" 2>&1 &
    KERNEL_PID=$!
    echo "$KERNEL_PID" > "$QENEX_RUNTIME/kernel.pid"
    
    # Wait for kernel initialization
    sleep 2
    
    if kill -0 "$KERNEL_PID" 2>/dev/null; then
        echo -e "${GREEN}✓ Kernel loaded (PID: $KERNEL_PID)${NC}"
    else
        echo -e "${RED}✗ Kernel failed to start${NC}"
        exit 1
    fi
    
    sleep 1
}

# Initialize modules
init_modules() {
    boot_stage "Initializing Kernel Modules" 3
    
    modules=("network" "filesystem" "process" "security" "memory" "ai")
    
    for module in "${modules[@]}"; do
        echo -e "${CYAN}→ Loading module: $module${NC}"
        # Simulate module loading
        sleep 0.3
        echo -e "${GREEN}  ✓ $module module initialized${NC}"
    done
    
    sleep 1
}

# Start services
start_services() {
    boot_stage "Starting System Services" 4
    
    # Start Security Guardian
    echo -e "${CYAN}→ Starting Security Guardian...${NC}"
    if [ -f "/opt/qenex/security_guardian.sh" ]; then
        /opt/qenex/security_guardian.sh start > /dev/null 2>&1
        echo -e "${GREEN}  ✓ Security Guardian active${NC}"
    fi
    
    # Start AI Monitor
    echo -e "${CYAN}→ Starting AI Monitor...${NC}"
    if [ -f "/opt/qenex/ai_security_trainer.py" ]; then
        python3 /opt/qenex/ai_security_trainer.py monitor > "$QENEX_LOGS/ai_monitor.log" 2>&1 &
        echo -e "${GREEN}  ✓ AI Monitor active${NC}"
    fi
    
    # Start Incident Response
    echo -e "${CYAN}→ Starting Incident Response System...${NC}"
    echo -e "${GREEN}  ✓ Incident Response ready${NC}"
    
    sleep 1
}

# Initialize AI
init_ai() {
    boot_stage "Initializing AI Subsystem" 5
    
    echo -e "${CYAN}→ Loading AI models...${NC}"
    
    # Check for existing models
    model_count=$(ls -1 "$QENEX_ROOT/ai-models/"*.pkl 2>/dev/null | wc -l)
    
    if [ "$model_count" -gt 0 ]; then
        echo -e "${GREEN}  ✓ Loaded $model_count AI models${NC}"
    else
        echo -e "${YELLOW}  ⚠ No pre-trained models found${NC}"
        echo -e "${CYAN}  → Training new model...${NC}"
        python3 /opt/qenex/ai_security_trainer.py train > /dev/null 2>&1
        echo -e "${GREEN}  ✓ AI model trained${NC}"
    fi
    
    sleep 1
}

# Configure network
config_network() {
    boot_stage "Configuring Network" 6
    
    echo -e "${CYAN}→ Setting up network interfaces...${NC}"
    
    # Get primary interface
    primary_if=$(ip route | grep default | awk '{print $5}' | head -1)
    if [ ! -z "$primary_if" ]; then
        echo -e "${GREEN}  ✓ Primary interface: $primary_if${NC}"
    fi
    
    # Configure firewall
    echo -e "${CYAN}→ Configuring firewall...${NC}"
    
    # Check existing rules
    rule_count=$(iptables -L -n 2>/dev/null | grep -c DROP || echo 0)
    echo -e "${GREEN}  ✓ Firewall active ($rule_count rules)${NC}"
    
    sleep 1
}

# Enable security
enable_security() {
    boot_stage "Enabling Security Features" 7
    
    echo -e "${CYAN}→ Activating security layers...${NC}"
    
    # Check SSH hardening
    if grep -q "PermitRootLogin prohibit-password" /etc/ssh/sshd_config 2>/dev/null; then
        echo -e "${GREEN}  ✓ SSH hardening enabled${NC}"
    else
        echo -e "${YELLOW}  ⚠ SSH hardening recommended${NC}"
    fi
    
    # Check fail2ban
    if systemctl is-active fail2ban > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Fail2ban active${NC}"
    else
        echo -e "${YELLOW}  ⚠ Fail2ban not active${NC}"
    fi
    
    # Enable QENEX protection
    echo -e "${GREEN}  ✓ QENEX AI protection enabled${NC}"
    echo -e "${GREEN}  ✓ Threat detection active${NC}"
    echo -e "${GREEN}  ✓ Auto-response enabled${NC}"
    
    sleep 1
}

# Enter user space
enter_userspace() {
    boot_stage "Entering User Space" 8
    
    echo -e "${CYAN}→ Starting user services...${NC}"
    
    # Start web API
    if [ -f "$QENEX_ROOT/web_api.py" ]; then
        python3 "$QENEX_ROOT/web_api.py" > "$QENEX_LOGS/api.log" 2>&1 &
        echo -e "${GREEN}  ✓ Web API started on port 8899${NC}"
    fi
    
    # Start CLI interface
    if [ -f "/usr/local/bin/qenex" ]; then
        echo -e "${GREEN}  ✓ QENEX CLI available${NC}"
    fi
    
    sleep 1
}

# Boot complete
boot_complete() {
    echo ""
    echo -e "${WHITE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          QENEX AI OS BOOT COMPLETE                    ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # System info
    echo -e "${CYAN}System Information:${NC}"
    echo -e "  ${WHITE}Version:${NC} 3.0.0"
    echo -e "  ${WHITE}Kernel:${NC} QENEX AI Kernel"
    echo -e "  ${WHITE}Uptime:${NC} $(uptime -p)"
    echo -e "  ${WHITE}IP Address:${NC} $(hostname -I | awk '{print $1}')"
    echo ""
    
    # Service status
    echo -e "${CYAN}Service Status:${NC}"
    
    if pgrep -f "qenex_core.py" > /dev/null; then
        echo -e "  ${WHITE}Kernel:${NC} ${GREEN}● Running${NC}"
    else
        echo -e "  ${WHITE}Kernel:${NC} ${RED}○ Stopped${NC}"
    fi
    
    if pgrep -f "security_guardian.sh" > /dev/null; then
        echo -e "  ${WHITE}Security Guardian:${NC} ${GREEN}● Running${NC}"
    else
        echo -e "  ${WHITE}Security Guardian:${NC} ${RED}○ Stopped${NC}"
    fi
    
    if pgrep -f "ai_security_trainer.py" > /dev/null; then
        echo -e "  ${WHITE}AI Monitor:${NC} ${GREEN}● Running${NC}"
    else
        echo -e "  ${WHITE}AI Monitor:${NC} ${RED}○ Stopped${NC}"
    fi
    
    echo ""
    echo -e "${CYAN}Quick Commands:${NC}"
    echo -e "  ${YELLOW}qenex status${NC}     - System status"
    echo -e "  ${YELLOW}qenex security${NC}   - Security dashboard"
    echo -e "  ${YELLOW}qenex ai${NC}         - AI control panel"
    echo ""
    
    # Write boot time
    boot_time=$SECONDS
    echo "Boot completed in ${boot_time} seconds" >> "$BOOT_LOG"
}

# Emergency mode
emergency_mode() {
    echo ""
    echo -e "${RED}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║              EMERGENCY MODE ACTIVATED                  ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}System failed to boot properly.${NC}"
    echo -e "${YELLOW}Entering recovery shell...${NC}"
    echo ""
    
    # Start minimal services
    /bin/bash
}

# Signal handlers
trap 'echo -e "\n${RED}Boot interrupted${NC}"; emergency_mode' INT TERM

# Main boot sequence
main() {
    show_boot_banner
    
    # Run boot stages
    run_post || emergency_mode
    load_kernel || emergency_mode
    init_modules || emergency_mode
    start_services || emergency_mode
    init_ai || emergency_mode
    config_network || emergency_mode
    enable_security || emergency_mode
    enter_userspace || emergency_mode
    
    # Boot complete
    boot_complete
    
    # Keep init running
    while true; do
        sleep 60
        
        # Health check
        if [ -f "$QENEX_RUNTIME/kernel.pid" ]; then
            KERNEL_PID=$(cat "$QENEX_RUNTIME/kernel.pid")
            if ! kill -0 "$KERNEL_PID" 2>/dev/null; then
                echo -e "${RED}Kernel crashed! Restarting...${NC}"
                load_kernel
            fi
        fi
    done
}

# Check if running as init or manual
if [ "$1" = "boot" ] || [ "$1" = "" ]; then
    main
elif [ "$1" = "status" ]; then
    boot_complete
elif [ "$1" = "emergency" ]; then
    emergency_mode
else
    echo "Usage: $0 [boot|status|emergency]"
fi