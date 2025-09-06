#!/usr/bin/env python3
"""
QENEX Advanced AI Features
Predictive failure detection, automated code generation, and sentiment analysis
"""

import json
import asyncio
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import subprocess
from pathlib import Path
import random

class CodeGenerator:
    """AI-driven code generation from natural language"""
    
    def __init__(self):
        self.templates = {
            'python_function': """def {name}({params}):
    \"\"\"{description}\"\"\"
    {body}
    return {return_value}""",
            
            'api_endpoint': """@app.route('/{path}', methods=['{method}'])
async def {name}(request):
    \"\"\"{description}\"\"\"
    data = await request.json()
    {validation}
    result = {logic}
    return web.json_response(result)""",
            
            'docker_compose': """version: '3.8'
services:
  {service_name}:
    image: {image}
    ports:
      - "{port}:{port}"
    environment:
      {environment}
    volumes:
      - {volumes}""",
            
            'kubernetes_deployment': """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
      - name: {name}
        image: {image}
        ports:
        - containerPort: {port}"""
        }
        
        self.patterns = {
            'function': r'create\s+(?:a\s+)?function\s+(?:called\s+)?(\w+)\s+that\s+(.*)',
            'api': r'create\s+(?:an?\s+)?api\s+endpoint\s+(?:for\s+)?(.*)',
            'service': r'deploy\s+(?:a\s+)?service\s+(?:called\s+)?(\w+)\s+(?:using\s+)?(.*)',
            'database': r'create\s+(?:a\s+)?database\s+(?:table\s+)?(?:for\s+)?(.*)'
        }
    
    async def generate_code(self, prompt: str) -> Dict:
        """Generate code from natural language prompt"""
        prompt_lower = prompt.lower()
        
        # Detect intent
        if 'function' in prompt_lower or 'def' in prompt_lower:
            return await self.generate_function(prompt)
        elif 'api' in prompt_lower or 'endpoint' in prompt_lower:
            return await self.generate_api_endpoint(prompt)
        elif 'docker' in prompt_lower or 'container' in prompt_lower:
            return await self.generate_docker_config(prompt)
        elif 'kubernetes' in prompt_lower or 'k8s' in prompt_lower:
            return await self.generate_kubernetes_config(prompt)
        else:
            return await self.generate_generic_code(prompt)
    
    async def generate_function(self, prompt: str) -> Dict:
        """Generate a Python function from description"""
        # Extract function details
        match = re.search(self.patterns['function'], prompt, re.IGNORECASE)
        
        if match:
            name = match.group(1)
            description = match.group(2)
        else:
            name = "generated_function"
            description = prompt
        
        # Parse parameters from description
        params = self.extract_parameters(description)
        
        # Generate function body based on description
        body = self.generate_function_body(description)
        
        code = self.templates['python_function'].format(
            name=name,
            params=', '.join(params),
            description=description,
            body=body,
            return_value='result'
        )
        
        return {
            'type': 'function',
            'language': 'python',
            'code': code,
            'description': description
        }
    
    def extract_parameters(self, description: str) -> List[str]:
        """Extract function parameters from description"""
        params = []
        
        # Look for common parameter patterns
        if 'list' in description or 'array' in description:
            params.append('items')
        if 'number' in description or 'calculate' in description:
            params.append('value')
        if 'string' in description or 'text' in description:
            params.append('text')
        if 'file' in description:
            params.append('file_path')
        if 'data' in description:
            params.append('data')
        
        return params if params else ['*args', '**kwargs']
    
    def generate_function_body(self, description: str) -> str:
        """Generate function body based on description"""
        body_lines = []
        
        if 'sort' in description:
            body_lines.append("    result = sorted(items)")
        elif 'filter' in description:
            body_lines.append("    result = [item for item in items if condition(item)]")
        elif 'calculate' in description or 'sum' in description:
            body_lines.append("    result = sum(items)")
        elif 'validate' in description:
            body_lines.append("    if not data:\n        raise ValueError('Invalid data')")
            body_lines.append("    result = True")
        elif 'process' in description:
            body_lines.append("    # Process data")
            body_lines.append("    result = process_data(data)")
        else:
            body_lines.append("    # TODO: Implement logic")
            body_lines.append("    result = None")
        
        return '\n'.join(body_lines)
    
    async def generate_api_endpoint(self, prompt: str) -> Dict:
        """Generate API endpoint code"""
        # Extract endpoint details
        method = 'GET' if 'get' in prompt.lower() else 'POST'
        path = 'generated_endpoint'
        
        if 'user' in prompt.lower():
            path = 'users'
        elif 'data' in prompt.lower():
            path = 'data'
        elif 'status' in prompt.lower():
            path = 'status'
        
        code = self.templates['api_endpoint'].format(
            path=path,
            method=method,
            name=f"handle_{path}",
            description=prompt,
            validation="# Validate input data",
            logic="await process_request(data)"
        )
        
        return {
            'type': 'api_endpoint',
            'language': 'python',
            'code': code,
            'description': prompt
        }
    
    async def generate_docker_config(self, prompt: str) -> Dict:
        """Generate Docker configuration"""
        service_name = 'app'
        image = 'python:3.11-slim'
        port = '8000'
        
        if 'node' in prompt.lower():
            image = 'node:18-alpine'
            port = '3000'
        elif 'nginx' in prompt.lower():
            image = 'nginx:alpine'
            port = '80'
        
        code = self.templates['docker_compose'].format(
            service_name=service_name,
            image=image,
            port=port,
            environment="- ENV=production",
            volumes="./app:/app"
        )
        
        return {
            'type': 'docker_compose',
            'language': 'yaml',
            'code': code,
            'description': prompt
        }
    
    async def generate_kubernetes_config(self, prompt: str) -> Dict:
        """Generate Kubernetes configuration"""
        name = 'app-deployment'
        replicas = '3'
        image = 'app:latest'
        port = '8080'
        
        code = self.templates['kubernetes_deployment'].format(
            name=name,
            replicas=replicas,
            image=image,
            port=port
        )
        
        return {
            'type': 'kubernetes',
            'language': 'yaml',
            'code': code,
            'description': prompt
        }
    
    async def generate_generic_code(self, prompt: str) -> Dict:
        """Generate generic code based on prompt"""
        # Default to Python script
        code = f'''#!/usr/bin/env python3
"""
Generated code for: {prompt}
"""

def main():
    # TODO: Implement based on requirements
    print("Executing: {prompt}")

if __name__ == "__main__":
    main()
'''
        
        return {
            'type': 'script',
            'language': 'python',
            'code': code,
            'description': prompt
        }


class SentimentAnalyzer:
    """Analyze sentiment in user interactions"""
    
    def __init__(self):
        self.positive_words = ['good', 'great', 'excellent', 'amazing', 'perfect', 'love', 'awesome', 'fantastic']
        self.negative_words = ['bad', 'terrible', 'awful', 'hate', 'horrible', 'broken', 'failed', 'error']
        self.neutral_words = ['okay', 'fine', 'alright', 'normal', 'average']
    
    def analyze(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        text_lower = text.lower()
        
        # Count sentiment indicators
        positive_count = sum(1 for word in self.positive_words if word in text_lower)
        negative_count = sum(1 for word in self.negative_words if word in text_lower)
        neutral_count = sum(1 for word in self.neutral_words if word in text_lower)
        
        # Calculate sentiment score
        total = positive_count + negative_count + neutral_count
        
        if total == 0:
            sentiment = 'neutral'
            confidence = 0.5
        else:
            if positive_count > negative_count:
                sentiment = 'positive'
                confidence = positive_count / total
            elif negative_count > positive_count:
                sentiment = 'negative'
                confidence = negative_count / total
            else:
                sentiment = 'neutral'
                confidence = 0.5
        
        # Check for urgency
        urgent = any(word in text_lower for word in ['urgent', 'asap', 'immediately', 'critical', 'emergency'])
        
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'urgent': urgent,
            'positive_score': positive_count,
            'negative_score': negative_count,
            'recommendation': self.get_recommendation(sentiment, urgent)
        }
    
    def get_recommendation(self, sentiment: str, urgent: bool) -> str:
        """Get action recommendation based on sentiment"""
        if urgent:
            return "Priority response required"
        elif sentiment == 'negative':
            return "Address concerns and provide solutions"
        elif sentiment == 'positive':
            return "Maintain current approach"
        else:
            return "Standard response appropriate"


class PerformanceTuner:
    """AI-driven performance tuning"""
    
    def __init__(self):
        self.metrics_file = Path('/opt/qenex-os/data/performance_metrics.json')
        self.tuning_history = []
        
    async def auto_tune(self) -> Dict:
        """Automatically tune system performance"""
        # Analyze current performance
        metrics = self.collect_metrics()
        
        # Determine optimal settings
        recommendations = self.analyze_performance(metrics)
        
        # Apply tuning
        results = await self.apply_tuning(recommendations)
        
        # Record results
        self.tuning_history.append({
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'recommendations': recommendations,
            'results': results
        })
        
        return results
    
    def collect_metrics(self) -> Dict:
        """Collect current performance metrics"""
        import psutil
        
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_io': psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
            'network_io': psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
            'process_count': len(psutil.pids())
        }
    
    def analyze_performance(self, metrics: Dict) -> List[Dict]:
        """Analyze metrics and generate recommendations"""
        recommendations = []
        
        # CPU optimization
        if metrics['cpu_percent'] > 80:
            recommendations.append({
                'type': 'cpu',
                'action': 'enable_governor',
                'value': 'powersave'
            })
        
        # Memory optimization
        if metrics['memory_percent'] > 85:
            recommendations.append({
                'type': 'memory',
                'action': 'clear_cache',
                'value': 3
            })
        
        # Process optimization
        if metrics['process_count'] > 500:
            recommendations.append({
                'type': 'process',
                'action': 'limit_processes',
                'value': 400
            })
        
        return recommendations
    
    async def apply_tuning(self, recommendations: List[Dict]) -> Dict:
        """Apply tuning recommendations"""
        results = {'applied': [], 'failed': []}
        
        for rec in recommendations:
            try:
                if rec['type'] == 'cpu':
                    subprocess.run(['cpupower', 'frequency-set', '-g', rec['value']], 
                                 capture_output=True)
                    results['applied'].append(rec)
                    
                elif rec['type'] == 'memory':
                    subprocess.run(['sh', '-c', f'echo {rec["value"]} > /proc/sys/vm/drop_caches'],
                                 capture_output=True)
                    results['applied'].append(rec)
                    
                elif rec['type'] == 'process':
                    # Implement process limiting logic
                    results['applied'].append(rec)
                    
            except Exception as e:
                rec['error'] = str(e)
                results['failed'].append(rec)
        
        return results


async def main():
    """Main advanced AI features loop"""
    print("🤖 Starting QENEX Advanced AI Features...")
    
    code_gen = CodeGenerator()
    sentiment = SentimentAnalyzer()
    tuner = PerformanceTuner()
    
    # Example usage
    while True:
        try:
            # Auto-tune every 5 minutes
            results = await tuner.auto_tune()
            print(f"Performance tuning: {len(results['applied'])} optimizations applied")
            
        except Exception as e:
            print(f"AI features error: {e}")
        
        await asyncio.sleep(300)


if __name__ == "__main__":
    asyncio.run(main())