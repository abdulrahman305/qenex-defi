#!/bin/bash
# QENEX Automated Cleanup Script

echo "[$(date)] Starting QENEX cleanup..."

# Log rotation and cleanup
echo "Cleaning up logs..."
find /opt/qenex-os/logs -name "*.log" -type f -mtime +7 -exec gzip {} \;
find /opt/qenex-os/logs -name "*.gz" -type f -mtime +30 -delete
find /var/log -name "*.log.[0-9]*" -type f -mtime +30 -delete

# Clean up old pipeline data
echo "Cleaning up old pipeline data..."
sqlite3 /opt/qenex-os/data/qenex.db <<EOF
DELETE FROM pipelines WHERE created_at < datetime('now', '-30 days') AND status IN ('success', 'failed', 'cancelled');
DELETE FROM pipeline_stages WHERE pipeline_id NOT IN (SELECT id FROM pipelines);
DELETE FROM metrics WHERE timestamp < datetime('now', '-7 days');
DELETE FROM audit_log WHERE timestamp < datetime('now', '-90 days');
VACUUM;
EOF

# Clean up Docker resources
if command -v docker &> /dev/null; then
    echo "Cleaning up Docker resources..."
    docker system prune -af --volumes --filter "until=72h" 2>/dev/null || true
    docker image prune -af --filter "until=168h" 2>/dev/null || true
fi

# Clean up temporary files
echo "Cleaning up temporary files..."
find /tmp -type f -atime +2 -delete 2>/dev/null || true
find /opt/qenex-os/tmp -type f -atime +1 -delete 2>/dev/null || true

# Clean up cache directories
echo "Cleaning up cache..."
find /opt/qenex-os/cache -type f -atime +7 -delete 2>/dev/null || true
rm -rf /root/.cache/pip/*
rm -rf /tmp/npm-*

# Clean up old backups (keep last 30 days)
echo "Cleaning up old backups..."
find /opt/qenex-os/backups -name "*.tar.gz" -type f -mtime +30 -delete 2>/dev/null || true

# Clean APT cache
echo "Cleaning APT cache..."
apt-get clean
apt-get autoremove -y
apt-get autoclean

# Clear systemd journal logs older than 7 days
echo "Cleaning systemd journals..."
journalctl --vacuum-time=7d

# Monitor disk usage
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "WARNING: Disk usage is at ${DISK_USAGE}%"
    # Aggressive cleanup
    find /opt/qenex-os/logs -name "*.log" -type f -mtime +3 -delete
    docker system prune -af --volumes 2>/dev/null || true
fi

# Memory cleanup
echo "Clearing memory caches..."
sync
echo 1 > /proc/sys/vm/drop_caches

echo "[$(date)] QENEX cleanup completed"

# Report cleanup results
FREED_SPACE=$(du -sh /opt/qenex-os/logs | cut -f1)
echo "Freed space in logs: $FREED_SPACE"