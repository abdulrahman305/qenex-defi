#!/usr/bin/env python3
"""
QENEX Visual Pipeline Builder
Drag-and-drop interface for creating and managing AI/data processing pipelines
"""

import asyncio
import json
import time
import logging
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Union
from concurrent.futures import ThreadPoolExecutor
import aiohttp
from aiohttp import web, ClientSession
import subprocess

@dataclass
class PipelineNode:
    """Individual node in the pipeline"""
    node_id: str
    node_type: str  # input, processor, output, condition, loop
    name: str
    description: str
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=dict)  # x, y coordinates
    inputs: List[str] = field(default_factory=list)  # Input port names
    outputs: List[str] = field(default_factory=list)  # Output port names
    status: str = "inactive"  # inactive, running, completed, error
    execution_time: float = 0
    error_message: Optional[str] = None

@dataclass
class PipelineConnection:
    """Connection between pipeline nodes"""
    connection_id: str
    source_node: str
    source_port: str
    target_node: str
    target_port: str
    data_type: str = "any"

@dataclass
class Pipeline:
    """Complete pipeline definition"""
    pipeline_id: str
    name: str
    description: str
    version: str = "1.0.0"
    created_at: float = 0
    updated_at: float = 0
    nodes: List[PipelineNode] = field(default_factory=list)
    connections: List[PipelineConnection] = field(default_factory=list)
    global_config: Dict[str, Any] = field(default_factory=dict)
    status: str = "draft"  # draft, active, running, completed, error
    tags: List[str] = field(default_factory=list)

class PipelineNodeRegistry:
    """Registry of available pipeline node types"""
    
    def __init__(self):
        self.node_types = {}
        self.register_default_nodes()
        
    def register_node_type(self, node_type: str, definition: Dict[str, Any]):
        """Register a new node type"""
        self.node_types[node_type] = definition
        
    def register_default_nodes(self):
        """Register default node types"""
        
        # Input nodes
        self.register_node_type("file_input", {
            "name": "File Input",
            "category": "input",
            "description": "Read data from file",
            "inputs": [],
            "outputs": ["data"],
            "config_schema": {
                "file_path": {"type": "string", "required": True, "description": "Path to input file"},
                "file_format": {"type": "select", "options": ["json", "csv", "txt", "xml"], "default": "json"},
                "encoding": {"type": "string", "default": "utf-8"}
            }
        })
        
        self.register_node_type("database_input", {
            "name": "Database Input", 
            "category": "input",
            "description": "Read data from database",
            "inputs": [],
            "outputs": ["data"],
            "config_schema": {
                "connection_string": {"type": "string", "required": True},
                "query": {"type": "text", "required": True, "description": "SQL query to execute"},
                "parameters": {"type": "json", "default": {}}
            }
        })
        
        self.register_node_type("api_input", {
            "name": "API Input",
            "category": "input", 
            "description": "Fetch data from API endpoint",
            "inputs": [],
            "outputs": ["data"],
            "config_schema": {
                "url": {"type": "string", "required": True},
                "method": {"type": "select", "options": ["GET", "POST", "PUT"], "default": "GET"},
                "headers": {"type": "json", "default": {}},
                "body": {"type": "json", "default": {}}
            }
        })
        
        # Processing nodes
        self.register_node_type("data_transform", {
            "name": "Data Transform",
            "category": "processor",
            "description": "Transform data using custom logic",
            "inputs": ["input"],
            "outputs": ["output"],
            "config_schema": {
                "transformation": {"type": "select", "options": ["filter", "map", "reduce", "custom"], "default": "map"},
                "expression": {"type": "text", "description": "Transformation expression or code"},
                "language": {"type": "select", "options": ["python", "javascript", "jq"], "default": "python"}
            }
        })
        
        self.register_node_type("ai_model", {
            "name": "AI Model",
            "category": "processor",
            "description": "Apply AI model for inference",
            "inputs": ["input"],
            "outputs": ["prediction", "confidence"],
            "config_schema": {
                "model_type": {"type": "select", "options": ["classification", "regression", "nlp", "vision"], "default": "classification"},
                "model_path": {"type": "string", "required": True},
                "input_format": {"type": "select", "options": ["json", "image", "text"], "default": "json"},
                "batch_size": {"type": "number", "default": 1}
            }
        })
        
        self.register_node_type("data_validation", {
            "name": "Data Validation",
            "category": "processor",
            "description": "Validate data against schema",
            "inputs": ["input"],
            "outputs": ["valid", "invalid"],
            "config_schema": {
                "schema": {"type": "json", "required": True, "description": "JSON schema for validation"},
                "strict_mode": {"type": "boolean", "default": True},
                "error_handling": {"type": "select", "options": ["stop", "continue", "log"], "default": "stop"}
            }
        })
        
        # Control flow nodes
        self.register_node_type("condition", {
            "name": "Condition",
            "category": "control",
            "description": "Branch pipeline based on condition",
            "inputs": ["input"],
            "outputs": ["true", "false"],
            "config_schema": {
                "condition": {"type": "text", "required": True, "description": "Boolean expression"},
                "language": {"type": "select", "options": ["python", "javascript"], "default": "python"}
            }
        })
        
        self.register_node_type("loop", {
            "name": "Loop",
            "category": "control",
            "description": "Process data in loop",
            "inputs": ["input"],
            "outputs": ["item", "complete"],
            "config_schema": {
                "loop_type": {"type": "select", "options": ["for_each", "while", "range"], "default": "for_each"},
                "condition": {"type": "text", "description": "Loop condition (for while loops)"},
                "max_iterations": {"type": "number", "default": 1000}
            }
        })
        
        # Output nodes
        self.register_node_type("file_output", {
            "name": "File Output",
            "category": "output",
            "description": "Write data to file",
            "inputs": ["data"],
            "outputs": [],
            "config_schema": {
                "file_path": {"type": "string", "required": True},
                "file_format": {"type": "select", "options": ["json", "csv", "txt", "xml"], "default": "json"},
                "append_mode": {"type": "boolean", "default": False}
            }
        })
        
        self.register_node_type("database_output", {
            "name": "Database Output",
            "category": "output",
            "description": "Write data to database",
            "inputs": ["data"],
            "outputs": [],
            "config_schema": {
                "connection_string": {"type": "string", "required": True},
                "table_name": {"type": "string", "required": True},
                "operation": {"type": "select", "options": ["insert", "upsert", "update"], "default": "insert"}
            }
        })
        
        self.register_node_type("api_output", {
            "name": "API Output", 
            "category": "output",
            "description": "Send data to API endpoint",
            "inputs": ["data"],
            "outputs": ["response"],
            "config_schema": {
                "url": {"type": "string", "required": True},
                "method": {"type": "select", "options": ["POST", "PUT", "PATCH"], "default": "POST"},
                "headers": {"type": "json", "default": {"Content-Type": "application/json"}}
            }
        })

class QenexPipelineBuilder:
    """Visual pipeline builder and execution engine"""
    
    def __init__(self, config_path: str = "/opt/qenex-os/config/pipeline_builder.json"):
        self.config_path = config_path
        self.pipelines: Dict[str, Pipeline] = {}
        self.node_registry = PipelineNodeRegistry()
        self.execution_history: List[Dict] = []
        self.active_executions: Dict[str, Dict] = {}
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/opt/qenex-os/logs/pipeline_builder.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('QenexPipelineBuilder')
        
        # Load configuration and data
        self.load_config()
        self.load_pipelines()
        
    def load_config(self):
        """Load pipeline builder configuration"""
        default_config = {
            "enabled": True,
            "max_concurrent_executions": 5,
            "default_timeout": 3600,
            "auto_save": True,
            "execution_history_limit": 1000,
            "web_interface": {
                "host": "0.0.0.0",
                "port": 8004,
                "enable_cors": True
            },
            "storage": {
                "pipeline_directory": "/opt/qenex-os/data/pipelines",
                "execution_logs": "/opt/qenex-os/logs/pipeline_executions"
            }
        }
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = default_config
                self.save_config()
        except Exception as e:
            self.logger.warning(f"Failed to load config: {e}, using defaults")
            self.config = default_config
            
    def save_config(self):
        """Save current configuration"""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
            
    def load_pipelines(self):
        """Load existing pipelines from storage"""
        try:
            pipeline_dir = Path(self.config["storage"]["pipeline_directory"])
            pipeline_dir.mkdir(parents=True, exist_ok=True)
            
            for pipeline_file in pipeline_dir.glob("*.json"):
                with open(pipeline_file, 'r') as f:
                    pipeline_data = json.load(f)
                    
                pipeline = Pipeline(**pipeline_data)
                pipeline.nodes = [PipelineNode(**node) for node in pipeline_data.get("nodes", [])]
                pipeline.connections = [PipelineConnection(**conn) for conn in pipeline_data.get("connections", [])]
                
                self.pipelines[pipeline.pipeline_id] = pipeline
                
            self.logger.info(f"Loaded {len(self.pipelines)} pipelines")
            
        except Exception as e:
            self.logger.error(f"Failed to load pipelines: {e}")
            
    def save_pipeline(self, pipeline: Pipeline):
        """Save pipeline to storage"""
        try:
            pipeline_dir = Path(self.config["storage"]["pipeline_directory"])
            pipeline_dir.mkdir(parents=True, exist_ok=True)
            
            pipeline_file = pipeline_dir / f"{pipeline.pipeline_id}.json"
            
            # Convert to serializable format
            pipeline_data = asdict(pipeline)
            
            with open(pipeline_file, 'w') as f:
                json.dump(pipeline_data, f, indent=2)
                
            self.logger.info(f"Saved pipeline: {pipeline.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to save pipeline: {e}")
            
    def create_pipeline(self, name: str, description: str = "") -> str:
        """Create new pipeline"""
        pipeline_id = str(uuid.uuid4())
        
        pipeline = Pipeline(
            pipeline_id=pipeline_id,
            name=name,
            description=description,
            created_at=time.time(),
            updated_at=time.time()
        )
        
        self.pipelines[pipeline_id] = pipeline
        self.save_pipeline(pipeline)
        
        self.logger.info(f"Created new pipeline: {name} ({pipeline_id})")
        return pipeline_id
        
    def add_node(self, pipeline_id: str, node_type: str, name: str, 
                position: Dict[str, float], config: Dict[str, Any] = None) -> str:
        """Add node to pipeline"""
        if pipeline_id not in self.pipelines:
            raise ValueError("Pipeline not found")
            
        if node_type not in self.node_registry.node_types:
            raise ValueError("Unknown node type")
            
        pipeline = self.pipelines[pipeline_id]
        node_id = str(uuid.uuid4())
        
        node_definition = self.node_registry.node_types[node_type]
        
        node = PipelineNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            description=node_definition["description"],
            config=config or {},
            position=position,
            inputs=node_definition["inputs"].copy(),
            outputs=node_definition["outputs"].copy()
        )
        
        pipeline.nodes.append(node)
        pipeline.updated_at = time.time()
        
        if self.config["auto_save"]:
            self.save_pipeline(pipeline)
            
        return node_id
        
    def add_connection(self, pipeline_id: str, source_node: str, source_port: str,
                      target_node: str, target_port: str) -> str:
        """Add connection between nodes"""
        if pipeline_id not in self.pipelines:
            raise ValueError("Pipeline not found")
            
        pipeline = self.pipelines[pipeline_id]
        connection_id = str(uuid.uuid4())
        
        # Validate nodes exist
        source_exists = any(n.node_id == source_node for n in pipeline.nodes)
        target_exists = any(n.node_id == target_node for n in pipeline.nodes)
        
        if not source_exists or not target_exists:
            raise ValueError("Source or target node not found")
            
        connection = PipelineConnection(
            connection_id=connection_id,
            source_node=source_node,
            source_port=source_port,
            target_node=target_node,
            target_port=target_port
        )
        
        pipeline.connections.append(connection)
        pipeline.updated_at = time.time()
        
        if self.config["auto_save"]:
            self.save_pipeline(pipeline)
            
        return connection_id
        
    def validate_pipeline(self, pipeline_id: str) -> Tuple[bool, List[str]]:
        """Validate pipeline structure and configuration"""
        if pipeline_id not in self.pipelines:
            return False, ["Pipeline not found"]
            
        pipeline = self.pipelines[pipeline_id]
        errors = []
        
        # Check for nodes
        if not pipeline.nodes:
            errors.append("Pipeline has no nodes")
            
        # Check for input nodes
        input_nodes = [n for n in pipeline.nodes if not n.inputs]
        if not input_nodes:
            errors.append("Pipeline has no input nodes")
            
        # Check for output nodes
        output_nodes = [n for n in pipeline.nodes if not n.outputs]
        if not output_nodes:
            errors.append("Pipeline has no output nodes")
            
        # Validate node configurations
        for node in pipeline.nodes:
            node_def = self.node_registry.node_types.get(node.node_type)
            if not node_def:
                errors.append(f"Unknown node type: {node.node_type}")
                continue
                
            # Check required configuration
            config_schema = node_def.get("config_schema", {})
            for param_name, param_def in config_schema.items():
                if param_def.get("required", False) and param_name not in node.config:
                    errors.append(f"Node {node.name}: missing required parameter {param_name}")
                    
        # Check connections
        for connection in pipeline.connections:
            source_node = next((n for n in pipeline.nodes if n.node_id == connection.source_node), None)
            target_node = next((n for n in pipeline.nodes if n.node_id == connection.target_node), None)
            
            if not source_node:
                errors.append(f"Connection source node not found: {connection.source_node}")
                continue
                
            if not target_node:
                errors.append(f"Connection target node not found: {connection.target_node}")
                continue
                
            if connection.source_port not in source_node.outputs:
                errors.append(f"Invalid source port: {connection.source_port}")
                
            if connection.target_port not in target_node.inputs:
                errors.append(f"Invalid target port: {connection.target_port}")
                
        # Check for cycles (simplified)
        if self.has_cycles(pipeline):
            errors.append("Pipeline contains cycles")
            
        return len(errors) == 0, errors
        
    def has_cycles(self, pipeline: Pipeline) -> bool:
        """Check if pipeline has cycles (simplified implementation)"""
        # Build adjacency list
        graph = {}
        for node in pipeline.nodes:
            graph[node.node_id] = []
            
        for connection in pipeline.connections:
            graph[connection.source_node].append(connection.target_node)
            
        # DFS cycle detection
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
                    
            rec_stack.remove(node)
            return False
            
        for node_id in graph:
            if node_id not in visited:
                if has_cycle(node_id):
                    return True
                    
        return False
        
    async def execute_pipeline(self, pipeline_id: str, input_data: Dict[str, Any] = None) -> str:
        """Execute pipeline asynchronously"""
        if pipeline_id not in self.pipelines:
            raise ValueError("Pipeline not found")
            
        # Validate pipeline
        valid, errors = self.validate_pipeline(pipeline_id)
        if not valid:
            raise ValueError(f"Invalid pipeline: {', '.join(errors)}")
            
        # Check concurrent execution limit
        if len(self.active_executions) >= self.config["max_concurrent_executions"]:
            raise RuntimeError("Maximum concurrent executions reached")
            
        execution_id = str(uuid.uuid4())
        pipeline = self.pipelines[pipeline_id]
        
        # Initialize execution context
        execution_context = {
            "execution_id": execution_id,
            "pipeline_id": pipeline_id,
            "start_time": time.time(),
            "status": "running",
            "current_node": None,
            "data_flow": {},
            "input_data": input_data or {},
            "results": {},
            "errors": []
        }
        
        self.active_executions[execution_id] = execution_context
        
        # Execute pipeline in background
        asyncio.create_task(self._execute_pipeline_async(pipeline, execution_context))
        
        self.logger.info(f"Started pipeline execution: {pipeline.name} ({execution_id})")
        return execution_id
        
    async def _execute_pipeline_async(self, pipeline: Pipeline, context: Dict):
        """Execute pipeline nodes in correct order"""
        try:
            # Determine execution order (topological sort)
            execution_order = self._calculate_execution_order(pipeline)
            
            # Execute nodes in order
            for node_id in execution_order:
                node = next(n for n in pipeline.nodes if n.node_id == node_id)
                context["current_node"] = node_id
                
                node.status = "running"
                start_time = time.time()
                
                try:
                    # Execute node
                    result = await self._execute_node(node, context)
                    
                    # Store results
                    context["data_flow"][node_id] = result
                    
                    node.status = "completed"
                    node.execution_time = time.time() - start_time
                    
                except Exception as e:
                    node.status = "error"
                    node.error_message = str(e)
                    context["errors"].append({
                        "node_id": node_id,
                        "node_name": node.name,
                        "error": str(e)
                    })
                    
                    self.logger.error(f"Node execution failed: {node.name} - {e}")
                    break
                    
            # Finalize execution
            context["status"] = "completed" if not context["errors"] else "error"
            context["end_time"] = time.time()
            context["execution_time"] = context["end_time"] - context["start_time"]
            
            # Store execution history
            self.execution_history.append(context.copy())
            if len(self.execution_history) > self.config["execution_history_limit"]:
                self.execution_history.pop(0)
                
            # Save execution log
            self._save_execution_log(context)
            
        except Exception as e:
            context["status"] = "error"
            context["errors"].append({"error": str(e)})
            self.logger.error(f"Pipeline execution failed: {e}")
            
        finally:
            # Clean up active execution
            if context["execution_id"] in self.active_executions:
                del self.active_executions[context["execution_id"]]
                
    def _calculate_execution_order(self, pipeline: Pipeline) -> List[str]:
        """Calculate correct execution order using topological sort"""
        # Build dependency graph
        dependencies = {}
        for node in pipeline.nodes:
            dependencies[node.node_id] = set()
            
        for connection in pipeline.connections:
            dependencies[connection.target_node].add(connection.source_node)
            
        # Topological sort
        execution_order = []
        no_deps = [node_id for node_id, deps in dependencies.items() if not deps]
        
        while no_deps:
            current = no_deps.pop(0)
            execution_order.append(current)
            
            # Remove current node from dependencies
            for node_id in dependencies:
                if current in dependencies[node_id]:
                    dependencies[node_id].remove(current)
                    if not dependencies[node_id]:
                        no_deps.append(node_id)
                        
        return execution_order
        
    async def _execute_node(self, node: PipelineNode, context: Dict) -> Dict[str, Any]:
        """Execute individual pipeline node"""
        
        # Get input data
        input_data = {}
        pipeline = self.pipelines[context["pipeline_id"]]
        
        for connection in pipeline.connections:
            if connection.target_node == node.node_id:
                source_data = context["data_flow"].get(connection.source_node, {})
                input_data[connection.target_port] = source_data.get(connection.source_port)
                
        # Add initial input data for input nodes
        if not node.inputs and context["input_data"]:
            input_data.update(context["input_data"])
            
        # Execute based on node type
        if node.node_type == "file_input":
            return await self._execute_file_input(node, input_data)
        elif node.node_type == "database_input":
            return await self._execute_database_input(node, input_data)
        elif node.node_type == "api_input":
            return await self._execute_api_input(node, input_data)
        elif node.node_type == "data_transform":
            return await self._execute_data_transform(node, input_data)
        elif node.node_type == "ai_model":
            return await self._execute_ai_model(node, input_data)
        elif node.node_type == "data_validation":
            return await self._execute_data_validation(node, input_data)
        elif node.node_type == "condition":
            return await self._execute_condition(node, input_data)
        elif node.node_type == "file_output":
            return await self._execute_file_output(node, input_data)
        elif node.node_type == "database_output":
            return await self._execute_database_output(node, input_data)
        elif node.node_type == "api_output":
            return await self._execute_api_output(node, input_data)
        else:
            raise ValueError(f"Unknown node type: {node.node_type}")
            
    async def _execute_file_input(self, node: PipelineNode, input_data: Dict) -> Dict[str, Any]:
        """Execute file input node"""
        file_path = node.config["file_path"]
        file_format = node.config.get("file_format", "json")
        encoding = node.config.get("encoding", "utf-8")
        
        with open(file_path, 'r', encoding=encoding) as f:
            if file_format == "json":
                data = json.load(f)
            elif file_format == "csv":
                import csv
                reader = csv.DictReader(f)
                data = list(reader)
            else:
                data = f.read()
                
        return {"data": data}
        
    async def _execute_data_transform(self, node: PipelineNode, input_data: Dict) -> Dict[str, Any]:
        """Execute data transformation node"""
        transformation = node.config["transformation"]
        expression = node.config["expression"]
        language = node.config.get("language", "python")
        
        input_value = input_data.get("input", {})
        
        if language == "python":
            # SECURITY FIX: Removed dangerous exec() call
            # Python code execution must be done in a secure sandbox environment
            result = {"error": "Python code execution disabled for security - implement secure sandbox"}
            print("WARNING: Python code execution blocked for security reasons")
        else:
            # Placeholder for other languages
            result = input_value
            
        return {"output": result}
        
    async def _execute_ai_model(self, node: PipelineNode, input_data: Dict) -> Dict[str, Any]:
        """Execute AI model node"""
        model_type = node.config["model_type"] 
        model_path = node.config["model_path"]
        input_format = node.config.get("input_format", "json")
        
        input_value = input_data.get("input", {})
        
        # Simulate AI model execution
        await asyncio.sleep(0.5)  # Simulate processing time
        
        prediction = f"prediction_for_{hash(str(input_value))}"
        confidence = 0.85
        
        return {
            "prediction": prediction,
            "confidence": confidence
        }
        
    async def _execute_file_output(self, node: PipelineNode, input_data: Dict) -> Dict[str, Any]:
        """Execute file output node"""
        file_path = node.config["file_path"]
        file_format = node.config.get("file_format", "json")
        append_mode = node.config.get("append_mode", False)
        
        data = input_data.get("data", {})
        mode = "a" if append_mode else "w"
        
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, mode) as f:
            if file_format == "json":
                json.dump(data, f, indent=2)
            else:
                f.write(str(data))
                
        return {"status": "written", "file_path": file_path}
        
    # Placeholder implementations for other node types
    async def _execute_database_input(self, node: PipelineNode, input_data: Dict) -> Dict[str, Any]:
        return {"data": [{"id": 1, "name": "sample"}]}
        
    async def _execute_api_input(self, node: PipelineNode, input_data: Dict) -> Dict[str, Any]:
        return {"data": {"response": "api_data"}}
        
    async def _execute_data_validation(self, node: PipelineNode, input_data: Dict) -> Dict[str, Any]:
        return {"valid": input_data.get("input", {}), "invalid": []}
        
    async def _execute_condition(self, node: PipelineNode, input_data: Dict) -> Dict[str, Any]:
        # Simplified condition evaluation
        condition = node.config["condition"]
        input_value = input_data.get("input", {})
        
        # SECURITY FIX: Removed dangerous eval() call
        # Condition evaluation must use safe expression parser
        print(f"WARNING: Condition evaluation '{condition}' blocked for security")
        result = False  # Default to false for security
        
        if result:
            return {"true": input_value}
        else:
            return {"false": input_value}
            
    async def _execute_database_output(self, node: PipelineNode, input_data: Dict) -> Dict[str, Any]:
        return {"status": "inserted", "records": 1}
        
    async def _execute_api_output(self, node: PipelineNode, input_data: Dict) -> Dict[str, Any]:
        return {"response": {"status": "success"}}
        
    def _save_execution_log(self, context: Dict):
        """Save execution log to file"""
        try:
            log_dir = Path(self.config["storage"]["execution_logs"])
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / f"{context['execution_id']}.json"
            
            with open(log_file, 'w') as f:
                json.dump(context, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save execution log: {e}")
            
    def get_pipeline_status(self, pipeline_id: str) -> Dict:
        """Get pipeline status and statistics"""
        if pipeline_id not in self.pipelines:
            return {"error": "Pipeline not found"}
            
        pipeline = self.pipelines[pipeline_id]
        
        # Get execution history for this pipeline
        executions = [e for e in self.execution_history if e["pipeline_id"] == pipeline_id]
        
        # Calculate statistics
        total_executions = len(executions)
        successful_executions = len([e for e in executions if e["status"] == "completed"])
        failed_executions = len([e for e in executions if e["status"] == "error"])
        
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
        
        avg_execution_time = 0
        if executions:
            total_time = sum(e.get("execution_time", 0) for e in executions)
            avg_execution_time = total_time / len(executions)
            
        return {
            "pipeline_id": pipeline_id,
            "name": pipeline.name,
            "status": pipeline.status,
            "version": pipeline.version,
            "nodes": len(pipeline.nodes),
            "connections": len(pipeline.connections),
            "created_at": pipeline.created_at,
            "updated_at": pipeline.updated_at,
            "statistics": {
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "failed_executions": failed_executions,
                "success_rate": round(success_rate, 2),
                "avg_execution_time": round(avg_execution_time, 2)
            },
            "last_execution": executions[-1] if executions else None
        }
        
    async def create_web_interface(self):
        """Create web interface for pipeline builder"""
        app = web.Application()
        
        # Enable CORS if configured
        if self.config["web_interface"]["enable_cors"]:
            from aiohttp_cors import setup as cors_setup, ResourceOptions
            cors = cors_setup(app, defaults={
                "*": ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })
        
        # API endpoints
        async def get_pipelines(request):
            pipeline_list = []
            for pipeline in self.pipelines.values():
                pipeline_list.append({
                    "pipeline_id": pipeline.pipeline_id,
                    "name": pipeline.name,
                    "description": pipeline.description,
                    "status": pipeline.status,
                    "created_at": pipeline.created_at,
                    "updated_at": pipeline.updated_at,
                    "nodes": len(pipeline.nodes),
                    "connections": len(pipeline.connections)
                })
            return web.json_response(pipeline_list)
            
        async def get_pipeline(request):
            pipeline_id = request.match_info['pipeline_id']
            if pipeline_id not in self.pipelines:
                return web.json_response({"error": "Pipeline not found"}, status=404)
                
            pipeline = self.pipelines[pipeline_id]
            return web.json_response(asdict(pipeline))
            
        async def create_pipeline_endpoint(request):
            data = await request.json()
            name = data.get('name')
            description = data.get('description', '')
            
            if not name:
                return web.json_response({"error": "Name required"}, status=400)
                
            pipeline_id = self.create_pipeline(name, description)
            return web.json_response({"pipeline_id": pipeline_id})
            
        async def execute_pipeline_endpoint(request):
            pipeline_id = request.match_info['pipeline_id']
            data = await request.json() if request.can_read_body else {}
            input_data = data.get('input_data', {})
            
            try:
                execution_id = await self.execute_pipeline(pipeline_id, input_data)
                return web.json_response({"execution_id": execution_id})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=400)
                
        async def get_node_types(request):
            return web.json_response(self.node_registry.node_types)
            
        async def get_execution_status(request):
            execution_id = request.match_info['execution_id']
            
            # Check active executions
            if execution_id in self.active_executions:
                return web.json_response(self.active_executions[execution_id])
                
            # Check execution history
            for execution in self.execution_history:
                if execution['execution_id'] == execution_id:
                    return web.json_response(execution)
                    
            return web.json_response({"error": "Execution not found"}, status=404)
        
        # Serve static files for web interface
        async def serve_index(request):
            return web.Response(text=self.get_web_interface_html(), content_type='text/html')
            
        # Register routes
        app.router.add_get('/', serve_index)
        app.router.add_get('/api/pipelines', get_pipelines)
        app.router.add_get('/api/pipelines/{pipeline_id}', get_pipeline)
        app.router.add_post('/api/pipelines', create_pipeline_endpoint)
        app.router.add_post('/api/pipelines/{pipeline_id}/execute', execute_pipeline_endpoint)
        app.router.add_get('/api/node-types', get_node_types)
        app.router.add_get('/api/executions/{execution_id}', get_execution_status)
        
        # Setup CORS for all routes
        if self.config["web_interface"]["enable_cors"]:
            for route in list(app.router.routes()):
                cors.add(route)
                
        return app
        
    def get_web_interface_html(self) -> str:
        """Get HTML for web interface"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>QENEX Visual Pipeline Builder</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; margin: -20px -20px 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .pipeline-list { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .pipeline-item { padding: 15px; border-bottom: 1px solid #eee; cursor: pointer; }
        .pipeline-item:hover { background: #f8f9fa; }
        .btn { padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #2980b9; }
        .canvas { border: 1px solid #ddd; background: white; min-height: 400px; margin-top: 20px; }
        .node-palette { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .node-type { display: inline-block; padding: 8px 15px; margin: 5px; background: #ecf0f1; border-radius: 4px; cursor: pointer; }
        .node-type:hover { background: #bdc3c7; }
    </style>
</head>
<body>
    <div class="header">
        <h1>QENEX Visual Pipeline Builder</h1>
        <p>Drag-and-drop AI/Data processing pipeline creation</p>
    </div>
    
    <div class="container">
        <div class="node-palette">
            <h3>Node Types</h3>
            <div id="nodeTypes">Loading node types...</div>
        </div>
        
        <div class="pipeline-list">
            <h3>Pipelines</h3>
            <button class="btn" onclick="createPipeline()">Create New Pipeline</button>
            <div id="pipelineList">Loading pipelines...</div>
        </div>
        
        <div class="canvas" id="pipelineCanvas" style="display: none;">
            <h3>Pipeline Editor</h3>
            <p>Visual pipeline editor would be implemented here with a graph library like D3.js or vis.js</p>
        </div>
    </div>
    
    <script>
        // Load pipelines
        fetch('/api/pipelines')
            .then(response => response.json())
            .then(pipelines => {
                const container = document.getElementById('pipelineList');
                container.innerHTML = '';
                
                pipelines.forEach(pipeline => {
                    const item = document.createElement('div');
                    item.className = 'pipeline-item';
                    item.innerHTML = `
                        <h4>${pipeline.name}</h4>
                        <p>${pipeline.description}</p>
                        <small>Nodes: ${pipeline.nodes}, Status: ${pipeline.status}</small>
                    `;
                    item.onclick = () => openPipeline(pipeline.pipeline_id);
                    container.appendChild(item);
                });
            });
            
        // Load node types
        fetch('/api/node-types')
            .then(response => response.json())
            .then(nodeTypes => {
                const container = document.getElementById('nodeTypes');
                container.innerHTML = '';
                
                Object.entries(nodeTypes).forEach(([type, definition]) => {
                    const item = document.createElement('div');
                    item.className = 'node-type';
                    item.textContent = definition.name;
                    item.title = definition.description;
                    container.appendChild(item);
                });
            });
        
        function createPipeline() {
            const name = prompt('Pipeline name:');
            if (!name) return;
            
            fetch('/api/pipelines', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name, description: ''})
            })
            .then(response => response.json())
            .then(result => {
                alert('Pipeline created: ' + result.pipeline_id);
                location.reload();
            });
        }
        
        function openPipeline(pipelineId) {
            document.getElementById('pipelineCanvas').style.display = 'block';
            // Load and display pipeline in visual editor
        }
    </script>
</body>
</html>
        '''
        
    async def start(self):
        """Start the pipeline builder service"""
        self.logger.info("Starting QENEX Visual Pipeline Builder")
        
        # Create sample pipeline if none exist
        if not self.pipelines:
            sample_id = self.create_sample_pipeline()
            self.logger.info(f"Created sample pipeline: {sample_id}")
        
        # Create web interface
        app = await self.create_web_interface()
        
        # Start web server
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(
            runner,
            self.config["web_interface"]["host"],
            self.config["web_interface"]["port"]
        )
        await site.start()
        
        self.logger.info(f"Pipeline Builder web interface started on http://{self.config['web_interface']['host']}:{self.config['web_interface']['port']}")
        
        # Keep running
        try:
            while self.config.get('enabled', True):
                await asyncio.sleep(60)
                
        except asyncio.CancelledError:
            pass
        finally:
            await runner.cleanup()
            
    def create_sample_pipeline(self) -> str:
        """Create a sample pipeline for demonstration"""
        pipeline_id = self.create_pipeline("Sample Data Processing Pipeline", 
                                         "Demonstrates file input, transformation, and output")
        
        # Add file input node
        input_node = self.add_node(pipeline_id, "file_input", "Load Data", 
                                  {"x": 100, "y": 100}, 
                                  {"file_path": "/tmp/sample_input.json", "file_format": "json"})
        
        # Add transform node  
        transform_node = self.add_node(pipeline_id, "data_transform", "Process Data",
                                     {"x": 300, "y": 100},
                                     {"transformation": "custom", "expression": "result = [item for item in data if item.get('active', True)]", "language": "python"})
        
        # Add output node
        output_node = self.add_node(pipeline_id, "file_output", "Save Results",
                                   {"x": 500, "y": 100},
                                   {"file_path": "/tmp/sample_output.json", "file_format": "json"})
        
        # Connect nodes
        self.add_connection(pipeline_id, input_node, "data", transform_node, "input")
        self.add_connection(pipeline_id, transform_node, "output", output_node, "data")
        
        return pipeline_id
        
    def stop(self):
        """Stop the pipeline builder"""
        self.logger.info("Stopping QENEX Visual Pipeline Builder")
        self.config['enabled'] = False

async def main():
    """Main entry point"""
    pipeline_builder = QenexPipelineBuilder()
    
    try:
        await pipeline_builder.start()
    except KeyboardInterrupt:
        pipeline_builder.stop()
        print("\nPipeline builder stopped")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())