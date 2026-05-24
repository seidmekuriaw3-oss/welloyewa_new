# ============================
# WOLLOYEWA STORE BOT - STORAGE BASE
# ============================
"""Base storage provider interface and exceptions."""

from abc import ABC, abstractmethod
from typing import Optional, BinaryIO
from dataclasses import dataclass
from datetime import datetime


class StorageException(Exception):
    """Base exception for storage operations."""
    pass


class FileNotFoundError(StorageException):
    """Raised when a file is not found."""
    pass


class UploadError(StorageException):
    """Raised when file upload fails."""
    pass


class DownloadError(StorageException):
    """Raised when file download fails."""
    pass


@dataclass
class StorageFile:
    """File metadata."""
    
    filename: str
    size: int
    content_type: str
    url: str
    path: str
    created_at: datetime
    etag: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "filename": self.filename,
            "size": self.size,
            "content_type": self.content_type,
            "url": self.url,
            "path": self.path,
            "created_at": self.created_at.isoformat(),
            "etag": self.etag,
        }


class StorageProvider(ABC):
    """
    Abstract base class for storage providers.
    
    Implementations should provide methods for uploading, downloading,
    and managing files in cloud storage or local filesystem.
    """
    
    @abstractmethod
    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload a file to storage.
        
        Args:
            file_data: File content as bytes
            filename: Original filename
            content_type: MIME type of the file
            metadata: Additional metadata to store
            
        Returns:
            Path or URL of the uploaded file
            
        Raises:
            UploadError: If upload fails
        """
        pass
    
    @abstractmethod
    async def download(self, path: str) -> bytes:
        """
        Download a file from storage.
        
        Args:
            path: Path or key of the file
            
        Returns:
            File content as bytes
            
        Raises:
            FileNotFoundError: If file doesn't exist
            DownloadError: If download fails
        """
        pass
    
    @abstractmethod
    async def delete(self, path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            path: Path or key of the file
            
        Returns:
            True if deleted, False if file didn't exist
            
        Raises:
            StorageException: If deletion fails
        """
        pass
    
    @abstractmethod
    async def get_url(self, path: str, expires_in: Optional[int] = None) -> str:
        """
        Get URL for a file.
        
        Args:
            path: Path or key of the file
            expires_in: Expiration time in seconds (for signed URLs)
            
        Returns:
            URL of the file
        """
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            path: Path or key of the file
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_metadata(self, path: str) -> Optional[StorageFile]:
        """
        Get metadata for a file.
        
        Args:
            path: Path or key of the file
            
        Returns:
            StorageFile object or None if not found
        """
        pass
    
    @abstractmethod
    async def list_files(
        self,
        prefix: str = "",
        limit: int = 100,
    ) -> list[StorageFile]:
        """
        List files in storage.
        
        Args:
            prefix: Filter by path prefix
            limit: Maximum number of files to return
            
        Returns:
            List of StorageFile objects
        """
        pass
    
    async def upload_stream(
        self,
        stream: BinaryIO,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload a file from a stream.
        
        Args:
            stream: Binary stream to read from
            filename: Original filename
            content_type: MIME type of the file
            metadata: Additional metadata to store
            
        Returns:
            Path or URL of the uploaded file
        """
        file_data = stream.read()
        return await self.upload(file_data, filename, content_type, metadata)
    
    def _generate_path(self, filename: str) -> str:
        """
        Generate a unique path for a file.
        
        Args:
            filename: Original filename
            
        Returns:
            Unique path
        """
        import uuid
        from pathlib import Path
        
        ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        
        # Organize by date
        from datetime import datetime
        date_path = datetime.utcnow().strftime("%Y/%m/%d")
        
        return f"{date_path}/{unique_name}"
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename."""
        import mimetypes
        
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"


__all__ = [
    "StorageProvider",
    "StorageFile",
    "StorageException",
    "FileNotFoundError",
    "UploadError",
    "DownloadError",
]