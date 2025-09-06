#!/usr/bin/env python3
"""
QENEX CI/CD Pipeline Templates
Pre-configured templates for common workflows
Version: 1.0.0
"""

import os
import json
import yaml
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

class TemplateType(Enum):
    NODEJS = "nodejs"
    PYTHON = "python"
    GO = "golang"
    JAVA = "java"
    RUST = "rust"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    TERRAFORM = "terraform"
    REACT = "react"
    ANGULAR = "angular"
    VUE = "vue"
    DJANGO = "django"
    FLASK = "flask"
    SPRING = "spring"
    DOTNET = "dotnet"
    RUBY = "ruby"
    PHP = "php"
    MOBILE = "mobile"
    SERVERLESS = "serverless"
    MICROSERVICES = "microservices"

@dataclass
class PipelineTemplate:
    name: str
    type: TemplateType
    description: str
    stages: List[Dict]
    environment: Dict[str, str]
    cache_paths: List[str]
    artifacts: List[str]
    requirements: List[str]

class TemplateManager:
    """Manage and generate pipeline templates"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[TemplateType, PipelineTemplate]:
        """Initialize all pipeline templates"""
        templates = {}
        
        # Node.js Template
        templates[TemplateType.NODEJS] = PipelineTemplate(
            name="Node.js Application",
            type=TemplateType.NODEJS,
            description="Standard Node.js application with npm",
            stages=[
                {"name": "checkout", "type": "source"},
                {"name": "cache_restore", "type": "cache", "paths": ["node_modules"]},
                {"name": "install", "type": "setup", "commands": ["npm ci"]},
                {"name": "lint", "type": "quality", "commands": ["npm run lint"], "parallel": True},
                {"name": "test", "type": "test", "commands": ["npm test"], "parallel": True},
                {"name": "build", "type": "build", "commands": ["npm run build"]},
                {"name": "security_scan", "type": "security", "commands": ["npm audit"]},
                {"name": "cache_save", "type": "cache", "paths": ["node_modules"]},
                {"name": "package", "type": "package", "artifacts": ["dist/", "build/"]},
                {"name": "deploy", "type": "deploy"}
            ],
            environment={"NODE_ENV": "production"},
            cache_paths=["node_modules", ".npm"],
            artifacts=["dist/**/*", "build/**/*"],
            requirements=["node", "npm"]
        )
        
        # Python Template
        templates[TemplateType.PYTHON] = PipelineTemplate(
            name="Python Application",
            type=TemplateType.PYTHON,
            description="Python application with pip and pytest",
            stages=[
                {"name": "checkout", "type": "source"},
                {"name": "setup_venv", "type": "setup", "commands": ["python -m venv venv", "source venv/bin/activate"]},
                {"name": "cache_restore", "type": "cache", "paths": ["venv", ".pip"]},
                {"name": "install", "type": "setup", "commands": ["pip install -r requirements.txt"]},
                {"name": "lint", "type": "quality", "commands": ["flake8 .", "black --check ."], "parallel": True},
                {"name": "type_check", "type": "quality", "commands": ["mypy ."], "parallel": True},
                {"name": "test", "type": "test", "commands": ["pytest --cov=. --cov-report=xml"]},
                {"name": "security_scan", "type": "security", "commands": ["bandit -r .", "safety check"]},
                {"name": "build", "type": "build", "commands": ["python setup.py bdist_wheel"]},
                {"name": "cache_save", "type": "cache", "paths": ["venv", ".pip"]},
                {"name": "package", "type": "package", "artifacts": ["dist/"]},
                {"name": "deploy", "type": "deploy"}
            ],
            environment={"PYTHONPATH": ".", "PIP_CACHE_DIR": ".pip"},
            cache_paths=["venv", ".pip", ".pytest_cache"],
            artifacts=["dist/*.whl", "coverage.xml"],
            requirements=["python3", "pip"]
        )
        
        # Go Template
        templates[TemplateType.GO] = PipelineTemplate(
            name="Go Application",
            type=TemplateType.GO,
            description="Go application with modules",
            stages=[
                {"name": "checkout", "type": "source"},
                {"name": "cache_restore", "type": "cache", "paths": ["go/pkg/mod"]},
                {"name": "download", "type": "setup", "commands": ["go mod download"]},
                {"name": "lint", "type": "quality", "commands": ["golangci-lint run"], "parallel": True},
                {"name": "test", "type": "test", "commands": ["go test -v -race -coverprofile=coverage.out ./..."]},
                {"name": "build", "type": "build", "commands": ["go build -o app ."]},
                {"name": "security_scan", "type": "security", "commands": ["gosec ./..."]},
                {"name": "cache_save", "type": "cache", "paths": ["go/pkg/mod"]},
                {"name": "package", "type": "package", "artifacts": ["app"]},
                {"name": "deploy", "type": "deploy"}
            ],
            environment={"GO111MODULE": "on", "GOCACHE": "/tmp/go-cache"},
            cache_paths=["go/pkg/mod", "/tmp/go-cache"],
            artifacts=["app", "coverage.out"],
            requirements=["go"]
        )
        
        # Docker Template
        templates[TemplateType.DOCKER] = PipelineTemplate(
            name="Docker Container",
            type=TemplateType.DOCKER,
            description="Build and push Docker containers",
            stages=[
                {"name": "checkout", "type": "source"},
                {"name": "docker_login", "type": "setup", "commands": ["docker login -u $DOCKER_USER -p $DOCKER_PASS"]},
                {"name": "build", "type": "build", "commands": ["docker build -t $IMAGE_NAME:$CI_COMMIT_SHA ."]},
                {"name": "test", "type": "test", "commands": ["docker run --rm $IMAGE_NAME:$CI_COMMIT_SHA test"]},
                {"name": "scan", "type": "security", "commands": ["trivy image $IMAGE_NAME:$CI_COMMIT_SHA"]},
                {"name": "tag", "type": "package", "commands": [
                    "docker tag $IMAGE_NAME:$CI_COMMIT_SHA $IMAGE_NAME:latest",
                    "docker tag $IMAGE_NAME:$CI_COMMIT_SHA $IMAGE_NAME:$VERSION"
                ]},
                {"name": "push", "type": "deploy", "commands": [
                    "docker push $IMAGE_NAME:$CI_COMMIT_SHA",
                    "docker push $IMAGE_NAME:latest"
                ]}
            ],
            environment={"DOCKER_BUILDKIT": "1"},
            cache_paths=[],
            artifacts=["image.tar"],
            requirements=["docker"]
        )
        
        # Kubernetes Template
        templates[TemplateType.KUBERNETES] = PipelineTemplate(
            name="Kubernetes Deployment",
            type=TemplateType.KUBERNETES,
            description="Deploy to Kubernetes cluster",
            stages=[
                {"name": "checkout", "type": "source"},
                {"name": "validate", "type": "quality", "commands": ["kubectl apply --dry-run=client -f k8s/"]},
                {"name": "lint", "type": "quality", "commands": ["kubeval k8s/*.yaml"], "parallel": True},
                {"name": "security_scan", "type": "security", "commands": ["kubesec scan k8s/*.yaml"]},
                {"name": "deploy_staging", "type": "deploy", "commands": [
                    "kubectl apply -f k8s/ --namespace=staging",
                    "kubectl rollout status deployment/app -n staging"
                ]},
                {"name": "smoke_test", "type": "test", "commands": ["./scripts/smoke-test.sh staging"]},
                {"name": "deploy_prod", "type": "deploy", "commands": [
                    "kubectl apply -f k8s/ --namespace=production",
                    "kubectl rollout status deployment/app -n production"
                ], "manual": True}
            ],
            environment={"KUBECONFIG": "/etc/kubernetes/config"},
            cache_paths=[],
            artifacts=["k8s/*.yaml"],
            requirements=["kubectl", "helm"]
        )
        
        # React Template
        templates[TemplateType.REACT] = PipelineTemplate(
            name="React Application",
            type=TemplateType.REACT,
            description="React SPA with testing and optimization",
            stages=[
                {"name": "checkout", "type": "source"},
                {"name": "cache_restore", "type": "cache", "paths": ["node_modules"]},
                {"name": "install", "type": "setup", "commands": ["npm ci"]},
                {"name": "lint", "type": "quality", "commands": ["npm run lint"], "parallel": True},
                {"name": "test", "type": "test", "commands": ["npm test -- --coverage --watchAll=false"]},
                {"name": "build", "type": "build", "commands": ["npm run build"]},
                {"name": "analyze", "type": "quality", "commands": ["npm run analyze"], "parallel": True},
                {"name": "e2e", "type": "test", "commands": ["npm run e2e"]},
                {"name": "lighthouse", "type": "quality", "commands": ["lighthouse --output=json --output-path=./lighthouse.json"]},
                {"name": "cache_save", "type": "cache", "paths": ["node_modules"]},
                {"name": "deploy", "type": "deploy", "commands": ["aws s3 sync build/ s3://$BUCKET_NAME"]}
            ],
            environment={"NODE_ENV": "production", "CI": "true"},
            cache_paths=["node_modules", ".npm"],
            artifacts=["build/**/*", "coverage/**/*"],
            requirements=["node", "npm"]
        )
        
        # Django Template
        templates[TemplateType.DJANGO] = PipelineTemplate(
            name="Django Application",
            type=TemplateType.DJANGO,
            description="Django web application with migrations",
            stages=[
                {"name": "checkout", "type": "source"},
                {"name": "cache_restore", "type": "cache", "paths": ["venv"]},
                {"name": "install", "type": "setup", "commands": [
                    "python -m venv venv",
                    "source venv/bin/activate",
                    "pip install -r requirements.txt"
                ]},
                {"name": "migrate", "type": "setup", "commands": ["python manage.py migrate"]},
                {"name": "collect_static", "type": "build", "commands": ["python manage.py collectstatic --noinput"]},
                {"name": "test", "type": "test", "commands": ["python manage.py test"]},
                {"name": "coverage", "type": "test", "commands": ["coverage run --source='.' manage.py test", "coverage xml"]},
                {"name": "security", "type": "security", "commands": ["python manage.py check --deploy"]},
                {"name": "cache_save", "type": "cache", "paths": ["venv"]},
                {"name": "deploy", "type": "deploy"}
            ],
            environment={"DJANGO_SETTINGS_MODULE": "app.settings.production"},
            cache_paths=["venv", ".pip"],
            artifacts=["staticfiles/", "media/"],
            requirements=["python3", "pip", "postgresql"]
        )
        
        # Terraform Template
        templates[TemplateType.TERRAFORM] = PipelineTemplate(
            name="Terraform Infrastructure",
            type=TemplateType.TERRAFORM,
            description="Infrastructure as Code with Terraform",
            stages=[
                {"name": "checkout", "type": "source"},
                {"name": "init", "type": "setup", "commands": ["terraform init"]},
                {"name": "validate", "type": "quality", "commands": ["terraform validate"]},
                {"name": "fmt", "type": "quality", "commands": ["terraform fmt -check"], "parallel": True},
                {"name": "tflint", "type": "quality", "commands": ["tflint"], "parallel": True},
                {"name": "security", "type": "security", "commands": ["tfsec ."]},
                {"name": "plan", "type": "build", "commands": ["terraform plan -out=tfplan"]},
                {"name": "cost", "type": "quality", "commands": ["infracost breakdown --path tfplan"]},
                {"name": "apply", "type": "deploy", "commands": ["terraform apply tfplan"], "manual": True}
            ],
            environment={"TF_IN_AUTOMATION": "true"},
            cache_paths=[".terraform"],
            artifacts=["tfplan", "*.tfstate"],
            requirements=["terraform", "tflint", "tfsec"]
        )
        
        # Microservices Template
        templates[TemplateType.MICROSERVICES] = PipelineTemplate(
            name="Microservices Suite",
            type=TemplateType.MICROSERVICES,
            description="Multi-service deployment with orchestration",
            stages=[
                {"name": "checkout", "type": "source"},
                {"name": "detect_changes", "type": "setup", "commands": ["./scripts/detect-changes.sh"]},
                {"name": "build_services", "type": "build", "parallel": True, "matrix": [
                    {"service": "auth", "commands": ["cd services/auth && docker build -t auth:$VERSION ."]},
                    {"service": "api", "commands": ["cd services/api && docker build -t api:$VERSION ."]},
                    {"service": "web", "commands": ["cd services/web && docker build -t web:$VERSION ."]},
                    {"service": "worker", "commands": ["cd services/worker && docker build -t worker:$VERSION ."]}
                ]},
                {"name": "test_services", "type": "test", "parallel": True, "commands": ["docker-compose run tests"]},
                {"name": "integration_tests", "type": "test", "commands": ["./scripts/integration-tests.sh"]},
                {"name": "push_images", "type": "package", "commands": ["./scripts/push-images.sh"]},
                {"name": "deploy_staging", "type": "deploy", "commands": ["helm upgrade --install app ./chart -n staging"]},
                {"name": "smoke_test", "type": "test", "commands": ["./scripts/smoke-test.sh"]},
                {"name": "deploy_prod", "type": "deploy", "commands": ["helm upgrade --install app ./chart -n production"], "manual": True}
            ],
            environment={"COMPOSE_PROJECT_NAME": "microservices"},
            cache_paths=["vendor/", "node_modules/"],
            artifacts=["docker-compose.yaml", "chart/"],
            requirements=["docker", "docker-compose", "helm", "kubectl"]
        )
        
        # Serverless Template
        templates[TemplateType.SERVERLESS] = PipelineTemplate(
            name="Serverless Functions",
            type=TemplateType.SERVERLESS,
            description="Deploy serverless functions to cloud providers",
            stages=[
                {"name": "checkout", "type": "source"},
                {"name": "install", "type": "setup", "commands": ["npm install"]},
                {"name": "lint", "type": "quality", "commands": ["npm run lint"]},
                {"name": "test", "type": "test", "commands": ["npm test"]},
                {"name": "build", "type": "build", "commands": ["npm run build"]},
                {"name": "package", "type": "package", "commands": ["serverless package"]},
                {"name": "deploy_dev", "type": "deploy", "commands": ["serverless deploy --stage dev"]},
                {"name": "test_endpoints", "type": "test", "commands": ["npm run test:integration"]},
                {"name": "deploy_prod", "type": "deploy", "commands": ["serverless deploy --stage prod"], "manual": True}
            ],
            environment={"AWS_REGION": "us-east-1"},
            cache_paths=["node_modules", ".serverless"],
            artifacts=[".serverless/**/*"],
            requirements=["node", "serverless"]
        )
        
        return templates
    
    def get_template(self, template_type: TemplateType) -> PipelineTemplate:
        """Get a specific template"""
        return self.templates.get(template_type)
    
    def list_templates(self) -> List[Dict]:
        """List all available templates"""
        return [
            {
                "type": t.value,
                "name": template.name,
                "description": template.description,
                "stages": len(template.stages),
                "requirements": template.requirements
            }
            for t, template in self.templates.items()
        ]
    
    def generate_pipeline_config(self, template_type: TemplateType, customizations: Dict = None) -> Dict:
        """Generate pipeline configuration from template"""
        template = self.get_template(template_type)
        if not template:
            raise ValueError(f"Template {template_type} not found")
        
        config = {
            "name": template.name,
            "type": template.type.value,
            "stages": template.stages,
            "environment": template.environment,
            "cache": {
                "paths": template.cache_paths
            },
            "artifacts": template.artifacts
        }
        
        # Apply customizations
        if customizations:
            if "name" in customizations:
                config["name"] = customizations["name"]
            if "environment" in customizations:
                config["environment"].update(customizations["environment"])
            if "stages" in customizations:
                # Merge or replace stages
                config["stages"] = customizations["stages"]
        
        return config
    
    def generate_yaml(self, template_type: TemplateType, customizations: Dict = None) -> str:
        """Generate YAML pipeline configuration"""
        config = self.generate_pipeline_config(template_type, customizations)
        return yaml.dump(config, default_flow_style=False)
    
    def generate_json(self, template_type: TemplateType, customizations: Dict = None) -> str:
        """Generate JSON pipeline configuration"""
        config = self.generate_pipeline_config(template_type, customizations)
        return json.dumps(config, indent=2)
    
    def detect_project_type(self, project_path: str) -> TemplateType:
        """Auto-detect project type based on files"""
        files = os.listdir(project_path)
        
        # Check for specific files
        if "package.json" in files:
            with open(os.path.join(project_path, "package.json"), 'r') as f:
                pkg = json.load(f)
                deps = pkg.get("dependencies", {})
                
                if "react" in deps:
                    return TemplateType.REACT
                elif "angular" in deps or "@angular/core" in deps:
                    return TemplateType.ANGULAR
                elif "vue" in deps:
                    return TemplateType.VUE
                else:
                    return TemplateType.NODEJS
        
        elif "requirements.txt" in files or "setup.py" in files:
            if "manage.py" in files:
                return TemplateType.DJANGO
            elif "app.py" in files or "application.py" in files:
                return TemplateType.FLASK
            else:
                return TemplateType.PYTHON
        
        elif "go.mod" in files:
            return TemplateType.GO
        
        elif "pom.xml" in files:
            return TemplateType.JAVA
        
        elif "Cargo.toml" in files:
            return TemplateType.RUST
        
        elif "Gemfile" in files:
            return TemplateType.RUBY
        
        elif "composer.json" in files:
            return TemplateType.PHP
        
        elif "Dockerfile" in files:
            return TemplateType.DOCKER
        
        elif "terraform" in files or any(f.endswith(".tf") for f in files):
            return TemplateType.TERRAFORM
        
        elif "serverless.yml" in files or "serverless.yaml" in files:
            return TemplateType.SERVERLESS
        
        elif "k8s" in files or "kubernetes" in files:
            return TemplateType.KUBERNETES
        
        elif "docker-compose.yml" in files or "docker-compose.yaml" in files:
            return TemplateType.MICROSERVICES
        
        else:
            return TemplateType.NODEJS  # Default

# Global template manager
template_manager = None

def get_template_manager():
    """Get or create template manager"""
    global template_manager
    if template_manager is None:
        template_manager = TemplateManager()
    return template_manager

if __name__ == '__main__':
    manager = get_template_manager()
    
    # List all templates
    print("Available Pipeline Templates:")
    print("=" * 50)
    for template in manager.list_templates():
        print(f"- {template['type']}: {template['name']}")
        print(f"  {template['description']}")
        print(f"  Stages: {template['stages']}, Requirements: {', '.join(template['requirements'])}")
        print()