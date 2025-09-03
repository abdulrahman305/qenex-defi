#!/bin/bash
#
# QENEX OS Package Builder
# Creates distributable archive
#

VERSION="5.0.0"
PACKAGE_NAME="qenex-os-v${VERSION}"
BUILD_DIR="/tmp/${PACKAGE_NAME}"

echo "Building QENEX OS Package v${VERSION}..."

# Create build directory
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR

# Copy essential files
echo "Copying files..."
cp -r /opt/qenex-os/* $BUILD_DIR/ 2>/dev/null || true
cp /usr/local/bin/qenex $BUILD_DIR/bin/qenex 2>/dev/null || true

# Create tarball
echo "Creating archive..."
cd /tmp
tar -czf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}/"

# Create self-extracting installer
echo "Creating self-extracting installer..."
cat > "${PACKAGE_NAME}-installer.sh" << 'INSTALLER'
#!/bin/bash
echo "QENEX OS Self-Extracting Installer"
ARCHIVE=$(awk '/^__ARCHIVE_BELOW__/ {print NR + 1; exit 0; }' $0)
tail -n+$ARCHIVE $0 | tar xz -C /opt/
/opt/qenex-os/installer.sh
exit 0
__ARCHIVE_BELOW__
INSTALLER

cat "${PACKAGE_NAME}.tar.gz" >> "${PACKAGE_NAME}-installer.sh"
chmod +x "${PACKAGE_NAME}-installer.sh"

# Move to output directory
mv "${PACKAGE_NAME}.tar.gz" /opt/qenex-os/
mv "${PACKAGE_NAME}-installer.sh" /opt/qenex-os/

# Cleanup
rm -rf $BUILD_DIR

echo "✓ Package created: /opt/qenex-os/${PACKAGE_NAME}.tar.gz"
echo "✓ Installer created: /opt/qenex-os/${PACKAGE_NAME}-installer.sh"
echo ""
echo "Distribution methods:"
echo "1. Share the tar.gz file and extract with: tar -xzf ${PACKAGE_NAME}.tar.gz -C /opt/"
echo "2. Share the installer and run with: sudo ./${PACKAGE_NAME}-installer.sh"
echo "3. Use Docker: docker-compose up -d"
