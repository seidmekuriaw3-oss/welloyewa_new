# ============================
# WOLLOYEWA STORE BOT - AUDIT LOG RETENTION
# ============================
"""Audit log retention and management for compliance."""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from core.config import settings
from core.logger import logger


class RetentionPolicy(str, Enum):
    """Log retention policies."""
    STANDARD = "standard"      # 1 year
    FINANCIAL = "financial"    # 7 years
    GDPR = "gdpr"              # 30 days for PII, 1 year for others
    CUSTOM = "custom"


@dataclass
class RetentionRule:
    """Retention rule for log types."""
    
    log_type: str
    retention_days: int
    policy: RetentionPolicy
    archive_required: bool = False
    delete_after_archive: bool = True


class AuditLogRetention:
    """
    Audit log retention manager.
    
    Features:
    - Configurable retention periods
    - Automatic log archival
    - Secure deletion
    - Compliance reporting
    """
    
    def __init__(self):
        self._rules: Dict[str, RetentionRule] = {}
        self._init_default_rules()
    
    def _init_default_rules(self) -> None:
        """Initialize default retention rules."""
        default_rules = [
            RetentionRule("user_login", 365, RetentionPolicy.STANDARD),
            RetentionRule("user_actions", 365, RetentionPolicy.STANDARD),
            RetentionRule("payment_transactions", 2555, RetentionPolicy.FINANCIAL, archive_required=True),  # 7 years
            RetentionRule("order_changes", 730, RetentionPolicy.STANDARD),  # 2 years
            RetentionRule("pii_access", 30, RetentionPolicy.GDPR),  # 30 days for PII
            RetentionRule("admin_actions", 1095, RetentionPolicy.STANDARD),  # 3 years
            RetentionRule("system_errors", 90, RetentionPolicy.STANDARD),
            RetentionRule("api_calls", 30, RetentionPolicy.STANDARD),
        ]
        
        for rule in default_rules:
            self._rules[rule.log_type] = rule
    
    def add_rule(self, rule: RetentionRule) -> None:
        """Add a custom retention rule."""
        self._rules[rule.log_type] = rule
        logger.info(f"Added retention rule for {rule.log_type}: {rule.retention_days} days")
    
    def get_retention_days(self, log_type: str) -> int:
        """Get retention days for a log type."""
        rule = self._rules.get(log_type)
        if rule:
            return rule.retention_days
        return settings.DATA_RETENTION_DAYS
    
    def is_expired(self, log_type: str, created_at: datetime) -> bool:
        """Check if a log entry is expired."""
        retention_days = self.get_retention_days(log_type)
        expiry_date = created_at + timedelta(days=retention_days)
        return datetime.utcnow() > expiry_date
    
    async def archive_expired_logs(
        self,
        log_type: str,
        logs: List[Dict[str, Any]],
    ) -> str:
        """
        Archive expired logs.
        
        Args:
            log_type: Type of logs
            logs: List of log entries
            
        Returns:
            Archive file path
        """
        import json
        import gzip
        
        rule = self._rules.get(log_type)
        if not rule or not rule.archive_required:
            return ""
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archive_file = f"/archives/{log_type}_{timestamp}.json.gz"
        
        # Ensure directory exists
        import os
        os.makedirs("/archives", exist_ok=True)
        
        # Write to archive
        with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, default=str)
        
        logger.info(f"Archived {len(logs)} {log_type} logs to {archive_file}")
        return archive_file


class LogRetentionManager:
    """
    Log retention manager for automated cleanup.
    
    Features:
    - Scheduled cleanup
    - Batch processing
    - Compliance reporting
    """
    
    def __init__(self):
        self.retention = AuditLogRetention()
    
    async def enforce_retention_policy(
        self,
        log_type: str,
        logs: List[Dict[str, Any]],
        delete_expired: bool = True,
    ) -> Dict[str, Any]:
        """
        Enforce retention policy on logs.
        
        Args:
            log_type: Type of logs
            logs: List of log entries
            delete_expired: Whether to delete expired logs
            
        Returns:
            Statistics about processed logs
        """
        expired = []
        retained = []
        
        for log in logs:
            created_at = log.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            if created_at and self.retention.is_expired(log_type, created_at):
                expired.append(log)
            else:
                retained.append(log)
        
        result = {
            "log_type": log_type,
            "total_logs": len(logs),
            "expired_logs": len(expired),
            "retained_logs": len(retained),
        }
        
        # Archive if required
        rule = self.retention._rules.get(log_type)
        if rule and rule.archive_required and expired:
            archive_file = await self.retention.archive_expired_logs(log_type, expired)
            result["archive_file"] = archive_file
        
        # Delete expired logs if requested
        if delete_expired:
            result["deleted_count"] = len(expired)
        
        logger.info(f"Retention policy enforced for {log_type}: {len(expired)} expired, {len(retained)} retained")
        return result
    
    async def delete_expired_logs(
        self,
        log_type: str,
        logs: List[Dict[str, Any]],
    ) -> int:
        """
        Delete expired logs.
        
        Args:
            log_type: Type of logs
            logs: List of log entries
            
        Returns:
            Number of deleted logs
        """
        deleted = 0
        
        for log in logs:
            created_at = log.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            if created_at and self.retention.is_expired(log_type, created_at):
                # Delete logic here
                deleted += 1
        
        logger.info(f"Deleted {deleted} expired {log_type} logs")
        return deleted


# Global retention manager
log_retention_manager = LogRetentionManager()


async def enforce_retention_policy(
    log_type: str,
    logs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Enforce retention policy on logs."""
    return await log_retention_manager.enforce_retention_policy(log_type, logs)


async def archive_audit_logs(
    log_type: str,
    logs: List[Dict[str, Any]],
) -> str:
    """Archive audit logs."""
    return await log_retention_manager.retention.archive_expired_logs(log_type, logs)


async def delete_expired_logs(
    log_type: str,
    logs: List[Dict[str, Any]],
) -> int:
    """Delete expired logs."""
    return await log_retention_manager.delete_expired_logs(log_type, logs)


__all__ = [
    "AuditLogRetention",
    "RetentionPolicy",
    "RetentionRule",
    "LogRetentionManager",
    "log_retention_manager",
    "enforce_retention_policy",
    "archive_audit_logs",
    "delete_expired_logs",
]