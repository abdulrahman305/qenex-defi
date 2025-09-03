#!/bin/bash
# QENEX Unified AI OS - Package Builder
# Creates distribution packages (tar.gz, deb, rpm, docker)

set -e

VERSION="3.0.0"
PACKAGE_NAME="qenex-unified-ai-os"
BUILD_DIR="./build"
DIST_DIR="./dist"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Building QENEX Unified AI OS packages v${VERSION}...${NC}"

# Clean previous builds
rm -rf $BUILD_DIR $DIST_DIR
mkdir -p $BUILD_DIR $DIST_DIR

# Create package structure
PACKAGE_DIR="$BUILD_DIR/${PACKAGE_NAME}-${VERSION}"
mkdir -p $PACKAGE_DIR

# Copy files
echo "Copying files..."
cp -r kernel cicd ai $PACKAGE_DIR/ 2>/dev/null || true
cp -r config runtime $PACKAGE_DIR/ 2>/dev/null || true
cp requirements.txt package.json Dockerfile README.md LICENSE $PACKAGE_DIR/ 2>/dev/null || true
cp install.sh $PACKAGE_DIR/
chmod +x $PACKAGE_DIR/install.sh

# Remove __pycache__ and .pyc files
find $PACKAGE_DIR -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find $PACKAGE_DIR -type f -name "*.pyc" -delete 2>/dev/null || true

# Create tar.gz package
echo -e "${BLUE}Creating tar.gz package...${NC}"
cd $BUILD_DIR
tar -czf "$PACKAGE_NAME-$VERSION.tar.gz" "$PACKAGE_NAME-$VERSION"
mv "$PACKAGE_NAME-$VERSION.tar.gz" ../dist/
cd ..
echo -e "${GREEN}✓ Created dist/$PACKAGE_NAME-$VERSION.tar.gz${NC}"

# Create ZIP package
echo -e "${BLUE}Creating ZIP package...${NC}"
cd $BUILD_DIR
zip -r "$PACKAGE_NAME-$VERSION.zip" "$PACKAGE_NAME-$VERSION" -q
mv "$PACKAGE_NAME-$VERSION.zip" ../dist/
cd ..
echo -e "${GREEN}✓ Created dist/$PACKAGE_NAME-$VERSION.zip${NC}"

# Create DEB package (if dpkg-deb is available)
if command -v dpkg-deb &> /dev/null; then
    echo -e "${BLUE}Creating DEB package...${NC}"
    
    DEB_DIR="$BUILD_DIR/deb"
    mkdir -p $DEB_DIR/DEBIAN
    mkdir -p $DEB_DIR/opt/qenex-os
    mkdir -p $DEB_DIR/usr/local/bin
    mkdir -p $DEB_DIR/etc/systemd/system
    
    # Copy files
    cp -r $PACKAGE_DIR/* $DEB_DIR/opt/qenex-os/
    
    # Create control file
    cat > $DEB_DIR/DEBIAN/control << EOL
Package: qenex-unified-ai-os
Version: $VERSION
Section: admin
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-pip
Maintainer: QENEX Team
Description: QENEX Unified AI Operating System
 Autonomous CI/CD platform with AI-driven orchestration
 Features include GitOps, distributed execution, and self-healing pipelines
EOL
    
    # Create postinst script
    cat > $DEB_DIR/DEBIAN/postinst << 'EOL'
#!/bin/bash
ln -sf /opt/qenex-os/kernel/qenex_shell.py /usr/local/bin/qenex-shell
ln -sf /opt/qenex-os/kernel/unified_ai_os.py /usr/local/bin/qenex-os
chmod +x /usr/local/bin/qenex*
pip3 install -r /opt/qenex-os/requirements.txt 2>/dev/null || true
systemctl daemon-reload
echo "QENEX OS installed. Run 'qenex-shell' to start."
EOL
    chmod 755 $DEB_DIR/DEBIAN/postinst
    
    # Build DEB
    dpkg-deb --build $DEB_DIR "dist/${PACKAGE_NAME}_${VERSION}_all.deb"
    echo -e "${GREEN}✓ Created dist/${PACKAGE_NAME}_${VERSION}_all.deb${NC}"
fi

# Create RPM package (if rpmbuild is available)
if command -v rpmbuild &> /dev/null; then
    echo -e "${BLUE}Creating RPM package...${NC}"
    
    RPM_DIR="$BUILD_DIR/rpm"
    mkdir -p $RPM_DIR/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
    
    # Create spec file
    cat > $RPM_DIR/SPECS/qenex.spec << EOL
Name:           qenex-unified-ai-os
Version:        $VERSION
Release:        1%{?dist}
Summary:        QENEX Unified AI Operating System
License:        MIT
URL:            https://github.com/qenex/unified-ai-os
Source0:        %{name}-%{version}.tar.gz

Requires:       python3 >= 3.8
Requires:       python3-pip

%description
Autonomous CI/CD platform with AI-driven orchestration

%prep
%setup -q

%install
mkdir -p %{buildroot}/opt/qenex-os
cp -r * %{buildroot}/opt/qenex-os/

%files
/opt/qenex-os

%post
ln -sf /opt/qenex-os/kernel/qenex_shell.py /usr/local/bin/qenex-shell
ln -sf /opt/qenex-os/kernel/unified_ai_os.py /usr/local/bin/qenex-os
chmod +x /usr/local/bin/qenex*

%changelog
* $(date +"%a %b %d %Y") QENEX Team
- Initial release
EOL
    
    # Copy source
    cp "dist/$PACKAGE_NAME-$VERSION.tar.gz" $RPM_DIR/SOURCES/
    
    # Build RPM
    rpmbuild --define "_topdir $PWD/$RPM_DIR" -ba $RPM_DIR/SPECS/qenex.spec 2>/dev/null && {
        mv $RPM_DIR/RPMS/noarch/*.rpm dist/ 2>/dev/null || true
        echo -e "${GREEN}✓ Created RPM package${NC}"
    } || echo -e "${YELLOW}⚠ RPM build failed${NC}"
fi

# Build Docker image
if command -v docker &> /dev/null; then
    echo -e "${BLUE}Building Docker image...${NC}"
    docker build -t ${PACKAGE_NAME}:${VERSION} -t ${PACKAGE_NAME}:latest . 2>/dev/null && {
        
        # Save Docker image
        docker save ${PACKAGE_NAME}:${VERSION} | gzip > dist/${PACKAGE_NAME}-${VERSION}-docker.tar.gz
        echo -e "${GREEN}✓ Created Docker image: ${PACKAGE_NAME}:${VERSION}${NC}"
        echo -e "${GREEN}✓ Saved to dist/${PACKAGE_NAME}-${VERSION}-docker.tar.gz${NC}"
    } || echo -e "${YELLOW}⚠ Docker build failed${NC}"
fi

# Create installer script
echo -e "${BLUE}Creating standalone installer...${NC}"
cat > dist/install-qenex.sh << 'EOL'
#!/bin/bash
# QENEX Quick Installer
echo "Downloading QENEX Unified AI OS..."
curl -L https://github.com/qenex/unified-ai-os/releases/latest/download/qenex-unified-ai-os-3.0.0.tar.gz -o qenex.tar.gz
tar -xzf qenex.tar.gz
cd qenex-unified-ai-os-*
sudo ./install.sh
EOL
chmod +x dist/install-qenex.sh

# Create checksums
echo -e "${BLUE}Creating checksums...${NC}"
cd dist
sha256sum * > SHA256SUMS
cd ..

# Summary
echo
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              PACKAGE BUILD COMPLETE!                          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo
echo "Packages created in dist/:"
ls -lh dist/
echo
echo "To install:"
echo "  tar -xzf dist/${PACKAGE_NAME}-${VERSION}.tar.gz"
echo "  cd ${PACKAGE_NAME}-${VERSION}"
echo "  sudo ./install.sh"
echo
echo "Or with Docker:"
echo "  docker load < dist/${PACKAGE_NAME}-${VERSION}-docker.tar.gz"
echo "  docker run -d -p 8080:8080 ${PACKAGE_NAME}:${VERSION}"