#!/usr/bin/env python3
"""
QENEX Backup and Recovery System
Comprehensive data protection with automated backup, versioning, and disaster recovery
"""

import asyncio
import json
import time
import shutil
import tarfile
import gzip
import hashlib
import sqlite3
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import boto3
from cryptography.fernet import Fernet

@dataclass
class BackupJob:
    """Backup job configuration"""
    name: str
    source_path: str
    backup_type: str  # full, incremental, differential
    schedule: str     # cron-like: "0 2 * * *" (daily at 2 AM)
    retention_days: int
    compression: bool
    encryption: bool
    cloud_sync: bool
    
@dataclass  
class BackupRecord:
    """Backup record for tracking"""
    job_name: str
    backup_id: str
    timestamp: float
    backup_type: str
    source_path: str
    backup_path: str
    size_bytes: int
    checksum: str
    status: str  # success, failed, in_progress
    error_message: Optional[str] = None

class QenexBackupSystem:
    """Advanced backup and recovery system"""
    
    def __init__(self, config_path: str = "/opt/qenex-os/config/backup.json"):
        self.config_path = config_path
        self.backup_root = Path("/opt/qenex-os/backups")
        self.db_path = "/opt/qenex-os/data/backup_records.db"
        self.encryption_key_path = "/opt/qenex-os/.backup_encryption_key"
        
        # Create directories
        self.backup_root.mkdir(parents=True, exist_ok=True)
        Path("/opt/qenex-os/data").mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/opt/qenex-os/logs/backup.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('QenexBackupSystem')
        
        # Initialize components
        self.load_config()
        self.init_database()
        self.init_encryption()
        self.init_cloud_storage()
        
    def load_config(self):
        """Load backup configuration"""
        default_config = {
            "enabled": True,
            "max_concurrent_jobs": 3,
            "default_retention_days": 30,
            "backup_jobs": [
                {
                    "name": "qenex_system",
                    "source_path": "/opt/qenex-os",
                    "backup_type": "incremental",
                    "schedule": "0 2 * * *",
                    "retention_days": 30,
                    "compression": True,
                    "encryption": True,
                    "cloud_sync": True
                },
                {
                    "name": "qenex_data",
                    "source_path": "/opt/qenex-os/data",
                    "backup_type": "full",
                    "schedule": "0 1 * * 0",  # Weekly
                    "retention_days": 90,
                    "compression": True,
                    "encryption": True,
                    "cloud_sync": True
                },
                {
                    "name": "qenex_configs",
                    "source_path": "/opt/qenex-os/config",
                    "backup_type": "full",
                    "schedule": "0 3 * * *",
                    "retention_days": 60,
                    "compression": True,
                    "encryption": True,
                    "cloud_sync": False
                }
            ],
            "cloud_storage": {
                "provider": "s3",
                "bucket": "qenex-backups",
                "region": "us-east-1",
                "access_key_id": "",
                "secret_access_key": "",
                "encryption": True
            },
            "notifications": {
                "email": "ceo@qenex.ai",
                "webhook": "https://hooks.slack.com/services/..."
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
            
    def init_database(self):
        """Initialize backup records database"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS backup_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name TEXT NOT NULL,
                    backup_id TEXT UNIQUE NOT NULL,
                    timestamp REAL NOT NULL,
                    backup_type TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    backup_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    checksum TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT
                )
            ''')
            
            self.conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_backup_timestamp 
                ON backup_records(timestamp)
            ''')
            
            self.conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_backup_job_name 
                ON backup_records(job_name)
            ''')
            
            self.conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            
    def init_encryption(self):
        """Initialize encryption for backups"""
        try:
            if Path(self.encryption_key_path).exists():
                with open(self.encryption_key_path, 'rb') as f:
                    self.encryption_key = f.read()
            else:
                # Generate new encryption key
                self.encryption_key = Fernet.generate_key()
                with open(self.encryption_key_path, 'wb') as f:
                    f.write(self.encryption_key)
                # Secure the key file
                subprocess.run(['chmod', '600', self.encryption_key_path])
                
            self.cipher = Fernet(self.encryption_key)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize encryption: {e}")
            self.cipher = None
            
    def init_cloud_storage(self):
        """Initialize cloud storage client"""
        try:
            cloud_config = self.config.get("cloud_storage", {})
            if cloud_config.get("provider") == "s3":
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=cloud_config.get("access_key_id"),
                    aws_secret_access_key=cloud_config.get("secret_access_key"),
                    region_name=cloud_config.get("region", "us-east-1")
                )
            else:
                self.s3_client = None
        except Exception as e:
            self.logger.warning(f"Failed to initialize cloud storage: {e}")
            self.s3_client = None
            
    def generate_backup_id(self, job_name: str) -> str:
        """Generate unique backup ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{job_name}_{timestamp}_{int(time.time())}"
        
    def calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
            
    def create_backup_archive(self, job: BackupJob, backup_id: str) -> Tuple[str, int]:
        """Create backup archive"""
        backup_filename = f"{backup_id}.tar"
        if job.compression:
            backup_filename += ".gz"
        if job.encryption:
            backup_filename += ".enc"
            
        backup_path = self.backup_root / backup_filename
        
        try:
            # Create tar archive
            tar_mode = "w:gz" if job.compression else "w"
            
            with tarfile.open(backup_path if not job.encryption else str(backup_path) + ".tmp", tar_mode) as tar:
                source_path = Path(job.source_path)
                
                if job.backup_type == "incremental":
                    # Get last backup timestamp
                    last_backup_time = self.get_last_backup_time(job.name)
                    
                    # Only include modified files
                    for item in source_path.rglob("*"):
                        if item.is_file():
                            try:
                                if item.stat().st_mtime > last_backup_time:
                                    arcname = str(item.relative_to(source_path.parent))
                                    tar.add(str(item), arcname=arcname)
                            except Exception as e:
                                self.logger.warning(f"Skipping {item}: {e}")
                else:
                    # Full backup
                    arcname = source_path.name
                    tar.add(str(source_path), arcname=arcname)
                    
            # Encrypt if required
            if job.encryption and self.cipher:
                temp_path = str(backup_path) + ".tmp"
                with open(temp_path, 'rb') as f:
                    encrypted_data = self.cipher.encrypt(f.read())
                
                with open(backup_path, 'wb') as f:
                    f.write(encrypted_data)
                    
                Path(temp_path).unlink()
                
            backup_size = backup_path.stat().st_size
            return str(backup_path), backup_size
            
        except Exception as e:
            self.logger.error(f"Failed to create backup archive: {e}")
            if backup_path.exists():
                backup_path.unlink()
            raise
            
    def get_last_backup_time(self, job_name: str) -> float:
        """Get timestamp of last successful backup"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT MAX(timestamp) FROM backup_records 
                WHERE job_name = ? AND status = 'success'
            ''', (job_name,))
            
            result = cursor.fetchone()
            return result[0] if result[0] else 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to get last backup time: {e}")
            return 0.0
            
    def upload_to_cloud(self, local_path: str, backup_id: str) -> bool:
        """Upload backup to cloud storage"""
        if not self.s3_client:
            return False
            
        try:
            cloud_config = self.config.get("cloud_storage", {})
            bucket = cloud_config.get("bucket")
            
            if not bucket:
                return False
                
            key = f"qenex-backups/{backup_id}/{Path(local_path).name}"
            
            self.logger.info(f"Uploading {local_path} to cloud storage")
            self.s3_client.upload_file(local_path, bucket, key)
            
            self.logger.info(f"Successfully uploaded to s3://{bucket}/{key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload to cloud: {e}")
            return False
            
    def perform_backup(self, job: BackupJob) -> BackupRecord:
        """Perform a single backup job"""
        backup_id = self.generate_backup_id(job.name)
        start_time = time.time()
        
        self.logger.info(f"Starting backup job: {job.name} ({job.backup_type})")
        
        record = BackupRecord(
            job_name=job.name,
            backup_id=backup_id,
            timestamp=start_time,
            backup_type=job.backup_type,
            source_path=job.source_path,
            backup_path="",
            size_bytes=0,
            checksum="",
            status="in_progress"
        )
        
        try:
            # Check if source exists
            if not Path(job.source_path).exists():
                raise FileNotFoundError(f"Source path does not exist: {job.source_path}")
                
            # Create backup archive
            backup_path, backup_size = self.create_backup_archive(job, backup_id)
            
            # Calculate checksum
            checksum = self.calculate_checksum(backup_path)
            
            # Update record
            record.backup_path = backup_path
            record.size_bytes = backup_size
            record.checksum = checksum
            
            # Upload to cloud if configured
            if job.cloud_sync:
                cloud_success = self.upload_to_cloud(backup_path, backup_id)
                if not cloud_success:
                    self.logger.warning(f"Cloud upload failed for {backup_id}")
                    
            record.status = "success"
            duration = time.time() - start_time
            
            self.logger.info(f"Backup completed: {job.name} ({backup_size} bytes, {duration:.1f}s)")
            
        except Exception as e:
            record.status = "failed"
            record.error_message = str(e)
            self.logger.error(f"Backup failed for {job.name}: {e}")
            
        # Save record to database
        self.save_backup_record(record)
        
        return record
        
    def save_backup_record(self, record: BackupRecord):
        """Save backup record to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO backup_records 
                (job_name, backup_id, timestamp, backup_type, source_path, 
                 backup_path, size_bytes, checksum, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.job_name, record.backup_id, record.timestamp,
                record.backup_type, record.source_path, record.backup_path,
                record.size_bytes, record.checksum, record.status,
                record.error_message
            ))
            
            self.conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to save backup record: {e}")
            
    def restore_backup(self, backup_id: str, restore_path: str) -> bool:
        """Restore from backup"""
        try:
            # Get backup record
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM backup_records WHERE backup_id = ?
            ''', (backup_id,))
            
            result = cursor.fetchone()
            if not result:
                self.logger.error(f"Backup not found: {backup_id}")
                return False
                
            backup_path = Path(result[6])  # backup_path column
            
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
                
            # Verify checksum
            expected_checksum = result[8]  # checksum column
            if self.calculate_checksum(str(backup_path)) != expected_checksum:
                self.logger.error(f"Checksum mismatch for {backup_id}")
                return False
                
            self.logger.info(f"Restoring backup {backup_id} to {restore_path}")
            
            # Decrypt if encrypted
            extract_path = backup_path
            if str(backup_path).endswith('.enc'):
                if not self.cipher:
                    self.logger.error("Cannot decrypt: encryption not initialized")
                    return False
                    
                with open(backup_path, 'rb') as f:
                    encrypted_data = f.read()
                    
                decrypted_data = self.cipher.decrypt(encrypted_data)
                
                decrypt_path = backup_path.with_suffix('')
                with open(decrypt_path, 'wb') as f:
                    f.write(decrypted_data)
                    
                extract_path = decrypt_path
                
            # Extract archive
            tar_mode = "r:gz" if str(extract_path).endswith('.gz') else "r"
            
            with tarfile.open(extract_path, tar_mode) as tar:
                tar.extractall(path=restore_path)
                
            # Clean up temporary decrypted file
            if str(backup_path).endswith('.enc') and extract_path != backup_path:
                extract_path.unlink()
                
            self.logger.info(f"Successfully restored {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup {backup_id}: {e}")
            return False
            
    def cleanup_old_backups(self):
        """Clean up old backups based on retention policies"""
        try:
            cursor = self.conn.cursor()
            
            for job_config in self.config["backup_jobs"]:
                job_name = job_config["name"]
                retention_days = job_config["retention_days"]
                cutoff_time = time.time() - (retention_days * 24 * 3600)
                
                # Get old backups
                cursor.execute('''
                    SELECT backup_id, backup_path FROM backup_records 
                    WHERE job_name = ? AND timestamp < ?
                ''', (job_name, cutoff_time))
                
                old_backups = cursor.fetchall()
                
                for backup_id, backup_path in old_backups:
                    # Delete backup file
                    if Path(backup_path).exists():
                        Path(backup_path).unlink()
                        self.logger.info(f"Deleted old backup file: {backup_path}")
                        
                    # Delete from cloud if configured
                    if self.s3_client and job_config.get("cloud_sync"):
                        try:
                            cloud_config = self.config.get("cloud_storage", {})
                            bucket = cloud_config.get("bucket")
                            key = f"qenex-backups/{backup_id}/{Path(backup_path).name}"
                            
                            self.s3_client.delete_object(Bucket=bucket, Key=key)
                            self.logger.info(f"Deleted old backup from cloud: {key}")
                        except Exception as e:
                            self.logger.warning(f"Failed to delete cloud backup {key}: {e}")
                
                # Delete records from database
                cursor.execute('''
                    DELETE FROM backup_records 
                    WHERE job_name = ? AND timestamp < ?
                ''', (job_name, cutoff_time))
                
            self.conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")
            
    def get_backup_status(self) -> Dict:
        """Get current backup system status"""
        try:
            cursor = self.conn.cursor()
            
            # Get recent backups
            cursor.execute('''
                SELECT job_name, COUNT(*) as count, MAX(timestamp) as last_backup
                FROM backup_records 
                WHERE timestamp > ?
                GROUP BY job_name
            ''', (time.time() - 24 * 3600,))  # Last 24 hours
            
            recent_backups = cursor.fetchall()
            
            # Get success rate
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful
                FROM backup_records 
                WHERE timestamp > ?
            ''', (time.time() - 7 * 24 * 3600,))  # Last 7 days
            
            stats = cursor.fetchone()
            total_backups = stats[0] if stats[0] else 0
            successful_backups = stats[1] if stats[1] else 0
            success_rate = (successful_backups / total_backups * 100) if total_backups > 0 else 0
            
            # Calculate total backup size
            cursor.execute('SELECT SUM(size_bytes) FROM backup_records WHERE status = "success"')
            total_size = cursor.fetchone()[0] or 0
            
            return {
                'enabled': self.config['enabled'],
                'total_backups': total_backups,
                'success_rate': round(success_rate, 2),
                'total_size_gb': round(total_size / (1024**3), 2),
                'recent_backups': [
                    {
                        'job_name': row[0],
                        'count': row[1],
                        'last_backup': datetime.fromtimestamp(row[2]).isoformat() if row[2] else None
                    }
                    for row in recent_backups
                ],
                'cloud_storage_enabled': bool(self.s3_client),
                'encryption_enabled': bool(self.cipher),
                'last_check': time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get backup status: {e}")
            return {'error': str(e)}
            
    def list_backups(self, job_name: Optional[str] = None) -> List[Dict]:
        """List available backups"""
        try:
            cursor = self.conn.cursor()
            
            if job_name:
                cursor.execute('''
                    SELECT * FROM backup_records 
                    WHERE job_name = ? 
                    ORDER BY timestamp DESC
                ''', (job_name,))
            else:
                cursor.execute('''
                    SELECT * FROM backup_records 
                    ORDER BY timestamp DESC
                ''')
                
            columns = [desc[0] for desc in cursor.description]
            backups = []
            
            for row in cursor.fetchall():
                backup_dict = dict(zip(columns, row))
                backup_dict['timestamp_iso'] = datetime.fromtimestamp(backup_dict['timestamp']).isoformat()
                backup_dict['size_mb'] = round(backup_dict['size_bytes'] / (1024**2), 2)
                backups.append(backup_dict)
                
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []
            
    async def scheduler_loop(self):
        """Main scheduler loop for automated backups"""
        self.logger.info("Starting backup scheduler")
        
        while self.config.get('enabled', True):
            try:
                current_time = datetime.now()
                
                for job_config in self.config["backup_jobs"]:
                    job = BackupJob(**job_config)
                    
                    # Simple scheduling (run daily at specified hour)
                    # In production, implement proper cron parsing
                    if self.should_run_job(job, current_time):
                        asyncio.create_task(self.run_backup_job(job))
                        
                # Cleanup old backups periodically
                if current_time.hour == 4 and current_time.minute < 5:  # 4 AM daily
                    self.cleanup_old_backups()
                    
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                
            await asyncio.sleep(60)  # Check every minute
            
    def should_run_job(self, job: BackupJob, current_time: datetime) -> bool:
        """Check if job should run based on schedule"""
        # Simplified scheduling - in production use cron library
        last_run = self.get_last_backup_time(job.name)
        last_run_date = datetime.fromtimestamp(last_run).date() if last_run > 0 else None
        
        if last_run_date == current_time.date():
            return False  # Already ran today
            
        # Parse simple schedule format "0 2 * * *" (hour 2)
        try:
            schedule_parts = job.schedule.split()
            if len(schedule_parts) >= 2:
                scheduled_hour = int(schedule_parts[1])
                return current_time.hour == scheduled_hour and current_time.minute < 5
        except:
            pass
            
        return False
        
    async def run_backup_job(self, job: BackupJob):
        """Run single backup job asynchronously"""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, self.perform_backup, job)
            
    async def start(self):
        """Start the backup system"""
        self.logger.info("Starting QENEX Backup & Recovery System")
        
        # Start scheduler
        await self.scheduler_loop()
        
    def stop(self):
        """Stop the backup system"""
        self.logger.info("Stopping QENEX Backup & Recovery System")
        self.config['enabled'] = False
        if hasattr(self, 'conn'):
            self.conn.close()

async def main():
    """Main entry point"""
    backup_system = QenexBackupSystem()
    
    try:
        await backup_system.start()
    except KeyboardInterrupt:
        backup_system.stop()
        print("\nBackup system stopped")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())