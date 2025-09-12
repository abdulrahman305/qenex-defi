# QENEX Unified AI Operating System

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/qenex/unified-ai-os)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

## 🚀 Overview

QENEX Unified AI OS is a revolutionary autonomous operating system that combines artificial intelligence, CI/CD automation, and self-healing capabilities into a single, cohesive platform. It features continuous learning, predictive analytics, and intelligent resource management.

### Key Features

- **🤖 AI-Driven Orchestration**: Autonomous decision-making with continuous learning
- **🔄 Complete CI/CD Platform**: GitOps, pipelines, and distributed execution
- **🛡️ Enterprise Security**: AES-256 encryption, RBAC, and audit logging
- **📊 Real-time Monitoring**: Dashboard, metrics, and observability
- **🔧 Self-Healing**: Automatic issue detection and resolution
- **🌐 Multi-Cloud Ready**: Deploy anywhere - AWS, GCP, Azure, or on-premise
- **📦 20+ Pipeline Templates**: Pre-configured for all major languages
- **🔌 Extensive Integrations**: GitHub, GitLab, Slack, Kubernetes, and more

## 📋 Requirements

### System Requirements
- **OS**: Linux/Unix (Ubuntu 20.04+, CentOS 8+, Debian 10+)
- **CPU**: 4+ cores recommended
- **Memory**: 8GB minimum, 16GB recommended
- **Disk**: 50GB minimum free space
- **Python**: 3.8 or higher

### Optional Requirements
- Docker (for containerized deployments)
- Kubernetes (for orchestration)
- Git (for version control)

## 🔧 Installation

### Quick Install

```bash
curl -fsSL https://get.qenex.ai/install | sudo bash
```

### Manual Installation

1. **Download the package:**
```bash
wget https://github.com/qenex/unified-ai-os/releases/latest/download/qenex-unified-ai-os-3.0.0.tar.gz
tar -xzf qenex-unified-ai-os-3.0.0.tar.gz
cd qenex-unified-ai-os-3.0.0
```

2. **Run the installer:**
```bash
sudo ./install.sh
```

3. **Start QENEX OS:**
```bash
qenex boot
```

### Docker Installation

```bash
docker pull qenex/unified-ai-os:latest
docker run -d \
  --name qenex-os \
  -p 8080:8080 \
  -p 8000:8000 \
  -p 8082:8082 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  qenex/unified-ai-os:latest
```

### Kubernetes Deployment

```bash
kubectl apply -f https://raw.githubusercontent.com/qenex/unified-ai-os/main/k8s/deployment.yaml
```

## 🚀 Getting Started

### 1. Access the QENEX Shell

```bash
qenex-shell
```

### 2. Basic Commands

```bash
# System commands
status              # Show system status
services            # List running services
kernel              # Kernel information

# CI/CD commands
cicd list           # List pipelines
cicd trigger app /path/to/repo  # Create pipeline
cicd ai status      # AI engine status

# GitOps commands
cicd gitops add https://github.com/user/repo
cicd gitops sync app-name
cicd gitops list
```

### 3. Web Interfaces

- **Dashboard**: https://abdulrahman305.github.io/qenex-docs
- **API Documentation**: https://abdulrahman305.github.io/qenex-docs
- **Metrics**: https://abdulrahman305.github.io/qenex-docs

## 🏗️ Architecture

```
QENEX Unified AI OS
├── Kernel Layer
│   ├── unified_ai_os.py       # Core OS kernel
│   ├── qenex_shell.py          # Interactive shell
│   └── qenex_core.py           # System core
├── CI/CD Layer
│   ├── autonomous_cicd.py      # Pipeline engine
│   ├── gitops_controller.py    # GitOps management
│   ├── ai_autonomous_engine.py # AI decision engine
│   └── unified_enhancements.py # Enhancement system
├── Service Layer
│   ├── dashboard_server.py     # Web dashboard
│   ├── api_server.py           # REST API
│   ├── webhook_server.py       # Webhook handler
│   └── distributed_executor.py # Distributed execution
└── Storage Layer
    ├── secret_manager.py        # Secret management
    ├── cache_manager.py         # Caching system
    └── persistence.py           # Data persistence
```

## 🔐 Security

QENEX OS implements multiple security layers:

- **Encryption**: AES-256 for secrets at rest
- **Authentication**: JWT tokens and API keys
- **Authorization**: Role-based access control (RBAC)
- **Audit**: Complete audit trail of all operations
- **Network**: TLS/SSL for all communications
- **Compliance**: SOC2, HIPAA, GDPR ready

## 🤖 AI Features

### Continuous Learning
The AI engine continuously learns from:
- Pipeline execution patterns
- Resource usage metrics
- Failure scenarios
- User interactions

### Predictive Analytics
- Failure prediction before it happens
- Resource requirement forecasting
- Optimal deployment strategy selection
- Performance bottleneck identification

### Self-Healing
- Automatic issue detection
- Intelligent remediation
- Rollback on failures
- Resource rebalancing

## 📊 Monitoring & Observability

### Metrics Export
Prometheus-compatible metrics available at:
```
https://abdulrahman305.github.io/qenex-docs
```

### Logging
All logs stored in `/opt/qenex-os/logs/`

### Tracing
OpenTelemetry support for distributed tracing

## 🔌 Integrations

### Version Control
- GitHub
- GitLab
- Bitbucket
- Gitea

### Cloud Providers
- AWS
- Google Cloud Platform
- Microsoft Azure
- DigitalOcean

### Container Platforms
- Docker
- Kubernetes
- OpenShift
- Rancher

### Communication
- Slack
- Discord
- Microsoft Teams
- Email

## 📚 Documentation

### Pipeline Templates

QENEX includes templates for:
- Node.js
- Python
- Go
- Java
- Rust
- Docker
- Kubernetes
- Terraform
- React/Angular/Vue
- Microservices

Example:
```python
from pipeline_templates import get_template_manager

manager = get_template_manager()
config = manager.generate_pipeline_config('nodejs')
```

### API Reference

Full API documentation available at:
- Interactive: https://abdulrahman305.github.io/qenex-docs
- OpenAPI spec: https://abdulrahman305.github.io/qenex-docs

## 🛠️ Configuration

Configuration file: `/opt/qenex-os/config/qenex.yaml`

```yaml
system:
  mode: production
  auto_start: true
  
ai:
  enabled: true
  continuous_learning: true
  
cicd:
  dashboard_port: 8080
  api_port: 8000
  
security:
  encryption: true
  audit_logging: true
```

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use:**
```bash
# Change ports in config/qenex.yaml
cicd:
  dashboard_port: 8081
  api_port: 8001
```

2. **Permission denied:**
```bash
sudo chown -R $USER:$USER /opt/qenex-os
```

3. **Service won't start:**
```bash
# Check logs
tail -f /opt/qenex-os/logs/qenex.log

# Restart service
sudo systemctl restart qenex-os
```

### Debug Mode

```bash
qenex-os boot --mode development
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- The open-source community
- All contributors and users
- AI/ML research community

## 📞 Support

- **Documentation**: https://abdulrahman305.github.io/qenex-docs
- **Issues**: https://github.com/qenex/unified-ai-os/issues
- **Discord**: https://discord.gg/qenex
- **Email**: ceo@qenex.ai

## 🚦 Status

- Build: ![Build Status](https://img.shields.io/badge/build-passing-green.svg)
- Tests: ![Test Status](https://img.shields.io/badge/tests-passing-green.svg)
- Coverage: ![Coverage](https://img.shields.io/badge/coverage-85%25-yellow.svg)

---

**QENEX Unified AI OS** - The Future of Autonomous Operations

*Powered by AI, Driven by Innovation*