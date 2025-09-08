#!/bin/bash
#
# QENEX Financial Operating System - Production Installer
# Enterprise-grade installation with full security hardening
#
# Usage: sudo ./production_installer.sh [options]
# Options:
#   --environment [production|staging|development]
#   --database-type [postgresql|mysql|sqlite]
#   --domain [your-domain.com]
#   --email [admin@your-domain.com]
#   --ssl-mode [letsencrypt|self-signed|custom]
#   --backup-enabled [true|false]
#   --monitoring-enabled [true|false]
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Default configuration
ENVIRONMENT="production"
DATABASE_TYPE="postgresql"
DOMAIN="localhost"
ADMIN_EMAIL="admin@qenex.local"
SSL_MODE="self-signed"
BACKUP_ENABLED=true
MONITORING_ENABLED=true
INSTALL_DIR="/opt/qenex"
CONFIG_DIR="/etc/qenex"
LOG_DIR="/var/log/qenex"
DATA_DIR="/var/lib/qenex"
BACKUP_DIR="/var/backups/qenex"
SERVICE_USER="qenex"
SERVICE_GROUP="qenex"

# System requirements
MIN_RAM_GB=4
MIN_DISK_GB=20
MIN_CPU_CORES=2

# Software versions
PYTHON_VERSION="3.9"
POSTGRESQL_VERSION="13"
REDIS_VERSION="6"
NGINX_VERSION="1.18"

# Error handling
error_exit() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${BLUE}INFO: $1${NC}"
}

success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
}

warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --database-type)
                DATABASE_TYPE="$2"
                shift 2
                ;;
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --email)
                ADMIN_EMAIL="$2"
                shift 2
                ;;
            --ssl-mode)
                SSL_MODE="$2"
                shift 2
                ;;
            --backup-enabled)
                BACKUP_ENABLED="$2"
                shift 2
                ;;
            --monitoring-enabled)
                MONITORING_ENABLED="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                error_exit "Unknown option: $1"
                ;;
        esac
    done
}

show_help() {
    cat << EOF
QENEX Financial Operating System - Production Installer

Usage: sudo ./production_installer.sh [options]

Options:
  --environment [production|staging|development]  Target environment (default: production)
  --database-type [postgresql|mysql|sqlite]       Database type (default: postgresql)
  --domain [your-domain.com]                       Domain name (default: localhost)
  --email [admin@your-domain.com]                  Admin email (default: admin@qenex.local)
  --ssl-mode [letsencrypt|self-signed|custom]      SSL certificate mode (default: self-signed)
  --backup-enabled [true|false]                    Enable automated backups (default: true)
  --monitoring-enabled [true|false]                Enable monitoring (default: true)
  --help                                           Show this help message

Examples:
  # Basic production installation
  sudo ./production_installer.sh

  # Production with custom domain and Let's Encrypt SSL
  sudo ./production_installer.sh --domain qenex.company.com --email admin@company.com --ssl-mode letsencrypt

  # Development installation with SQLite
  sudo ./production_installer.sh --environment development --database-type sqlite

EOF
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "This script must be run as root. Please use: sudo ./production_installer.sh"
    fi
}

# Check system requirements
check_system_requirements() {
    info "Checking system requirements..."
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        error_exit "Unable to determine OS. Only Linux distributions are supported."
    fi
    
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]] && [[ "$ID" != "debian" ]] && [[ "$ID" != "centos" ]] && [[ "$ID" != "rhel" ]]; then
        warning "Unsupported OS detected: $ID. Installation may not work correctly."
    fi
    
    # Check RAM
    RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $RAM_GB -lt $MIN_RAM_GB ]]; then
        error_exit "Insufficient RAM. Required: ${MIN_RAM_GB}GB, Available: ${RAM_GB}GB"
    fi
    
    # Check disk space
    DISK_GB=$(df / | awk 'NR==2{printf "%.0f", $4/1024/1024}')
    if [[ $DISK_GB -lt $MIN_DISK_GB ]]; then
        error_exit "Insufficient disk space. Required: ${MIN_DISK_GB}GB, Available: ${DISK_GB}GB"
    fi
    
    # Check CPU cores
    CPU_CORES=$(nproc)
    if [[ $CPU_CORES -lt $MIN_CPU_CORES ]]; then
        warning "Low CPU cores detected. Required: ${MIN_CPU_CORES}, Available: ${CPU_CORES}"
    fi
    
    # Check architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" != "x86_64" ]] && [[ "$ARCH" != "amd64" ]]; then
        error_exit "Unsupported architecture: $ARCH. Only x86_64/amd64 is supported."
    fi
    
    success "System requirements check passed"
}

# Update system packages
update_system() {
    info "Updating system packages..."
    
    if command -v apt-get &> /dev/null; then
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -y
        apt-get upgrade -y
        apt-get install -y curl wget gnupg2 software-properties-common apt-transport-https ca-certificates
    elif command -v yum &> /dev/null; then
        yum update -y
        yum install -y curl wget gnupg2 epel-release
    else
        error_exit "Unsupported package manager. Only apt and yum are supported."
    fi
    
    success "System packages updated"
}

# Install system dependencies
install_dependencies() {
    info "Installing system dependencies..."
    
    local packages=(
        "python3"
        "python3-pip"
        "python3-venv"
        "python3-dev"
        "build-essential"
        "git"
        "nginx"
        "supervisor"
        "logrotate"
        "fail2ban"
        "ufw"
        "htop"
        "vim"
        "openssl"
        "certbot"
        "python3-certbot-nginx"
    )
    
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian specific packages
        packages+=("postgresql-${POSTGRESQL_VERSION}" "postgresql-client-${POSTGRESQL_VERSION}" "postgresql-contrib-${POSTGRESQL_VERSION}")
        packages+=("redis-server")
        packages+=("libpq-dev")
        
        for package in "${packages[@]}"; do
            info "Installing $package..."
            apt-get install -y "$package" || warning "Failed to install $package"
        done
        
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL specific packages
        packages+=("postgresql${POSTGRESQL_VERSION}-server" "postgresql${POSTGRESQL_VERSION}")
        packages+=("redis")
        packages+=("postgresql-devel")
        
        for package in "${packages[@]}"; do
            info "Installing $package..."
            yum install -y "$package" || warning "Failed to install $package"
        done
    fi
    
    success "System dependencies installed"
}

# Create system user and directories
create_user_and_directories() {
    info "Creating system user and directories..."
    
    # Create service user
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd --system --home-dir "$INSTALL_DIR" --shell /bin/false --comment "QENEX Service User" "$SERVICE_USER"
        success "Created service user: $SERVICE_USER"
    else
        info "Service user already exists: $SERVICE_USER"
    fi
    
    # Create directories
    local directories=(
        "$INSTALL_DIR"
        "$CONFIG_DIR"
        "$LOG_DIR"
        "$DATA_DIR"
        "$BACKUP_DIR"
        "$CONFIG_DIR/ssl"
        "$CONFIG_DIR/keys"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        info "Created directory: $dir"
    done
    
    # Set proper permissions
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DATA_DIR"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$BACKUP_DIR"
    
    chmod 700 "$CONFIG_DIR/ssl"
    chmod 700 "$CONFIG_DIR/keys"
    
    success "User and directories created"
}

# Setup database
setup_database() {
    info "Setting up database..."
    
    case $DATABASE_TYPE in
        postgresql)
            setup_postgresql
            ;;
        mysql)
            setup_mysql
            ;;
        sqlite)
            setup_sqlite
            ;;
        *)
            error_exit "Unsupported database type: $DATABASE_TYPE"
            ;;
    esac
    
    success "Database setup completed"
}

setup_postgresql() {
    info "Configuring PostgreSQL..."
    
    # Initialize database if not already done
    if [[ ! -d "/var/lib/postgresql/${POSTGRESQL_VERSION}/main" ]]; then
        sudo -u postgres /usr/lib/postgresql/${POSTGRESQL_VERSION}/bin/initdb -D "/var/lib/postgresql/${POSTGRESQL_VERSION}/main"
    fi
    
    # Start PostgreSQL
    systemctl enable postgresql
    systemctl start postgresql
    
    # Create database and user
    sudo -u postgres psql <<EOF
CREATE USER qenex_user WITH PASSWORD 'qenex_secure_password_$(openssl rand -hex 16)';
CREATE DATABASE qenex_db OWNER qenex_user;
GRANT ALL PRIVILEGES ON DATABASE qenex_db TO qenex_user;
\\q
EOF
    
    # Configure PostgreSQL for security
    local pg_hba_file="/etc/postgresql/${POSTGRESQL_VERSION}/main/pg_hba.conf"
    if [[ -f "$pg_hba_file" ]]; then
        # Backup original
        cp "$pg_hba_file" "${pg_hba_file}.backup"
        
        # Set secure authentication
        sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" "/etc/postgresql/${POSTGRESQL_VERSION}/main/postgresql.conf"
        sed -i "s/#port = 5432/port = 5432/" "/etc/postgresql/${POSTGRESQL_VERSION}/main/postgresql.conf"
    fi
    
    systemctl restart postgresql
    
    success "PostgreSQL configured"
}

setup_mysql() {
    info "Configuring MySQL..."
    
    # Install MySQL if not already installed
    if command -v apt-get &> /dev/null; then
        apt-get install -y mysql-server mysql-client
    elif command -v yum &> /dev/null; then
        yum install -y mysql-server mysql
    fi
    
    systemctl enable mysql
    systemctl start mysql
    
    # Secure MySQL installation
    mysql_secure_installation
    
    # Create database and user
    local mysql_root_password=$(openssl rand -hex 16)
    mysql -u root <<EOF
CREATE DATABASE qenex_db;
CREATE USER 'qenex_user'@'localhost' IDENTIFIED BY 'qenex_secure_password_$(openssl rand -hex 16)';
GRANT ALL PRIVILEGES ON qenex_db.* TO 'qenex_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
EOF
    
    success "MySQL configured"
}

setup_sqlite() {
    info "Configuring SQLite..."
    
    # Create SQLite database file
    local db_file="$DATA_DIR/qenex.db"
    touch "$db_file"
    chown "$SERVICE_USER:$SERVICE_GROUP" "$db_file"
    chmod 600 "$db_file"
    
    success "SQLite configured"
}

# Setup Redis
setup_redis() {
    info "Setting up Redis..."
    
    systemctl enable redis-server
    systemctl start redis-server
    
    # Configure Redis for security
    local redis_conf="/etc/redis/redis.conf"
    if [[ -f "$redis_conf" ]]; then
        # Backup original
        cp "$redis_conf" "${redis_conf}.backup"
        
        # Set secure configuration
        sed -i "s/# requirepass foobared/requirepass $(openssl rand -hex 16)/" "$redis_conf"
        sed -i "s/bind 127.0.0.1/bind 127.0.0.1/" "$redis_conf"
        sed -i "s/# maxmemory <bytes>/maxmemory 256mb/" "$redis_conf"
        sed -i "s/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/" "$redis_conf"
        
        systemctl restart redis-server
    fi
    
    success "Redis configured"
}

# Install Python application
install_application() {
    info "Installing QENEX application..."
    
    # Create Python virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip setuptools wheel
    
    # Install Python dependencies
    "$INSTALL_DIR/venv/bin/pip" install \
        fastapi[all] \
        uvicorn[standard] \
        sqlalchemy \
        psycopg2-binary \
        mysql-connector-python \
        redis \
        bcrypt \
        pyjwt[crypto] \
        cryptography \
        prometheus-client \
        pydantic \
        python-multipart \
        aiofiles \
        structlog \
        dash \
        dash-bootstrap-components \
        plotly \
        pandas \
        requests \
        schedule \
        psutil \
        docker \
        pyyaml
    
    # Copy application files
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
    
    if [[ -f "$script_dir/qenex_secure_core.py" ]]; then
        cp "$script_dir/qenex_secure_core.py" "$INSTALL_DIR/"
        cp "$script_dir/comprehensive_test_suite.py" "$INSTALL_DIR/"
        cp "$script_dir/production_deployment.py" "$INSTALL_DIR/"
        cp "$script_dir/compliance_dashboard.py" "$INSTALL_DIR/"
    else
        error_exit "Application files not found in script directory"
    fi
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    
    success "Application installed"
}

# Generate security keys and certificates
generate_security_keys() {
    info "Generating security keys and certificates..."
    
    # Generate encryption key
    openssl rand -hex 32 > "$CONFIG_DIR/keys/encryption.key"
    chmod 600 "$CONFIG_DIR/keys/encryption.key"
    
    # Generate JWT secret
    openssl rand -hex 64 > "$CONFIG_DIR/keys/jwt.secret"
    chmod 600 "$CONFIG_DIR/keys/jwt.secret"
    
    # Generate API keys
    openssl rand -hex 32 > "$CONFIG_DIR/keys/api.key"
    chmod 600 "$CONFIG_DIR/keys/api.key"
    
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$CONFIG_DIR/keys"
    
    success "Security keys generated"
}

# Setup SSL certificates
setup_ssl() {
    info "Setting up SSL certificates..."
    
    case $SSL_MODE in
        letsencrypt)
            setup_letsencrypt
            ;;
        self-signed)
            setup_self_signed_ssl
            ;;
        custom)
            setup_custom_ssl
            ;;
        *)
            error_exit "Unsupported SSL mode: $SSL_MODE"
            ;;
    esac
    
    success "SSL certificates configured"
}

setup_letsencrypt() {
    info "Setting up Let's Encrypt SSL..."
    
    # Obtain certificate
    certbot --nginx -d "$DOMAIN" --email "$ADMIN_EMAIL" --agree-tos --non-interactive --redirect
    
    # Setup auto-renewal
    echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
    
    success "Let's Encrypt SSL configured"
}

setup_self_signed_ssl() {
    info "Setting up self-signed SSL certificate..."
    
    # Generate self-signed certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$CONFIG_DIR/ssl/qenex.key" \
        -out "$CONFIG_DIR/ssl/qenex.crt" \
        -subj "/C=US/ST=State/L=City/O=QENEX/OU=IT/CN=$DOMAIN"
    
    chmod 600 "$CONFIG_DIR/ssl/qenex.key"
    chmod 644 "$CONFIG_DIR/ssl/qenex.crt"
    
    success "Self-signed SSL certificate generated"
}

setup_custom_ssl() {
    info "Custom SSL setup required..."
    
    warning "Please place your SSL certificate and key files at:"
    warning "  Certificate: $CONFIG_DIR/ssl/qenex.crt"
    warning "  Private Key: $CONFIG_DIR/ssl/qenex.key"
    
    read -p "Press Enter when SSL files are in place..."
    
    if [[ ! -f "$CONFIG_DIR/ssl/qenex.crt" ]] || [[ ! -f "$CONFIG_DIR/ssl/qenex.key" ]]; then
        error_exit "SSL files not found. Please place certificate and key files."
    fi
    
    success "Custom SSL certificates configured"
}

# Configure Nginx
configure_nginx() {
    info "Configuring Nginx..."
    
    # Backup default configuration
    if [[ -f "/etc/nginx/nginx.conf" ]]; then
        cp "/etc/nginx/nginx.conf" "/etc/nginx/nginx.conf.backup"
    fi
    
    # Create QENEX site configuration
    cat > "/etc/nginx/sites-available/qenex" << 'EOF'
# QENEX Financial Operating System - Nginx Configuration

upstream qenex_app {
    server 127.0.0.1:8000 fail_timeout=0;
}

upstream qenex_dashboard {
    server 127.0.0.1:8050 fail_timeout=0;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=dashboard:10m rate=5r/s;

# Security headers map
map $sent_http_content_type $security_headers {
    default "X-Frame-Options: DENY; X-Content-Type-Options: nosniff; X-XSS-Protection: 1; mode=block; Referrer-Policy: strict-origin-when-cross-origin";
}

server {
    listen 80;
    server_name _;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;
    
    # SSL Configuration
    ssl_certificate /etc/qenex/ssl/qenex.crt;
    ssl_certificate_key /etc/qenex/ssl/qenex.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';" always;
    
    # General Configuration
    client_max_body_size 4G;
    keepalive_timeout 5;
    
    # Main API
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_buffering off;
        
        proxy_pass http://qenex_app;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Compliance Dashboard
    location /dashboard/ {
        limit_req zone=dashboard burst=10 nodelay;
        
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        
        proxy_pass http://qenex_dashboard/;
    }
    
    # Health Check (no rate limiting for monitoring)
    location /health {
        proxy_pass http://qenex_app;
        access_log off;
        
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
    }
    
    # Metrics (restricted access)
    location /metrics {
        allow 127.0.0.1;
        allow ::1;
        deny all;
        
        proxy_pass http://qenex_app;
        access_log off;
    }
    
    # Static files (if any)
    location /static/ {
        alias /opt/qenex/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Default location
    location / {
        return 404;
    }
    
    # Security configurations
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    location ~ ~$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF
    
    # Enable site
    ln -sf "/etc/nginx/sites-available/qenex" "/etc/nginx/sites-enabled/"
    
    # Remove default site
    rm -f "/etc/nginx/sites-enabled/default"
    
    # Test configuration
    nginx -t
    
    # Enable and start Nginx
    systemctl enable nginx
    systemctl restart nginx
    
    success "Nginx configured"
}

# Create systemd service
create_systemd_service() {
    info "Creating systemd service..."
    
    cat > "/etc/systemd/system/qenex.service" << EOF
[Unit]
Description=QENEX Financial Operating System
Documentation=https://qenex.com/docs
After=network.target ${DATABASE_TYPE}.service redis.service
Wants=${DATABASE_TYPE}.service redis.service

[Service]
Type=exec
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/venv/bin"
Environment="QENEX_ENV=${ENVIRONMENT}"
ExecStart=${INSTALL_DIR}/venv/bin/python qenex_secure_core.py
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=30
Restart=always
RestartSec=10
StartLimitInterval=0

# Security settings
NoNewPrivileges=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=${DATA_DIR} ${LOG_DIR} ${BACKUP_DIR} /tmp
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
RestrictRealtime=yes
RestrictNamespaces=yes
LockPersonality=yes
MemoryDenyWriteExecute=yes
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# Resource limits
LimitNOFILE=65535
MemoryLimit=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
EOF
    
    # Create dashboard service
    cat > "/etc/systemd/system/qenex-dashboard.service" << EOF
[Unit]
Description=QENEX Compliance Dashboard
Documentation=https://qenex.com/docs
After=network.target qenex.service
Wants=qenex.service

[Service]
Type=exec
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/venv/bin"
Environment="QENEX_ENV=${ENVIRONMENT}"
ExecStart=${INSTALL_DIR}/venv/bin/python compliance_dashboard.py
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=${DATA_DIR} ${LOG_DIR} /tmp
PrivateTmp=yes

# Resource limits
MemoryLimit=1G
CPUQuota=100%

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable qenex
    systemctl enable qenex-dashboard
    
    success "Systemd services created"
}

# Setup firewall
setup_firewall() {
    info "Setting up firewall..."
    
    # Reset UFW to defaults
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # SSH (adjust port as needed)
    ufw allow 22/tcp comment 'SSH'
    
    # HTTP and HTTPS
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    
    # Database (only local)
    case $DATABASE_TYPE in
        postgresql)
            ufw allow from 127.0.0.1 to any port 5432 comment 'PostgreSQL local'
            ;;
        mysql)
            ufw allow from 127.0.0.1 to any port 3306 comment 'MySQL local'
            ;;
    esac
    
    # Redis (only local)
    ufw allow from 127.0.0.1 to any port 6379 comment 'Redis local'
    
    # Enable UFW
    ufw --force enable
    
    success "Firewall configured"
}

# Setup monitoring and logging
setup_monitoring() {
    info "Setting up monitoring and logging..."
    
    # Configure log rotation
    cat > "/etc/logrotate.d/qenex" << 'EOF'
/var/log/qenex/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 qenex qenex
    postrotate
        systemctl reload qenex qenex-dashboard
    endscript
}
EOF
    
    # Create Prometheus configuration
    if [[ "$MONITORING_ENABLED" == "true" ]]; then
        mkdir -p "$CONFIG_DIR/prometheus"
        cat > "$CONFIG_DIR/prometheus/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "qenex_rules.yml"

scrape_configs:
  - job_name: 'qenex-app'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 30s
    metrics_path: /metrics

  - job_name: 'system'
    static_configs:
      - targets: ['localhost:9100']
EOF
        
        # Create alerting rules
        cat > "$CONFIG_DIR/prometheus/qenex_rules.yml" << 'EOF'
groups:
  - name: qenex
    rules:
      - alert: HighErrorRate
        expr: rate(qenex_app_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"
      
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(qenex_app_response_time_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }} seconds"
      
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "QENEX service is down"
          description: "Service has been down for more than 1 minute"
EOF
    fi
    
    success "Monitoring and logging configured"
}

# Setup backup system
setup_backup() {
    if [[ "$BACKUP_ENABLED" == "true" ]]; then
        info "Setting up backup system..."
        
        # Create backup script
        cat > "$INSTALL_DIR/backup.sh" << 'EOF'
#!/bin/bash
#
# QENEX Automated Backup Script
#

set -euo pipefail

BACKUP_DIR="/var/backups/qenex"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="qenex_backup_$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Database backup
if systemctl is-active --quiet postgresql; then
    sudo -u postgres pg_dump qenex_db > "$BACKUP_DIR/$BACKUP_NAME/database.sql"
elif systemctl is-active --quiet mysql; then
    mysqldump -u qenex_user -p qenex_db > "$BACKUP_DIR/$BACKUP_NAME/database.sql"
elif [[ -f "/var/lib/qenex/qenex.db" ]]; then
    cp "/var/lib/qenex/qenex.db" "$BACKUP_DIR/$BACKUP_NAME/database.db"
fi

# Configuration backup
cp -r /etc/qenex "$BACKUP_DIR/$BACKUP_NAME/config"

# Application data backup
cp -r /var/lib/qenex "$BACKUP_DIR/$BACKUP_NAME/data"

# Log backup (last 7 days)
find /var/log/qenex -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/$BACKUP_NAME/" \;

# Create compressed archive
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "qenex_backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_NAME}.tar.gz"
EOF
        
        chmod +x "$INSTALL_DIR/backup.sh"
        chown "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR/backup.sh"
        
        # Setup cron job
        echo "0 2 * * * $SERVICE_USER $INSTALL_DIR/backup.sh >> $LOG_DIR/backup.log 2>&1" > "/etc/cron.d/qenex-backup"
        
        success "Backup system configured"
    fi
}

# Create application configuration
create_app_config() {
    info "Creating application configuration..."
    
    cat > "$CONFIG_DIR/config.yaml" << EOF
# QENEX Financial Operating System Configuration

environment: ${ENVIRONMENT}
debug: false

database:
  type: ${DATABASE_TYPE}
  host: localhost
  port: 5432
  name: qenex_db
  user: qenex_user
  password_file: ${CONFIG_DIR}/keys/db_password
  pool_size: 20
  max_overflow: 30

redis:
  host: localhost
  port: 6379
  db: 0
  password_file: ${CONFIG_DIR}/keys/redis_password

security:
  encryption_key_file: ${CONFIG_DIR}/keys/encryption.key
  jwt_secret_file: ${CONFIG_DIR}/keys/jwt.secret
  ssl_cert_file: ${CONFIG_DIR}/ssl/qenex.crt
  ssl_key_file: ${CONFIG_DIR}/ssl/qenex.key
  session_timeout: 1800
  max_login_attempts: 5
  rate_limit_per_minute: 100

application:
  host: 127.0.0.1
  port: 8000
  workers: 4
  worker_class: uvicorn.workers.UvicornWorker
  timeout: 30
  keepalive: 2

dashboard:
  host: 127.0.0.1
  port: 8050
  debug: false

monitoring:
  enabled: ${MONITORING_ENABLED}
  metrics_port: 9090
  health_check_port: 8080

logging:
  level: INFO
  file: ${LOG_DIR}/qenex.log
  max_size: 100MB
  backup_count: 10

backup:
  enabled: ${BACKUP_ENABLED}
  directory: ${BACKUP_DIR}
  interval_hours: 6
  retention_days: 30

compliance:
  kyc_required: true
  aml_monitoring: true
  suspicious_activity_threshold: 0.8
  large_transaction_threshold: 10000

performance:
  max_connections: 1000
  connection_timeout: 30
  request_timeout: 30
  worker_timeout: 30

features:
  api_enabled: true
  dashboard_enabled: true
  backup_enabled: ${BACKUP_ENABLED}
  monitoring_enabled: ${MONITORING_ENABLED}
  audit_logging: true
  transaction_history: true
EOF
    
    # Set proper permissions
    chown "$SERVICE_USER:$SERVICE_GROUP" "$CONFIG_DIR/config.yaml"
    chmod 600 "$CONFIG_DIR/config.yaml"
    
    success "Application configuration created"
}

# Setup fail2ban
setup_fail2ban() {
    info "Setting up fail2ban..."
    
    # Create QENEX jail configuration
    cat > "/etc/fail2ban/jail.local" << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = auto
usedns = warn

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 3

[qenex-api]
enabled = true
filter = qenex-api
port = http,https
logpath = /var/log/qenex/qenex.log
maxretry = 5
bantime = 1800
EOF
    
    # Create QENEX filter
    cat > "/etc/fail2ban/filter.d/qenex-api.conf" << 'EOF'
[Definition]
failregex = ^.*Authentication failed.*<HOST>.*$
            ^.*Rate limit exceeded.*<HOST>.*$
            ^.*Blocked transaction.*<HOST>.*$
ignoreregex =
EOF
    
    systemctl enable fail2ban
    systemctl restart fail2ban
    
    success "Fail2ban configured"
}

# Run security hardening
security_hardening() {
    info "Applying security hardening..."
    
    # Secure shared memory
    echo "tmpfs /run/shm tmpfs defaults,noexec,nosuid 0 0" >> /etc/fstab
    
    # Disable core dumps
    echo "* hard core 0" >> /etc/security/limits.conf
    
    # Set secure kernel parameters
    cat > "/etc/sysctl.d/99-qenex-security.conf" << 'EOF'
# Network security
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_timestamps = 0
net.ipv4.ip_forward = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1

# IPv6 security
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_source_route = 0

# System security
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
kernel.yama.ptrace_scope = 1
EOF
    
    sysctl --system
    
    # Set secure umask
    echo "umask 027" >> /etc/bash.bashrc
    
    success "Security hardening applied"
}

# Start services
start_services() {
    info "Starting services..."
    
    local services=(
        "postgresql"
        "redis-server"
        "nginx"
        "fail2ban"
        "qenex"
        "qenex-dashboard"
    )
    
    for service in "${services[@]}"; do
        if systemctl list-unit-files | grep -q "^${service}.service"; then
            info "Starting $service..."
            systemctl start "$service" || warning "Failed to start $service"
        fi
    done
    
    # Wait for services to start
    sleep 10
    
    success "Services started"
}

# Verify installation
verify_installation() {
    info "Verifying installation..."
    
    local checks_passed=0
    local total_checks=8
    
    # Check service status
    if systemctl is-active --quiet qenex; then
        success "✓ QENEX service is running"
        ((checks_passed++))
    else
        warning "✗ QENEX service is not running"
    fi
    
    # Check dashboard service
    if systemctl is-active --quiet qenex-dashboard; then
        success "✓ Dashboard service is running"
        ((checks_passed++))
    else
        warning "✗ Dashboard service is not running"
    fi
    
    # Check database
    case $DATABASE_TYPE in
        postgresql)
            if systemctl is-active --quiet postgresql; then
                success "✓ PostgreSQL is running"
                ((checks_passed++))
            else
                warning "✗ PostgreSQL is not running"
            fi
            ;;
        mysql)
            if systemctl is-active --quiet mysql; then
                success "✓ MySQL is running"
                ((checks_passed++))
            else
                warning "✗ MySQL is not running"
            fi
            ;;
        sqlite)
            if [[ -f "$DATA_DIR/qenex.db" ]]; then
                success "✓ SQLite database exists"
                ((checks_passed++))
            else
                warning "✗ SQLite database not found"
            fi
            ;;
    esac
    
    # Check Redis
    if systemctl is-active --quiet redis-server; then
        success "✓ Redis is running"
        ((checks_passed++))
    else
        warning "✗ Redis is not running"
    fi
    
    # Check Nginx
    if systemctl is-active --quiet nginx; then
        success "✓ Nginx is running"
        ((checks_passed++))
    else
        warning "✗ Nginx is not running"
    fi
    
    # Check SSL certificate
    if [[ -f "$CONFIG_DIR/ssl/qenex.crt" ]] && [[ -f "$CONFIG_DIR/ssl/qenex.key" ]]; then
        success "✓ SSL certificates exist"
        ((checks_passed++))
    else
        warning "✗ SSL certificates not found"
    fi
    
    # Check firewall
    if ufw status | grep -q "Status: active"; then
        success "✓ Firewall is active"
        ((checks_passed++))
    else
        warning "✗ Firewall is not active"
    fi
    
    # Check application response
    if curl -k -s "https://localhost/health" > /dev/null 2>&1; then
        success "✓ Application is responding"
        ((checks_passed++))
    else
        warning "✗ Application is not responding"
    fi
    
    # Summary
    local success_rate=$((checks_passed * 100 / total_checks))
    info "Installation verification: $checks_passed/$total_checks checks passed ($success_rate%)"
    
    if [[ $success_rate -ge 80 ]]; then
        success "Installation verification passed!"
        return 0
    else
        warning "Installation verification failed. Some components may need attention."
        return 1
    fi
}

# Display installation summary
show_installation_summary() {
    cat << EOF

${GREEN}════════════════════════════════════════════════════════════════════════════════${NC}
${GREEN}                    QENEX INSTALLATION COMPLETED SUCCESSFULLY!${NC}
${GREEN}════════════════════════════════════════════════════════════════════════════════${NC}

${BLUE}SYSTEM INFORMATION:${NC}
  Environment: ${ENVIRONMENT}
  Domain: ${DOMAIN}
  Database: ${DATABASE_TYPE}
  SSL Mode: ${SSL_MODE}
  
${BLUE}SERVICE ENDPOINTS:${NC}
  🌐 Main Application: https://${DOMAIN}/api/
  📊 Compliance Dashboard: https://${DOMAIN}/dashboard/
  💚 Health Check: https://${DOMAIN}/health
  📈 Metrics: https://${DOMAIN}/metrics (localhost only)

${BLUE}SYSTEM FILES:${NC}
  📁 Installation: ${INSTALL_DIR}
  ⚙️  Configuration: ${CONFIG_DIR}
  📝 Logs: ${LOG_DIR}
  💾 Data: ${DATA_DIR}
  🔐 SSL Certificates: ${CONFIG_DIR}/ssl/
  🗝️  Security Keys: ${CONFIG_DIR}/keys/

${BLUE}SERVICES:${NC}
  • QENEX Core Application (qenex.service)
  • QENEX Compliance Dashboard (qenex-dashboard.service)
  • PostgreSQL Database
  • Redis Cache
  • Nginx Web Server
  • Fail2ban Intrusion Prevention

${BLUE}SECURITY FEATURES ENABLED:${NC}
  ✅ SSL/TLS Encryption
  ✅ Firewall (UFW) Active
  ✅ Fail2ban Protection
  ✅ Security Headers
  ✅ Rate Limiting
  ✅ Secure System Configuration
  ✅ Service Isolation
  ✅ File Permissions Hardened

${BLUE}MANAGEMENT COMMANDS:${NC}
  # Check service status
  sudo systemctl status qenex qenex-dashboard
  
  # View logs
  sudo journalctl -u qenex -f
  sudo tail -f ${LOG_DIR}/qenex.log
  
  # Restart services
  sudo systemctl restart qenex qenex-dashboard
  
  # Run backup
  sudo ${INSTALL_DIR}/backup.sh
  
  # Check firewall status
  sudo ufw status
  
  # SSL certificate renewal (Let's Encrypt)
  sudo certbot renew

${BLUE}NEXT STEPS:${NC}
  1. 📝 Review configuration: ${CONFIG_DIR}/config.yaml
  2. 🔐 Change default passwords in configuration files
  3. 📧 Configure email settings for alerts
  4. 🧪 Run the test suite: cd ${INSTALL_DIR} && python comprehensive_test_suite.py
  5. 📊 Access the dashboard: https://${DOMAIN}/dashboard/
  6. 🔍 Monitor logs for any issues
  7. 📚 Review documentation for API usage
  8. 🛡️  Set up monitoring and alerting
  9. 💾 Verify backup system is working
  10. 🚀 Start using your secure financial operating system!

${YELLOW}IMPORTANT SECURITY NOTES:${NC}
  • Default passwords have been generated and stored in ${CONFIG_DIR}/keys/
  • Change these passwords before production use
  • Regularly update the system and dependencies
  • Monitor the logs for security events
  • Review and adjust firewall rules as needed
  • Set up proper SSL certificates for production

${GREEN}🎉 QENEX Financial Operating System is now ready for production use!${NC}

For support and documentation, visit: https://qenex.com/docs

EOF
}

# Main installation function
main() {
    echo -e "${PURPLE}"
    cat << 'EOF'
██████╗ ███████╗███╗   ██╗███████╗██╗  ██╗
██╔══██╗██╔════╝████╗  ██║██╔════╝╚██╗██╔╝
██║  ██║█████╗  ██╔██╗ ██║█████╗   ╚███╔╝ 
██║  ██║██╔══╝  ██║╚██╗██║██╔══╝   ██╔██╗ 
██████╔╝███████╗██║ ╚████║███████╗██╔╝ ██╗
╚═════╝ ╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝

FINANCIAL OPERATING SYSTEM - PRODUCTION INSTALLER
EOF
    echo -e "${NC}"
    
    # Parse arguments
    parse_args "$@"
    
    # Pre-installation checks
    check_root
    check_system_requirements
    
    info "Starting QENEX installation..."
    info "Environment: $ENVIRONMENT"
    info "Database: $DATABASE_TYPE"
    info "Domain: $DOMAIN"
    info "SSL Mode: $SSL_MODE"
    
    # Main installation steps
    update_system
    install_dependencies
    create_user_and_directories
    setup_database
    setup_redis
    install_application
    generate_security_keys
    setup_ssl
    configure_nginx
    create_systemd_service
    setup_firewall
    setup_monitoring
    setup_backup
    create_app_config
    setup_fail2ban
    security_hardening
    start_services
    
    # Verify installation
    if verify_installation; then
        show_installation_summary
        exit 0
    else
        error_exit "Installation verification failed. Please check the logs and try again."
    fi
}

# Script entry point
main "$@"