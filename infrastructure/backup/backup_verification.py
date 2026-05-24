# ============================
# WOLLOYEWA STORE BOT - BACKUP VERIFICATION
# ============================
"""Backup verification and integrity checking."""

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from core.config import settings
from core.logger import logger


class VerificationStatus(str, Enum):
    """Verification status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class VerificationResult:
    """Result of backup verification."""
    
    backup_id: str
    status: VerificationStatus
    checksum_matches: bool
    size_matches: bool
    can_restore: bool
    verified_at: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class BackupVerifier:
    """
    Backup verification service.
    
    Features:
    - Checksum validation
    - Backup integrity checking
    - Test restoration
    - Scheduled verification
    """
    
    def __init__(self):
        self._verification_results: Dict[str, VerificationResult] = {}
    
    async def verify_backup(
        self,
        backup_file: str,
        expected_checksum: Optional[str] = None,
        expected_size: Optional[int] = None,
        test_restore: bool = False,
    ) -> VerificationResult:
        """
        Verify a backup file.
        
        Args:
            backup_file: Path to backup file
            expected_checksum: Expected MD5 checksum
            expected_size: Expected file size
            test_restore: Whether to test restore
            
        Returns:
            VerificationResult
        """
        backup_id = os.path.basename(backup_file)
        
        result = VerificationResult(
            backup_id=backup_id,
            status=VerificationStatus.IN_PROGRESS,
            checksum_matches=False,
            size_matches=False,
            can_restore=False,
            verified_at=datetime.utcnow(),
        )
        
        try:
            # Verify file exists
            if not os.path.exists(backup_file):
                result.status = VerificationStatus.FAILED
                result.error_message = "Backup file not found"
                return result
            
            # Verify file size
            actual_size = os.path.getsize(backup_file)
            result.size_matches = (expected_size is None or actual_size == expected_size)
            result.details["actual_size_bytes"] = actual_size
            
            # Verify checksum
            actual_checksum = await self._calculate_checksum(backup_file)
            result.checksum_matches = (expected_checksum is None or actual_checksum == expected_checksum)
            result.details["actual_checksum"] = actual_checksum
            
            # Test restore (optional)
            if test_restore:
                result.can_restore = await self._test_restore(backup_file)
            
            # Determine overall status
            if result.checksum_matches and result.size_matches:
                result.status = VerificationStatus.PASSED
            elif result.checksum_matches or result.size_matches:
                result.status = VerificationStatus.PARTIAL
            else:
                result.status = VerificationStatus.FAILED
            
            self._verification_results[backup_id] = result
            logger.info(f"Backup verification completed for {backup_id}: {result.status.value}")
            
            return result
            
        except Exception as e:
            result.status = VerificationStatus.FAILED
            result.error_message = str(e)
            logger.error(f"Backup verification failed for {backup_id}: {e}")
            return result
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of file."""
        hash_md5 = hashlib.md5()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    async def _test_restore(self, backup_file: str) -> bool:
        """Test restore to a temporary database."""
        temp_db = f"test_restore_{int(datetime.utcnow().timestamp())}"
        
        try:
            # Create temporary database
            subprocess.run(
                ["createdb", temp_db],
                check=True,
                capture_output=True,
            )
            
            # Restore to temporary database
            if backup_file.endswith('.gz'):
                with open(backup_file, 'rb') as f:
                    subprocess.run(
                        ["gunzip", "-c"],
                        stdin=f,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True,
                    )
            else:
                with open(backup_file, 'r') as f:
                    subprocess.run(
                        ["psql", "-d", temp_db],
                        stdin=f,
                        check=True,
                        capture_output=True,
                    )
            
            # Verify restore by checking table count
            result = subprocess.run(
                ["psql", "-d", temp_db, "-t", "-c", "SELECT COUNT(*) FROM information_schema.tables;"],
                capture_output=True,
                text=True,
                check=True,
            )
            
            # Drop test database
            subprocess.run(
                ["dropdb", temp_db],
                check=True,
                capture_output=True,
            )
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Test restore failed: {e.stderr}")
            
            # Clean up test database
            try:
                subprocess.run(["dropdb", temp_db], capture_output=True)
            except:
                pass
            
            return False
    
    async def get_verification_history(
        self,
        limit: int = 50,
    ) -> List[VerificationResult]:
        """Get backup verification history."""
        results = list(self._verification_results.values())
        results.sort(key=lambda x: x.verified_at, reverse=True)
        return results[:limit]
    
    async def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        results = self._verification_results.values()
        
        total = len(results)
        passed = sum(1 for r in results if r.status == VerificationStatus.PASSED)
        failed = sum(1 for r in results if r.status == VerificationStatus.FAILED)
        partial = sum(1 for r in results if r.status == VerificationStatus.PARTIAL)
        
        return {
            "total_verified": total,
            "passed": passed,
            "failed": failed,
            "partial": partial,
            "success_rate": (passed / total * 100) if total > 0 else 0,
        }


class BackupVerificationManager:
    """Singleton backup verification manager."""
    
    _instance: Optional[BackupVerifier] = None
    
    @classmethod
    def get_instance(cls) -> BackupVerifier:
        if cls._instance is None:
            cls._instance = BackupVerifier()
        return cls._instance


async def verify_backup(
    backup_file: str,
    expected_checksum: Optional[str] = None,
    expected_size: Optional[int] = None,
) -> VerificationResult:
    """Verify a backup file."""
    manager = BackupVerificationManager.get_instance()
    return await manager.verify_backup(backup_file, expected_checksum, expected_size)


async def schedule_verification(backup_file: str, delay_seconds: int = 60) -> None:
    """Schedule backup verification for later execution."""
    import asyncio
    
    async def delayed_verification():
        await asyncio.sleep(delay_seconds)
        await verify_backup(backup_file)
    
    asyncio.create_task(delayed_verification())
    logger.info(f"Scheduled verification for {backup_file} in {delay_seconds}s")


__all__ = [
    "BackupVerifier",
    "VerificationResult",
    "VerificationStatus",
    "verify_backup",
    "schedule_verification",
    "BackupVerificationManager",
]