#!/bin/bash
# QENEX Unified AI OS - Installation Script
# Version: 3.0.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
QENEX_ROOT="/opt/qenex-os"
BACKUP_DIR="/opt/qenex-backup-$(date +%Y%m%d-%H%M%S)"
MIN_PYTHON_VERSION="3.8"
MIN_MEMORY_GB=8
MIN_DISK_GB=50

# Banner
print_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║              QENEX UNIFIED AI OS INSTALLER                    ║
║                     Version 3.0.0                             ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}This script must be run as root${NC}"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    echo -e "${BLUE}Checking system requirements...${NC}"
    
    # Check OS
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        echo -e "${RED}This installer only supports Linux${NC}"
        exit 1
    fi
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        if (( $(echo "$PYTHON_VERSION < $MIN_PYTHON_VERSION" | bc -l) )); then
            echo -e "${RED}Python $MIN_PYTHON_VERSION or higher is required (found $PYTHON_VERSION)${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"
    else
        echo -e "${RED}Python3 is not installed${NC}"
        exit 1
    fi
    
    # Check memory
    TOTAL_MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [ $TOTAL_MEM_GB -lt $MIN_MEMORY_GB ]; then
        echo -e "${YELLOW}⚠ Warning: System has ${TOTAL_MEM_GB}GB RAM (recommended: ${MIN_MEMORY_GB}GB)${NC}"
    else
        echo -e "${GREEN}✓ Memory: ${TOTAL_MEM_GB}GB${NC}"
    fi
    
    # Check disk space
    AVAILABLE_DISK_GB=$(df /opt | awk 'NR==2 {print int($4/1048576)}')
    if [ $AVAILABLE_DISK_GB -lt $MIN_DISK_GB ]; then
        echo -e "${RED}Insufficient disk space: ${AVAILABLE_DISK_GB}GB available (required: ${MIN_DISK_GB}GB)${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ Disk space: ${AVAILABLE_DISK_GB}GB available${NC}"
    fi
    
    # Check for required commands
    REQUIRED_COMMANDS=("git" "curl" "tar")
    for cmd in "${REQUIRED_COMMANDS[@]}"; do
        if command -v $cmd &> /dev/null; then
            echo -e "${GREEN}✓ $cmd installed${NC}"
        else
            echo -e "${YELLOW}⚠ $cmd not found, will install${NC}"
            MISSING_COMMANDS+=($cmd)
        fi
    done
}

# Install missing dependencies
install_dependencies() {
    echo -e "${BLUE}Installing dependencies...${NC}"
    
    # Detect package manager
    if command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt-get"
        UPDATE_CMD="apt-get update"
        INSTALL_CMD="apt-get install -y"
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
        UPDATE_CMD="yum check-update"
        INSTALL_CMD="yum install -y"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
        UPDATE_CMD="dnf check-update"
        INSTALL_CMD="dnf install -y"
    else
        echo -e "${RED}Unsupported package manager${NC}"
        exit 1
    fi
    
    # Update package lists
    echo "Updating package lists..."
    $UPDATE_CMD || true
    
    # Install system packages
    PACKAGES="python3-pip python3-venv git curl wget vim htop net-tools"
    
    if [ "$PKG_MANAGER" = "apt-get" ]; then
        $INSTALL_CMD $PACKAGES python3-dev build-essential
    else
        $INSTALL_CMD $PACKAGES python3-devel gcc
    fi
    
    # Install Docker (optional)
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}Docker not installed. Install it? (y/n)${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            curl -fsSL https://get.docker.com | sh
            usermod -aG docker $SUDO_USER 2>/dev/null || true
        fi
    fi
    
    # Install kubectl (optional)
    if ! command -v kubectl &> /dev/null; then
        echo -e "${YELLOW}kubectl not installed. Install it? (y/n)${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
            install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
            rm kubectl
        fi
    fi
}

# Backup existing installation
backup_existing() {
    if [ -d "$QENEX_ROOT" ]; then
        echo -e "${YELLOW}Existing installation found. Creating backup...${NC}"
        mkdir -p "$BACKUP_DIR"
        cp -r "$QENEX_ROOT"/* "$BACKUP_DIR"/ 2>/dev/null || true
        echo -e "${GREEN}✓ Backup created at $BACKUP_DIR${NC}"
    fi
}

# Install QENEX OS
install_qenex() {
    echo -e "${BLUE}Installing QENEX Unified AI OS...${NC}"
    
    # Create directories
    mkdir -p $QENEX_ROOT/{kernel,cicd,ai,config,runtime,logs,data,bin}
    
    # Copy files (assuming we're in the source directory)
    if [ -f "kernel/unified_ai_os.py" ]; then
        cp -r kernel/* $QENEX_ROOT/kernel/ 2>/dev/null || true
        cp -r cicd/* $QENEX_ROOT/cicd/ 2>/dev/null || true
        cp -r ai/* $QENEX_ROOT/ai/ 2>/dev/null || true
    else
        echo -e "${YELLOW}Source files not found in current directory${NC}"
    fi
    
    # Install Python dependencies
    echo "Installing Python packages..."
    pip3 install --upgrade pip
    
    # Create virtual environment
    python3 -m venv $QENEX_ROOT/venv
    source $QENEX_ROOT/venv/bin/activate
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt 2>/dev/null || {
            echo -e "${YELLOW}Some packages failed to install, installing core dependencies only${NC}"
            pip install psutil pyyaml requests 2>/dev/null || true
        }
    fi
    
    deactivate
    
    # Create command shortcuts
    echo "Creating command shortcuts..."
    
    cat > /usr/local/bin/qenex-shell << 'EOL'
#!/bin/bash
source /opt/qenex-os/venv/bin/activate 2>/dev/null
python3 /opt/qenex-os/kernel/qenex_shell.py "$@"
EOL
    
    cat > /usr/local/bin/qenex-os << 'EOL'
#!/bin/bash
source /opt/qenex-os/venv/bin/activate 2>/dev/null
python3 /opt/qenex-os/kernel/unified_ai_os.py "$@"
EOL
    
    cat > /usr/local/bin/qenex << 'EOL'
#!/bin/bash
source /opt/qenex-os/venv/bin/activate 2>/dev/null
if [ -z "$1" ]; then
    python3 /opt/qenex-os/kernel/qenex_shell.py
else
    python3 /opt/qenex-os/kernel/unified_ai_os.py "$@"
fi
EOL
    
    chmod +x /usr/local/bin/qenex*
    
    # Create systemd service
    echo "Creating systemd service..."
    cat > /etc/systemd/system/qenex-os.service << 'EOL'
[Unit]
Description=QENEX Unified AI Operating System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qenex-os
Environment="PATH=/opt/qenex-os/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/qenex-os/venv/bin/python3 /opt/qenex-os/kernel/unified_ai_os.py boot
ExecStop=/opt/qenex-os/venv/bin/python3 /opt/qenex-os/kernel/unified_ai_os.py shutdown
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL
    
    systemctl daemon-reload
    
    # Set permissions
    chmod -R 755 $QENEX_ROOT
    chmod +x $QENEX_ROOT/kernel/*.py
    chmod +x $QENEX_ROOT/cicd/*.py
    
    echo -e "${GREEN}✓ QENEX OS installed successfully${NC}"
}

# Configure QENEX
configure_qenex() {
    echo -e "${BLUE}Configuring QENEX OS...${NC}"
    
    # Create default configuration
    mkdir -p $QENEX_ROOT/config
    
    cat > $QENEX_ROOT/config/qenex.yaml << 'EOL'
# QENEX Unified AI OS Configuration
version: 3.0.0

system:
  mode: normal
  auto_start: true
  
ai:
  enabled: true
  continuous_learning: true
  auto_optimization: true
  
cicd:
  dashboard_port: 8080
  api_port: 8000
  webhook_port: 8082
  
security:
  encryption: true
  audit_logging: true
  secret_rotation: true
  
performance:
  cache_enabled: true
  parallel_processing: true
  distributed_mode: false
EOL
    
    echo -e "${GREEN}✓ Configuration created${NC}"
}

# Post-installation setup
post_install() {
    echo -e "${BLUE}Running post-installation setup...${NC}"
    
    # Initialize database
    mkdir -p $QENEX_ROOT/data/db
    
    # Create log rotation
    cat > /etc/logrotate.d/qenex << 'EOL'
/opt/qenex-os/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 640 root root
}
EOL
    
    # Add to PATH
    echo 'export PATH=/opt/qenex-os/bin:$PATH' >> /etc/profile.d/qenex.sh
    chmod +x /etc/profile.d/qenex.sh
    
    echo -e "${GREEN}✓ Post-installation complete${NC}"
}

# Display completion message
completion_message() {
    echo
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         QENEX UNIFIED AI OS INSTALLATION COMPLETE!            ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${CYAN}Quick Start Commands:${NC}"
    echo "  qenex-shell     - Launch QENEX interactive shell"
    echo "  qenex status    - Check system status"
    echo "  qenex boot      - Start QENEX OS"
    echo
    echo -e "${CYAN}Services:${NC}"
    echo "  systemctl start qenex-os    - Start as service"
    echo "  systemctl enable qenex-os   - Enable auto-start"
    echo
    echo -e "${CYAN}Web Interfaces:${NC}"
    echo "  Dashboard: http://localhost:8080"
    echo "  API Docs:  http://localhost:8000/docs"
    echo "  Webhooks:  http://localhost:8082"
    echo
    echo -e "${YELLOW}Documentation: /opt/qenex-os/README.md${NC}"
    echo -e "${YELLOW}Logs: /opt/qenex-os/logs/${NC}"
    echo
}

# Main installation flow
main() {
    print_banner
    check_root
    check_requirements
    
    echo
    echo -e "${CYAN}Ready to install QENEX Unified AI OS${NC}"
    echo -e "${YELLOW}Installation directory: $QENEX_ROOT${NC}"
    echo -e "${YELLOW}This will install QENEX OS and its dependencies${NC}"
    echo
    read -p "Continue with installation? (y/n) " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled"
        exit 0
    fi
    
    install_dependencies
    backup_existing
    install_qenex
    configure_qenex
    post_install
    completion_message
    
    echo
    read -p "Would you like to start QENEX OS now? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Starting QENEX OS...${NC}"
        systemctl start qenex-os
        sleep 3
        systemctl status qenex-os --no-pager
    fi
}

# Run main function
main "$@"