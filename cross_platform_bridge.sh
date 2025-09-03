#!/bin/bash
# QENEX AI OS - Cross-Platform Bridge
# Universal compatibility layer for Windows, Unix, and macOS

set -e

# Detect platform
detect_platform() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        PLATFORM="linux"
        PLATFORM_NAME="Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        PLATFORM="macos"
        PLATFORM_NAME="macOS"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        PLATFORM="windows"
        PLATFORM_NAME="Windows"
    elif [[ "$OSTYPE" == "freebsd"* ]]; then
        PLATFORM="freebsd"
        PLATFORM_NAME="FreeBSD"
    else
        PLATFORM="unknown"
        PLATFORM_NAME="Unknown"
    fi
    
    echo "Detected platform: $PLATFORM_NAME"
}

# Cross-platform paths
setup_paths() {
    case $PLATFORM in
        windows)
            QENEX_ROOT="C:/ProgramData/QENEX-OS"
            QENEX_LOGS="$QENEX_ROOT/logs"
            QENEX_CONFIG="$QENEX_ROOT/config"
            PATH_SEP=";"
            ;;
        *)
            QENEX_ROOT="/opt/qenex-os"
            QENEX_LOGS="/var/log/qenex-os"
            QENEX_CONFIG="/etc/qenex-os"
            PATH_SEP=":"
            ;;
    esac
    
    export QENEX_ROOT
    export QENEX_LOGS
    export QENEX_CONFIG
}

# Create directories (cross-platform)
create_directories() {
    case $PLATFORM in
        windows)
            mkdir -p "$QENEX_ROOT" 2>/dev/null || powershell -Command "New-Item -ItemType Directory -Force -Path '$QENEX_ROOT'"
            mkdir -p "$QENEX_LOGS" 2>/dev/null || powershell -Command "New-Item -ItemType Directory -Force -Path '$QENEX_LOGS'"
            mkdir -p "$QENEX_CONFIG" 2>/dev/null || powershell -Command "New-Item -ItemType Directory -Force -Path '$QENEX_CONFIG'"
            ;;
        *)
            mkdir -p "$QENEX_ROOT" "$QENEX_LOGS" "$QENEX_CONFIG"
            ;;
    esac
}

# Check Python (cross-platform)
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "Python not found. Installing..."
        install_python
    fi
    
    export PYTHON_CMD
}

# Install Python (cross-platform)
install_python() {
    case $PLATFORM in
        windows)
            echo "Please install Python from https://www.python.org/downloads/"
            exit 1
            ;;
        macos)
            if command -v brew &> /dev/null; then
                brew install python3
            else
                echo "Please install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;
        linux)
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y python3 python3-pip
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3 python3-pip
            elif command -v pacman &> /dev/null; then
                sudo pacman -S python python-pip
            fi
            ;;
        freebsd)
            pkg install -y python3 py39-pip
            ;;
    esac
}

# Install dependencies (cross-platform)
install_dependencies() {
    echo "Installing Python dependencies..."
    
    # Common dependencies
    DEPS="psutil numpy"
    
    # Platform-specific dependencies
    case $PLATFORM in
        windows)
            DEPS="$DEPS wmi pywin32"
            ;;
        linux)
            DEPS="$DEPS python-apt"
            ;;
    esac
    
    # Install
    $PYTHON_CMD -m pip install $DEPS 2>/dev/null || true
}

# Process management (cross-platform)
list_processes() {
    case $PLATFORM in
        windows)
            tasklist /fo csv
            ;;
        macos)
            ps aux
            ;;
        *)
            ps aux
            ;;
    esac
}

# Network connections (cross-platform)
list_connections() {
    case $PLATFORM in
        windows)
            netstat -an
            ;;
        macos)
            netstat -an
            ;;
        linux)
            ss -tunap 2>/dev/null || netstat -tunap
            ;;
        freebsd)
            sockstat -4 -6
            ;;
    esac
}

# Service management (cross-platform)
manage_service() {
    local action=$1
    local service=$2
    
    case $PLATFORM in
        windows)
            case $action in
                start)
                    net start "$service" 2>/dev/null || sc start "$service"
                    ;;
                stop)
                    net stop "$service" 2>/dev/null || sc stop "$service"
                    ;;
                status)
                    sc query "$service"
                    ;;
            esac
            ;;
        macos)
            case $action in
                start)
                    launchctl load -w "/Library/LaunchDaemons/$service.plist" 2>/dev/null
                    ;;
                stop)
                    launchctl unload "/Library/LaunchDaemons/$service.plist" 2>/dev/null
                    ;;
                status)
                    launchctl list | grep "$service"
                    ;;
            esac
            ;;
        linux)
            if command -v systemctl &> /dev/null; then
                systemctl $action "$service"
            elif command -v service &> /dev/null; then
                service "$service" $action
            else
                /etc/init.d/"$service" $action
            fi
            ;;
        freebsd)
            service "$service" $action
            ;;
    esac
}

# Firewall management (cross-platform)
configure_firewall() {
    echo "Configuring firewall..."
    
    case $PLATFORM in
        windows)
            # Windows Firewall
            netsh advfirewall firewall add rule name="QENEX-OS" dir=in action=allow protocol=TCP localport=8899
            netsh advfirewall firewall add rule name="QENEX-SSH-Block" dir=out action=block protocol=TCP remoteport=22 remoteip=139.99.0.0/16
            ;;
        macos)
            # macOS pfctl
            echo "block out proto tcp from any to 139.99.0.0/16 port 22" | sudo tee -a /etc/pf.conf
            sudo pfctl -e -f /etc/pf.conf
            ;;
        linux)
            # Linux iptables
            if command -v iptables &> /dev/null; then
                iptables -I OUTPUT -p tcp --dport 22 -d 139.99.0.0/16 -j DROP
                iptables -I INPUT -p tcp --dport 8899 -j ACCEPT
            elif command -v ufw &> /dev/null; then
                ufw deny out to 139.99.0.0/16 port 22
                ufw allow 8899/tcp
            fi
            ;;
        freebsd)
            # FreeBSD ipfw
            ipfw add deny tcp from any to 139.99.0.0/16 22 out
            ipfw add allow tcp from any to me 8899 in
            ;;
    esac
}

# System information (cross-platform)
get_system_info() {
    case $PLATFORM in
        windows)
            echo "System: Windows"
            systeminfo | head -20
            ;;
        macos)
            echo "System: macOS"
            system_profiler SPSoftwareDataType SPHardwareDataType | head -30
            ;;
        linux)
            echo "System: Linux"
            uname -a
            lsb_release -a 2>/dev/null || cat /etc/os-release
            ;;
        freebsd)
            echo "System: FreeBSD"
            uname -a
            freebsd-version
            ;;
    esac
}

# Memory info (cross-platform)
get_memory_info() {
    case $PLATFORM in
        windows)
            wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /value
            ;;
        macos)
            vm_stat
            ;;
        linux)
            free -h
            ;;
        freebsd)
            vmstat -h
            ;;
    esac
}

# CPU info (cross-platform)
get_cpu_info() {
    case $PLATFORM in
        windows)
            wmic cpu get Name,NumberOfCores,LoadPercentage /value
            ;;
        macos)
            sysctl -n machdep.cpu.brand_string
            sysctl -n hw.ncpu
            ;;
        linux)
            lscpu | head -15
            ;;
        freebsd)
            sysctl hw.model hw.ncpu
            ;;
    esac
}

# Install QENEX OS (cross-platform)
install_qenex_os() {
    echo "Installing QENEX AI OS (Cross-Platform)..."
    
    detect_platform
    setup_paths
    create_directories
    check_python
    install_dependencies
    
    # Copy files
    echo "Copying QENEX OS files..."
    
    # Create launcher script
    case $PLATFORM in
        windows)
            cat > "$QENEX_ROOT/qenex-os.bat" << 'EOF'
@echo off
set QENEX_ROOT=C:\ProgramData\QENEX-OS
python "%QENEX_ROOT%\kernel\qenex_core.py" %*
EOF
            ;;
        *)
            cat > "$QENEX_ROOT/qenex-os" << 'EOF'
#!/bin/bash
export QENEX_ROOT=/opt/qenex-os
python3 "$QENEX_ROOT/kernel/qenex_core.py" "$@"
EOF
            chmod +x "$QENEX_ROOT/qenex-os"
            ln -sf "$QENEX_ROOT/qenex-os" /usr/local/bin/qenex-os 2>/dev/null
            ;;
    esac
    
    echo "QENEX AI OS installed successfully!"
    echo "Platform: $PLATFORM_NAME"
    echo "Root: $QENEX_ROOT"
}

# Start continuous learning
start_continuous_learning() {
    echo "Starting Continuous Learning System..."
    
    detect_platform
    setup_paths
    check_python
    
    # Start learning engine
    case $PLATFORM in
        windows)
            start /B $PYTHON_CMD "$QENEX_ROOT/ai/continuous_learning.py" start
            ;;
        *)
            nohup $PYTHON_CMD "$QENEX_ROOT/ai/continuous_learning.py" start > "$QENEX_LOGS/learning.log" 2>&1 &
            echo $! > "$QENEX_ROOT/learning.pid"
            ;;
    esac
    
    echo "Continuous Learning System started"
}

# Stop services
stop_services() {
    echo "Stopping QENEX OS services..."
    
    detect_platform
    
    case $PLATFORM in
        windows)
            taskkill /F /IM python.exe /FI "WINDOWTITLE eq *qenex*" 2>/dev/null
            ;;
        *)
            if [ -f "$QENEX_ROOT/kernel.pid" ]; then
                kill $(cat "$QENEX_ROOT/kernel.pid") 2>/dev/null
            fi
            if [ -f "$QENEX_ROOT/learning.pid" ]; then
                kill $(cat "$QENEX_ROOT/learning.pid") 2>/dev/null
            fi
            pkill -f "qenex" 2>/dev/null
            ;;
    esac
    
    echo "Services stopped"
}

# Status check
check_status() {
    echo "QENEX OS Status"
    echo "==============="
    
    detect_platform
    setup_paths
    
    echo ""
    echo "Platform: $PLATFORM_NAME"
    echo "QENEX Root: $QENEX_ROOT"
    echo ""
    
    # Check processes
    echo "Running Services:"
    case $PLATFORM in
        windows)
            tasklist | findstr -i qenex || echo "  No QENEX services running"
            tasklist | findstr -i python | findstr -i qenex || true
            ;;
        *)
            ps aux | grep -i qenex | grep -v grep || echo "  No QENEX services running"
            ;;
    esac
    
    echo ""
    echo "System Resources:"
    get_memory_info | head -3
    
    echo ""
    echo "Network Status:"
    list_connections | head -10
}

# Main menu
show_menu() {
    clear
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║         QENEX AI OS - Cross-Platform Manager              ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "1. Install QENEX OS"
    echo "2. Start Services"
    echo "3. Stop Services"
    echo "4. Check Status"
    echo "5. Configure Firewall"
    echo "6. Start Continuous Learning"
    echo "7. System Information"
    echo "8. Exit"
    echo ""
    read -p "Select option: " choice
    
    case $choice in
        1) install_qenex_os ;;
        2) start_services ;;
        3) stop_services ;;
        4) check_status ;;
        5) configure_firewall ;;
        6) start_continuous_learning ;;
        7) get_system_info ;;
        8) exit 0 ;;
        *) echo "Invalid option" ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    show_menu
}

# Start services
start_services() {
    echo "Starting QENEX OS services..."
    
    detect_platform
    setup_paths
    check_python
    
    # Start kernel
    echo "Starting QENEX Kernel..."
    case $PLATFORM in
        windows)
            start /B $PYTHON_CMD "$QENEX_ROOT/kernel/qenex_core.py"
            ;;
        *)
            nohup $PYTHON_CMD "$QENEX_ROOT/kernel/qenex_core.py" > "$QENEX_LOGS/kernel.log" 2>&1 &
            echo $! > "$QENEX_ROOT/kernel.pid"
            ;;
    esac
    
    # Start learning engine
    start_continuous_learning
    
    echo "Services started"
}

# Handle command line arguments
case "$1" in
    install)
        install_qenex_os
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    status)
        check_status
        ;;
    firewall)
        detect_platform
        configure_firewall
        ;;
    learning)
        start_continuous_learning
        ;;
    info)
        detect_platform
        get_system_info
        ;;
    *)
        if [ -z "$1" ]; then
            show_menu
        else
            echo "Usage: $0 {install|start|stop|status|firewall|learning|info}"
        fi
        ;;
esac