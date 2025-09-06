#!/bin/bash
# QENEX System Optimization Script - Reduces load and fixes memory issues

echo "🔧 QENEX System Optimization Starting..."

# Kill duplicate QENEX processes
echo "Cleaning up duplicate processes..."
for pid in $(ps aux | grep -E 'qenex|cicd|gitops|ai_engine' | grep -v grep | awk '{print $2}' | tail -n +10); do
    kill -9 $pid 2>/dev/null
done

# Clear system caches
echo "Clearing system caches..."
sync
echo 3 > /proc/sys/vm/drop_caches

# Configure memory limits
echo "Setting memory limits..."
cat > /etc/sysctl.d/99-qenex.conf <<EOF
# QENEX Memory Optimization
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 8192
fs.file-max = 2097152
EOF
sysctl -p /etc/sysctl.d/99-qenex.conf

# Add swap if not exists
if [ ! -f /swapfile ]; then
    echo "Creating 4GB swap file..."
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Set process limits
cat > /etc/security/limits.d/qenex.conf <<EOF
* soft nofile 65536
* hard nofile 65536
* soft nproc 32768
* hard nproc 32768
EOF

# Optimize Python processes
echo "Optimizing Python processes..."
export PYTHONOPTIMIZE=2
export PYTHONDONTWRITEBYTECODE=1

# Clean up old logs
find /opt/qenex-os/logs -type f -mtime +7 -delete 2>/dev/null
find /var/log -type f -name "*.log" -mtime +30 -delete 2>/dev/null

# Restart critical services
echo "Restarting services..."
systemctl restart nginx
killall update_api.py 2>/dev/null
python3 /opt/qenex-os/dashboard/update_api.py &

echo "✅ System optimization complete!"
echo "Current load: $(uptime | awk -F'load average:' '{print $2}')"
echo "Memory usage: $(free -h | grep Mem | awk '{print $3 "/" $2}')"