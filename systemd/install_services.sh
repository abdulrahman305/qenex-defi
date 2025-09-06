#!/bin/bash
# Install QENEX systemd services

echo "📦 Installing QENEX systemd services..."

# Create service files
cat > /etc/systemd/system/qenex-api.service <<EOF
[Unit]
Description=QENEX Unified AI OS API Service
After=network.target
Wants=redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qenex-os
Environment="PYTHONPATH=/opt/qenex-os"
Environment="QENEX_ENV=production"
ExecStart=/usr/bin/python3 /opt/qenex-os/kernel/unified_ai_os.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/qenex-os/logs/api.log
StandardError=append:/opt/qenex-os/logs/api-error.log
LimitNOFILE=65536
MemoryLimit=2G

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/qenex-webhook.service <<EOF
[Unit]
Description=QENEX Webhook Handler Service
After=network.target qenex-api.service
Wants=qenex-api.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qenex-os
ExecStart=/usr/bin/python3 /opt/qenex-os/webhooks/webhook_handler.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/qenex-os/logs/webhook.log
StandardError=append:/opt/qenex-os/logs/webhook-error.log

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/qenex-metrics.service <<EOF
[Unit]
Description=QENEX Prometheus Metrics Exporter
After=network.target qenex-api.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qenex-os
ExecStart=/usr/bin/python3 /opt/qenex-os/monitoring/prometheus_exporter.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/qenex-autoscaler.service <<EOF
[Unit]
Description=QENEX Auto-Scaler Service
After=network.target docker.service qenex-api.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qenex-os
ExecStart=/usr/bin/python3 /opt/qenex-os/scaling/auto_scaler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/qenex-stats.service <<EOF
[Unit]
Description=QENEX Stats Updater Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qenex-os
ExecStart=/usr/bin/python3 /opt/qenex-os/dashboard/update_api.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/qenex-backup.service <<EOF
[Unit]
Description=QENEX Backup Service

[Service]
Type=oneshot
User=root
ExecStart=/opt/qenex-os/scripts/backup_system.sh
EOF

cat > /etc/systemd/system/qenex-backup.timer <<EOF
[Unit]
Description=Run QENEX Backup daily
Requires=qenex-backup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

cat > /etc/systemd/system/qenex-cleanup.service <<EOF
[Unit]
Description=QENEX Cleanup Service

[Service]
Type=oneshot
User=root
ExecStart=/opt/qenex-os/scripts/cleanup.sh
EOF

cat > /etc/systemd/system/qenex-cleanup.timer <<EOF
[Unit]
Description=Run QENEX Cleanup hourly
Requires=qenex-cleanup.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable services
echo "Enabling services..."
systemctl enable qenex-api.service
systemctl enable qenex-webhook.service
systemctl enable qenex-metrics.service
systemctl enable qenex-autoscaler.service
systemctl enable qenex-stats.service
systemctl enable qenex-backup.timer
systemctl enable qenex-cleanup.timer

# Start services
echo "Starting services..."
systemctl start qenex-stats.service
systemctl start qenex-backup.timer
systemctl start qenex-cleanup.timer

echo "✅ QENEX systemd services installed!"
echo ""
echo "Service management commands:"
echo "  systemctl status qenex-api"
echo "  systemctl start qenex-api"
echo "  systemctl stop qenex-api"
echo "  systemctl restart qenex-api"
echo "  journalctl -u qenex-api -f"
echo ""
echo "View all QENEX services:"
echo "  systemctl list-units 'qenex-*'"