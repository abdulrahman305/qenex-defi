#!/bin/bash
#
# QENEX Unified AI OS - Quick Installer
# Version 5.0.0
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       QENEX Unified AI OS - Installer          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo

# Check root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

echo "Installing QENEX OS..."

# Install dependencies
apt-get update
apt-get install -y python3-pip python3-venv nginx redis-server

# Create directories
mkdir -p /opt/qenex-os/{data,logs,cache,backups}

# Install Python packages
python3 -m pip install --upgrade pip
pip3 install aiohttp psutil redis pyyaml requests

# Configure nginx
systemctl enable nginx
systemctl start nginx

# Make executable
chmod +x /usr/local/bin/qenex
chmod +x /opt/qenex-os/*.py

echo -e "${GREEN}✓ Installation complete!${NC}"
echo "Run 'qenex start' to launch QENEX OS"
