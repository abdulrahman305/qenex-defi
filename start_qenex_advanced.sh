#!/bin/bash
"""
QENEX Advanced Features Startup Script
Launches all 7 advanced QENEX features with proper initialization
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
QENEX_HOME="/opt/qenex-os"
LOG_DIR="$QENEX_HOME/logs"
DATA_DIR="$QENEX_HOME/data" 
CONFIG_DIR="$QENEX_HOME/config"

# Create necessary directories
mkdir -p "$LOG_DIR" "$DATA_DIR" "$CONFIG_DIR"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                 QENEX Advanced Features                      ║${NC}"
echo -e "${BLUE}║              Unified AI Operating System                     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

print_feature() {
    local icon="$1"
    local name="$2"
    local description="$3"
    echo -e "${GREEN}$icon ${CYAN}$name${NC} - $description"
}

echo -e "${YELLOW}🚀 Available Advanced Features:${NC}"
echo

print_feature "⚡" "Auto-Scaling System" "Dynamic resource scaling for high loads"
print_feature "💾" "Backup & Recovery" "Automated backup with disaster recovery" 
print_feature "🌐" "Distributed Processing" "Multi-node load balancing and fault tolerance"
print_feature "🔒" "Zero-Trust Security" "Advanced authentication and authorization"
print_feature "🎨" "Visual Pipeline Builder" "Drag-and-drop workflow creation"
print_feature "🎙️" "Voice Control System" "Natural language AI interactions"
print_feature "⚛️" "Quantum-Ready Architecture" "Future-proof quantum computing integration"

echo
echo -e "${YELLOW}📋 System Requirements Check:${NC}"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -o "Python [0-9]\+\.[0-9]\+" | head -1)
if [[ $python_version == "Python 3."* ]]; then
    echo -e "${GREEN}✅ Python 3.x detected: $python_version${NC}"
else
    echo -e "${RED}❌ Python 3.x required${NC}"
    exit 1
fi

# Check available disk space
available_space=$(df "$QENEX_HOME" | awk 'NR==2 {print $4}')
if [ "$available_space" -gt 1000000 ]; then # 1GB
    echo -e "${GREEN}✅ Sufficient disk space available${NC}"
else
    echo -e "${YELLOW}⚠️  Low disk space warning${NC}"
fi

# Check memory
total_memory=$(free -m | awk 'NR==2{printf "%.0f", $2}')
if [ "$total_memory" -gt 2048 ]; then # 2GB
    echo -e "${GREEN}✅ Sufficient memory: ${total_memory}MB${NC}"
else
    echo -e "${YELLOW}⚠️  Memory may be insufficient: ${total_memory}MB${NC}"
fi

echo
echo -e "${YELLOW}🔧 Installing Python Dependencies:${NC}"

# Install required Python packages
pip_packages=(
    "asyncio"
    "aiohttp" 
    "docker"
    "redis"
    "psutil"
    "cryptography"
    "pyjwt"
    "bcrypt"
    "pyotp"
    "qrcode"
    "speechrecognition"
    "pyttsx3"
    "pyaudio"
    "nltk"
    "spacy"
    "numpy"
    "boto3"
    "uvloop"
)

echo "Installing core dependencies..."
for package in "${pip_packages[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo -e "${GREEN}✅ $package${NC}"
    else
        echo -e "${YELLOW}📦 Installing $package...${NC}"
        pip3 install "$package" --quiet || echo -e "${YELLOW}⚠️  Failed to install $package${NC}"
    fi
done

echo
echo -e "${YELLOW}🎯 Feature Selection:${NC}"

# Allow user to select features
declare -A features
features[1]="Auto-Scaling System"
features[2]="Backup & Recovery"
features[3]="Distributed Processing"
features[4]="Zero-Trust Security"
features[5]="Visual Pipeline Builder"
features[6]="Voice Control System"
features[7]="Quantum-Ready Architecture"
features[8]="All Features"

echo "Select features to start:"
for i in {1..8}; do
    echo "  $i) ${features[$i]}"
done

read -p "Enter selection (1-8) or press Enter for all: " selection
selection=${selection:-8}

# Set feature flags
declare -A enable_features
if [ "$selection" == "8" ]; then
    # Enable all features
    for i in {1..7}; do
        enable_features[$i]=true
    done
else
    # Enable selected feature
    enable_features[$selection]=true
fi

echo
echo -e "${YELLOW}🔧 Configuring System:${NC}"

# Create master configuration
cat > "$CONFIG_DIR/master.json" << EOF
{
  "enabled_components": {
    "autoscaling": ${enable_features[1]:-false},
    "backup_recovery": ${enable_features[2]:-false},
    "distributed": ${enable_features[3]:-false},
    "zero_trust": ${enable_features[4]:-false},
    "visual_pipeline": ${enable_features[5]:-false},
    "voice_control": ${enable_features[6]:-false},
    "quantum_ready": ${enable_features[7]:-false}
  },
  "startup_order": [
    "zero_trust",
    "backup_recovery", 
    "distributed",
    "autoscaling",
    "visual_pipeline",
    "quantum_ready",
    "voice_control"
  ],
  "health_check_interval": 30,
  "auto_restart": true,
  "system_dashboard": {
    "enabled": true,
    "port": 8080,
    "host": "0.0.0.0"
  }
}
EOF

echo -e "${GREEN}✅ Configuration created${NC}"

echo
echo -e "${YELLOW}🚀 Starting QENEX Advanced Features:${NC}"

# Set Python path
export PYTHONPATH="$QENEX_HOME:$PYTHONPATH"

# Start the system
if [[ "${enable_features[*]}" =~ "true" ]]; then
    echo -e "${GREEN}Starting QENEX Master System...${NC}"
    
    # Run in background and capture PID
    python3 "$QENEX_HOME/qenex_master_system.py" &
    master_pid=$!
    
    echo -e "${GREEN}✅ QENEX Master System started (PID: $master_pid)${NC}"
    echo "$master_pid" > "$QENEX_HOME/qenex_master.pid"
    
    # Wait a moment for startup
    sleep 3
    
    echo
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    System Access Points                      ║${NC}"
    echo -e "${BLUE}╠══════════════════════════════════════════════════════════════╣${NC}"
    
    if [ "${enable_features[4]}" == "true" ]; then
        echo -e "${BLUE}║ ${CYAN}🔒 Security API:${NC}        http://localhost:8003              ${BLUE}║${NC}"
    fi
    
    if [ "${enable_features[5]}" == "true" ]; then
        echo -e "${BLUE}║ ${CYAN}🎨 Pipeline Builder:${NC}    http://localhost:8004              ${BLUE}║${NC}"
    fi
    
    if [ "${enable_features[3]}" == "true" ]; then
        echo -e "${BLUE}║ ${CYAN}🌐 Distributed API:${NC}     http://localhost:8002              ${BLUE}║${NC}"
    fi
    
    echo -e "${BLUE}║ ${CYAN}📊 System Dashboard:${NC}    http://localhost:8080              ${BLUE}║${NC}"
    echo -e "${BLUE}║ ${CYAN}📋 Logs:${NC}                $LOG_DIR                 ${BLUE}║${NC}"
    echo -e "${BLUE}║ ${CYAN}⚙️  Config:${NC}              $CONFIG_DIR              ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    
    echo
    echo -e "${GREEN}🎉 QENEX Advanced Features are now running!${NC}"
    echo -e "${YELLOW}📝 Tips:${NC}"
    echo "  • Use 'tail -f $LOG_DIR/master_system.log' to monitor"
    echo "  • Check system status at http://localhost:8080"
    echo "  • Stop with: kill $master_pid"
    
    if [ "${enable_features[6]}" == "true" ]; then
        echo "  • Try voice commands: 'Hey QENEX, system status'"
    fi
    
    echo
    echo -e "${CYAN}Press Ctrl+C to stop all services${NC}"
    
    # Wait for process
    wait $master_pid
    
else
    echo -e "${YELLOW}⚠️  No features selected. Exiting.${NC}"
fi

echo
echo -e "${BLUE}Thank you for using QENEX AI Operating System!${NC}"