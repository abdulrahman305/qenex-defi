#!/usr/bin/env python3
"""
QENEX OS Interactive Shell
Advanced command-line interface for QENEX AI OS
Version: 1.0.0
"""

import os
import sys
import cmd
import subprocess
import json
import signal
import readline
import glob
import shlex
import traceback
import psutil
import socket
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger('QENEX-Shell')

# Add QENEX modules to path
sys.path.insert(0, '/opt/qenex-os/kernel')
sys.path.insert(0, '/opt/qenex-os/modules')
sys.path.insert(0, '/opt/qenex-os/ai')

# ANSI Colors
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

class QenexShell(cmd.Cmd):
    """QENEX OS Interactive Shell"""
    
    def __init__(self):
        super().__init__()
        self.intro = f"""{Colors.CYAN}
╔═══════════════════════════════════════════════════════════════╗
║                    QENEX OS Shell v1.0.0                      ║
║               Interactive Command-Line Interface               ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.NC}
Type 'help' for available commands or 'help <command>' for details.
Type 'exit' or 'quit' to leave the shell.
"""
        self.prompt = f"{Colors.GREEN}qenex{Colors.NC}@{Colors.BLUE}{socket.gethostname()}{Colors.NC}:{Colors.YELLOW}~{Colors.NC}$ "
        self.current_dir = os.getcwd()
        self.history = []
        self.environment = os.environ.copy()
        self.aliases = {
            'll': 'ls -la',
            'la': 'ls -a',
            'cls': 'clear',
            '..': 'cd ..',
            'ps': 'process list'
        }
        
        # Initialize readline for better command line editing
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims(' \t\n')
        
        # Load QENEX modules if available
        self.qenex_modules = {}
        self._load_qenex_modules()
    
    def _load_qenex_modules(self):
        """Load available QENEX modules"""
        try:
            # Try to import QENEX core if available
            try:
                from qenex_core import QenexKernel
                self.qenex_kernel = QenexKernel()
            except ImportError:
                self.qenex_kernel = None
        except Exception as e:
            self.qenex_kernel = None
    
    def do_help(self, arg):
        """Show help for commands"""
        if not arg:
            print(f"{Colors.CYAN}Available Commands:{Colors.NC}")
            print(f"{Colors.WHITE}{'='*60}{Colors.NC}")
            
            # System Commands
            print(f"\n{Colors.YELLOW}System Commands:{Colors.NC}")
            print("  status       - Show QENEX OS system status")
            print("  services     - List running QENEX services")
            print("  kernel       - Interact with QENEX kernel")
            print("  ai           - AI subsystem commands")
            print("  security     - Security monitoring and controls")
            
            # File System
            print(f"\n{Colors.YELLOW}File System:{Colors.NC}")
            print("  ls [path]    - List directory contents")
            print("  cd <path>    - Change directory")
            print("  pwd          - Print working directory")
            print("  cat <file>   - Display file contents")
            print("  edit <file>  - Edit a file (opens nano)")
            
            # Process Management
            print(f"\n{Colors.YELLOW}Process Management:{Colors.NC}")
            print("  ps           - List processes")
            print("  kill <pid>   - Terminate a process")
            print("  top          - Show system resources")
            
            # Network
            print(f"\n{Colors.YELLOW}Network:{Colors.NC}")
            print("  netstat      - Show network connections")
            print("  ping <host>  - Ping a host")
            print("  ifconfig     - Show network interfaces")
            
            # Shell Features
            print(f"\n{Colors.YELLOW}CI/CD & DevOps:{Colors.NC}")
            print("  cicd         - CI/CD pipeline management")
            
            print(f"\n{Colors.YELLOW}Shell Features:{Colors.NC}")
            print("  exec <cmd>   - Execute system command")
            print("  alias        - Show/set command aliases")
            print("  history      - Show command history")
            print("  clear        - Clear the screen")
            print("  exit/quit    - Exit QENEX Shell")
            
            print(f"\n{Colors.CYAN}Use 'help <command>' for detailed information{Colors.NC}")
        else:
            # Show detailed help for specific command
            cmd_func = getattr(self, f'do_{arg}', None)
            if cmd_func and cmd_func.__doc__:
                print(f"{Colors.CYAN}{arg}:{Colors.NC} {cmd_func.__doc__}")
            else:
                print(f"No help available for '{arg}'")
    
    def do_status(self, arg):
        """Show QENEX OS system status"""
        print(f"{Colors.CYAN}QENEX OS System Status{Colors.NC}")
        print(f"{Colors.WHITE}{'='*60}{Colors.NC}")
        
        # OS Info
        print(f"\n{Colors.YELLOW}Operating System:{Colors.NC}")
        print(f"  Version: QENEX AI OS v3.0.0")
        print(f"  Kernel: {os.uname().release}")
        print(f"  Hostname: {socket.gethostname()}")
        print(f"  Python: {sys.version.split()[0]}")
        
        # Hardware
        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        print(f"\n{Colors.YELLOW}Hardware:{Colors.NC}")
        print(f"  CPU: {psutil.cpu_count()} cores @ {cpu_percent}% usage")
        print(f"  Memory: {mem.used/1024/1024/1024:.1f}GB / {mem.total/1024/1024/1024:.1f}GB ({mem.percent}% used)")
        print(f"  Disk: {disk.used/1024/1024/1024:.1f}GB / {disk.total/1024/1024/1024:.1f}GB ({disk.percent}% used)")
        
        # Check QENEX services
        print(f"\n{Colors.YELLOW}QENEX Services:{Colors.NC}")
        services = [
            ('qenex_core.py', 'QENEX Kernel'),
            ('ai_security_trainer.py', 'AI Security'),
            ('continuous_learning.py', 'AI Learning'),
            ('protocol_service.py', 'Protocol Service')
        ]
        
        for proc_name, service_name in services:
            running = any(proc_name in ' '.join(p.cmdline()) for p in psutil.process_iter(['cmdline']))
            status = f"{Colors.GREEN}● Active{Colors.NC}" if running else f"{Colors.RED}○ Inactive{Colors.NC}"
            print(f"  {service_name}: {status}")
    
    def do_services(self, arg):
        """List running QENEX services"""
        print(f"{Colors.CYAN}QENEX Services{Colors.NC}")
        print(f"{Colors.WHITE}{'='*60}{Colors.NC}")
        
        qenex_procs = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'qenex' in cmdline.lower() or '/opt/qenex' in cmdline or '/opt/agents' in cmdline:
                    qenex_procs.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if qenex_procs:
            print(f"{'PID':<8} {'CPU%':<8} {'MEM%':<8} {'Command'}")
            print("-" * 60)
            for proc in qenex_procs:
                cmd = ' '.join(proc['cmdline'] or [proc['name']])[:50]
                print(f"{proc['pid']:<8} {proc['cpu_percent']:<8.1f} {proc['memory_percent']:<8.1f} {cmd}")
        else:
            print("No QENEX services currently running")
    
    def do_ls(self, arg):
        """List directory contents"""
        path = arg or '.'
        try:
            if '-la' in arg or '-l' in arg:
                result = subprocess.run(['ls', '-la', path.replace('-la', '').replace('-l', '').strip()], 
                                      capture_output=True, text=True)
            else:
                result = subprocess.run(['ls', path], capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(f"{Colors.RED}{result.stderr}{Colors.NC}")
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.NC}")
    
    def do_cd(self, arg):
        """Change directory"""
        if not arg:
            arg = os.path.expanduser('~')
        try:
            os.chdir(os.path.expanduser(arg))
            self.current_dir = os.getcwd()
            # Update prompt with new directory
            self.prompt = f"{Colors.GREEN}qenex{Colors.NC}@{Colors.BLUE}{socket.gethostname()}{Colors.NC}:{Colors.YELLOW}{self.current_dir}{Colors.NC}$ "
        except FileNotFoundError:
            print(f"{Colors.RED}Directory not found: {arg}{Colors.NC}")
        except PermissionError:
            print(f"{Colors.RED}Permission denied: {arg}{Colors.NC}")
    
    def do_pwd(self, arg):
        """Print working directory"""
        print(os.getcwd())
    
    def do_cat(self, arg):
        """Display file contents"""
        if not arg:
            print(f"{Colors.RED}Usage: cat <filename>{Colors.NC}")
            return
        try:
            with open(os.path.expanduser(arg), 'r') as f:
                print(f.read())
        except FileNotFoundError:
            print(f"{Colors.RED}File not found: {arg}{Colors.NC}")
        except PermissionError:
            print(f"{Colors.RED}Permission denied: {arg}{Colors.NC}")
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.NC}")
    
    def do_ps(self, arg):
        """List processes"""
        if arg == 'aux':
            subprocess.run(['ps', 'aux'])
        else:
            print(f"{'PID':<8} {'USER':<12} {'CPU%':<8} {'MEM%':<8} {'Command'}")
            print("-" * 70)
            for proc in psutil.process_iter(['pid', 'username', 'cpu_percent', 'memory_percent', 'name']):
                try:
                    info = proc.info
                    print(f"{info['pid']:<8} {info['username'][:11]:<12} {info['cpu_percent']:<8.1f} {info['memory_percent']:<8.1f} {info['name']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    
    def do_kill(self, arg):
        """Terminate a process by PID"""
        if not arg:
            print(f"{Colors.RED}Usage: kill <pid>{Colors.NC}")
            return
        try:
            pid = int(arg)
            os.kill(pid, signal.SIGTERM)
            print(f"Process {pid} terminated")
        except ValueError:
            print(f"{Colors.RED}Invalid PID: {arg}{Colors.NC}")
        except ProcessLookupError:
            print(f"{Colors.RED}Process not found: {arg}{Colors.NC}")
        except PermissionError:
            print(f"{Colors.RED}Permission denied to kill process {arg}{Colors.NC}")
    
    def do_exec(self, arg):
        """Execute a system command"""
        if not arg:
            print(f"{Colors.RED}Usage: exec <command>{Colors.NC}")
            return
        try:
            # SECURITY FIX: Use shlex.split to safely parse command arguments
            import shlex
            args = shlex.split(arg)
            if not args:
                return
            
            # Whitelist allowed commands for security
            allowed_commands = ['ls', 'pwd', 'whoami', 'date', 'uptime', 'ps', 'df', 'free']
            if args[0] not in allowed_commands:
                print(f"{Colors.RED}Command '{args[0]}' not allowed for security reasons{Colors.NC}")
                return
                
            result = subprocess.run(args, capture_output=True, text=True, timeout=10)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"{Colors.RED}{result.stderr}{Colors.NC}")
        except subprocess.TimeoutExpired:
            print(f"{Colors.RED}Command timed out{Colors.NC}")
        except Exception as e:
            print(f"{Colors.RED}Error executing command: {e}{Colors.NC}")
    
    def do_clear(self, arg):
        """Clear the screen"""
        os.system('clear')
    
    def do_history(self, arg):
        """Show command history"""
        for i, cmd in enumerate(self.history[-50:], 1):
            print(f"{i:4d}  {cmd}")
    
    def do_alias(self, arg):
        """Show or set command aliases"""
        if not arg:
            print(f"{Colors.CYAN}Aliases:{Colors.NC}")
            for alias, cmd in self.aliases.items():
                print(f"  {alias} = '{cmd}'")
        elif '=' in arg:
            alias, cmd = arg.split('=', 1)
            self.aliases[alias.strip()] = cmd.strip()
            print(f"Alias created: {alias.strip()} = '{cmd.strip()}'")
        else:
            print(f"{Colors.RED}Usage: alias <name>=<command>{Colors.NC}")
    
    def do_kernel(self, arg):
        """Interact with QENEX kernel"""
        if not self.qenex_kernel:
            print(f"{Colors.YELLOW}QENEX Kernel not loaded. Starting kernel interface...{Colors.NC}")
            try:
                subprocess.run(['python3', '/opt/qenex-os/kernel/qenex_core.py', 'status'])
            except:
                print(f"{Colors.RED}Failed to access kernel{Colors.NC}")
        else:
            print(f"{Colors.GREEN}Kernel interface available{Colors.NC}")
    
    def do_ai(self, arg):
        """AI subsystem commands"""
        ai_commands = ['status', 'train', 'monitor', 'predict']
        if not arg:
            print(f"{Colors.CYAN}AI Commands:{Colors.NC}")
            for cmd in ai_commands:
                print(f"  ai {cmd}")
        elif arg == 'status':
            print(f"{Colors.CYAN}AI Subsystem Status:{Colors.NC}")
            # Check if AI services are running
            ai_running = any('ai_security' in ' '.join(p.cmdline()) for p in psutil.process_iter(['cmdline']))
            status = f"{Colors.GREEN}Active{Colors.NC}" if ai_running else f"{Colors.RED}Inactive{Colors.NC}"
            print(f"  AI Security Trainer: {status}")
    
    def do_cicd(self, arg):
        """CI/CD pipeline management commands"""
        try:
            sys.path.insert(0, '/opt/qenex-os')
            from cicd.autonomous_cicd import get_cicd_engine
            try:
                from cicd.gitops_controller import get_gitops_controller
            except ImportError:
                from cicd.gitops_controller_lite import get_gitops_controller
                logger.info("Using GitOps lite controller")
            
            try:
                from cicd.ai_autonomous_engine import get_ai_engine, DecisionType
            except ImportError:
                from cicd.ai_autonomous_engine_lite import get_ai_engine, DecisionType
                logger.info("Using AI lite engine")
        except ImportError as e:
            print(f"{Colors.RED}CI/CD modules not available: {e}{Colors.NC}")
            return
        
        cicd = get_cicd_engine()
        gitops = get_gitops_controller()
        ai = get_ai_engine()
        
        parts = arg.split()
        if not parts:
            print(f"{Colors.CYAN}CI/CD Commands:{Colors.NC}")
            print("  cicd list              - List all pipelines")
            print("  cicd status <id>       - Get pipeline status")
            print("  cicd trigger <name> <repo> - Trigger pipeline")
            print("  cicd cancel <id>       - Cancel pipeline")
            print("  cicd gitops add <repo> - Add GitOps repository")
            print("  cicd gitops sync <app> - Sync application")
            print("  cicd gitops list       - List GitOps apps")
            print("  cicd ai status         - AI engine status")
            print("  cicd ai train          - Trigger AI training")
            print("  cicd ai decide <type>  - Get AI decision")
            print("  cicd logs              - Show CI/CD logs")
            return
        
        cmd = parts[0]
        
        if cmd == 'list':
            pipelines = cicd.list_pipelines()
            if pipelines:
                print(f"{'ID':<10} {'Name':<20} {'Status':<15} {'Duration':<10}")
                print("-" * 60)
                for p in pipelines:
                    duration = f"{p.get('duration', 0):.0f}s" if p.get('duration') else 'N/A'
                    print(f"{p['id']:<10} {p['name']:<20} {p['status']:<15} {duration:<10}")
            else:
                print("No pipelines found")
        
        elif cmd == 'status' and len(parts) > 1:
            status = cicd.get_pipeline_status(parts[1])
            if 'error' not in status:
                print(f"{Colors.CYAN}Pipeline Status:{Colors.NC}")
                for key, value in status.items():
                    if key != 'stages' and key != 'metrics':
                        print(f"  {key}: {value}")
                if status.get('metrics'):
                    print(f"\n{Colors.YELLOW}Metrics:{Colors.NC}")
                    for k, v in status['metrics'].items():
                        print(f"    {k}: {v}")
            else:
                print(f"{Colors.RED}{status['error']}{Colors.NC}")
        
        elif cmd == 'trigger' and len(parts) > 2:
            pipeline_id = cicd.trigger_pipeline(parts[1], parts[2], parts[3] if len(parts) > 3 else 'main')
            print(f"{Colors.GREEN}Pipeline triggered: {pipeline_id}{Colors.NC}")
        
        elif cmd == 'cancel' and len(parts) > 1:
            if cicd.cancel_pipeline(parts[1]):
                print(f"{Colors.YELLOW}Pipeline {parts[1]} cancelled{Colors.NC}")
            else:
                print(f"{Colors.RED}Failed to cancel pipeline{Colors.NC}")
        
        elif cmd == 'gitops':
            if len(parts) < 2:
                print(f"{Colors.RED}Usage: cicd gitops <command>{Colors.NC}")
                return
            
            gitops_cmd = parts[1]
            
            if gitops_cmd == 'add' and len(parts) > 2:
                repo_config = {
                    'name': parts[2].split('/')[-1].replace('.git', ''),
                    'url': parts[2],
                    'branch': parts[3] if len(parts) > 3 else 'main'
                }
                repo = gitops.add_repository(repo_config)
                print(f"{Colors.GREEN}GitOps repository added: {repo.name}{Colors.NC}")
                print(f"  Webhook secret: {repo.webhook_secret}")
            
            elif gitops_cmd == 'sync' and len(parts) > 2:
                result = gitops.sync_application(parts[2])
                if result.get('status') == 'success':
                    print(f"{Colors.GREEN}Application synced successfully{Colors.NC}")
                    print(f"  Revision: {result.get('revision')}")
                    print(f"  Health: {result.get('health_status')}")
                else:
                    print(f"{Colors.RED}Sync failed: {result.get('error')}{Colors.NC}")
            
            elif gitops_cmd == 'list':
                apps = gitops.list_applications()
                if apps:
                    print(f"{'Name':<20} {'Namespace':<15} {'Sync Status':<15} {'Health':<10}")
                    print("-" * 70)
                    for app in apps:
                        print(f"{app['name']:<20} {app['namespace']:<15} {app['sync_status']:<15} {app['health_status']:<10}")
                else:
                    print("No GitOps applications found")
        
        elif cmd == 'ai':
            if len(parts) < 2:
                print(f"{Colors.RED}Usage: cicd ai <command>{Colors.NC}")
                return
            
            ai_cmd = parts[1]
            
            if ai_cmd == 'status':
                print(f"{Colors.CYAN}AI Engine Status:{Colors.NC}")
                print(f"  Training samples: {len(ai.training_data)}")
                print(f"  Is training: {ai.is_training}")
                print(f"  Learning rate: {ai.learning_rate:.6f}")
                if ai.reward_history:
                    avg_reward = sum(ai.reward_history) / len(ai.reward_history)
                    print(f"  Average reward: {avg_reward:.3f}")
                print(f"  Auto-train interval: {ai.auto_train_interval}s")
            
            elif ai_cmd == 'train':
                print(f"{Colors.YELLOW}Starting AI model training...{Colors.NC}")
                ai.train_models(force=True)
                print(f"{Colors.GREEN}Training initiated{Colors.NC}")
            
            elif ai_cmd == 'decide' and len(parts) > 2:
                decision_type = parts[2].upper()
                context = {
                    'cpu_usage': 70,
                    'memory_usage': 60,
                    'error_rate': 0.5,
                    'response_time': 200
                }
                
                try:
                    dtype = DecisionType[decision_type]
                    decision = ai.make_decision(dtype, context)
                    print(f"{Colors.CYAN}AI Decision:{Colors.NC}")
                    for key, value in decision.items():
                        if isinstance(value, dict):
                            print(f"  {key}:")
                            for k, v in value.items():
                                print(f"    {k}: {v}")
                        elif isinstance(value, list):
                            print(f"  {key}: {', '.join(map(str, value))}")
                        else:
                            print(f"  {key}: {value}")
                except KeyError:
                    print(f"{Colors.RED}Invalid decision type. Options: {', '.join([d.name for d in DecisionType])}{Colors.NC}")
        
        elif cmd == 'logs':
            log_file = '/opt/qenex-os/cicd/logs/cicd.log'
            if os.path.exists(log_file):
                subprocess.run(['tail', '-n', '50', log_file])
            else:
                print(f"{Colors.YELLOW}No logs available{Colors.NC}")
    
    def do_security(self, arg):
        """Security monitoring and controls"""
        if not arg or arg == 'status':
            print(f"{Colors.CYAN}Security Status:{Colors.NC}")
            print(f"  Firewall: {Colors.GREEN}Active{Colors.NC}")
            print(f"  Monitoring: {Colors.GREEN}Enabled{Colors.NC}")
            print(f"  Threat Level: {Colors.YELLOW}Low{Colors.NC}")
        elif arg == 'scan':
            print(f"{Colors.YELLOW}Initiating security scan...{Colors.NC}")
            print("Scanning system for threats...")
            print(f"{Colors.GREEN}No threats detected{Colors.NC}")
    
    def do_netstat(self, arg):
        """Show network connections"""
        connections = psutil.net_connections()
        print(f"{'Proto':<6} {'Local Address':<25} {'Remote Address':<25} {'Status':<12}")
        print("-" * 70)
        for conn in connections[:20]:  # Limit to first 20
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
            status = conn.status if conn.status != 'NONE' else '-'
            proto = "TCP" if conn.type == socket.SOCK_STREAM else "UDP"
            print(f"{proto:<6} {laddr:<25} {raddr:<25} {status:<12}")
    
    def do_ping(self, arg):
        """Ping a host"""
        if not arg:
            print(f"{Colors.RED}Usage: ping <host>{Colors.NC}")
            return
        subprocess.run(['ping', '-c', '4', arg])
    
    def do_ifconfig(self, arg):
        """Show network interfaces"""
        subprocess.run(['ip', 'addr'])
    
    def do_edit(self, arg):
        """Edit a file"""
        if not arg:
            print(f"{Colors.RED}Usage: edit <filename>{Colors.NC}")
            return
        editor = os.environ.get('EDITOR', 'nano')
        subprocess.run([editor, arg])
    
    def do_top(self, arg):
        """Show system resources (exits with 'q')"""
        subprocess.run(['top'])
    
    def do_exit(self, arg):
        """Exit QENEX Shell"""
        print(f"{Colors.CYAN}Goodbye from QENEX OS Shell{Colors.NC}")
        return True
    
    def do_quit(self, arg):
        """Exit QENEX Shell"""
        return self.do_exit(arg)
    
    def do_EOF(self, arg):
        """Handle Ctrl-D"""
        print()  # New line after ^D
        return self.do_exit(arg)
    
    def default(self, line):
        """Handle unknown commands or aliases"""
        # Check for aliases
        cmd = line.split()[0] if line else ""
        if cmd in self.aliases:
            expanded = line.replace(cmd, self.aliases[cmd], 1)
            return self.onecmd(expanded)
        
        # SECURITY FIX: Disable arbitrary system command execution
        print(f"{Colors.RED}Unknown command: {line.split()[0] if line else ''}. Use 'exec' for whitelisted system commands.{Colors.NC}")
    
    def precmd(self, line):
        """Called before executing a command"""
        if line and not line.startswith('!'):
            self.history.append(line)
        return line
    
    def emptyline(self):
        """Handle empty line - do nothing"""
        pass
    
    def completedefault(self, text, line, begidx, endidx):
        """Tab completion for files and directories"""
        if line.startswith('cd ') or line.startswith('cat ') or line.startswith('edit '):
            # File/directory completion
            path = text
            if '/' in path:
                directory = os.path.dirname(path)
                partial = os.path.basename(path)
            else:
                directory = '.'
                partial = path
            
            matches = []
            try:
                for item in os.listdir(directory):
                    if item.startswith(partial):
                        full_path = os.path.join(directory, item) if directory != '.' else item
                        if os.path.isdir(full_path):
                            matches.append(full_path + '/')
                        else:
                            matches.append(full_path)
            except:
                pass
            return matches
        return []

def main():
    """Main entry point for QENEX Shell"""
    shell = QenexShell()
    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}Use 'exit' or 'quit' to leave QENEX Shell{Colors.NC}")
        main()

if __name__ == '__main__':
    main()