# QENEX Unified AI OS - Docker Image
FROM ubuntu:22.04

LABEL maintainer="QENEX Team"
LABEL version="5.0.0"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3.11 python3-pip nginx redis-server curl wget \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /opt/qenex-os/{data,logs,cache}

WORKDIR /opt/qenex-os
COPY . /opt/qenex-os/

# Install Python packages
RUN pip3 install aiohttp psutil redis pyyaml requests

# Configure nginx
RUN rm -f /etc/nginx/sites-enabled/default

# Expose ports
EXPOSE 80 8000 8001 8002

# Start command
CMD ["python3", "/opt/qenex-os/qenex_single_unified.py"]
