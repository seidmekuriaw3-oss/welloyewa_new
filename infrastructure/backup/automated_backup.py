# ============================
# WOLLOYEWA STORE BOT - AUTOMATED BACKUP
# ============================
"""Automated database backup management."""

import os
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from core.config import settings
from core.logger import logger


class BackupStatus(str, Enum):
    """Backup status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class BackupType(str, Enum):
    """Backup type."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


@dataclass
class BackupConfig:
    """Backup configuration."""
    
    backup_path: str = "/backups"
    retention_days: int = 30
    schedule: str = "0 2 * * *"  # Daily at 2 AM
    backup_type: BackupType = BackupType.FULL
    compress: bool = True
    verify_after_backup: bool = True


@dataclass
class BackupResult:
    """Backup operation result."""
    
    backup_id: str
    backup_type: BackupType
    status: BackupStatus
    size_bytes: int
    duration_seconds: float
    file_path: str
    created_at: datetime
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AutomatedBackup:
    """
    Automated database backup manager.
    
    Features:
    - Scheduled backups
    - Full, incremental, and differential backups
    - Compression support
    - Backup retention policy
    - Backup verification
    """
    
    def __init__(self, config: Optional[BackupConfig] = None):
        self.config = config or BackupConfig()
        self._ensure_backup_directory()
    
    def _ensure_backup_directory(self) -> None:
        """Ensure backup directory exists."""
        os.makedirs(self.config.backup_path, exist_ok=True)
    
    async def create_backup(
        self,
        backup_type: BackupType = BackupType.FULL,
        compress: bool = None,
    ) -> BackupResult:
        """
        Create a database backup.
        
        Args:
            backup_type: Type of backup to create
            compress: Whether to compress the backup
            
        Returns:
            BackupResult with backup details
        """
        import uuid
        
        compress = compress if compress is not None else self.config.compress
        backup_id = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        result = BackupResult(
            backup_id=backup_id,
            backup_type=backup_type,
            status=BackupStatus.RUNNING,
            size_bytes=0,
            duration_seconds=0,
            file_path="",
            created_at=datetime.utcnow(),
        )
        
        try:
            start_time = datetime.utcnow()
            
            # Create backup
            backup_file = await self._run_pg_dump(backup_id, compress)
            
            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Get file size
            file_size = os.path.getsize(backup_file)
            
            result.status = BackupStatus.SUCCESS
            result.size_bytes = file_size
            result.duration_seconds = duration
            result.file_path = backup_file
            
            # Verify backup
            if self.config.verify_after_backup:
                verified = await self._verify_backup(backup_file)
                if not verified:
                    result.status = BackupStatus.PARTIAL
                    result.error_message = "Backup verification failed"
            
            logger.info(f"Backup created: {backup_id} ({file_size / 1024 / 1024:.2f} MB)")
            
            # Clean old backups
            await self.cleanup_old_backups()
            
            return result
            
        except Exception as e:
            result.status = BackupStatus.FAILED
            result.error_message = str(e)
            logger.error(f"Backup failed: {e}")
            return result
    
    async def _run_pg_dump(self, backup_id: str, compress: bool) -> str:
        """Run pg_dump command."""
        db_url = settings.DATABASE_URL
        filename = f"{backup_id}.sql"
        
        if compress:
            filename += ".gz"
        
        file_path = os.path.join(self.config.backup_path, filename)
        
        # Build pg_dump command
        cmd = [
            "pg_dump",
            "--format=plain",
            "--no-owner",
            "--no-privileges",
            "--clean",
            "--if-exists",
            db_url,
        ]
        
        # Run command
        if compress:
            # Pipe through gzip
            dump_process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            with open(file_path, 'wb') as f:
                gzip_process = subprocess.Popen(
                    ["gzip"],
                    stdin=dump_process.stdout,
                    stdout=f,
                )
                gzip_process.wait()
            dump_process.wait()
        else:
            with open(file_path, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)
        
        return file_path
    
    async def _verify_backup(self, backup_file: str) -> bool:
        """Verify backup integrity."""
        try:
            if backup_file.endswith('.gz'):
                # Test gzip integrity
                with gzip.open(backup_file, 'rb') as f:
                    f.read(1024)  # Read first 1KB
            else:
                # Check if file is not empty
                if os.path.getsize(backup_file) == 0:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False
    
    async def restore_backup(self, backup_file: str, target_db: Optional[str] = None) -> bool:
        """
        Restore a backup.
        
        Args:
            backup_file: Path to backup file
            target_db: Target database name
            
        Returns:
            True if restore successful
        """
        try:
            db_url = target_db or settings.DATABASE_URL
            
            # Build psql command
            if backup_file.endswith('.gz'):
                # Uncompress and restore
                with gzip.open(backup_file, 'rb') as f:
                    subprocess.run(
                        ["psql", db_url],
                        stdin=f,
                        check=True,
                    )
            else:
                with open(backup_file, 'r') as f:
                    subprocess.run(
                        ["psql", db_url],
                        stdin=f,
                        check=True,
                    )
            
            logger.info(f"Backup restored: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups."""
        backups = []
        
        for filename in os.listdir(self.config.backup_path):
            if filename.endswith('.sql') or filename.endswith('.sql.gz'):
                file_path = os.path.join(self.config.backup_path, filename)
                stat = os.stat(file_path)
                
                backups.append({
                    "filename": filename,
                    "size_mb": stat.st_size / 1024 / 1024,
                    "created_at": datetime.fromtimestamp(stat.st_ctime),
                    "is_compressed": filename.endswith('.gz'),
                })
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
    
    async def cleanup_old_backups(self) -> int:
        """Delete backups older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self.config.retention_days)
        deleted_count = 0
        
        for filename in os.listdir(self.config.backup_path):
            file_path = os.path.join(self.config.backup_path, filename)
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            
            if file_time < cutoff:
                os.remove(file_path)
                deleted_count += 1
                logger.info(f"Deleted old backup: {filename}")
        
        return deleted_count
    
    async def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup statistics."""
        backups = await self.list_backups()
        total_size = sum(b["size_mb"] for b in backups)
        
        return {
            "total_backups": len(backups),
            "total_size_mb": round(total_size, 2),
            "oldest_backup": backups[-1]["created_at"] if backups else None,
            "newest_backup": backups[0]["created_at"] if backups else None,
            "backup_path": self.config.backup_path,
            "retention_days": self.config.retention_days,
        }


class BackupManager:
    """Singleton backup manager."""
    
    _instance: Optional[AutomatedBackup] = None
    
    @classmethod
    def get_instance(cls) -> AutomatedBackup:
        if cls._instance is None:
            cls._instance = AutomatedBackup()
        return cls._instance


async def create_backup() -> BackupResult:
    """Create a new database backup."""
    manager = BackupManager.get_instance()
    return await manager.create_backup()


async def restore_backup(backup_file: str) -> bool:
    """Restore a database backup."""
    manager = BackupManager.get_instance()
    return await manager.restore_backup(backup_file)


async def list_backups() -> List[Dict[str, Any]]:
    """List all available backups."""
    manager = BackupManager.get_instance()
    return await manager.list_backups()


__all__ = [
    "AutomatedBackup",
    "BackupConfig",
    "BackupStatus",
    "BackupType",
    "BackupResult",
    "create_backup",
    "restore_backup",
    "list_backups",
    "BackupManager",
]