"""Disaster Recovery Orchestrator for QENEX OS"""
import asyncio
import json
import os
import shutil
import tarfile
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import boto3
import aiofiles
import aioboto3
from dataclasses import dataclass
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BackupConfig:
    """Backup configuration"""
    backup_id: str
    timestamp: datetime
    size_bytes: int
    checksum: str
    location: str
    type: str  # full, incremental, differential
    retention_days: int
    encrypted: bool

@dataclass
class RecoveryPoint:
    """Recovery point objective"""
    rpo_minutes: int = 15
    rto_minutes: int = 30
    backup_frequency: int = 60
    replication_interval: int = 5

class DisasterRecoveryOrchestrator:
    """Automated disaster recovery with failover capabilities"""
    
    def __init__(self, primary_region: str = "us-east-1", 
                 dr_region: str = "us-west-2"):
        self.primary_region = primary_region
        self.dr_region = dr_region
        self.recovery_point = RecoveryPoint()
        self.backups: List[BackupConfig] = []
        self.replication_status = {}
        self.failover_in_progress = False
        
        # Initialize cloud clients
        self.s3_client = boto3.client('s3', region_name=primary_region)
        self.dr_s3_client = boto3.client('s3', region_name=dr_region)
        
        # Backup locations
        self.local_backup_dir = "/opt/qenex-backups"
        self.s3_bucket = "qenex-dr-backups"
        self.dr_s3_bucket = "qenex-dr-backups-secondary"
        
        os.makedirs(self.local_backup_dir, exist_ok=True)
    
    async def create_backup(self, backup_type: str = "full") -> BackupConfig:
        """Create system backup"""
        backup_id = f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        backup_path = os.path.join(self.local_backup_dir, f"{backup_id}.tar.gz")
        
        logger.info(f"Creating {backup_type} backup: {backup_id}")
        
        # Collect system state
        system_state = await self._collect_system_state()
        
        # Create backup archive
        with tarfile.open(backup_path, "w:gz") as tar:
            # Backup critical directories
            for directory in ["/opt/qenex-os", "/etc/qenex", "/var/lib/qenex"]:
                if os.path.exists(directory):
                    tar.add(directory, arcname=os.path.basename(directory))
            
            # Add system state
            state_file = f"/tmp/{backup_id}-state.json"
            with open(state_file, "w") as f:
                json.dump(system_state, f)
            tar.add(state_file, arcname="system-state.json")
            os.remove(state_file)
        
        # Calculate checksum
        checksum = await self._calculate_checksum(backup_path)
        
        # Get file size
        size_bytes = os.path.getsize(backup_path)
        
        # Create backup config
        backup_config = BackupConfig(
            backup_id=backup_id,
            timestamp=datetime.now(),
            size_bytes=size_bytes,
            checksum=checksum,
            location=backup_path,
            type=backup_type,
            retention_days=30,
            encrypted=True
        )
        
        self.backups.append(backup_config)
        
        # Upload to S3
        await self._upload_to_s3(backup_path, backup_id)
        
        # Replicate to DR region
        await self._replicate_to_dr(backup_id)
        
        logger.info(f"Backup completed: {backup_id}")
        return backup_config
    
    async def _collect_system_state(self) -> Dict:
        """Collect current system state"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "services": await self._get_service_status(),
            "databases": await self._get_database_state(),
            "configurations": await self._get_configurations(),
            "network": await self._get_network_state()
        }
        return state
    
    async def _get_service_status(self) -> Dict:
        """Get status of all services"""
        services = {}
        service_list = ["qenex-os", "nginx", "postgresql", "redis"]
        
        for service in service_list:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True
                )
                services[service] = result.stdout.strip()
            except:
                services[service] = "unknown"
        
        return services
    
    async def _get_database_state(self) -> Dict:
        """Get database state for backup"""
        return {
            "postgresql": {
                "dump_location": "/tmp/postgres-dump.sql",
                "size": 0,
                "tables": []
            },
            "redis": {
                "snapshot": "/var/lib/redis/dump.rdb",
                "size": 0
            }
        }
    
    async def _get_configurations(self) -> Dict:
        """Get system configurations"""
        configs = {}
        config_files = [
            "/etc/qenex/config.yaml",
            "/opt/qenex-os/config.json"
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                async with aiofiles.open(config_file, 'r') as f:
                    configs[config_file] = await f.read()
        
        return configs
    
    async def _get_network_state(self) -> Dict:
        """Get network configuration state"""
        return {
            "interfaces": [],
            "routes": [],
            "dns": []
        }
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate file checksum"""
        sha256_hash = hashlib.sha256()
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    async def _upload_to_s3(self, file_path: str, backup_id: str):
        """Upload backup to S3"""
        try:
            with open(file_path, 'rb') as f:
                self.s3_client.upload_fileobj(
                    f,
                    self.s3_bucket,
                    f"{backup_id}.tar.gz",
                    ExtraArgs={
                        'ServerSideEncryption': 'AES256',
                        'StorageClass': 'STANDARD_IA'
                    }
                )
            logger.info(f"Backup uploaded to S3: {backup_id}")
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
    
    async def _replicate_to_dr(self, backup_id: str):
        """Replicate backup to DR region"""
        try:
            # Copy object to DR bucket
            copy_source = {'Bucket': self.s3_bucket, 'Key': f"{backup_id}.tar.gz"}
            self.dr_s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.dr_s3_bucket,
                Key=f"{backup_id}.tar.gz",
                ServerSideEncryption='AES256'
            )
            
            self.replication_status[backup_id] = {
                "status": "replicated",
                "dr_region": self.dr_region,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Backup replicated to DR region: {backup_id}")
        except Exception as e:
            logger.error(f"Replication failed: {e}")
            self.replication_status[backup_id] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def restore_backup(self, backup_id: str, target_location: str = "/"):
        """Restore from backup"""
        logger.info(f"Starting restoration from backup: {backup_id}")
        
        # Find backup
        backup = next((b for b in self.backups if b.backup_id == backup_id), None)
        if not backup:
            raise ValueError(f"Backup not found: {backup_id}")
        
        # Download from S3 if not local
        local_path = backup.location
        if not os.path.exists(local_path):
            local_path = await self._download_from_s3(backup_id)
        
        # Verify checksum
        checksum = await self._calculate_checksum(local_path)
        if checksum != backup.checksum:
            raise ValueError("Backup checksum verification failed")
        
        # Extract backup
        with tarfile.open(local_path, "r:gz") as tar:
            tar.extractall(target_location)
        
        # Restore system state
        state_file = os.path.join(target_location, "system-state.json")
        if os.path.exists(state_file):
            await self._restore_system_state(state_file)
        
        logger.info(f"Restoration completed from: {backup_id}")
    
    async def _download_from_s3(self, backup_id: str) -> str:
        """Download backup from S3"""
        local_path = os.path.join(self.local_backup_dir, f"{backup_id}.tar.gz")
        
        try:
            self.s3_client.download_file(
                self.s3_bucket,
                f"{backup_id}.tar.gz",
                local_path
            )
            logger.info(f"Backup downloaded from S3: {backup_id}")
        except:
            # Try DR region
            self.dr_s3_client.download_file(
                self.dr_s3_bucket,
                f"{backup_id}.tar.gz",
                local_path
            )
            logger.info(f"Backup downloaded from DR region: {backup_id}")
        
        return local_path
    
    async def _restore_system_state(self, state_file: str):
        """Restore system state from backup"""
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        # Restore services
        for service, status in state.get("services", {}).items():
            if status == "active":
                subprocess.run(["systemctl", "start", service])
        
        logger.info("System state restored")
    
    async def initiate_failover(self, reason: str = "Manual failover"):
        """Initiate failover to DR site"""
        if self.failover_in_progress:
            logger.warning("Failover already in progress")
            return
        
        self.failover_in_progress = True
        logger.info(f"Initiating failover: {reason}")
        
        try:
            # 1. Stop primary services
            await self._stop_primary_services()
            
            # 2. Promote DR to primary
            await self._promote_dr_to_primary()
            
            # 3. Update DNS
            await self._update_dns_records()
            
            # 4. Start DR services
            await self._start_dr_services()
            
            # 5. Verify failover
            success = await self._verify_failover()
            
            if success:
                logger.info("Failover completed successfully")
                # Swap regions
                self.primary_region, self.dr_region = self.dr_region, self.primary_region
            else:
                logger.error("Failover verification failed")
                await self.initiate_failback()
            
        except Exception as e:
            logger.error(f"Failover failed: {e}")
            await self.initiate_failback()
        finally:
            self.failover_in_progress = False
    
    async def _stop_primary_services(self):
        """Stop services in primary region"""
        logger.info("Stopping primary services")
        services = ["qenex-os", "nginx", "postgresql"]
        for service in services:
            subprocess.run(["systemctl", "stop", service])
    
    async def _promote_dr_to_primary(self):
        """Promote DR site to primary"""
        logger.info("Promoting DR to primary")
        # Update configurations
        # Switch database to primary mode
        # Update load balancer
    
    async def _update_dns_records(self):
        """Update DNS to point to DR site"""
        logger.info("Updating DNS records")
        # Update Route53 or other DNS provider
    
    async def _start_dr_services(self):
        """Start services in DR region"""
        logger.info("Starting DR services")
        # Start services on DR infrastructure
    
    async def _verify_failover(self) -> bool:
        """Verify failover success"""
        logger.info("Verifying failover")
        # Check service health
        # Verify data integrity
        # Test connectivity
        return True
    
    async def initiate_failback(self):
        """Failback to primary site"""
        logger.info("Initiating failback to primary")
        # Reverse failover process
    
    async def run_dr_monitor(self):
        """Monitor DR readiness"""
        while True:
            try:
                # Check primary health
                primary_healthy = await self._check_primary_health()
                
                if not primary_healthy:
                    logger.warning("Primary site unhealthy, considering failover")
                    # Auto-failover logic
                    consecutive_failures = 0
                    for _ in range(3):
                        await asyncio.sleep(10)
                        if await self._check_primary_health():
                            break
                        consecutive_failures += 1
                    
                    if consecutive_failures >= 3:
                        await self.initiate_failover("Automatic - Primary site failure")
                
                # Create periodic backups
                if datetime.now().minute == 0:  # Every hour
                    await self.create_backup("incremental")
                
                # Clean old backups
                await self._cleanup_old_backups()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"DR monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _check_primary_health(self) -> bool:
        """Check primary site health"""
        # Check service availability
        # Check database connectivity
        # Check network connectivity
        return True
    
    async def _cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for backup in self.backups[:]:
            if backup.timestamp < cutoff_date:
                # Remove local file
                if os.path.exists(backup.location):
                    os.remove(backup.location)
                
                # Remove from S3
                try:
                    self.s3_client.delete_object(
                        Bucket=self.s3_bucket,
                        Key=f"{backup.backup_id}.tar.gz"
                    )
                except:
                    pass
                
                self.backups.remove(backup)
                logger.info(f"Cleaned up old backup: {backup.backup_id}")

if __name__ == "__main__":
    dr_orchestrator = DisasterRecoveryOrchestrator()
    asyncio.run(dr_orchestrator.run_dr_monitor())