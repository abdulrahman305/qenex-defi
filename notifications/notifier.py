#!/usr/bin/env python3
"""
QENEX Notification System - Email, Slack, Discord, Webhook notifications
"""

import smtplib
import json
import asyncio
import aiohttp
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.config = self.load_config()
        self.notification_history = []
        
    def load_config(self) -> Dict:
        """Load notification configuration"""
        config = {
            'email': {
                'enabled': os.environ.get('EMAIL_ENABLED', 'false').lower() == 'true',
                'smtp_host': os.environ.get('SMTP_HOST', 'smtp.gmail.com'),
                'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
                'smtp_user': os.environ.get('SMTP_USER', ''),
                'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
                'from_email': os.environ.get('FROM_EMAIL', 'qenex@localhost'),
                'to_emails': os.environ.get('TO_EMAILS', '').split(',')
            },
            'slack': {
                'enabled': os.environ.get('SLACK_ENABLED', 'false').lower() == 'true',
                'webhook_url': os.environ.get('SLACK_WEBHOOK_URL', ''),
                'channel': os.environ.get('SLACK_CHANNEL', '#qenex-alerts'),
                'username': os.environ.get('SLACK_USERNAME', 'QENEX Bot')
            },
            'discord': {
                'enabled': os.environ.get('DISCORD_ENABLED', 'false').lower() == 'true',
                'webhook_url': os.environ.get('DISCORD_WEBHOOK_URL', ''),
                'username': os.environ.get('DISCORD_USERNAME', 'QENEX Bot')
            },
            'webhook': {
                'enabled': os.environ.get('WEBHOOK_ENABLED', 'false').lower() == 'true',
                'url': os.environ.get('WEBHOOK_URL', ''),
                'headers': json.loads(os.environ.get('WEBHOOK_HEADERS', '{}'))
            },
            'telegram': {
                'enabled': os.environ.get('TELEGRAM_ENABLED', 'false').lower() == 'true',
                'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
                'chat_id': os.environ.get('TELEGRAM_CHAT_ID', '')
            }
        }
        return config
    
    async def send_notification(self, event_type: str, title: str, message: str, 
                               severity: str = 'info', data: Dict = None):
        """Send notification through all enabled channels"""
        notification = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'title': title,
            'message': message,
            'severity': severity,
            'data': data or {}
        }
        
        self.notification_history.append(notification)
        
        tasks = []
        
        if self.config['email']['enabled']:
            tasks.append(self.send_email(title, message, severity))
        
        if self.config['slack']['enabled']:
            tasks.append(self.send_slack(title, message, severity))
        
        if self.config['discord']['enabled']:
            tasks.append(self.send_discord(title, message, severity))
        
        if self.config['webhook']['enabled']:
            tasks.append(self.send_webhook(notification))
        
        if self.config['telegram']['enabled']:
            tasks.append(self.send_telegram(title, message, severity))
        
        # Send all notifications concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"Notification sent: {event_type} - {title}")
    
    async def send_email(self, subject: str, body: str, severity: str):
        """Send email notification"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[QENEX {severity.upper()}] {subject}"
            msg['From'] = self.config['email']['from_email']
            msg['To'] = ', '.join(self.config['email']['to_emails'])
            
            # Create HTML body
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px;">
                        <h2 style="color: {self.get_severity_color(severity)};">
                            🚀 QENEX Notification
                        </h2>
                        <h3>{subject}</h3>
                        <p style="font-size: 14px; color: #333;">
                            {body.replace(chr(10), '<br>')}
                        </p>
                        <hr style="border: 1px solid #ddd;">
                        <p style="font-size: 12px; color: #666;">
                            Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                            Severity: {severity.upper()}<br>
                            Server: 91.99.223.180
                        </p>
                    </div>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.config['email']['smtp_host'], 
                             self.config['email']['smtp_port']) as server:
                server.starttls()
                server.login(self.config['email']['smtp_user'], 
                           self.config['email']['smtp_password'])
                server.send_message(msg)
            
            logger.info(f"Email sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    async def send_slack(self, title: str, message: str, severity: str):
        """Send Slack notification"""
        try:
            color = self.get_severity_color(severity)
            
            payload = {
                'channel': self.config['slack']['channel'],
                'username': self.config['slack']['username'],
                'icon_emoji': ':rocket:',
                'attachments': [{
                    'color': color,
                    'title': title,
                    'text': message,
                    'fields': [
                        {
                            'title': 'Severity',
                            'value': severity.upper(),
                            'short': True
                        },
                        {
                            'title': 'Time',
                            'value': datetime.now().strftime('%H:%M:%S'),
                            'short': True
                        }
                    ],
                    'footer': 'QENEX Unified AI OS',
                    'ts': int(datetime.now().timestamp())
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.config['slack']['webhook_url'], 
                                       json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent: {title}")
                    else:
                        logger.error(f"Slack notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    async def send_discord(self, title: str, message: str, severity: str):
        """Send Discord notification"""
        try:
            color = int(self.get_severity_color(severity).replace('#', ''), 16)
            
            payload = {
                'username': self.config['discord']['username'],
                'avatar_url': 'https://example.com/qenex-logo.png',
                'embeds': [{
                    'title': f"🚀 {title}",
                    'description': message,
                    'color': color,
                    'fields': [
                        {
                            'name': 'Severity',
                            'value': severity.upper(),
                            'inline': True
                        },
                        {
                            'name': 'Server',
                            'value': '91.99.223.180',
                            'inline': True
                        }
                    ],
                    'footer': {
                        'text': 'QENEX Unified AI OS'
                    },
                    'timestamp': datetime.now().isoformat()
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.config['discord']['webhook_url'], 
                                       json=payload) as response:
                    if response.status in [200, 204]:
                        logger.info(f"Discord notification sent: {title}")
                    else:
                        logger.error(f"Discord notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
    
    async def send_telegram(self, title: str, message: str, severity: str):
        """Send Telegram notification"""
        try:
            emoji = self.get_severity_emoji(severity)
            
            text = f"{emoji} *{title}*\n\n{message}\n\n_Severity: {severity.upper()}_"
            
            url = f"https://api.telegram.org/bot{self.config['telegram']['bot_token']}/sendMessage"
            
            payload = {
                'chat_id': self.config['telegram']['chat_id'],
                'text': text,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Telegram notification sent: {title}")
                    else:
                        logger.error(f"Telegram notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
    
    async def send_webhook(self, notification: Dict):
        """Send generic webhook notification"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.config['webhook']['url'], 
                                       json=notification,
                                       headers=self.config['webhook']['headers']) as response:
                    if response.status in [200, 201, 204]:
                        logger.info(f"Webhook notification sent")
                    else:
                        logger.error(f"Webhook notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
    
    def get_severity_color(self, severity: str) -> str:
        """Get color based on severity"""
        colors = {
            'critical': '#FF0000',
            'error': '#FF6B6B',
            'warning': '#FFA500',
            'info': '#4A90E2',
            'success': '#00C851'
        }
        return colors.get(severity.lower(), '#808080')
    
    def get_severity_emoji(self, severity: str) -> str:
        """Get emoji based on severity"""
        emojis = {
            'critical': '🚨',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'success': '✅'
        }
        return emojis.get(severity.lower(), '📢')
    
    # Pipeline-specific notifications
    async def notify_pipeline_started(self, pipeline_id: str, repository: str, branch: str):
        """Notify when pipeline starts"""
        await self.send_notification(
            'pipeline_started',
            f'Pipeline Started: {pipeline_id}',
            f'Repository: {repository}\nBranch: {branch}\nStarted at: {datetime.now().strftime("%H:%M:%S")}',
            'info'
        )
    
    async def notify_pipeline_completed(self, pipeline_id: str, status: str, duration: float):
        """Notify when pipeline completes"""
        severity = 'success' if status == 'success' else 'error'
        await self.send_notification(
            'pipeline_completed',
            f'Pipeline {status.capitalize()}: {pipeline_id}',
            f'Duration: {duration:.2f} seconds\nStatus: {status}\nCompleted at: {datetime.now().strftime("%H:%M:%S")}',
            severity
        )
    
    async def notify_deployment(self, environment: str, version: str, status: str):
        """Notify about deployment"""
        severity = 'success' if status == 'success' else 'error'
        await self.send_notification(
            'deployment',
            f'Deployment to {environment}',
            f'Version: {version}\nEnvironment: {environment}\nStatus: {status}',
            severity
        )
    
    async def notify_alert(self, alert_type: str, message: str, severity: str = 'warning'):
        """Notify about system alerts"""
        await self.send_notification(
            'alert',
            f'System Alert: {alert_type}',
            message,
            severity
        )
    
    async def notify_error(self, error_type: str, error_message: str, stack_trace: str = None):
        """Notify about errors"""
        message = f'Error: {error_message}'
        if stack_trace:
            message += f'\n\nStack Trace:\n{stack_trace[:500]}...'
        
        await self.send_notification(
            'error',
            f'Error: {error_type}',
            message,
            'error'
        )

# Global notification manager instance
notifier = NotificationManager()

async def main():
    """Test notifications"""
    notifier = NotificationManager()
    
    # Test notification
    await notifier.send_notification(
        'test',
        'QENEX Notification System Test',
        'This is a test notification from QENEX Unified AI OS.\nAll systems operational.',
        'info'
    )
    
    print("Test notification sent!")

if __name__ == "__main__":
    asyncio.run(main())