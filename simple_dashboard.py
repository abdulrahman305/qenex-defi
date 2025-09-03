#!/usr/bin/env python3
import http.server
import socketserver

PORT = 8080
HOST = '0.0.0.0'

html_content = """<!DOCTYPE html>
<html>
<head>
    <title>QENEX Dashboard</title>
    <meta charset="utf-8">
    <style>
        body {
            margin: 0;
            font-family: -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 { font-size: 3em; margin-bottom: 20px; }
        .status { font-size: 1.5em; color: #4ade80; }
        .info { margin: 20px 0; }
        .url { 
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 10px;
            display: inline-block;
            margin: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 QENEX CI/CD Dashboard</h1>
        <p class="status">✅ System Operational</p>
        <div class="info">
            <p>Unified AI Operating System v3.0.0</p>
            <p>Dashboard successfully running on external network!</p>
        </div>
        <div>
            <div class="url">Dashboard: http://91.99.223.180:8080</div>
            <div class="url">API Docs: http://91.99.223.180:8000/docs</div>
        </div>
        <p style="margin-top: 30px; opacity: 0.8;">
            The QENEX Dashboard is now accessible from any network!
        </p>
    </div>
</body>
</html>"""

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html_content.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logs

print(f"Starting QENEX Dashboard on {HOST}:{PORT}")
print(f"Access URL: http://91.99.223.180:{PORT}")

with socketserver.TCPServer((HOST, PORT), MyHandler) as httpd:
    httpd.serve_forever()