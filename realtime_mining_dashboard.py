#!/usr/bin/env python3
"""
QENEX Real-Time Mining Dashboard
Live visualization of mining rewards and AI improvements
"""

import json
import time
import asyncio
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('MiningDashboard')

# HTML Dashboard Template
dashboard_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QENEX Mining Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            animation: fadeIn 1s;
        }
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s;
            animation: slideIn 0.5s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            background: rgba(255,255,255,0.15);
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
            color: #ffd700;
        }
        .stat-label {
            font-size: 1em;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .chart-container {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            height: 400px;
        }
        .live-feed {
            background: rgba(0,0,0,0.3);
            border-radius: 15px;
            padding: 20px;
            max-height: 300px;
            overflow-y: auto;
        }
        .feed-item {
            padding: 10px;
            margin: 5px 0;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            animation: slideIn 0.3s;
        }
        .leaderboard {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
        }
        .leaderboard-item {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            margin: 5px 0;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
        }
        .rank-1 { background: linear-gradient(90deg, #ffd700, #ffed4e); color: #000; }
        .rank-2 { background: linear-gradient(90deg, #c0c0c0, #e8e8e8); color: #000; }
        .rank-3 { background: linear-gradient(90deg, #cd7f32, #e6ac7d); color: #000; }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideIn {
            from { transform: translateX(-20px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .mining-animation {
            display: inline-block;
            animation: rotate 2s linear infinite;
        }
        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ QENEX Mining Dashboard</h1>
            <p>Real-Time AI Mining & Rewards Tracking</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card pulse">
                <div class="stat-label">Your Balance</div>
                <div class="stat-value" id="balance">0.00 QXC</div>
                <div class="stat-label">💰 Total Earned</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Mining Rate</div>
                <div class="stat-value" id="mining-rate">0.00 QXC/h</div>
                <div class="stat-label">⛏️ Per Hour</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Network Hashrate</div>
                <div class="stat-value" id="hashrate">0.00 TH/s</div>
                <div class="stat-label">🔥 Total Power</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">AI Improvements</div>
                <div class="stat-value" id="improvements">0</div>
                <div class="stat-label">🤖 Models Enhanced</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Active Miners</div>
                <div class="stat-value" id="miners">0</div>
                <div class="stat-label">👥 Online Now</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Block Height</div>
                <div class="stat-value" id="block-height">0</div>
                <div class="stat-label">📦 Current Block</div>
            </div>
        </div>
        
        <div class="chart-container">
            <canvas id="miningChart"></canvas>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div class="live-feed">
                <h3>🔴 Live Mining Feed</h3>
                <div id="feed-content"></div>
            </div>
            
            <div class="leaderboard">
                <h3>🏆 Top Miners</h3>
                <div id="leaderboard-content"></div>
            </div>
        </div>
    </div>
    
    <script>
        // Initialize Socket.IO connection
        const socket = io();
        
        // Chart setup
        const ctx = document.getElementById('miningChart').getContext('2d');
        const miningChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'QXC Mined',
                    data: [],
                    borderColor: '#ffd700',
                    backgroundColor: 'rgba(255, 215, 0, 0.1)',
                    tension: 0.4
                }, {
                    label: 'AI Score',
                    data: [],
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: 'white' }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: 'white' },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    },
                    y: {
                        ticks: { color: 'white' },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    }
                }
            }
        });
        
        // Update functions
        function updateStats(data) {
            document.getElementById('balance').textContent = data.balance.toFixed(2) + ' QXC';
            document.getElementById('mining-rate').textContent = data.miningRate.toFixed(4) + ' QXC/h';
            document.getElementById('hashrate').textContent = data.hashrate.toFixed(2) + ' TH/s';
            document.getElementById('improvements').textContent = data.improvements;
            document.getElementById('miners').textContent = data.activeMiners;
            document.getElementById('block-height').textContent = data.blockHeight;
        }
        
        function addToFeed(message) {
            const feed = document.getElementById('feed-content');
            const item = document.createElement('div');
            item.className = 'feed-item';
            item.innerHTML = `<small>${new Date().toLocaleTimeString()}</small> ${message}`;
            feed.insertBefore(item, feed.firstChild);
            if (feed.children.length > 10) {
                feed.removeChild(feed.lastChild);
            }
        }
        
        function updateLeaderboard(data) {
            const leaderboard = document.getElementById('leaderboard-content');
            leaderboard.innerHTML = data.map((miner, index) => `
                <div class="leaderboard-item ${index < 3 ? 'rank-' + (index + 1) : ''}">
                    <span>${index + 1}. ${miner.address.slice(0, 10)}...</span>
                    <span>${miner.balance.toFixed(2)} QXC</span>
                </div>
            `).join('');
        }
        
        // Socket event handlers
        socket.on('stats_update', (data) => {
            updateStats(data);
            
            // Update chart
            const now = new Date().toLocaleTimeString();
            miningChart.data.labels.push(now);
            miningChart.data.datasets[0].data.push(data.balance);
            miningChart.data.datasets[1].data.push(data.aiScore);
            
            if (miningChart.data.labels.length > 20) {
                miningChart.data.labels.shift();
                miningChart.data.datasets[0].data.shift();
                miningChart.data.datasets[1].data.shift();
            }
            
            miningChart.update();
        });
        
        socket.on('mining_event', (data) => {
            addToFeed(data.message);
        });
        
        socket.on('leaderboard_update', (data) => {
            updateLeaderboard(data);
        });
        
        // Simulate initial data
        setTimeout(() => {
            updateStats({
                balance: 1525.30,
                miningRate: 2.45,
                hashrate: 125.67,
                improvements: 42,
                activeMiners: 7,
                blockHeight: 15234
            });
            
            addToFeed('⛏️ Mined 0.125 QXC - AI accuracy improved by 2.3%');
            addToFeed('🤖 Model optimization completed - Reward: 0.75 QXC');
            addToFeed('📈 New block mined! Height: 15234');
            
            updateLeaderboard([
                { address: 'qxc_unified_user_wallet_main', balance: 1525.30 },
                { address: 'qxc_model_optimizer_wallet', balance: 745.47 },
                { address: 'qxc_unified_qenex_system', balance: 428.14 }
            ]);
        }, 1000);
    </script>
</body>
</html>
'''

from aiohttp import web
import aiohttp_cors

class RealtimeMiningDashboard:
    def __init__(self):
        self.wallet_dir = Path('/opt/qenex-os/wallets')
        self.app = web.Application()
        self.setup_routes()
        self.mining_stats = {
            'balance': 0,
            'miningRate': 0,
            'hashrate': 0,
            'improvements': 0,
            'activeMiners': 0,
            'blockHeight': 0,
            'aiScore': 0
        }
        
    def setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/api/stats', self.get_stats)
        self.app.router.add_get('/api/leaderboard', self.get_leaderboard)
        self.app.router.add_get('/api/mining-history', self.get_mining_history)
        
        # Setup CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        for route in list(self.app.router.routes()):
            cors.add(route)
            
    async def index(self, request):
        """Serve dashboard HTML"""
        return web.Response(text=dashboard_html, content_type='text/html')
        
    async def get_stats(self, request):
        """Get current mining statistics"""
        # Read wallet balance
        user_wallet = self.wallet_dir / 'USER_WALLET.wallet'
        if user_wallet.exists():
            with open(user_wallet, 'r') as f:
                wallet_data = json.load(f)
                self.mining_stats['balance'] = wallet_data.get('balance', 0)
                
        # Simulate dynamic stats
        self.mining_stats['miningRate'] = random.uniform(1.5, 3.5)
        self.mining_stats['hashrate'] = random.uniform(100, 200)
        self.mining_stats['improvements'] = int(time.time() / 100) % 100
        self.mining_stats['activeMiners'] = random.randint(5, 15)
        self.mining_stats['blockHeight'] = int(time.time() / 15)
        self.mining_stats['aiScore'] = random.uniform(85, 98)
        
        return web.json_response(self.mining_stats)
        
    async def get_leaderboard(self, request):
        """Get top miners leaderboard"""
        leaderboard = []
        
        # Read all wallets
        for wallet_file in self.wallet_dir.glob("*.wallet"):
            try:
                with open(wallet_file, 'r') as f:
                    data = json.load(f)
                    if 'balance' in data and data['balance'] > 0:
                        leaderboard.append({
                            'address': data.get('address', wallet_file.stem),
                            'balance': data.get('balance', 0)
                        })
            except:
                pass
                
        # Sort by balance
        leaderboard.sort(key=lambda x: x['balance'], reverse=True)
        
        return web.json_response(leaderboard[:10])
        
    async def get_mining_history(self, request):
        """Get mining history"""
        history = []
        
        # Generate sample history
        for i in range(24):
            timestamp = datetime.now() - timedelta(hours=i)
            history.append({
                'timestamp': timestamp.isoformat(),
                'mined': random.uniform(50, 150),
                'aiScore': random.uniform(80, 95)
            })
            
        return web.json_response(history)
        
    async def start_server(self):
        """Start the dashboard server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        logger.info("Mining Dashboard running at http://localhost:8080")
        
async def main():
    dashboard = RealtimeMiningDashboard()
    await dashboard.start_server()
    
    # Keep server running
    while True:
        await asyncio.sleep(3600)
        
if __name__ == '__main__':
    print("Starting QENEX Mining Dashboard...")
    print("Access at: http://localhost:8080")
    asyncio.run(main())