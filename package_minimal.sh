#!/bin/bash
VERSION="3.0.0-minimal"
PACKAGE_NAME="qxc-minimal-v${VERSION}"
BUILD_DIR="/tmp/${PACKAGE_NAME}"
OUTPUT_DIR="/opt/qenex-os/dist-minimal"

echo "📦 Creating minimal package v${VERSION}..."

rm -rf "$BUILD_DIR" "$OUTPUT_DIR"
mkdir -p "$BUILD_DIR" "$OUTPUT_DIR"

cd /opt/qenex-os

# Copy only working files
mkdir -p "$BUILD_DIR/contracts"
cp contracts/QXCToken.sol "$BUILD_DIR/contracts/"
cp contracts/QXCStakingFixed.sol "$BUILD_DIR/contracts/"
cp contracts/SimpleMultiSig.sol "$BUILD_DIR/contracts/"

mkdir -p "$BUILD_DIR/test"
cp test/QXCToken.test.js "$BUILD_DIR/test/"

mkdir -p "$BUILD_DIR/scripts"
cp scripts/deploy.js "$BUILD_DIR/scripts/"

# Copy config files
cp package.json hardhat.config.js "$BUILD_DIR/"

# Copy honest documentation
cp README_MINIMAL.md "$BUILD_DIR/README.md"
cp FULL_MINIMALIST_AUDIT.md "$BUILD_DIR/"

# Create package
cd /tmp
tar -czf "$OUTPUT_DIR/${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"

echo "✅ Minimal package created: $OUTPUT_DIR/${PACKAGE_NAME}.tar.gz"
ls -lh "$OUTPUT_DIR/"
