#!/usr/bin/env python3
"""
QENEX CI/CD Webhook Server
GitHub/GitLab webhook integration for automatic pipeline triggers
Version: 1.0.0
"""

import os
import sys
import json
import hmac
import hashlib
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('QENEX-Webhooks')

WEBHOOK_PORT = 8082
WEBHOOK_SECRETS = {}  # Repository -> secret mapping

class WebhookHandler(BaseHTTPRequestHandler):
    """Webhook request handler"""
    
    def do_POST(self):
        """Handle webhook POST requests"""
        path = urlparse(self.path).path
        
        if path == '/webhook/github':
            self.handle_github_webhook()
        elif path == '/webhook/gitlab':
            self.handle_gitlab_webhook()
        elif path == '/webhook/bitbucket':
            self.handle_bitbucket_webhook()
        elif path == '/webhook/generic':
            self.handle_generic_webhook()
        else:
            self.send_error(404)
    
    def handle_github_webhook(self):
        """Handle GitHub webhooks"""
        try:
            # Read payload
            content_length = int(self.headers['Content-Length'])
            payload = self.rfile.read(content_length)
            
            # Verify signature if secret is configured
            signature = self.headers.get('X-Hub-Signature-256')
            if signature:
                if not self.verify_github_signature(payload, signature):
                    self.send_error(401, "Invalid signature")
                    return
            
            # Parse payload
            data = json.loads(payload)
            event = self.headers.get('X-GitHub-Event', 'push')
            
            # Process based on event type
            if event == 'push':
                self.process_push_event(data, 'github')
            elif event == 'pull_request':
                self.process_pr_event(data, 'github')
            elif event == 'release':
                self.process_release_event(data, 'github')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'accepted'}).encode())
            
        except Exception as e:
            logger.error(f"GitHub webhook error: {e}")
            self.send_error(500)
    
    def handle_gitlab_webhook(self):
        """Handle GitLab webhooks"""
        try:
            # Read payload
            content_length = int(self.headers['Content-Length'])
            payload = self.rfile.read(content_length)
            
            # Verify token if configured
            token = self.headers.get('X-Gitlab-Token')
            # Add token verification logic here
            
            # Parse payload
            data = json.loads(payload)
            event = data.get('object_kind', 'push')
            
            # Process based on event type
            if event == 'push':
                self.process_push_event(data, 'gitlab')
            elif event == 'merge_request':
                self.process_mr_event(data, 'gitlab')
            elif event == 'tag_push':
                self.process_tag_event(data, 'gitlab')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'accepted'}).encode())
            
        except Exception as e:
            logger.error(f"GitLab webhook error: {e}")
            self.send_error(500)
    
    def handle_bitbucket_webhook(self):
        """Handle Bitbucket webhooks"""
        try:
            content_length = int(self.headers['Content-Length'])
            payload = self.rfile.read(content_length)
            data = json.loads(payload)
            
            # Process Bitbucket events
            event = self.headers.get('X-Event-Key', 'repo:push')
            
            if 'repo:push' in event:
                self.process_push_event(data, 'bitbucket')
            elif 'pullrequest' in event:
                self.process_pr_event(data, 'bitbucket')
            
            self.send_response(200)
            self.end_headers()
            
        except Exception as e:
            logger.error(f"Bitbucket webhook error: {e}")
            self.send_error(500)
    
    def handle_generic_webhook(self):
        """Handle generic webhooks"""
        try:
            content_length = int(self.headers['Content-Length'])
            payload = self.rfile.read(content_length)
            data = json.loads(payload)
            
            # Trigger pipeline with generic data
            self.trigger_pipeline({
                'name': data.get('project', 'generic'),
                'source': data.get('repository', ''),
                'branch': data.get('branch', 'main'),
                'commit': data.get('commit', ''),
                'author': data.get('author', 'webhook'),
                'message': data.get('message', 'Webhook trigger')
            })
            
            self.send_response(200)
            self.end_headers()
            
        except Exception as e:
            logger.error(f"Generic webhook error: {e}")
            self.send_error(500)
    
    def process_push_event(self, data, source):
        """Process push events"""
        if source == 'github':
            repo_name = data['repository']['name']
            repo_url = data['repository']['clone_url']
            branch = data['ref'].replace('refs/heads/', '')
            commit = data['head_commit']['id'][:7]
            author = data['head_commit']['author']['name']
            message = data['head_commit']['message']
        elif source == 'gitlab':
            repo_name = data['project']['name']
            repo_url = data['project']['git_http_url']
            branch = data['ref'].replace('refs/heads/', '')
            commit = data['checkout_sha'][:7]
            author = data['user_name']
            message = data['commits'][0]['message'] if data['commits'] else ''
        else:  # bitbucket
            repo_name = data['repository']['name']
            repo_url = data['repository']['links']['clone'][0]['href']
            branch = data['push']['changes'][0]['new']['name']
            commit = data['push']['changes'][0]['new']['target']['hash'][:7]
            author = data['actor']['display_name']
            message = data['push']['changes'][0]['new']['target']['message']
        
        logger.info(f"Push event: {repo_name} - {branch} - {commit}")
        
        # Trigger pipeline
        self.trigger_pipeline({
            'name': repo_name,
            'source': repo_url,
            'branch': branch,
            'commit': commit,
            'author': author,
            'message': message,
            'event': 'push'
        })
    
    def process_pr_event(self, data, source):
        """Process pull/merge request events"""
        if source == 'github':
            action = data['action']
            if action not in ['opened', 'synchronize', 'reopened']:
                return
            
            pr_number = data['pull_request']['number']
            pr_title = data['pull_request']['title']
            source_branch = data['pull_request']['head']['ref']
            target_branch = data['pull_request']['base']['ref']
            repo_url = data['repository']['clone_url']
        elif source == 'gitlab':
            action = data['object_attributes']['action']
            if action not in ['open', 'update', 'reopen']:
                return
            
            pr_number = data['object_attributes']['iid']
            pr_title = data['object_attributes']['title']
            source_branch = data['object_attributes']['source_branch']
            target_branch = data['object_attributes']['target_branch']
            repo_url = data['project']['git_http_url']
        else:
            return
        
        logger.info(f"PR event: #{pr_number} - {pr_title}")
        
        # Trigger PR pipeline
        self.trigger_pipeline({
            'name': f"PR-{pr_number}",
            'source': repo_url,
            'branch': source_branch,
            'target_branch': target_branch,
            'pr_number': pr_number,
            'pr_title': pr_title,
            'event': 'pull_request'
        })
    
    def process_release_event(self, data, source):
        """Process release events"""
        if source == 'github':
            tag = data['release']['tag_name']
            name = data['release']['name']
            repo_url = data['repository']['clone_url']
        else:
            return
        
        logger.info(f"Release event: {tag} - {name}")
        
        # Trigger release pipeline
        self.trigger_pipeline({
            'name': f"Release-{tag}",
            'source': repo_url,
            'branch': tag,
            'event': 'release',
            'release_name': name
        })
    
    def process_mr_event(self, data, source):
        """Process GitLab merge request events"""
        self.process_pr_event(data, source)
    
    def process_tag_event(self, data, source):
        """Process tag events"""
        tag = data['ref'].replace('refs/tags/', '')
        repo_url = data['project']['git_http_url']
        
        logger.info(f"Tag event: {tag}")
        
        self.trigger_pipeline({
            'name': f"Tag-{tag}",
            'source': repo_url,
            'branch': tag,
            'event': 'tag'
        })
    
    def trigger_pipeline(self, config):
        """Trigger a CI/CD pipeline"""
        try:
            sys.path.insert(0, '/opt/qenex-os')
            from cicd.autonomous_cicd import get_cicd_engine
            
            cicd = get_cicd_engine()
            
            # Add webhook-specific configuration
            config['triggered_by'] = 'webhook'
            config['triggered_at'] = datetime.now().isoformat()
            
            # Create pipeline
            pipeline = cicd.create_pipeline(config)
            
            logger.info(f"Pipeline triggered: {pipeline.id} - {pipeline.name}")
            
            # Send notification
            self.send_notification(pipeline)
            
        except Exception as e:
            logger.error(f"Failed to trigger pipeline: {e}")
    
    def send_notification(self, pipeline):
        """Send notifications about pipeline status"""
        # This would integrate with Slack, Discord, email, etc.
        logger.info(f"Notification would be sent for pipeline {pipeline.id}")
    
    def verify_github_signature(self, payload, signature):
        """Verify GitHub webhook signature"""
        # Get secret for this repository
        secret = WEBHOOK_SECRETS.get('github', b'default-secret')
        
        # Calculate expected signature
        expected = 'sha256=' + hmac.new(
            secret,
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(expected, signature)
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

class WebhookServer:
    """Webhook server manager"""
    
    def __init__(self):
        self.server = None
        self.running = False
    
    def start(self):
        """Start webhook server"""
        if self.running:
            logger.info("Webhook server already running")
            return
        
        self.running = True
        
        def run():
            with HTTPServer(("", WEBHOOK_PORT), WebhookHandler) as httpd:
                self.server = httpd
                logger.info(f"Webhook server running on port {WEBHOOK_PORT}")
                logger.info(f"GitHub webhook: http://your-server:{WEBHOOK_PORT}/webhook/github")
                logger.info(f"GitLab webhook: http://your-server:{WEBHOOK_PORT}/webhook/gitlab")
                httpd.serve_forever()
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop webhook server"""
        self.running = False
        if self.server:
            self.server.shutdown()
        logger.info("Webhook server stopped")
    
    def add_secret(self, repo, secret):
        """Add webhook secret for a repository"""
        WEBHOOK_SECRETS[repo] = secret.encode()
        logger.info(f"Added webhook secret for {repo}")

# Global webhook server
webhook_server = None

def get_webhook_server():
    """Get or create webhook server"""
    global webhook_server
    if webhook_server is None:
        webhook_server = WebhookServer()
    return webhook_server

if __name__ == '__main__':
    server = get_webhook_server()
    server.start()
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()