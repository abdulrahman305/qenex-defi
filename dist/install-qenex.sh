#!/bin/bash
# QENEX Quick Installer
echo "Downloading QENEX Unified AI OS..."
curl -L https://github.com/qenex/unified-ai-os/releases/latest/download/qenex-unified-ai-os-3.0.0.tar.gz -o qenex.tar.gz
tar -xzf qenex.tar.gz
cd qenex-unified-ai-os-*
sudo ./install.sh
