#!/usr/bin/env python3
"""
QENEX CLI - Command-line management tool for QENEX Unified AI OS
"""

import click
import requests
import json
import os
import sys
import subprocess
from tabulate import tabulate
from datetime import datetime
import yaml

API_URL = os.environ.get('QENEX_API_URL', 'https://abdulrahman305.github.io/qenex-docs)
API_KEY = os.environ.get('QENEX_API_KEY', '')

@click.group()
@click.option('--api-url', default=API_URL, help='QENEX API URL')
@click.option('--api-key', default=API_KEY, help='API Key for authentication')
@click.pass_context
def cli(ctx, api_url, api_key):
    """QENEX Unified AI OS Management CLI"""
    ctx.ensure_object(dict)
    ctx.obj['API_URL'] = api_url
    ctx.obj['API_KEY'] = api_key

# Pipeline commands
@cli.group()
def pipeline():
    """Manage CI/CD pipelines"""
    pass

@pipeline.command('list')
@click.pass_context
def pipeline_list(ctx):
    """List all pipelines"""
    try:
        response = requests.get(f"{ctx.obj['API_URL']}/api/pipelines",
                               headers={'X-API-Key': ctx.obj['API_KEY']})
        pipelines = response.json()
        
        table = [[p['id'], p['name'], p['status'], p['created_at']] 
                 for p in pipelines]
        print(tabulate(table, headers=['ID', 'Name', 'Status', 'Created'], 
                      tablefmt='grid'))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@pipeline.command('trigger')
@click.argument('repository')
@click.option('--branch', default='main', help='Branch to build')
@click.pass_context
def pipeline_trigger(ctx, repository, branch):
    """Trigger a new pipeline"""
    try:
        data = {'repository': repository, 'branch': branch}
        response = requests.post(f"{ctx.obj['API_URL']}/api/pipelines/trigger",
                                json=data,
                                headers={'X-API-Key': ctx.obj['API_KEY']})
        result = response.json()
        click.echo(f"✅ Pipeline triggered: {result['pipeline_id']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@pipeline.command('status')
@click.argument('pipeline_id')
@click.pass_context
def pipeline_status(ctx, pipeline_id):
    """Get pipeline status"""
    try:
        response = requests.get(f"{ctx.obj['API_URL']}/api/pipelines/{pipeline_id}",
                               headers={'X-API-Key': ctx.obj['API_KEY']})
        pipeline = response.json()
        
        click.echo(f"Pipeline: {pipeline['id']}")
        click.echo(f"Status: {pipeline['status']}")
        click.echo(f"Repository: {pipeline['repository']}")
        click.echo(f"Branch: {pipeline['branch']}")
        
        if pipeline.get('stages'):
            click.echo("\nStages:")
            for stage in pipeline['stages']:
                symbol = '✅' if stage['status'] == 'success' else '⏳'
                click.echo(f"  {symbol} {stage['name']}: {stage['status']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

# System commands
@cli.group()
def system():
    """System management"""
    pass

@system.command('status')
@click.pass_context
def system_status(ctx):
    """Get system status"""
    try:
        # Read from local API JSON file as fallback
        with open('/opt/qenex-os/dashboard/api.json', 'r') as f:
            status = json.load(f)
        
        click.echo("🚀 QENEX System Status")
        click.echo(f"Uptime: {status['uptime_hours']}h")
        click.echo(f"Load: {status['load_average']}")
        click.echo(f"Memory: {status['memory_usage']}%")
        click.echo(f"Active Pipelines: {status['pipelines']}")
        click.echo(f"Success Rate: {status['success_rate']}%")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@system.command('health')
def system_health():
    """Check system health"""
    try:
        response = subprocess.run(['curl', '-s', 'http://localhost/api.json'],
                                capture_output=True, text=True)
        if response.returncode == 0:
            click.echo("✅ System is healthy")
        else:
            click.echo("❌ System health check failed", err=True)
    except Exception as e:
        click.echo(f"❌ Cannot check health: {e}", err=True)

# Version command
@cli.command()
def version():
    """Show QENEX version"""
    click.echo("QENEX Unified AI OS v3.0.0")
    click.echo("Build: 2024.01.20")
    click.echo("API Version: 1.0")

if __name__ == '__main__':
    cli(obj={})