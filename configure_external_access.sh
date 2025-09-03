#!/bin/bash
# QENEX External Network Access Configuration
# Securely expose QENEX services to external networks

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
QENEX_ROOT="/opt/qenex-os"
CONFIG_FILE="$QENEX_ROOT/config/external_access.yaml"

# Get current IP addresses
get_ip_addresses() {
    echo -e "${CYAN}Current Network Configuration:${NC}"
    echo "----------------------------------------"
    
    # Get private IP
    PRIVATE_IP=$(hostname -I | awk '{print $1}')
    echo -e "Private IP: ${GREEN}$PRIVATE_IP${NC}"
    
    # Get public IP
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "Unable to detect")
    echo -e "Public IP: ${GREEN}$PUBLIC_IP${NC}"
    
    # Get all network interfaces
    echo -e "\nNetwork Interfaces:"
    ip -4 addr show | grep -E "inet " | awk '{print "  " $NF ": " $2}'
    
    echo "----------------------------------------"
}

# Configure firewall
configure_firewall() {
    echo -e "${BLUE}Configuring firewall rules...${NC}"
    
    # Check which firewall is installed
    if command -v ufw &> /dev/null; then
        echo "Using UFW firewall"
        
        # Enable UFW if not already enabled
        sudo ufw --force enable
        
        # Allow QENEX ports
        sudo ufw allow 8080/tcp comment 'QENEX Dashboard'
        sudo ufw allow 8000/tcp comment 'QENEX API'
        sudo ufw allow 8082/tcp comment 'QENEX Webhooks'
        
        # Allow SSH (important!)
        sudo ufw allow ssh
        
        # Reload firewall
        sudo ufw reload
        
        echo -e "${GREEN}✓ UFW firewall configured${NC}"
        sudo ufw status numbered
        
    elif command -v firewall-cmd &> /dev/null; then
        echo "Using firewalld"
        
        # Add QENEX services
        sudo firewall-cmd --permanent --add-port=8080/tcp
        sudo firewall-cmd --permanent --add-port=8000/tcp
        sudo firewall-cmd --permanent --add-port=8082/tcp
        
        # Reload firewall
        sudo firewall-cmd --reload
        
        echo -e "${GREEN}✓ firewalld configured${NC}"
        sudo firewall-cmd --list-all
        
    elif command -v iptables &> /dev/null; then
        echo "Using iptables"
        
        # Add iptables rules
        sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT -m comment --comment "QENEX Dashboard"
        sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT -m comment --comment "QENEX API"
        sudo iptables -A INPUT -p tcp --dport 8082 -j ACCEPT -m comment --comment "QENEX Webhooks"
        
        # Save iptables rules
        if command -v iptables-save &> /dev/null; then
            sudo iptables-save > /etc/iptables/rules.v4 2>/dev/null || sudo iptables-save > /etc/sysconfig/iptables 2>/dev/null || true
        fi
        
        echo -e "${GREEN}✓ iptables configured${NC}"
        sudo iptables -L -n | grep -E "8080|8000|8082"
    else
        echo -e "${YELLOW}⚠ No firewall detected. Please configure manually.${NC}"
    fi
}

# Configure services to listen on all interfaces
configure_services() {
    echo -e "${BLUE}Configuring QENEX services for external access...${NC}"
    
    # Update dashboard server
    if [ -f "$QENEX_ROOT/cicd/dashboard_server.py" ]; then
        # Backup original
        cp "$QENEX_ROOT/cicd/dashboard_server.py" "$QENEX_ROOT/cicd/dashboard_server.py.bak"
        
        # Update to listen on all interfaces (0.0.0.0)
        sed -i 's/("", DASHBOARD_PORT)/("0.0.0.0", DASHBOARD_PORT)/g' "$QENEX_ROOT/cicd/dashboard_server.py"
        sed -i 's/localhost/0.0.0.0/g' "$QENEX_ROOT/cicd/dashboard_server.py"
        
        echo -e "${GREEN}✓ Dashboard configured for external access${NC}"
    fi
    
    # Update API server
    if [ -f "$QENEX_ROOT/cicd/api_server.py" ]; then
        cp "$QENEX_ROOT/cicd/api_server.py" "$QENEX_ROOT/cicd/api_server.py.bak"
        sed -i 's/host="127.0.0.1"/host="0.0.0.0"/g' "$QENEX_ROOT/cicd/api_server.py"
        sed -i 's/localhost/0.0.0.0/g' "$QENEX_ROOT/cicd/api_server.py"
        
        echo -e "${GREEN}✓ API server configured for external access${NC}"
    fi
    
    # Update webhook server
    if [ -f "$QENEX_ROOT/cicd/webhook_server.py" ]; then
        cp "$QENEX_ROOT/cicd/webhook_server.py" "$QENEX_ROOT/cicd/webhook_server.py.bak"
        sed -i 's/("", WEBHOOK_PORT)/("0.0.0.0", WEBHOOK_PORT)/g' "$QENEX_ROOT/cicd/webhook_server.py"
        
        echo -e "${GREEN}✓ Webhook server configured for external access${NC}"
    fi
    
    # Create external access configuration
    mkdir -p "$QENEX_ROOT/config"
    cat > "$CONFIG_FILE" << EOL
# QENEX External Access Configuration
external_access:
  enabled: true
  listen_address: "0.0.0.0"
  
  dashboard:
    port: 8080
    ssl_enabled: false
    allowed_origins:
      - "*"
  
  api:
    port: 8000
    ssl_enabled: false
    cors_enabled: true
    allowed_origins:
      - "*"
  
  webhooks:
    port: 8082
    ssl_enabled: false
  
  security:
    rate_limiting: true
    max_requests_per_minute: 100
    ip_whitelist: []  # Add IPs here to restrict access
    ip_blacklist: []
    
  public_url: "http://$PUBLIC_IP"
EOL
    
    echo -e "${GREEN}✓ External access configuration created${NC}"
}

# Configure Nginx reverse proxy (optional)
configure_nginx() {
    echo -e "${BLUE}Would you like to configure Nginx as a reverse proxy? (y/n)${NC}"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        # Install Nginx if not present
        if ! command -v nginx &> /dev/null; then
            echo "Installing Nginx..."
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y nginx
            elif command -v yum &> /dev/null; then
                sudo yum install -y nginx
            fi
        fi
        
        # Create Nginx configuration
        cat > /tmp/qenex-nginx.conf << 'EOL'
# QENEX Reverse Proxy Configuration
upstream qenex_dashboard {
    server 127.0.0.1:8080;
}

upstream qenex_api {
    server 127.0.0.1:8000;
}

upstream qenex_webhooks {
    server 127.0.0.1:8082;
}

server {
    listen 80;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Dashboard
    location / {
        proxy_pass http://qenex_dashboard;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API
    location /api {
        proxy_pass http://qenex_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Webhooks
    location /webhooks {
        proxy_pass http://qenex_webhooks;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket support for dashboard
    location /ws {
        proxy_pass http://qenex_dashboard;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOL
        
        # Install Nginx configuration
        sudo cp /tmp/qenex-nginx.conf /etc/nginx/sites-available/qenex
        sudo ln -sf /etc/nginx/sites-available/qenex /etc/nginx/sites-enabled/
        
        # Test and reload Nginx
        sudo nginx -t && sudo systemctl reload nginx
        
        echo -e "${GREEN}✓ Nginx reverse proxy configured${NC}"
        echo -e "${CYAN}Access QENEX via: http://$PUBLIC_IP/${NC}"
    fi
}

# Configure SSL/TLS with Let's Encrypt
configure_ssl() {
    echo -e "${BLUE}Would you like to configure SSL/TLS with Let's Encrypt? (y/n)${NC}"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Enter your domain name (e.g., qenex.example.com):${NC}"
        read -r DOMAIN
        
        echo -e "${YELLOW}Enter your email for Let's Encrypt:${NC}"
        read -r EMAIL
        
        # Install Certbot
        if ! command -v certbot &> /dev/null; then
            echo "Installing Certbot..."
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y certbot python3-certbot-nginx
            elif command -v yum &> /dev/null; then
                sudo yum install -y certbot python3-certbot-nginx
            fi
        fi
        
        # Obtain certificate
        sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL"
        
        echo -e "${GREEN}✓ SSL/TLS configured for $DOMAIN${NC}"
        echo -e "${CYAN}Access QENEX via: https://$DOMAIN/${NC}"
    fi
}

# Security recommendations
show_security_recommendations() {
    echo
    echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}            SECURITY RECOMMENDATIONS                    ${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
    echo
    echo -e "${CYAN}1. Authentication:${NC}"
    echo "   - Enable authentication in QENEX settings"
    echo "   - Use strong passwords"
    echo "   - Consider implementing 2FA"
    echo
    echo -e "${CYAN}2. Network Security:${NC}"
    echo "   - Use SSL/TLS for production"
    echo "   - Implement IP whitelisting if possible"
    echo "   - Use VPN for sensitive environments"
    echo
    echo -e "${CYAN}3. Access Control:${NC}"
    echo "   - Restrict ports to specific IPs:"
    echo "     sudo ufw allow from <YOUR_IP> to any port 8080"
    echo
    echo -e "${CYAN}4. Monitoring:${NC}"
    echo "   - Monitor access logs: /var/log/nginx/access.log"
    echo "   - Set up alerts for suspicious activity"
    echo
    echo -e "${CYAN}5. Updates:${NC}"
    echo "   - Keep QENEX and system packages updated"
    echo "   - Regular security audits"
    echo
}

# Create access URLs file
create_access_urls() {
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "YOUR_PUBLIC_IP")
    PRIVATE_IP=$(hostname -I | awk '{print $1}')
    
    cat > "$QENEX_ROOT/ACCESS_URLS.txt" << EOL
QENEX External Access URLs
═══════════════════════════════════════════════════════

Dashboard Access:
  Local:    http://localhost:8080
  Private:  http://$PRIVATE_IP:8080
  Public:   http://$PUBLIC_IP:8080

API Documentation:
  Local:    http://localhost:8000/docs
  Private:  http://$PRIVATE_IP:8000/docs
  Public:   http://$PUBLIC_IP:8000/docs

Webhook Endpoints:
  GitHub:   http://$PUBLIC_IP:8082/webhook/github
  GitLab:   http://$PUBLIC_IP:8082/webhook/gitlab

WebSocket (for real-time updates):
  ws://$PUBLIC_IP:8081

Note: Replace $PUBLIC_IP with your actual public IP or domain name.

For SSL/TLS access (if configured):
  https://your-domain.com

Troubleshooting:
  - Ensure ports 8080, 8000, 8082 are open in your firewall
  - Check that services are running: systemctl status qenex-os
  - View logs: tail -f /opt/qenex-os/logs/qenex.log
EOL
    
    echo -e "${GREEN}✓ Access URLs saved to: $QENEX_ROOT/ACCESS_URLS.txt${NC}"
    cat "$QENEX_ROOT/ACCESS_URLS.txt"
}

# Main function
main() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     QENEX External Network Access Configuration       ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}This script must be run as root${NC}"
        exit 1
    fi
    
    # Show current network configuration
    get_ip_addresses
    
    echo -e "${YELLOW}This will configure QENEX to be accessible from external networks.${NC}"
    echo -e "${YELLOW}Continue? (y/n)${NC}"
    read -r response
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Configuration cancelled"
        exit 0
    fi
    
    # Configure components
    configure_firewall
    configure_services
    configure_nginx
    configure_ssl
    
    # Show security recommendations
    show_security_recommendations
    
    # Create access URLs file
    create_access_urls
    
    # Restart QENEX services
    echo
    echo -e "${BLUE}Restarting QENEX services...${NC}"
    systemctl restart qenex-os 2>/dev/null || echo "Please restart QENEX manually"
    
    echo
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║       External Access Configuration Complete!         ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${CYAN}You can now access QENEX from external networks!${NC}"
    echo
}

# Run main function
main "$@"