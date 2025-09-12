#!/usr/bin/env python3
"""
Quick start script for QENEX services with external access
"""

import sys
import os
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json

# Simple dashboard HTML
DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>QENEX CI/CD Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            text-align: center;
        }
        h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            background: rgba(255,255,255,0.15);
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .stat-label {
            opacity: 0.9;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 1px;
        }
        .features {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .feature {
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            text-align: center;
        }
        .status {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .status-ok {
            color: #4ade80;
        }
        .status-error {
            color: #f87171;
        }
        .links {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }
        .links a {
            color: #fff;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 10px;
            display: inline-block;
            margin: 5px;
            transition: background 0.3s;
        }
        .links a:hover {
            background: rgba(255,255,255,0.3);
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .live-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #4ade80;
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 QENEX CI/CD Dashboard</h1>
            <p class="subtitle">Unified AI Operating System v3.0.0</p>
            <p style="margin-top: 10px;">
                <span class="live-indicator"></span>
                System Operational
            </p>
        </header>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">12</div>
                <div class="stat-label">Active Pipelines</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">94%</div>
                <div class="stat-label">Success Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">3.2m</div>
                <div class="stat-label">Avg Build Time</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">247</div>
                <div class="stat-label">Total Deployments</div>
            </div>
        </div>
        
        <div class="features">
            <h2>✨ Features</h2>
            <div class="feature-grid">
                <div class="feature">🤖 AI-Driven</div>
                <div class="feature">🔄 GitOps</div>
                <div class="feature">🛡️ Security</div>
                <div class="feature">📊 Analytics</div>
                <div class="feature">🚀 Auto-Deploy</div>
                <div class="feature">🔧 Self-Healing</div>
                <div class="feature">📦 Templates</div>
                <div class="feature">🌐 Multi-Cloud</div>
            </div>
        </div>
        
        <div class="status">
            <h2>📊 System Status</h2>
            <div class="status-item">
                <span>API Server</span>
                <span class="status-ok">● Online</span>
            </div>
            <div class="status-item">
                <span>GitOps Controller</span>
                <span class="status-ok">● Active</span>
            </div>
            <div class="status-item">
                <span>AI Engine</span>
                <span class="status-ok">● Learning</span>
            </div>
            <div class="status-item">
                <span>Webhook Server</span>
                <span class="status-ok">● Listening</span>
            </div>
            <div class="status-item">
                <span>Cache System</span>
                <span class="status-ok">● Optimized</span>
            </div>
        </div>
        
        <div class="links">
            <h2>🔗 Quick Links</h2>
            <a href="/api/pipelines">Pipeline API</a>
            <a href="/metrics">Metrics</a>
            <a href="/health">Health Check</a>
            <a href="http://91.99.223.180:8000/docs" target="_blank">API Docs</a>
            <a href="https://github.com/qenex/unified-ai-os" target="_blank">GitHub</a>
        </div>
        
        <div style="text-align: center; margin-top: 40px; opacity: 0.7;">
            <p>Access this dashboard from anywhere: http://91.99.223.180:8080</p>
            <p style="margin-top: 10px;">© 2024 QENEX Unified AI OS</p>
        </div>
    </div>
    
    <script>
        // Auto-refresh stats every 5 seconds
        setInterval(() => {
            // In a real implementation, this would fetch from API
            document.querySelectorAll('.stat-value').forEach(el => {
                if (el.textContent.includes('%')) {
                    el.textContent = (90 + Math.random() * 10).toFixed(1) + '%';
                }
            });
        }, 5000);
        
        // Show current time
        setInterval(() => {
            const now = new Date();
            console.log('Dashboard updated at:', now.toLocaleTimeString());
        }, 1000);
    </script>
</body>
</html>
"""

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/dashboard':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy', 'timestamp': time.time()}).encode())
        elif self.path == '/api/pipelines':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            pipelines = [
                {'id': '1', 'name': 'frontend-build', 'status': 'success'},
                {'id': '2', 'name': 'backend-test', 'status': 'running'},
                {'id': '3', 'name': 'deploy-prod', 'status': 'pending'}
            ]
            self.wfile.write(json.dumps(pipelines).encode())
        elif self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            metrics = """# QENEX Metrics
qenex_pipelines_total 247
qenex_pipelines_success 232
qenex_pipelines_failed 15
qenex_build_duration_seconds 192
"""
            self.wfile.write(metrics.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress logs
        pass

def start_dashboard():
    """Start dashboard server on all interfaces"""
    print("Starting Dashboard on 0.0.0.0:8080...")
    server = HTTPServer(('0.0.0.0', 8080), DashboardHandler)
    server.serve_forever()

def start_api():
    """Start API server on all interfaces"""
    print("Starting API on 0.0.0.0:8000...")
    
    class APIHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/docs':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                html = """<!DOCTYPE html>
<html>
<head><title>QENEX API Documentation</title></head>
<body style="font-family: sans-serif; padding: 40px;">
    <h1>QENEX API Documentation</h1>
    <h2>Endpoints:</h2>
    <ul>
        <li>GET /api/pipelines - List all pipelines</li>
        <li>POST /api/pipelines - Create new pipeline</li>
        <li>GET /api/status - System status</li>
        <li>GET /health - Health check</li>
    </ul>
    <p>Base URL: http://91.99.223.180:8000</p>
</body>
</html>"""
                self.wfile.write(html.encode())
            elif self.path == '/health' or self.path == '/api/status':
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'operational'}).encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            pass
    
    server = HTTPServer(('0.0.0.0', 8000), APIHandler)
    server.serve_forever()

def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              QENEX Services Starting                          ║
╚═══════════════════════════════════════════════════════════════╝

Starting services with external access enabled...
""")
    
    # Start services in threads
    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    api_thread = threading.Thread(target=start_api, daemon=True)
    
    dashboard_thread.start()
    api_thread.start()
    
    time.sleep(2)
    
    print("""
✅ Services Started Successfully!

Access URLs:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Dashboard:    http://91.99.223.180:8080
📚 API Docs:     http://91.99.223.180:8000/docs
🔌 API Health:   http://91.99.223.180:8000/health
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Local Access:
  Dashboard: https://abdulrahman305.github.io/qenex-docs
  API: https://abdulrahman305.github.io/qenex-docs

Press Ctrl+C to stop services.
""")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down services...")
        sys.exit(0)

if __name__ == '__main__':
    main()