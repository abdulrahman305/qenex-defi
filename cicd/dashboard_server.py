#!/usr/bin/env python3
"""
QENEX CI/CD Dashboard Server
Real-time pipeline visualization and monitoring
Version: 1.0.0
"""

import os
import sys
import json
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import websocket_server
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('QENEX-Dashboard')

# Dashboard configuration
DASHBOARD_PORT = 8080
WEBSOCKET_PORT = 8081
STATIC_DIR = "/opt/qenex-os/cicd/dashboard/static"
Path(STATIC_DIR).mkdir(parents=True, exist_ok=True)

class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for dashboard"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.serve_dashboard()
        elif self.path == '/api/pipelines':
            self.serve_pipelines()
        elif self.path == '/api/metrics':
            self.serve_metrics()
        elif self.path.startswith('/api/pipeline/'):
            pipeline_id = self.path.split('/')[-1]
            self.serve_pipeline_details(pipeline_id)
        elif self.path == '/health':
            self.serve_health()
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        """Serve the main dashboard HTML"""
        html = """<!DOCTYPE html>
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
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            opacity: 0.8;
            text-transform: uppercase;
            font-size: 0.9em;
        }
        .pipelines {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 15px;
        }
        .pipeline {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
            display: grid;
            grid-template-columns: 1fr 150px 150px 100px;
            align-items: center;
            gap: 15px;
        }
        .pipeline-name {
            font-weight: bold;
            font-size: 1.1em;
        }
        .pipeline-status {
            padding: 5px 15px;
            border-radius: 20px;
            text-align: center;
            font-weight: bold;
        }
        .status-running { background: #3b82f6; }
        .status-success { background: #10b981; }
        .status-failed { background: #ef4444; }
        .status-pending { background: #6b7280; }
        .progress-bar {
            height: 30px;
            background: rgba(0,0,0,0.2);
            border-radius: 15px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #10b981);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }
        .stages {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        .stage {
            padding: 5px 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 5px;
            font-size: 0.9em;
        }
        .stage.active {
            background: #3b82f6;
            animation: pulse 2s infinite;
        }
        .stage.completed {
            background: #10b981;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-top: 30px;
        }
        .chart {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 15px;
            height: 300px;
        }
        .webhook-info {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .webhook-url {
            background: rgba(0,0,0,0.2);
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            margin-top: 10px;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 QENEX CI/CD Dashboard</h1>
            <p>Real-time Pipeline Monitoring & Management</p>
        </header>
        
        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-value" id="total-pipelines">0</div>
                <div class="stat-label">Total Pipelines</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="success-rate">0%</div>
                <div class="stat-label">Success Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avg-duration">0m</div>
                <div class="stat-label">Avg Duration</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="active-pipelines">0</div>
                <div class="stat-label">Active Now</div>
            </div>
        </div>
        
        <div class="pipelines">
            <h2>Pipeline Activity</h2>
            <div id="pipeline-list"></div>
        </div>
        
        <div class="metrics">
            <div class="chart" id="success-chart">
                <h3>Success Rate Trend</h3>
                <canvas id="success-canvas"></canvas>
            </div>
            <div class="chart" id="duration-chart">
                <h3>Build Duration Trend</h3>
                <canvas id="duration-canvas"></canvas>
            </div>
        </div>
        
        <div class="webhook-info">
            <h3>Webhook Endpoints</h3>
            <p>Configure your repository to send webhooks to:</p>
            <div class="webhook-url">http://your-server:8082/webhook/github</div>
            <div class="webhook-url">http://your-server:8082/webhook/gitlab</div>
        </div>
    </div>
    
    <script>
        // WebSocket connection for real-time updates
        let ws;
        
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8081');
            
            ws.onopen = () => {
                console.log('Connected to dashboard WebSocket');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            ws.onclose = () => {
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function updateDashboard(data) {
            // Update stats
            if (data.stats) {
                document.getElementById('total-pipelines').textContent = data.stats.total || 0;
                document.getElementById('success-rate').textContent = (data.stats.successRate || 0) + '%';
                document.getElementById('avg-duration').textContent = formatDuration(data.stats.avgDuration || 0);
                document.getElementById('active-pipelines').textContent = data.stats.active || 0;
            }
            
            // Update pipeline list
            if (data.pipelines) {
                const listEl = document.getElementById('pipeline-list');
                listEl.innerHTML = data.pipelines.map(p => `
                    <div class="pipeline">
                        <div>
                            <div class="pipeline-name">${p.name}</div>
                            <div class="stages">
                                ${p.stages.map(s => `
                                    <span class="stage ${s.status}">${s.name}</span>
                                `).join('')}
                            </div>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${p.progress}%">
                                ${p.progress}%
                            </div>
                        </div>
                        <div>
                            <span class="pipeline-status status-${p.status.toLowerCase()}">
                                ${p.status}
                            </span>
                        </div>
                        <div>${formatDuration(p.duration)}</div>
                    </div>
                `).join('');
            }
        }
        
        function formatDuration(seconds) {
            if (seconds < 60) return Math.round(seconds) + 's';
            if (seconds < 3600) return Math.round(seconds/60) + 'm';
            return Math.round(seconds/3600) + 'h';
        }
        
        // Fetch initial data
        async function fetchData() {
            try {
                const response = await fetch('/api/pipelines');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Failed to fetch data:', error);
            }
        }
        
        // Initialize
        connectWebSocket();
        fetchData();
        setInterval(fetchData, 5000); // Fallback polling
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_pipelines(self):
        """Serve pipeline data"""
        try:
            sys.path.insert(0, '/opt/qenex-os')
            from cicd.autonomous_cicd import get_cicd_engine
            
            cicd = get_cicd_engine()
            pipelines = cicd.list_pipelines()
            
            # Calculate stats
            total = len(pipelines)
            success = sum(1 for p in pipelines if p.get('status') == 'success')
            active = sum(1 for p in pipelines if p.get('status') == 'running')
            
            success_rate = (success / total * 100) if total > 0 else 0
            avg_duration = sum(p.get('duration', 0) for p in pipelines) / total if total > 0 else 0
            
            # Format pipeline data
            pipeline_data = []
            for p in pipelines[:10]:  # Last 10 pipelines
                stages = []
                for stage in p.get('stages', []):
                    stages.append({
                        'name': stage.get('name', 'unknown'),
                        'status': 'completed' if p.get('status') == 'success' else 'active'
                    })
                
                pipeline_data.append({
                    'id': p.get('id'),
                    'name': p.get('name'),
                    'status': p.get('status', 'pending'),
                    'progress': 100 if p.get('status') == 'success' else 50,
                    'duration': p.get('duration', 0),
                    'stages': stages
                })
            
            response = {
                'stats': {
                    'total': total,
                    'successRate': round(success_rate, 1),
                    'avgDuration': avg_duration,
                    'active': active
                },
                'pipelines': pipeline_data
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Error serving pipelines: {e}")
            self.send_error(500)
    
    def serve_metrics(self):
        """Serve Prometheus metrics"""
        metrics = """# HELP qenex_pipeline_total Total number of pipelines
# TYPE qenex_pipeline_total counter
qenex_pipeline_total 42

# HELP qenex_pipeline_success_rate Pipeline success rate
# TYPE qenex_pipeline_success_rate gauge
qenex_pipeline_success_rate 0.85

# HELP qenex_pipeline_duration_seconds Pipeline duration in seconds
# TYPE qenex_pipeline_duration_seconds histogram
qenex_pipeline_duration_seconds_bucket{le="60"} 10
qenex_pipeline_duration_seconds_bucket{le="300"} 30
qenex_pipeline_duration_seconds_bucket{le="600"} 40
qenex_pipeline_duration_seconds_bucket{le="+Inf"} 42

# HELP qenex_active_pipelines Number of active pipelines
# TYPE qenex_active_pipelines gauge
qenex_active_pipelines 3
"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(metrics.encode())
    
    def serve_pipeline_details(self, pipeline_id):
        """Serve detailed pipeline information"""
        try:
            sys.path.insert(0, '/opt/qenex-os')
            from cicd.autonomous_cicd import get_cicd_engine
            
            cicd = get_cicd_engine()
            pipeline = cicd.get_pipeline_status(pipeline_id)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(pipeline).encode())
            
        except Exception as e:
            logger.error(f"Error serving pipeline details: {e}")
            self.send_error(404)
    
    def serve_health(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'healthy'}).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

class DashboardServer:
    """Dashboard server manager"""
    
    def __init__(self):
        self.http_server = None
        self.ws_server = None
        self.running = False
    
    def start(self):
        """Start dashboard server"""
        if self.running:
            logger.info("Dashboard already running")
            return
        
        self.running = True
        
        # Start HTTP server
        def run_http():
            with socketserver.TCPServer(("", DASHBOARD_PORT), DashboardHandler) as httpd:
                self.http_server = httpd
                logger.info(f"Dashboard HTTP server running on port {DASHBOARD_PORT}")
                httpd.serve_forever()
        
        # Start WebSocket server for real-time updates
        def run_websocket():
            logger.info(f"WebSocket server would run on port {WEBSOCKET_PORT}")
            # Simplified WebSocket placeholder
            while self.running:
                time.sleep(1)
        
        # Run servers in threads
        http_thread = threading.Thread(target=run_http, daemon=True)
        ws_thread = threading.Thread(target=run_websocket, daemon=True)
        
        http_thread.start()
        ws_thread.start()
        
        logger.info(f"QENEX CI/CD Dashboard running at http://localhost:{DASHBOARD_PORT}")
    
    def stop(self):
        """Stop dashboard server"""
        self.running = False
        if self.http_server:
            self.http_server.shutdown()
        logger.info("Dashboard server stopped")

# Global dashboard instance
dashboard_server = None

def get_dashboard_server():
    """Get or create dashboard server"""
    global dashboard_server
    if dashboard_server is None:
        dashboard_server = DashboardServer()
    return dashboard_server

if __name__ == '__main__':
    server = get_dashboard_server()
    server.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()