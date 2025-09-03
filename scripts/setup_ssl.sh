#!/bin/bash
# QENEX SSL/HTTPS Setup with Let's Encrypt

DOMAIN=${1:-"91.99.223.180"}
EMAIL=${2:-"admin@qenex.local"}

echo "🔐 Setting up SSL/HTTPS for QENEX..."

# Install certbot if not present
if ! command -v certbot &> /dev/null; then
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Create webroot directory
mkdir -p /var/www/certbot

# Update nginx config for SSL
cat > /etc/nginx/sites-available/qenex-ssl <<'EOF'
server {
    listen 80;
    server_name _;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name _;
    
    ssl_certificate /etc/letsencrypt/live/qenex/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/qenex/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    root /opt/qenex-os/dashboard;
    index index.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /metrics {
        proxy_pass http://localhost:9090/metrics;
    }
    
    location /grafana/ {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location = /api.json {
        add_header Content-Type application/json;
        try_files $uri =404;
    }
    
    location = /api.php {
        fastcgi_pass unix:/var/run/php/php8.3-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
EOF

# Generate self-signed certificate for now
if [ ! -f /etc/letsencrypt/live/qenex/fullchain.pem ]; then
    mkdir -p /etc/letsencrypt/live/qenex
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/letsencrypt/live/qenex/privkey.pem \
        -out /etc/letsencrypt/live/qenex/fullchain.pem \
        -subj "/C=US/ST=State/L=City/O=QENEX/CN=$DOMAIN"
    echo "✅ Self-signed certificate generated"
fi

# Enable SSL site
ln -sf /etc/nginx/sites-available/qenex-ssl /etc/nginx/sites-enabled/
nginx -t && nginx -s reload

echo "✅ SSL/HTTPS setup complete!"
echo "Access QENEX at: https://$DOMAIN"

# Try to get real Let's Encrypt certificate if domain is valid
if [[ "$DOMAIN" =~ ^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    echo "Attempting to get Let's Encrypt certificate for $DOMAIN..."
    certbot certonly --webroot -w /var/www/certbot -d $DOMAIN --email $EMAIL --agree-tos --non-interactive || true
fi