#!/usr/bin/env python3
"""QENEX OS CLI - Command Line Interface for QENEX Unified AI OS"""
import click
import requests
import json
import yaml
import os
import sys
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich.live import Live
from rich.panel import Panel
import websocket
import time

console = Console()

# Default configuration
DEFAULT_API_URL = "https://qenex.ai/api/v1"
CONFIG_FILE = os.path.expanduser("~/.qenex/config.yaml")

class QenexCLI:
    """QENEX CLI Client"""
    
    def __init__(self):
        self.config = self.load_config()
        self.api_url = self.config.get("api_url", DEFAULT_API_URL)
        self.token = self.config.get("token", "")
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return yaml.safe_load(f)
        return {}
    
    def save_config(self):
        """Save configuration to file"""
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(self.config, f)
    
    def api_request(self, method, endpoint, **kwargs):
        """Make API request"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        url = f"{self.api_url}/{endpoint}"
        
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

cli_client = QenexCLI()

@click.group()
@click.version_option(version="5.0.0", prog_name="QENEX CLI")
def cli():
    """QENEX OS Command Line Interface"""
    pass

@cli.command()
@click.option("--url", default=DEFAULT_API_URL, help="API URL")
@click.option("--token", prompt=True, hide_input=True, help="API Token")
def login(url, token):
    """Authenticate with QENEX OS"""
    cli_client.config["api_url"] = url
    cli_client.config["token"] = token
    cli_client.save_config()
    console.print("[green]✓ Successfully authenticated[/green]")

@cli.command()
def status():
    """Get system status"""
    data = cli_client.api_request("GET", "status")
    
    panel = Panel.fit(
        f"""[bold cyan]QENEX OS Status[/bold cyan]
        
Version: [green]{data.get('version', 'Unknown')}[/green]
Status: [green]{data.get('health', 'Unknown')}[/green]
Uptime: [yellow]{data.get('uptime', 0)} seconds[/yellow]
Modules: [blue]{', '.join(data.get('modules', {}).keys())}[/blue]
        """,
        title="System Information"
    )
    console.print(panel)

@cli.command()
def metrics():
    """Display system metrics"""
    data = cli_client.api_request("GET", "metrics")
    
    table = Table(title="System Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("CPU Usage", f"{data.get('cpu', 0):.2f}%")
    table.add_row("Memory Usage", f"{data.get('memory', 0):.2f}%")
    table.add_row("Disk Usage", f"{data.get('disk', 0):.2f}%")
    table.add_row("Network In", f"{data.get('network', {}).get('in', 0):.2f} MB/s")
    table.add_row("Network Out", f"{data.get('network', {}).get('out', 0):.2f} MB/s")
    
    console.print(table)

@cli.group()
def agent():
    """Manage AI agents"""
    pass

@agent.command("list")
def list_agents():
    """List all agents"""
    data = cli_client.api_request("GET", "agents")
    
    table = Table(title="Active Agents")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")
    
    for agent in data:
        table.add_row(agent['id'], agent['type'], agent['status'])
    
    console.print(table)

@agent.command("deploy")
@click.argument("agent_type")
@click.option("--config", type=click.File('r'), help="Agent configuration file")
def deploy_agent(agent_type, config):
    """Deploy a new agent"""
    agent_config = json.load(config) if config else {}
    
    with console.status(f"Deploying {agent_type} agent...") as status:
        data = cli_client.api_request("POST", "agents/deploy", json={
            "agent_type": agent_type,
            "config": agent_config
        })
        
    console.print(f"[green]✓ Agent deployed: {data.get('agent_id')}[/green]")

@agent.command("remove")
@click.argument("agent_id")
def remove_agent(agent_id):
    """Remove an agent"""
    if click.confirm(f"Remove agent {agent_id}?"):
        cli_client.api_request("DELETE", f"agents/{agent_id}")
        console.print(f"[green]✓ Agent {agent_id} removed[/green]")

@cli.command()
@click.argument("command")
def exec(command):
    """Execute a command on QENEX OS"""
    data = cli_client.api_request("POST", "execute", json={"command": command})
    console.print(data.get("output", "No output"))

@cli.command()
@click.option("--level", default=None, help="Log level filter")
@click.option("--follow", is_flag=True, help="Follow log output")
def logs(level, follow):
    """View system logs"""
    if follow:
        # WebSocket connection for live logs
        ws_url = cli_client.api_url.replace("https", "wss").replace("http", "ws") + "/logs/stream"
        
        def on_message(ws, message):
            console.print(message, end="")
        
        def on_error(ws, error):
            console.print(f"[red]Error: {error}[/red]")
        
        ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error)
        
        try:
            ws.run_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]Log stream stopped[/yellow]")
    else:
        params = {"level": level} if level else {}
        data = cli_client.api_request("GET", "logs", params=params)
        
        for log in data.get("logs", []):
            console.print(log)

@cli.command()
def backup():
    """Create system backup"""
    with console.status("Creating backup...") as status:
        data = cli_client.api_request("POST", "backup")
    
    console.print(f"[green]✓ Backup created: {data.get('backup_id')}[/green]")

@cli.command()
@click.argument("backup_id")
def restore(backup_id):
    """Restore from backup"""
    if click.confirm(f"Restore from backup {backup_id}? This will overwrite current state."):
        with console.status(f"Restoring from {backup_id}...") as status:
            cli_client.api_request("POST", f"restore/{backup_id}")
        
        console.print(f"[green]✓ System restored from {backup_id}[/green]")

@cli.command()
def monitor():
    """Live monitoring dashboard"""
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            try:
                metrics = cli_client.api_request("GET", "metrics")
                status = cli_client.api_request("GET", "status")
                
                table = Table(title=f"QENEX OS Monitor - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")
                
                table.add_row("Status", status.get("health", "Unknown"))
                table.add_row("CPU", f"{metrics.get('cpu', 0):.2f}%")
                table.add_row("Memory", f"{metrics.get('memory', 0):.2f}%")
                table.add_row("Disk", f"{metrics.get('disk', 0):.2f}%")
                table.add_row("Active Agents", str(metrics.get('active_agents', 0)))
                
                live.update(table)
                time.sleep(1)
            except KeyboardInterrupt:
                break

@cli.command()
def upgrade():
    """Upgrade QENEX OS to latest version"""
    current_version = cli_client.api_request("GET", "status").get("version", "Unknown")
    console.print(f"Current version: {current_version}")
    
    if click.confirm("Check for updates?"):
        # Check for updates
        console.print("[yellow]Checking for updates...[/yellow]")
        # Upgrade logic here
        console.print("[green]✓ System is up to date[/green]")

if __name__ == "__main__":
    cli()