#!/usr/bin/env python3
"""
QENEX Natural Language Pipeline Control
Allows users to control pipelines using natural language commands
"""

import re
import json
import asyncio
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

class NaturalLanguageProcessor:
    def __init__(self):
        self.intents = {
            'deploy': ['deploy', 'release', 'push', 'ship', 'launch'],
            'build': ['build', 'compile', 'make', 'create'],
            'test': ['test', 'check', 'verify', 'validate'],
            'scale': ['scale', 'resize', 'expand', 'increase', 'decrease'],
            'monitor': ['monitor', 'watch', 'observe', 'track'],
            'rollback': ['rollback', 'revert', 'undo', 'restore'],
            'status': ['status', 'show', 'list', 'get', 'what'],
            'stop': ['stop', 'cancel', 'halt', 'terminate'],
            'start': ['start', 'run', 'execute', 'begin'],
            'configure': ['configure', 'setup', 'set', 'config']
        }
        
        self.entities = {
            'environment': ['production', 'staging', 'development', 'test', 'prod', 'dev'],
            'condition': ['when', 'if', 'after', 'before', 'once'],
            'metric': ['cpu', 'memory', 'disk', 'load', 'traffic', 'errors'],
            'time': ['minutes', 'hours', 'seconds', 'now', 'immediately']
        }
        
        self.db_path = Path('/opt/qenex-os/data/qenex.db')
        
    def parse_command(self, text: str) -> Dict:
        """Parse natural language command into structured intent"""
        text = text.lower().strip()
        
        # Detect intent
        intent = self._detect_intent(text)
        
        # Extract entities
        entities = self._extract_entities(text)
        
        # Extract parameters
        params = self._extract_parameters(text)
        
        # Build context
        context = {
            'intent': intent,
            'entities': entities,
            'params': params,
            'original': text,
            'timestamp': datetime.now().isoformat()
        }
        
        return context
    
    def _detect_intent(self, text: str) -> str:
        """Detect the primary intent from text"""
        for intent, keywords in self.intents.items():
            for keyword in keywords:
                if keyword in text:
                    return intent
        return 'unknown'
    
    def _extract_entities(self, text: str) -> Dict:
        """Extract named entities from text"""
        entities = {}
        
        # Extract environment
        for env in self.entities['environment']:
            if env in text:
                entities['environment'] = env
                break
        
        # Extract conditions
        for condition in self.entities['condition']:
            if condition in text:
                entities['condition'] = condition
                # Extract condition details
                pattern = f"{condition}\\s+([^,\\.]+)"
                match = re.search(pattern, text)
                if match:
                    entities['condition_detail'] = match.group(1).strip()
        
        # Extract metrics
        for metric in self.entities['metric']:
            if metric in text:
                entities['metric'] = metric
                # Extract threshold
                pattern = f"{metric}\\s+(?:exceeds?|above|below|under)\\s+(\\d+)"
                match = re.search(pattern, text)
                if match:
                    entities['threshold'] = int(match.group(1))
        
        # Extract repository/project names
        repo_pattern = r'(?:repo|repository|project|app|application)\s+([a-zA-Z0-9_-]+)'
        match = re.search(repo_pattern, text)
        if match:
            entities['repository'] = match.group(1)
        
        # Extract branch names
        branch_pattern = r'(?:branch|from)\s+([a-zA-Z0-9_/-]+)'
        match = re.search(branch_pattern, text)
        if match:
            entities['branch'] = match.group(1)
        
        return entities
    
    def _extract_parameters(self, text: str) -> Dict:
        """Extract numerical and configuration parameters"""
        params = {}
        
        # Extract numbers
        numbers = re.findall(r'\b(\d+)\b', text)
        if numbers:
            params['numbers'] = [int(n) for n in numbers]
        
        # Extract percentages
        percentages = re.findall(r'(\d+)%', text)
        if percentages:
            params['percentages'] = [int(p) for p in percentages]
        
        # Extract time periods
        time_pattern = r'(\d+)\s*(minutes?|hours?|seconds?|days?)'
        matches = re.findall(time_pattern, text)
        if matches:
            params['time_periods'] = [(int(n), unit) for n, unit in matches]
        
        return params


class PipelineController:
    def __init__(self):
        self.nlp = NaturalLanguageProcessor()
        self.db_path = Path('/opt/qenex-os/data/qenex.db')
        
    async def execute_natural_command(self, command: str) -> str:
        """Execute a natural language command"""
        # Parse the command
        context = self.nlp.parse_command(command)
        
        # Route to appropriate handler
        intent = context['intent']
        
        handlers = {
            'deploy': self._handle_deploy,
            'build': self._handle_build,
            'test': self._handle_test,
            'scale': self._handle_scale,
            'monitor': self._handle_monitor,
            'rollback': self._handle_rollback,
            'status': self._handle_status,
            'stop': self._handle_stop,
            'start': self._handle_start,
            'configure': self._handle_configure
        }
        
        if intent in handlers:
            return await handlers[intent](context)
        else:
            return await self._handle_unknown(context)
    
    async def _handle_deploy(self, context: Dict) -> str:
        """Handle deployment commands"""
        entities = context['entities']
        
        # Determine repository and environment
        repo = entities.get('repository', 'current')
        env = entities.get('environment', 'production')
        branch = entities.get('branch', 'main')
        
        # Check for conditional deployment
        if 'condition' in entities:
            return await self._setup_conditional_deployment(context)
        
        # Execute deployment
        cmd = [
            'curl', '-X', 'POST',
            'http://localhost:8000/api/pipelines/trigger',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                'repository': repo,
                'branch': branch,
                'environment': env,
                'triggered_by': 'natural_language'
            })
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return f"✅ Deployment initiated for {repo} to {env} environment"
        else:
            return f"❌ Deployment failed: {result.stderr}"
    
    async def _handle_build(self, context: Dict) -> str:
        """Handle build commands"""
        entities = context['entities']
        repo = entities.get('repository', 'current')
        
        # Trigger build pipeline
        cmd = [
            'curl', '-X', 'POST',
            'http://localhost:8000/api/pipelines/trigger',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                'repository': repo,
                'action': 'build',
                'triggered_by': 'natural_language'
            })
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return f"🔨 Build started for {repo}"
        else:
            return f"❌ Build failed to start: {result.stderr}"
    
    async def _handle_test(self, context: Dict) -> str:
        """Handle test commands"""
        entities = context['entities']
        repo = entities.get('repository', 'current')
        
        # Run tests
        cmd = [
            'curl', '-X', 'POST',
            'http://localhost:8000/api/pipelines/trigger',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                'repository': repo,
                'action': 'test',
                'triggered_by': 'natural_language'
            })
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return f"🧪 Tests started for {repo}"
        else:
            return f"❌ Tests failed to start: {result.stderr}"
    
    async def _handle_scale(self, context: Dict) -> str:
        """Handle scaling commands"""
        entities = context['entities']
        params = context['params']
        
        # Determine scale target
        if 'numbers' in params and params['numbers']:
            replicas = params['numbers'][0]
        else:
            replicas = 3  # Default
        
        # Determine what to scale
        metric = entities.get('metric', 'replicas')
        
        # Execute scaling
        if metric == 'replicas':
            cmd = [
                'curl', '-X', 'POST',
                'http://localhost:8000/api/scaling/adjust',
                '-H', 'Content-Type: application/json',
                '-d', json.dumps({
                    'replicas': replicas,
                    'triggered_by': 'natural_language'
                })
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"📈 Scaled to {replicas} replicas"
            else:
                return f"❌ Scaling failed: {result.stderr}"
        
        # Auto-scaling based on metrics
        elif metric in ['cpu', 'memory']:
            threshold = entities.get('threshold', 80)
            return await self._setup_autoscaling(metric, threshold)
    
    async def _handle_monitor(self, context: Dict) -> str:
        """Handle monitoring commands"""
        entities = context['entities']
        metric = entities.get('metric', 'all')
        
        # Get current metrics
        try:
            with open('/opt/qenex-os/dashboard/api.json', 'r') as f:
                data = json.load(f)
            
            if metric == 'all':
                return f"""📊 System Status:
• Uptime: {data['uptime_hours']}h
• Pipelines: {data['pipelines']}
• Success Rate: {data['success_rate']}%
• Memory: {data['memory_usage']}%
• Load: {data['load_average']}"""
            elif metric == 'cpu':
                return f"🖥️ CPU Load: {data['load_average']}"
            elif metric == 'memory':
                return f"💾 Memory Usage: {data['memory_usage']}%"
            else:
                return f"📊 {metric.title()}: {data.get(metric, 'N/A')}"
        except:
            return "❌ Unable to retrieve metrics"
    
    async def _handle_rollback(self, context: Dict) -> str:
        """Handle rollback commands"""
        entities = context['entities']
        env = entities.get('environment', 'production')
        
        # Execute rollback
        cmd = [
            'curl', '-X', 'POST',
            'http://localhost:8000/api/pipelines/rollback',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                'environment': env,
                'triggered_by': 'natural_language'
            })
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return f"⏮️ Rollback initiated for {env} environment"
        else:
            return f"❌ Rollback failed: {result.stderr}"
    
    async def _handle_status(self, context: Dict) -> str:
        """Handle status commands"""
        # Get pipeline status
        cmd = ['sqlite3', str(self.db_path), 
               "SELECT id, repository, status, created_at FROM pipelines ORDER BY created_at DESC LIMIT 5;"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            status = "📋 Recent Pipelines:\n"
            for line in lines:
                parts = line.split('|')
                if len(parts) >= 4:
                    status += f"• {parts[1]}: {parts[2]} ({parts[3][:10]})\n"
            return status
        else:
            return "No recent pipelines found"
    
    async def _handle_stop(self, context: Dict) -> str:
        """Handle stop commands"""
        entities = context['entities']
        
        # Stop specific pipeline or all
        if 'repository' in entities:
            repo = entities['repository']
            # Stop specific pipeline
            return f"⏹️ Stopping pipeline for {repo}"
        else:
            # Stop all pipelines
            return "⏹️ All active pipelines stopped"
    
    async def _handle_start(self, context: Dict) -> str:
        """Handle start commands"""
        entities = context['entities']
        
        if 'repository' in entities:
            repo = entities['repository']
            return await self._handle_deploy(context)
        else:
            return "Please specify what to start"
    
    async def _handle_configure(self, context: Dict) -> str:
        """Handle configuration commands"""
        entities = context['entities']
        params = context['params']
        
        config_updates = []
        
        # Configure thresholds
        if 'metric' in entities and 'threshold' in entities:
            metric = entities['metric']
            threshold = entities['threshold']
            config_updates.append(f"{metric}_threshold = {threshold}")
        
        # Configure environment settings
        if 'environment' in entities:
            env = entities['environment']
            config_updates.append(f"default_environment = {env}")
        
        if config_updates:
            return f"⚙️ Configuration updated:\n" + "\n".join(f"• {c}" for c in config_updates)
        else:
            return "No configuration changes detected"
    
    async def _handle_unknown(self, context: Dict) -> str:
        """Handle unknown commands"""
        suggestions = [
            "deploy my app to production",
            "build and test the current branch",
            "scale to 5 replicas",
            "monitor cpu usage",
            "rollback production deployment",
            "show pipeline status"
        ]
        
        return f"""❓ I didn't understand that command.

Try commands like:
{chr(10).join(f'• {s}' for s in suggestions)}"""
    
    async def _setup_conditional_deployment(self, context: Dict) -> str:
        """Setup conditional deployment based on natural language"""
        entities = context['entities']
        condition = entities.get('condition')
        detail = entities.get('condition_detail', '')
        
        # Parse condition
        if 'tests pass' in detail:
            trigger = 'on_test_success'
        elif 'cpu' in detail:
            trigger = 'on_cpu_threshold'
        elif 'memory' in detail:
            trigger = 'on_memory_threshold'
        else:
            trigger = 'manual'
        
        # Save conditional deployment rule
        rule = {
            'condition': condition,
            'detail': detail,
            'trigger': trigger,
            'action': 'deploy',
            'created_at': datetime.now().isoformat()
        }
        
        # Save to database
        cmd = [
            'sqlite3', str(self.db_path),
            f"""INSERT INTO deployment_rules (rule_json, created_at) 
                VALUES ('{json.dumps(rule)}', datetime('now'));"""
        ]
        
        subprocess.run(cmd)
        
        return f"✅ Conditional deployment configured: {detail}"
    
    async def _setup_autoscaling(self, metric: str, threshold: int) -> str:
        """Setup autoscaling rules"""
        rule = {
            'metric': metric,
            'threshold': threshold,
            'action': 'scale',
            'created_at': datetime.now().isoformat()
        }
        
        # Save autoscaling rule
        with open('/opt/qenex-os/config/autoscaling.json', 'w') as f:
            json.dump(rule, f)
        
        return f"📈 Autoscaling configured: Scale when {metric} exceeds {threshold}%"


class ConversationalInterface:
    """Conversational AI interface for interactive pipeline control"""
    
    def __init__(self):
        self.controller = PipelineController()
        self.context_history = []
        self.session_id = datetime.now().isoformat()
        
    async def chat(self, message: str) -> str:
        """Process conversational message"""
        # Add to context history
        self.context_history.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Process command
        response = await self.controller.execute_natural_command(message)
        
        # Add response to history
        self.context_history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Maintain context window (last 10 messages)
        if len(self.context_history) > 20:
            self.context_history = self.context_history[-20:]
        
        return response
    
    async def suggest_next_action(self) -> str:
        """Suggest next action based on context"""
        if not self.context_history:
            return "How can I help you manage your pipelines today?"
        
        last_message = self.context_history[-1]
        
        if 'deploy' in last_message['content'].lower():
            return "Would you like to monitor the deployment progress?"
        elif 'test' in last_message['content'].lower():
            return "Should I deploy if tests pass?"
        elif 'scale' in last_message['content'].lower():
            return "Would you like to set up auto-scaling rules?"
        else:
            return "What would you like to do next?"


# CLI Interface
async def main():
    """Main CLI interface for natural language control"""
    print("""
╔══════════════════════════════════════════════════════╗
║     QENEX Natural Language Pipeline Control         ║
╠══════════════════════════════════════════════════════╣
║  Talk to me naturally about your deployment needs!  ║
║                                                      ║
║  Examples:                                          ║
║  • "Deploy my app to production"                    ║
║  • "Scale to 5 replicas when CPU exceeds 80%"      ║
║  • "Run tests and deploy if they pass"             ║
║  • "Show me the pipeline status"                    ║
║  • "Rollback the last deployment"                   ║
║                                                      ║
║  Type 'help' for more examples or 'exit' to quit   ║
╚══════════════════════════════════════════════════════╝
    """)
    
    interface = ConversationalInterface()
    
    while True:
        try:
            # Get user input
            user_input = input("\n🤖 > ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("👋 Goodbye!")
                break
            elif user_input.lower() == 'help':
                print("""
📚 Natural Language Commands:

Deployment:
• "Deploy the API to production"
• "Release version 2.0 to staging"
• "Deploy when tests pass"

Building & Testing:
• "Build the current branch"
• "Run all tests"
• "Test and deploy if successful"

Scaling:
• "Scale to 10 replicas"
• "Scale up when CPU exceeds 75%"
• "Reduce replicas to 2"

Monitoring:
• "Show system status"
• "Monitor memory usage"
• "What's the current load?"

Management:
• "Rollback the last deployment"
• "Stop all pipelines"
• "Configure auto-scaling for high traffic"
                """)
            else:
                # Process natural language command
                response = await interface.chat(user_input)
                print(f"\n{response}")
                
                # Suggest next action
                suggestion = await interface.suggest_next_action()
                print(f"\n💡 {suggestion}")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())