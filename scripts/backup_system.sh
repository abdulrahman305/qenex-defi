#!/bin/bash
# QENEX Automated Backup System

BACKUP_DIR="/opt/qenex-os/backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="qenex-backup-${TIMESTAMP}"
RETENTION_DAYS=30

echo "📦 Starting QENEX backup..."

# Create backup directory
mkdir -p ${BACKUP_DIR}

# Database backup
echo "Backing up databases..."
sqlite3 /opt/qenex-os/data/qenex.db ".backup ${BACKUP_DIR}/${BACKUP_NAME}-db.sqlite"
sqlite3 /opt/qenex-os/data/metrics.db ".backup ${BACKUP_DIR}/${BACKUP_NAME}-metrics.sqlite"
sqlite3 /opt/qenex-os/data/webhooks.db ".backup ${BACKUP_DIR}/${BACKUP_NAME}-webhooks.sqlite"

# Configuration backup
echo "Backing up configuration..."
tar -czf ${BACKUP_DIR}/${BACKUP_NAME}-config.tar.gz \
    /opt/qenex-os/config \
    /opt/qenex-os/docker \
    /etc/nginx/sites-available/qenex* \
    2>/dev/null

# Code backup
echo "Backing up code..."
tar -czf ${BACKUP_DIR}/${BACKUP_NAME}-code.tar.gz \
    /opt/qenex-os/*.py \
    /opt/qenex-os/kernel \
    /opt/qenex-os/cicd \
    /opt/qenex-os/core \
    /opt/qenex-os/auth \
    /opt/qenex-os/webhooks \
    /opt/qenex-os/monitoring \
    /opt/qenex-os/scaling \
    /opt/qenex-os/database \
    2>/dev/null

# Dashboard backup
echo "Backing up dashboard..."
tar -czf ${BACKUP_DIR}/${BACKUP_NAME}-dashboard.tar.gz \
    /opt/qenex-os/dashboard \
    2>/dev/null

# Create master backup archive
echo "Creating master backup..."
tar -czf ${BACKUP_DIR}/${BACKUP_NAME}-full.tar.gz \
    ${BACKUP_DIR}/${BACKUP_NAME}-*.{sqlite,tar.gz} \
    2>/dev/null

# Upload to cloud storage (optional)
if [ -n "$AWS_BACKUP_BUCKET" ]; then
    echo "Uploading to AWS S3..."
    aws s3 cp ${BACKUP_DIR}/${BACKUP_NAME}-full.tar.gz s3://${AWS_BACKUP_BUCKET}/qenex/
fi

# Cleanup old backups
echo "Cleaning up old backups..."
find ${BACKUP_DIR} -name "qenex-backup-*.tar.gz" -mtime +${RETENTION_DAYS} -delete

# Generate backup report
cat > ${BACKUP_DIR}/latest-backup.json <<EOF
{
  "timestamp": "${TIMESTAMP}",
  "backup_name": "${BACKUP_NAME}",
  "size": "$(du -sh ${BACKUP_DIR}/${BACKUP_NAME}-full.tar.gz | cut -f1)",
  "databases": ["qenex.db", "metrics.db", "webhooks.db"],
  "retention_days": ${RETENTION_DAYS},
  "location": "${BACKUP_DIR}/${BACKUP_NAME}-full.tar.gz"
}
EOF

echo "✅ Backup complete: ${BACKUP_DIR}/${BACKUP_NAME}-full.tar.gz"
echo "Size: $(du -sh ${BACKUP_DIR}/${BACKUP_NAME}-full.tar.gz | cut -f1)"

# Cleanup temporary files
rm -f ${BACKUP_DIR}/${BACKUP_NAME}-*.{sqlite,tar.gz}