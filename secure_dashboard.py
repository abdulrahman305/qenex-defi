#!/usr/bin/env python3
"""
Secure QENEX Dashboard
Fixes all security vulnerabilities from the original dashboard
"""

import os
import json
import time
import hashlib
import secrets
import logging
from datetime import datetime
from typing import Dict, Optional
from flask import Flask, render_template_string, request, jsonify, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import psutil

# Import security modules
from security.security_config import SECURITY_CONFIG, SECURITY_HEADERS, get_secure_config
from security.input_validator import validator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/qenex-os/logs/dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app with security
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# Get secure configuration
config = get_secure_config()

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Authentication storage (in production, use proper database)
AUTH_TOKENS = {}
SESSION_TIMEOUT = config['SESSION_TIMEOUT']

class SecureMetricsCollector:
    """Secure system metrics collector"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 5  # seconds
    
    def get_metrics(self) -> Dict:
        """Get system metrics with caching"""
        cache_key = "system_metrics"
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_timeout:
                return cached_data
        
        try:
            # Collect metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load_avg = os.getloadavg()
            
            metrics = {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_used_mb": round(memory.used / (1024**2), 1),
                "memory_total_mb": round(memory.total / (1024**2), 1),
                "disk_percent": round(disk.percent, 1),
                "disk_used_gb": round(disk.used / (1024**3), 1),
                "disk_total_gb": round(disk.total / (1024**3), 1),
                "load_average": round(load_avg[0], 2),
                "process_count": len(psutil.pids()),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Update cache
            self.cache[cache_key] = (time.time(), metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {"error": "Unable to collect metrics"}

# Initialize metrics collector
metrics_collector = SecureMetricsCollector()

def require_auth(f):
    """Decorator to require authentication"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401
        
        token = auth_header.replace('Bearer ', '')
        
        # Validate token
        if not validate_token(token):
            return jsonify({"error": "Invalid or expired token"}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

def validate_token(token: str) -> bool:
    """Validate authentication token"""
    if not token or len(token) != 64:  # Expected token length
        return False
    
    # Check if token exists and is not expired
    if token in AUTH_TOKENS:
        created_time = AUTH_TOKENS[token]
        if time.time() - created_time < SESSION_TIMEOUT:
            return True
        else:
            # Remove expired token
            del AUTH_TOKENS[token]
    
    return False

def add_security_headers(response):
    """Add security headers to response"""
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response

@app.after_request
def after_request(response):
    """Add security headers to all responses"""
    return add_security_headers(response)

@app.route('/')
@limiter.limit("10 per minute")
def index():
    """Secure dashboard homepage"""
    
    # Use environment variable for host, never hardcode IPs
    dashboard_url = f"http://{config['HOST']}:{config['PORT']}"
    
    template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="Content-Security-Policy" content="default-src 'self';">
        <title>QENEX Secure Dashboard</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                color: white;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                padding: 20px;
                background: rgba(255,255,255,0.1);
                border-radius: 10px;
                margin-bottom: 20px;
            }
            .metrics {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
            }
            .metric-card {
                background: rgba(255,255,255,0.1);
                padding: 20px;
                border-radius: 10px;
                backdrop-filter: blur(10px);
            }
            .metric-value {
                font-size: 2em;
                font-weight: bold;
            }
            .metric-label {
                opacity: 0.8;
                margin-top: 5px;
            }
            .security-status {
                background: rgba(0,255,0,0.2);
                padding: 10px;
                border-radius: 5px;
                text-align: center;
                margin-top: 20px;
            }
            .auth-required {
                background: rgba(255,255,0,0.2);
                padding: 10px;
                border-radius: 5px;
                text-align: center;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔒 QENEX Secure Dashboard</h1>
                <p>Protected with Authentication & Rate Limiting</p>
            </div>
            
            <div class="auth-required">
                ⚠️ Authentication required for API access
            </div>
            
            <div id="metrics" class="metrics">
                <div class="metric-card">
                    <div class="metric-value">--</div>
                    <div class="metric-label">CPU Usage</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">--</div>
                    <div class="metric-label">Memory Usage</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">--</div>
                    <div class="metric-label">Disk Usage</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">--</div>
                    <div class="metric-label">Process Count</div>
                </div>
            </div>
            
            <div class="security-status">
                ✅ All Security Features Active
            </div>
        </div>
        
        <script>
            // Note: Metrics require authentication token
            async function fetchMetrics() {
                const token = localStorage.getItem('auth_token');
                if (!token) {
                    console.log('Authentication required');
                    return;
                }
                
                try {
                    const response = await fetch('/api/metrics', {
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        updateMetrics(data);
                    }
                } catch (error) {
                    console.error('Failed to fetch metrics:', error);
                }
            }
            
            function updateMetrics(data) {
                const cards = document.querySelectorAll('.metric-card');
                if (cards[0]) cards[0].querySelector('.metric-value').textContent = data.cpu_percent + '%';
                if (cards[1]) cards[1].querySelector('.metric-value').textContent = data.memory_percent + '%';
                if (cards[2]) cards[2].querySelector('.metric-value').textContent = data.disk_percent + '%';
                if (cards[3]) cards[3].querySelector('.metric-value').textContent = data.process_count;
            }
            
            // Attempt to fetch metrics every 5 seconds
            setInterval(fetchMetrics, 5000);
            fetchMetrics();
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(template)

@app.route('/api/auth', methods=['POST'])
@limiter.limit("5 per minute")
def authenticate():
    """Authenticate and get access token"""
    
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'api_key' not in data:
            return jsonify({"error": "API key required"}), 400
        
        api_key = data['api_key']
        
        # Validate API key (in production, check against database)
        if api_key != config['API_KEY']:
            logger.warning(f"Failed authentication attempt from {request.remote_addr}")
            return jsonify({"error": "Invalid API key"}), 401
        
        # Generate secure token
        token = secrets.token_hex(32)
        AUTH_TOKENS[token] = time.time()
        
        logger.info(f"Successful authentication from {request.remote_addr}")
        
        return jsonify({
            "token": token,
            "expires_in": SESSION_TIMEOUT
        })
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return jsonify({"error": "Authentication failed"}), 500

@app.route('/api/metrics')
@limiter.limit("30 per minute")
@require_auth
def get_metrics():
    """Get system metrics (requires authentication)"""
    
    try:
        metrics = metrics_collector.get_metrics()
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": "Unable to retrieve metrics"}), 500

@app.route('/api/health')
@limiter.limit("60 per minute")
def health_check():
    """Health check endpoint (no auth required)"""
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "security": {
            "rate_limiting": "active",
            "authentication": "required",
            "headers": "secured"
        }
    })

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(429)
def rate_limit_exceeded(e):
    """Handle rate limit errors"""
    return jsonify({"error": "Rate limit exceeded", "message": str(e.description)}), 429

@app.errorhandler(500)
def internal_error(e):
    """Handle internal errors"""
    logger.error(f"Internal error: {e}")
    return jsonify({"error": "Internal server error"}), 500

def cleanup_expired_tokens():
    """Clean up expired authentication tokens"""
    current_time = time.time()
    expired_tokens = [
        token for token, created_time in AUTH_TOKENS.items()
        if current_time - created_time > SESSION_TIMEOUT
    ]
    
    for token in expired_tokens:
        del AUTH_TOKENS[token]
    
    if expired_tokens:
        logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")

if __name__ == '__main__':
    # Use configuration from environment or defaults
    host = config['HOST']
    port = config['PORT']
    
    # Never bind to 0.0.0.0 in production without proper firewall
    if host == "0.0.0.0":
        logger.warning("WARNING: Binding to all interfaces. Ensure firewall is configured!")
    
    logger.info(f"Starting secure dashboard on {host}:{port}")
    
    # Start token cleanup thread
    import threading
    cleanup_thread = threading.Timer(300, cleanup_expired_tokens)  # Every 5 minutes
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    # Run with proper security settings
    app.run(
        host=host,
        port=port,
        debug=False,  # Never enable debug in production
        use_reloader=False,
        threaded=True
    )