#!/bin/bash

# QENEX OS Packaging Script
VERSION="2.0.0"
PACKAGE_NAME="qenex-os-v${VERSION}"
BUILD_DIR="/tmp/${PACKAGE_NAME}"
OUTPUT_DIR="/opt/qenex-os/dist"

echo "📦 Packaging QENEX OS v${VERSION}..."

# Clean and create directories
rm -rf "$BUILD_DIR" "$OUTPUT_DIR"
mkdir -p "$BUILD_DIR" "$OUTPUT_DIR"

echo "📁 Creating package structure..."

# Core package - Essential files only
mkdir -p "$BUILD_DIR/core"
cp -r contracts "$BUILD_DIR/core/"
cp -r scripts "$BUILD_DIR/core/"
cp -r test "$BUILD_DIR/core/"
cp package.json "$BUILD_DIR/core/"
cp hardhat.config.js "$BUILD_DIR/core/"
cp README.md "$BUILD_DIR/core/"
cp LICENSE "$BUILD_DIR/core/" 2>/dev/null || echo "MIT License" > "$BUILD_DIR/core/LICENSE"

# Documentation package
mkdir -p "$BUILD_DIR/docs"
cp *.md "$BUILD_DIR/docs/" 2>/dev/null || true

# Additional contracts package
mkdir -p "$BUILD_DIR/extended-contracts"
for dir in metaverse institutional perpetual insurance dao social ai-marketplace cards quantum oracle layer2 privacy dex; do
    if [ -d "$dir" ]; then
        cp -r "$dir" "$BUILD_DIR/extended-contracts/"
    fi
done

# Create quick start script
cat > "$BUILD_DIR/quickstart.sh" << 'QUICKSTART'
#!/bin/bash
echo "🚀 QENEX OS Quick Start"
echo ""
cd core
npm install
npx hardhat compile
npm test
echo "✅ Setup complete!"
QUICKSTART
chmod +x "$BUILD_DIR/quickstart.sh"

echo "📦 Creating archives..."

# Create tar.gz archive
cd /tmp
tar -czf "$OUTPUT_DIR/${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"

# Create zip archive
zip -qr "$OUTPUT_DIR/${PACKAGE_NAME}.zip" "$PACKAGE_NAME"

# Create minimal core package
cd "$BUILD_DIR/core"
tar -czf "$OUTPUT_DIR/${PACKAGE_NAME}-core-only.tar.gz" .

# Calculate checksums
cd "$OUTPUT_DIR"
sha256sum *.tar.gz *.zip 2>/dev/null > checksums.sha256

echo "✅ Packaging complete!"
echo "📁 Packages created in: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR" 2>/dev/null
