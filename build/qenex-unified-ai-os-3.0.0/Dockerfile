# QENEX Unified AI OS - Docker Image
FROM ubuntu:22.04

LABEL maintainer="QENEX Team"
LABEL version="3.0.0"
LABEL description="QENEX Unified AI Operating System with Autonomous CI/CD"

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV QENEX_ROOT=/opt/qenex-os
ENV PATH="$QENEX_ROOT/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    git \
    curl \
    wget \
    vim \
    htop \
    net-tools \
    iputils-ping \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && apt-get install -y docker-ce-cli && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl

# Install Helm
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Create QENEX directories
RUN mkdir -p $QENEX_ROOT/{kernel,cicd,ai,config,runtime,logs,data,bin}

# Copy QENEX OS files
COPY . $QENEX_ROOT/

# Install Python dependencies
WORKDIR $QENEX_ROOT
RUN pip3 install --no-cache-dir -r requirements.txt || true

# Create symbolic links for commands
RUN ln -s $QENEX_ROOT/kernel/qenex_shell.py /usr/local/bin/qenex-shell && \
    ln -s $QENEX_ROOT/kernel/unified_ai_os.py /usr/local/bin/qenex-os && \
    ln -s $QENEX_ROOT/cicd/unified_enhancements.py /usr/local/bin/qenex-enhance && \
    chmod +x /usr/local/bin/qenex-*

# Create non-root user
RUN useradd -m -s /bin/bash qenex && \
    chown -R qenex:qenex $QENEX_ROOT

# Expose ports
EXPOSE 8000 8080 8082 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Switch to non-root user
USER qenex
WORKDIR $QENEX_ROOT

# Default command
CMD ["python3", "kernel/unified_ai_os.py", "boot"]