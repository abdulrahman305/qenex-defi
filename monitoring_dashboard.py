#!/usr/bin/env python3
"""
QENEX OS Monitoring Dashboard
Real-time web dashboard for system monitoring
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import time
import sqlite3
import psutil
import threading
import os
from datetime import datetime, timedelta
import subprocess
from functools import lru_cache
from collections import deque
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'qenex-secret-key-2024'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global metrics storage with bounded size to prevent memory leaks
MAX_METRICS_SIZE = 1000
system_metrics = {
    "cpu_usage": deque(maxlen=MAX_METRICS_SIZE),
    "memory_usage": deque(maxlen=MAX_METRICS_SIZE),
    "disk_usage": deque(maxlen=MAX_METRICS_SIZE),
    "network_io": deque(maxlen=MAX_METRICS_SIZE),
    "mining_stats": {},
    "ai_performance": {},
    "blockchain_info": {},
    "wallet_balances": {},
    "active_processes": deque(maxlen=100)
}

# Thread pool for concurrent operations
executor = ThreadPoolExecutor(max_workers=4)

# Cache for expensive operations
class MetricsCache:
    def __init__(self, ttl=5):
        self.cache = {}
        self.ttl = ttl
        self.lock = threading.RLock()
    
    def get(self, key):
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                del self.cache[key]
        return None
    
    def set(self, key, value):
        with self.lock:
            self.cache[key] = (value, time.time())

metrics_cache = MetricsCache(ttl=5)

class MetricsCollector:
    """Collects system and QENEX metrics"""
    
    def __init__(self):
        self.running = True
        self.blockchain_db = "/opt/qenex-os/blockchain/qxc.db"
        self.wallet_db = "/opt/qenex-os/blockchain/wallets.db"
        self.model_path = "/opt/qenex-os/models/unified_model.json"
        
    @lru_cache(maxsize=128)
    def get_static_system_info(self):
        """Get static system information (cached)"""
        return {
            "boot_time": psutil.boot_time(),
            "cpu_count": psutil.cpu_count(),
            "total_memory": psutil.virtual_memory().total,
            "total_disk": psutil.disk_usage('/').total
        }
    
    def collect_system_metrics(self):
        """Collect system performance metrics with caching"""
        # Check cache first
        cached = metrics_cache.get('system_metrics')
        if cached:
            return cached
        
        # Use non-blocking interval for CPU percent
        metrics = {
            "timestamp": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),  # Reduced interval
            "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            "memory": {
                "total": psutil.virtual_memory().total,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "percent": psutil.disk_usage('/').percent
            },
            "network": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv,
                "packets_sent": psutil.net_io_counters().packets_sent,
                "packets_recv": psutil.net_io_counters().packets_recv
            },
            "processes": len(psutil.pids()),
            "boot_time": self.get_static_system_info()['boot_time']
        }
        
        # Cache the result
        metrics_cache.set('system_metrics', metrics)
        return metrics
    
    def collect_blockchain_metrics(self):
        """Collect blockchain and mining metrics with connection pooling"""
        # Check cache first
        cached = metrics_cache.get('blockchain_metrics')
        if cached:
            return cached
        
        metrics = {
            "blocks": 0,
            "total_supply": 0,
            "difficulty": "0000",
            "last_block_time": 0,
            "mining_rate": 0
        }
        
        if os.path.exists(self.blockchain_db):
            try:
                with sqlite3.connect(self.blockchain_db, timeout=5) as conn:
                    conn.row_factory = sqlite3.Row
                    # Enable WAL mode for better concurrency
                    conn.execute('PRAGMA journal_mode=WAL')
                    conn.execute('PRAGMA synchronous=NORMAL')
                    
                    # Use single query to get all stats
                    cursor = conn.execute("""
                        SELECT 
                            COUNT(*) as block_count,
                            MAX(timestamp) as last_time
                        FROM blocks
                    """)
                    row = cursor.fetchone()
                    if row:
                        metrics["blocks"] = row[0]
                        if row[1]:
                            metrics["last_block_time"] = row[1]
                            elapsed_hours = (time.time() - row[1]) / 3600
                            if elapsed_hours > 0:
                                metrics["mining_rate"] = metrics["blocks"] / elapsed_hours
            except Exception as e:
                # Log error but don't crash
                print(f"Error collecting blockchain metrics: {e}")
        
        # Cache the result
        metrics_cache.set('blockchain_metrics', metrics)
        return metrics
    
    def collect_ai_metrics(self):
        """Collect AI model performance metrics"""
        metrics = {
            "model_version": 1,
            "capabilities": {},
            "improvements": 0,
            "training_time": 0
        }
        
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'r') as f:
                    model = json.load(f)
                    metrics["model_version"] = model.get("version", 1)
                    metrics["capabilities"] = model.get("capabilities", {})
                    metrics["improvements"] = model.get("total_improvements", 0)
            except:
                pass
        
        return metrics
    
    def collect_wallet_metrics(self):
        """Collect wallet balance information"""
        wallets = {}
        
        if os.path.exists(self.wallet_db):
            try:
                with sqlite3.connect(self.wallet_db) as conn:
                    cursor = conn.execute("SELECT address FROM wallets")
                    for (address,) in cursor:
                        wallets[address] = {
                            "balance": 0,  # Would need blockchain scan for real balance
                            "transactions": 0
                        }
            except:
                pass
        
        return wallets
    
    def check_qenex_processes(self):
        """Check running QENEX processes"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'qenex' in cmdline.lower() or 'qxc' in cmdline.lower() or 'mining' in cmdline.lower():
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cmdline": cmdline[:100],
                        "cpu": proc.info['cpu_percent'],
                        "memory": proc.info['memory_percent']
                    })
            except:
                pass
        return processes
    
    def run(self):
        """Main collection loop"""
        while self.running:
            try:
                # Collect all metrics
                system_metrics["system"] = self.collect_system_metrics()
                system_metrics["blockchain_info"] = self.collect_blockchain_metrics()
                system_metrics["ai_performance"] = self.collect_ai_metrics()
                system_metrics["wallet_balances"] = self.collect_wallet_metrics()
                system_metrics["active_processes"] = self.check_qenex_processes()
                
                # Emit to connected clients
                socketio.emit('metrics_update', system_metrics)
                
                time.sleep(2)  # Update every 2 seconds
            except Exception as e:
                print(f"Metrics collection error: {e}")

# HTML Template
dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>QENEX OS Monitoring Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .card h2 {
            margin-bottom: 15px;
            font-size: 1.3em;
            color: #ffd700;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding: 8px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
        }
        .metric-value {
            font-weight: bold;
            color: #00ff88;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-green { background: #00ff88; }
        .status-yellow { background: #ffdd00; }
        .status-red { background: #ff4444; }
        .chart-container {
            position: relative;
            height: 200px;
            margin-top: 10px;
        }
        .process-list {
            max-height: 200px;
            overflow-y: auto;
            font-size: 0.9em;
        }
        .process-item {
            padding: 5px;
            margin-bottom: 5px;
            background: rgba(255,255,255,0.05);
            border-radius: 5px;
        }
        .mining-indicator {
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .button {
            background: linear-gradient(135deg, #00ff88 0%, #00cc66 100%);
            color: black;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            margin: 5px;
            transition: all 0.3s;
        }
        .button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,255,136,0.4);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 QENEX OS Monitoring Dashboard</h1>
        <p>Real-time System & Blockchain Monitoring</p>
    </div>
    
    <div class="dashboard">
        <!-- System Status -->
        <div class="card">
            <h2>⚡ System Status</h2>
            <div class="metric">
                <span>CPU Usage</span>
                <span class="metric-value" id="cpu-usage">0%</span>
            </div>
            <div class="metric">
                <span>Memory Usage</span>
                <span class="metric-value" id="memory-usage">0%</span>
            </div>
            <div class="metric">
                <span>Disk Usage</span>
                <span class="metric-value" id="disk-usage">0%</span>
            </div>
            <div class="metric">
                <span>Network I/O</span>
                <span class="metric-value" id="network-io">0 MB/s</span>
            </div>
            <div class="metric">
                <span>Processes</span>
                <span class="metric-value" id="process-count">0</span>
            </div>
        </div>
        
        <!-- Blockchain Info -->
        <div class="card">
            <h2>⛓️ Blockchain Status</h2>
            <div class="metric">
                <span>Block Height</span>
                <span class="metric-value" id="block-height">0</span>
            </div>
            <div class="metric">
                <span>Total Supply</span>
                <span class="metric-value" id="total-supply">0 QXC</span>
            </div>
            <div class="metric">
                <span>Difficulty</span>
                <span class="metric-value" id="difficulty">0000</span>
            </div>
            <div class="metric">
                <span>Mining Rate</span>
                <span class="metric-value mining-indicator" id="mining-rate">0 blocks/hr</span>
            </div>
            <div class="metric">
                <span>Last Block</span>
                <span class="metric-value" id="last-block">Never</span>
            </div>
        </div>
        
        <!-- AI Performance -->
        <div class="card">
            <h2>🧠 AI Performance</h2>
            <div class="metric">
                <span>Model Version</span>
                <span class="metric-value" id="model-version">v1</span>
            </div>
            <div class="metric">
                <span>Total Improvements</span>
                <span class="metric-value" id="improvements">0</span>
            </div>
            <div class="metric">
                <span>Mathematics</span>
                <span class="metric-value" id="math-score">50%</span>
            </div>
            <div class="metric">
                <span>Language</span>
                <span class="metric-value" id="lang-score">50%</span>
            </div>
            <div class="metric">
                <span>Code</span>
                <span class="metric-value" id="code-score">50%</span>
            </div>
        </div>
        
        <!-- Mining Statistics -->
        <div class="card">
            <h2>⛏️ Mining Statistics</h2>
            <canvas id="mining-chart"></canvas>
        </div>
        
        <!-- System Performance Chart -->
        <div class="card">
            <h2>📊 System Performance</h2>
            <canvas id="performance-chart"></canvas>
        </div>
        
        <!-- Active Processes -->
        <div class="card">
            <h2>🔧 QENEX Processes</h2>
            <div class="process-list" id="process-list">
                <div class="process-item">No processes detected</div>
            </div>
            <button class="button" onclick="restartSystem()">Restart Core</button>
            <button class="button" onclick="stopMining()">Stop Mining</button>
        </div>
    </div>
    
    <script>
        // Initialize Socket.IO connection
        const socket = io();
        
        // Charts
        let performanceChart, miningChart;
        
        // Chart data
        const performanceData = {
            labels: [],
            datasets: [{
                label: 'CPU %',
                data: [],
                borderColor: '#00ff88',
                tension: 0.4
            }, {
                label: 'Memory %',
                data: [],
                borderColor: '#ffdd00',
                tension: 0.4
            }]
        };
        
        const miningData = {
            labels: [],
            datasets: [{
                label: 'Blocks Mined',
                data: [],
                borderColor: '#ffd700',
                backgroundColor: 'rgba(255, 215, 0, 0.2)',
                tension: 0.4
            }]
        };
        
        // Initialize charts
        window.onload = function() {
            const perfCtx = document.getElementById('performance-chart').getContext('2d');
            performanceChart = new Chart(perfCtx, {
                type: 'line',
                data: performanceData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: 'white' } }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: { color: 'white' }
                        },
                        x: {
                            ticks: { color: 'white' }
                        }
                    }
                }
            });
            
            const miningCtx = document.getElementById('mining-chart').getContext('2d');
            miningChart = new Chart(miningCtx, {
                type: 'line',
                data: miningData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: 'white' } }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { color: 'white' }
                        },
                        x: {
                            ticks: { color: 'white' }
                        }
                    }
                }
            });
        };
        
        // Socket event handlers
        socket.on('metrics_update', function(data) {
            // Update system metrics
            if (data.system) {
                document.getElementById('cpu-usage').textContent = data.system.cpu_percent.toFixed(1) + '%';
                document.getElementById('memory-usage').textContent = data.system.memory.percent.toFixed(1) + '%';
                document.getElementById('disk-usage').textContent = data.system.disk.percent.toFixed(1) + '%';
                
                const mbSent = (data.system.network.bytes_sent / 1048576).toFixed(2);
                const mbRecv = (data.system.network.bytes_recv / 1048576).toFixed(2);
                document.getElementById('network-io').textContent = `↑${mbSent} ↓${mbRecv} MB`;
                
                document.getElementById('process-count').textContent = data.system.processes;
                
                // Update performance chart
                const now = new Date().toLocaleTimeString();
                if (performanceData.labels.length > 20) {
                    performanceData.labels.shift();
                    performanceData.datasets[0].data.shift();
                    performanceData.datasets[1].data.shift();
                }
                performanceData.labels.push(now);
                performanceData.datasets[0].data.push(data.system.cpu_percent);
                performanceData.datasets[1].data.push(data.system.memory.percent);
                performanceChart.update();
            }
            
            // Update blockchain info
            if (data.blockchain_info) {
                document.getElementById('block-height').textContent = data.blockchain_info.blocks;
                document.getElementById('total-supply').textContent = data.blockchain_info.total_supply.toFixed(0) + ' QXC';
                document.getElementById('difficulty').textContent = data.blockchain_info.difficulty;
                document.getElementById('mining-rate').textContent = data.blockchain_info.mining_rate.toFixed(2) + ' blocks/hr';
                
                if (data.blockchain_info.last_block_time > 0) {
                    const lastBlock = new Date(data.blockchain_info.last_block_time * 1000);
                    document.getElementById('last-block').textContent = lastBlock.toLocaleTimeString();
                }
                
                // Update mining chart
                if (miningData.labels.length > 20) {
                    miningData.labels.shift();
                    miningData.datasets[0].data.shift();
                }
                miningData.labels.push(new Date().toLocaleTimeString());
                miningData.datasets[0].data.push(data.blockchain_info.blocks);
                miningChart.update();
            }
            
            // Update AI metrics
            if (data.ai_performance) {
                document.getElementById('model-version').textContent = 'v' + data.ai_performance.model_version;
                document.getElementById('improvements').textContent = data.ai_performance.improvements;
                
                if (data.ai_performance.capabilities.mathematics) {
                    const mathAvg = Object.values(data.ai_performance.capabilities.mathematics).reduce((a,b) => a+b, 0) / 
                                   Object.values(data.ai_performance.capabilities.mathematics).length;
                    document.getElementById('math-score').textContent = (mathAvg * 100).toFixed(1) + '%';
                }
                if (data.ai_performance.capabilities.language) {
                    const langAvg = Object.values(data.ai_performance.capabilities.language).reduce((a,b) => a+b, 0) / 
                                   Object.values(data.ai_performance.capabilities.language).length;
                    document.getElementById('lang-score').textContent = (langAvg * 100).toFixed(1) + '%';
                }
                if (data.ai_performance.capabilities.code) {
                    const codeAvg = Object.values(data.ai_performance.capabilities.code).reduce((a,b) => a+b, 0) / 
                                   Object.values(data.ai_performance.capabilities.code).length;
                    document.getElementById('code-score').textContent = (codeAvg * 100).toFixed(1) + '%';
                }
            }
            
            // Update process list
            if (data.active_processes && data.active_processes.length > 0) {
                const processList = document.getElementById('process-list');
                processList.innerHTML = '';
                data.active_processes.forEach(proc => {
                    const div = document.createElement('div');
                    div.className = 'process-item';
                    div.innerHTML = `<span class="status-indicator status-green"></span>
                                    PID ${proc.pid}: ${proc.cmdline.substring(0, 50)}...
                                    <br>CPU: ${proc.cpu}% | Mem: ${proc.memory.toFixed(1)}%`;
                    processList.appendChild(div);
                });
            }
        });
        
        // Control functions
        function restartSystem() {
            if (confirm('Restart QENEX Core System?')) {
                fetch('/api/restart', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => alert(data.message));
            }
        }
        
        function stopMining() {
            if (confirm('Stop all mining processes?')) {
                fetch('/api/stop-mining', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => alert(data.message));
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the dashboard"""
    return dashboard_html

@app.route('/api/status')
def api_status():
    """API endpoint for system status"""
    return jsonify(system_metrics)

@app.route('/api/restart', methods=['POST'])
def restart_system():
    """Restart QENEX core system"""
    try:
        # SECURITY FIX: Use safe subprocess calls without shell=True
        # Stop old processes using specific PID management
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if any('qenex_core_integrated' in str(cmd) for cmd in proc.info['cmdline'] or []):
                    proc.terminate()
                    proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
        
        time.sleep(2)
        # Start new process safely
        subprocess.Popen(["python3", "/opt/qenex-os/qenex_core_integrated.py"], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify({"success": True, "message": "System restarted"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/stop-mining', methods=['POST'])
def stop_mining():
    """Stop all mining processes"""
    try:
        # SECURITY FIX: Safe process termination without shell=True
        import psutil
        mining_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline'] or []
                if any('mining' in str(cmd).lower() or 'qxc' in str(cmd).lower() for cmd in cmdline):
                    mining_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Terminate mining processes safely
        for proc in mining_processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                try:
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        
        return jsonify({"success": True, "message": f"Mining stopped ({len(mining_processes)} processes)"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

def run_dashboard():
    """Run the monitoring dashboard"""
    # Start metrics collector
    collector = MetricsCollector()
    collector_thread = threading.Thread(target=collector.run, daemon=True)
    collector_thread.start()
    
    print("\n" + "="*60)
    print("QENEX OS MONITORING DASHBOARD")
    print("="*60)
    print("\n📊 Dashboard available at: http://localhost:5000")
    print("📡 API endpoint: http://localhost:5000/api/status\n")
    
    # Run Flask app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    run_dashboard()