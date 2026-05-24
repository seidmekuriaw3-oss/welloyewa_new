# ============================
# WOLLOYEWA STORE BOT - DATABASE MIGRATIONS
# ============================
"""Alembic migration management utilities."""

import os
import subprocess
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.config import settings
from core.logger import logger


async def run_migrations(target: str = "head") -> bool:
    """
    Run database migrations to target revision.
    
    Args:
        target: Target revision (head, base, or revision ID)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        cmd = ["alembic", "upgrade", target]
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            logger.info(f"Database migrations completed successfully to {target}")
            logger.debug(result.stdout)
            return True
        else:
            logger.error(f"Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        return False


async def create_migration(message: str, autogenerate: bool = True) -> Optional[str]:
    """
    Create a new migration.
    
    Args:
        message: Migration message
        autogenerate: Whether to autogenerate from model changes
        
    Returns:
        Migration file path if successful
    """
    try:
        cmd = ["alembic", "revision"]
        if autogenerate:
            cmd.append("--autogenerate")
        cmd.extend(["-m", message])
        
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            # Extract migration file path from output
            output = result.stdout
            logger.info(f"Migration created: {message}")
            logger.debug(output)
            
            # Try to extract the file path
            for line in output.split("\n"):
                if "Generating" in line or "Creating" in line:
                    # Extract file path
                    parts = line.split("/")
                    if parts:
                        return parts[-1].strip()
            return "Migration created successfully"
        else:
            logger.error(f"Failed to create migration: {result.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        return None


async def downgrade_migration(revision: str = "-1") -> bool:
    """
    Downgrade database to a previous revision.
    
    Args:
        revision: Target revision (default: -1 for previous)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        cmd = ["alembic", "downgrade", revision]
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            logger.info(f"Database downgraded to {revision}")
            logger.debug(result.stdout)
            return True
        else:
            logger.error(f"Downgrade failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to downgrade: {e}")
        return False


async def get_migration_status() -> Dict[str, Any]:
    """
    Get current migration status.
    
    Returns:
        Dictionary with migration status information
    """
    try:
        # Get current revision
        current_result = subprocess.run(
            ["alembic", "current"],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            capture_output=True,
            text=True,
        )
        
        # Get heads
        heads_result = subprocess.run(
            ["alembic", "heads"],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            capture_output=True,
            text=True,
        )
        
        # Get history
        history_result = subprocess.run(
            ["alembic", "history", "--verbose"],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            capture_output=True,
            text=True,
        )
        
        return {
            "current": current_result.stdout.strip() if current_result.returncode == 0 else "Unknown",
            "heads": heads_result.stdout.strip() if heads_result.returncode == 0 else "Unknown",
            "is_head": "head" in current_result.stdout.lower() if current_result.returncode == 0 else False,
            "history": history_result.stdout if history_result.returncode == 0 else "",
        }
        
    except Exception as e:
        logger.error(f"Failed to get migration status: {e}")
        return {
            "current": "Error",
            "heads": "Error",
            "is_head": False,
            "history": "",
            "error": str(e),
        }


async def check_migration_health() -> Dict[str, Any]:
    """
    Check if migrations are healthy and up to date.
    
    Returns:
        Dictionary with health status
    """
    status = await get_migration_status()
    
    # Check for split heads
    has_split_heads = len(status.get("heads", "").split("\n")) > 1
    
    return {
        "healthy": status.get("is_head", False) and not has_split_heads,
        "is_head": status.get("is_head", False),
        "has_split_heads": has_split_heads,
        "current_revision": status.get("current"),
        "heads": status.get("heads"),
    }


__all__ = [
    "run_migrations",
    "create_migration",
    "downgrade_migration",
    "get_migration_status",
    "check_migration_health",
]