#!/usr/bin/env python3
"""
QENEX Webhook Handler - GitHub/GitLab integration
"""

import json
import hmac
import hashlib
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from aiohttp import web
import aiohttp
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebhookHandler:
    def __init__(self, port=8001):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        self.db_path = "/opt/qenex-os/data/webhooks.db"
        self.init_database()
        
    def init_database(self):
        """Initialize webhook database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS webhooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                event_type TEXT,
                repository TEXT,
                branch TEXT,
                commit_sha TEXT,
                author TEXT,
                message TEXT,
                timestamp DATETIME,
                status TEXT,
                pipeline_id TEXT
            )
        ''')
        conn.commit()
        conn.close()
        
    def setup_routes(self):
        """Setup webhook routes"""
        self.app.router.add_post('/webhooks/github', self.handle_github)
        self.app.router.add_post('/webhooks/gitlab', self.handle_gitlab)
        self.app.router.add_post('/webhooks/bitbucket', self.handle_bitbucket)
        self.app.router.add_get('/webhooks/status', self.get_status)
        
    def verify_github_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify GitHub webhook signature"""
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)
    
    async def handle_github(self, request: web.Request) -> web.Response:
        """Handle GitHub webhooks"""
        try:
            payload = await request.read()
            data = json.loads(payload)
            
            # Verify signature if secret is configured
            signature = request.headers.get('X-Hub-Signature-256')
            secret = os.environ.get('GITHUB_WEBHOOK_SECRET')
            if secret and signature:
                if not self.verify_github_signature(payload, signature, secret):
                    return web.json_response({'error': 'Invalid signature'}, status=401)
            
            event_type = request.headers.get('X-GitHub-Event', 'unknown')
            
            # Process different event types
            if event_type == 'push':
                await self.handle_push_event(data, 'github')
            elif event_type == 'pull_request':
                await self.handle_pr_event(data, 'github')
            elif event_type == 'release':
                await self.handle_release_event(data, 'github')
                
            return web.json_response({'status': 'success', 'event': event_type})
            
        except Exception as e:
            logger.error(f"GitHub webhook error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def handle_gitlab(self, request: web.Request) -> web.Response:
        """Handle GitLab webhooks"""
        try:
            data = await request.json()
            event_type = request.headers.get('X-Gitlab-Event', 'unknown')
            
            # Verify token if configured
            token = request.headers.get('X-Gitlab-Token')
            expected_token = os.environ.get('GITLAB_WEBHOOK_TOKEN')
            if expected_token and token != expected_token:
                return web.json_response({'error': 'Invalid token'}, status=401)
            
            # Process events
            if event_type == 'Push Hook':
                await self.handle_push_event(data, 'gitlab')
            elif event_type == 'Merge Request Hook':
                await self.handle_pr_event(data, 'gitlab')
            elif event_type == 'Tag Push Hook':
                await self.handle_release_event(data, 'gitlab')
                
            return web.json_response({'status': 'success', 'event': event_type})
            
        except Exception as e:
            logger.error(f"GitLab webhook error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def handle_bitbucket(self, request: web.Request) -> web.Response:
        """Handle Bitbucket webhooks"""
        try:
            data = await request.json()
            event_type = request.headers.get('X-Event-Key', 'unknown')
            
            # Process events
            if 'push' in event_type:
                await self.handle_push_event(data, 'bitbucket')
            elif 'pullrequest' in event_type:
                await self.handle_pr_event(data, 'bitbucket')
                
            return web.json_response({'status': 'success', 'event': event_type})
            
        except Exception as e:
            logger.error(f"Bitbucket webhook error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def handle_push_event(self, data: Dict[str, Any], source: str):
        """Handle push events from any source"""
        # Extract common fields based on source
        if source == 'github':
            repo = data['repository']['full_name']
            branch = data['ref'].split('/')[-1]
            commit = data['head_commit']['id']
            author = data['head_commit']['author']['name']
            message = data['head_commit']['message']
        elif source == 'gitlab':
            repo = data['project']['path_with_namespace']
            branch = data['ref'].split('/')[-1]
            commit = data['commits'][0]['id'] if data['commits'] else ''
            author = data['commits'][0]['author']['name'] if data['commits'] else ''
            message = data['commits'][0]['message'] if data['commits'] else ''
        else:  # bitbucket
            repo = data['repository']['full_name']
            branch = data['push']['changes'][0]['new']['name']
            commit = data['push']['changes'][0]['new']['target']['hash']
            author = data['actor']['display_name']
            message = data['push']['changes'][0]['new']['target']['message']
        
        # Trigger CI/CD pipeline
        pipeline_id = await self.trigger_pipeline(repo, branch, commit)
        
        # Store in database
        self.store_webhook_event(
            source, 'push', repo, branch, commit, 
            author, message, 'triggered', pipeline_id
        )
        
        logger.info(f"Push event: {repo}#{branch} by {author}")
    
    async def handle_pr_event(self, data: Dict[str, Any], source: str):
        """Handle pull/merge request events"""
        if source == 'github':
            repo = data['repository']['full_name']
            pr_number = data['pull_request']['number']
            action = data['action']
            author = data['pull_request']['user']['login']
            title = data['pull_request']['title']
        elif source == 'gitlab':
            repo = data['project']['path_with_namespace']
            pr_number = data['merge_request']['iid']
            action = data['object_attributes']['action']
            author = data['user']['name']
            title = data['merge_request']['title']
        else:  # bitbucket
            repo = data['repository']['full_name']
            pr_number = data['pullrequest']['id']
            action = data['pullrequest']['state']
            author = data['actor']['display_name']
            title = data['pullrequest']['title']
        
        # Trigger PR validation pipeline
        if action in ['opened', 'synchronize', 'reopened']:
            pipeline_id = await self.trigger_pr_pipeline(repo, pr_number)
            logger.info(f"PR #{pr_number} {action} in {repo} by {author}")
    
    async def handle_release_event(self, data: Dict[str, Any], source: str):
        """Handle release/tag events"""
        if source == 'github':
            repo = data['repository']['full_name']
            tag = data['release']['tag_name']
            author = data['release']['author']['login']
        elif source == 'gitlab':
            repo = data['project']['path_with_namespace']
            tag = data['ref'].split('/')[-1]
            author = data['user_name']
        else:
            return
        
        # Trigger deployment pipeline
        pipeline_id = await self.trigger_deployment(repo, tag)
        logger.info(f"Release {tag} in {repo} by {author}")
    
    async def trigger_pipeline(self, repo: str, branch: str, commit: str) -> str:
        """Trigger CI/CD pipeline"""
        pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Call QENEX CI/CD API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'http://localhost:8000/api/pipelines/trigger',
                    json={
                        'repository': repo,
                        'branch': branch,
                        'commit': commit,
                        'pipeline_id': pipeline_id
                    }
                ) as response:
                    if response.status == 200:
                        logger.info(f"Pipeline {pipeline_id} triggered for {repo}#{branch}")
        except Exception as e:
            logger.error(f"Failed to trigger pipeline: {e}")
        
        return pipeline_id
    
    async def trigger_pr_pipeline(self, repo: str, pr_number: int) -> str:
        """Trigger PR validation pipeline"""
        pipeline_id = f"pr_{pr_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Trigger validation checks
        logger.info(f"PR validation {pipeline_id} triggered for {repo} PR#{pr_number}")
        return pipeline_id
    
    async def trigger_deployment(self, repo: str, tag: str) -> str:
        """Trigger deployment pipeline"""
        pipeline_id = f"deploy_{tag}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Trigger deployment
        logger.info(f"Deployment {pipeline_id} triggered for {repo} tag {tag}")
        return pipeline_id
    
    def store_webhook_event(self, source, event_type, repo, branch, commit, 
                           author, message, status, pipeline_id):
        """Store webhook event in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO webhooks 
            (source, event_type, repository, branch, commit_sha, author, 
             message, timestamp, status, pipeline_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (source, event_type, repo, branch, commit, author, 
              message, datetime.now(), status, pipeline_id))
        conn.commit()
        conn.close()
    
    async def get_status(self, request: web.Request) -> web.Response:
        """Get webhook handler status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get recent webhooks
        cursor.execute('''
            SELECT source, event_type, repository, timestamp, status
            FROM webhooks
            ORDER BY timestamp DESC
            LIMIT 10
        ''')
        recent = cursor.fetchall()
        
        # Get statistics
        cursor.execute('SELECT COUNT(*) FROM webhooks')
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM webhooks WHERE status='triggered'")
        triggered = cursor.fetchone()[0]
        
        conn.close()
        
        return web.json_response({
            'status': 'running',
            'total_webhooks': total,
            'triggered_pipelines': triggered,
            'recent_events': [
                {
                    'source': r[0],
                    'type': r[1],
                    'repo': r[2],
                    'time': r[3],
                    'status': r[4]
                } for r in recent
            ]
        })
    
    async def start(self):
        """Start webhook server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Webhook handler listening on port {self.port}")
        
        # Keep running
        while True:
            await asyncio.sleep(3600)

import os

async def main():
    handler = WebhookHandler(port=8001)
    await handler.start()

if __name__ == "__main__":
    asyncio.run(main())