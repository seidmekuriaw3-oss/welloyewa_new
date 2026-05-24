# ============================
# WOLLOYEWA STORE BOT - LOCAL STORAGE PROVIDER
# ============================
"""Local filesystem storage provider for development."""

import os
import aiofiles
from pathlib import Path
from typing import Optional
from datetime import datetime

from infrastructure.storage.base import (
    StorageProvider,
    StorageFile,
    UploadError,
    DownloadError,
    FileNotFoundError,
)
from core.config import settings
from core.logger import logger


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage provider.
    
    Stores files in a local directory. Primarily for development
    and testing. Not recommended for production use.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or "media"
        self._ensure_base_directory()
    
    def _ensure_base_directory(self) -> None:
        """Ensure the base storage directory exists."""
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
    
    def _get_full_path(self, path: str) -> Path:
        """Get full filesystem path."""
        return Path(self.base_path) / path
    
    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload file to local storage.
        
        Args:
            file_data: File content as bytes
            filename: Original filename
            content_type: MIME type (ignored for local storage)
            metadata: Additional metadata (ignored)
            
        Returns:
            Relative path of the uploaded file
        """
        try:
            # Generate unique path
            path = self._generate_path(filename)
            full_path = self._get_full_path(path)
            
            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(file_data)
            
            logger.info(f"File uploaded to local storage: {path}")
            return path
            
        except Exception as e:
            logger.error(f"Local upload failed: {e}")
            raise UploadError(f"Failed to upload file: {e}")
    
    async def download(self, path: str) -> bytes:
        """
        Download file from local storage.
        
        Args:
            path: Relative path of the file
            
        Returns:
            File content as bytes
        """
        try:
            full_path = self._get_full_path(path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            
            async with aiofiles.open(full_path, 'rb') as f:
                return await f.read()
                
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Local download failed: {e}")
            raise DownloadError(f"Failed to download file: {e}")
    
    async def delete(self, path: str) -> bool:
        """
        Delete file from local storage.
        
        Args:
            path: Relative path of the file
            
        Returns:
            True if deleted, False if file didn't exist
        """
        try:
            full_path = self._get_full_path(path)
            
            if not full_path.exists():
                return False
            
            full_path.unlink()
            logger.info(f"File deleted from local storage: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Local delete failed: {e}")
            raise UploadError(f"Failed to delete file: {e}")
    
    async def get_url(self, path: str, expires_in: Optional[int] = None) -> str:
        """
        Get URL for a file.
        
        Args:
            path: Relative path of the file
            expires_in: Ignored for local storage
            
        Returns:
            Local URL for the file
        """
        base_url = settings.STORAGE_BASE_URL.rstrip('/')
        return f"{base_url}/media/{path}"
    
    async def exists(self, path: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            path: Relative path of the file
            
        Returns:
            True if file exists, False otherwise
        """
        full_path = self._get_full_path(path)
        return full_path.exists()
    
    async def get_metadata(self, path: str) -> Optional[StorageFile]:
        """
        Get metadata for a file.
        
        Args:
            path: Relative path of the file
            
        Returns:
            StorageFile object or None
        """
        try:
            full_path = self._get_full_path(path)
            
            if not full_path.exists():
                return None
            
            stat = full_path.stat()
            
            return StorageFile(
                filename=full_path.name,
                size=stat.st_size,
                content_type=self._get_content_type(full_path.name),
                url=await self.get_url(path),
                path=path,
                created_at=datetime.fromtimestamp(stat.st_ctime),
            )
            
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return None
    
    async def list_files(
        self,
        prefix: str = "",
        limit: int = 100,
    ) -> list[StorageFile]:
        """
        List files in storage.
        
        Args:
            prefix: Filter by path prefix
            limit: Maximum number of files
            
        Returns:
            List of StorageFile objects
        """
        try:
            search_path = self._get_full_path(prefix)
            
            if not search_path.exists():
                return []
            
            files = []
            for file_path in search_path.rglob('*'):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(self.base_path))
                    metadata = await self.get_metadata(relative_path)
                    if metadata:
                        files.append(metadata)
                    
                    if len(files) >= limit:
                        break
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []


__all__ = ["LocalStorageProvider"]