# ============================
# WOLLOYEWA STORE BOT - CLOUDINARY STORAGE PROVIDER
# ============================
"""Cloudinary storage provider for image and video hosting."""

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


class CloudinaryProvider(StorageProvider):
    """
    Cloudinary storage provider.
    
    Features:
    - Automatic image optimization
    - On-the-fly transformations
    - CDN delivery
    - Video support
    """
    
    def __init__(self):
        self._client = None
        self.cloud_name = settings.CLOUDINARY_CLOUD_NAME
        self.api_key = settings.CLOUDINARY_API_KEY
        self.api_secret = settings.CLOUDINARY_API_SECRET
        self._initialized = False
    
    async def _get_client(self):
        """Get Cloudinary client (lazy initialization)."""
        if not self._initialized:
            try:
                import cloudinary
                import cloudinary.uploader
                import cloudinary.api
                
                cloudinary.config(
                    cloud_name=self.cloud_name,
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    secure=True,
                )
                
                self._initialized = True
                logger.info(f"Cloudinary storage initialized: cloud_name={self.cloud_name}")
                
            except ImportError:
                logger.warning("cloudinary not installed. Cloudinary storage will not work.")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Cloudinary client: {e}")
                raise
        
        import cloudinary.uploader
        return cloudinary.uploader
    
    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload file to Cloudinary.
        
        Args:
            file_data: File content as bytes
            filename: Original filename
            content_type: MIME type (ignored)
            metadata: Additional metadata
            
        Returns:
            Cloudinary public_id
        """
        try:
            import cloudinary.uploader
            import tempfile
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp:
                tmp.write(file_data)
                tmp_path = tmp.name
            
            # Upload options
            upload_options = {
                'public_id': self._generate_public_id(filename),
                'resource_type': 'auto',
                'context': metadata or {},
            }
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(tmp_path, **upload_options)
            
            # Clean up temp file
            import os
            os.unlink(tmp_path)
            
            public_id = result['public_id']
            logger.info(f"File uploaded to Cloudinary: {public_id}")
            return public_id
            
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            raise UploadError(f"Failed to upload to Cloudinary: {e}")
    
    async def download(self, public_id: str) -> bytes:
        """
        Download file from Cloudinary.
        
        Args:
            public_id: Cloudinary public_id
            
        Returns:
            File content as bytes
        """
        try:
            import cloudinary.utils
            import aiohttp
            
            # Get URL for download
            url = cloudinary.utils.cloudinary_url(public_id, resource_type='auto')[0]
            
            # Download file
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 404:
                        raise FileNotFoundError(f"File not found: {public_id}")
                    response.raise_for_status()
                    return await response.read()
                    
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Cloudinary download failed: {e}")
            raise DownloadError(f"Failed to download from Cloudinary: {e}")
    
    async def delete(self, public_id: str) -> bool:
        """
        Delete file from Cloudinary.
        
        Args:
            public_id: Cloudinary public_id
            
        Returns:
            True if deleted
        """
        try:
            import cloudinary.uploader
            
            result = cloudinary.uploader.destroy(public_id, resource_type='auto')
            
            if result.get('result') == 'ok':
                logger.info(f"File deleted from Cloudinary: {public_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Cloudinary delete failed: {e}")
            return False
    
    async def get_url(
        self,
        public_id: str,
        expires_in: Optional[int] = None,
        transformations: Optional[dict] = None,
    ) -> str:
        """
        Get URL for a file.
        
        Args:
            public_id: Cloudinary public_id
            expires_in: Ignored (Cloudinary uses signed URLs)
            transformations: Image transformations
            
        Returns:
            Cloudinary URL
        """
        import cloudinary.utils
        
        if transformations:
            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type='auto',
                transformation=transformations
            )[0]
        else:
            url = cloudinary.utils.cloudinary_url(public_id, resource_type='auto')[0]
        
        return url
    
    async def exists(self, public_id: str) -> bool:
        """
        Check if a file exists in Cloudinary.
        
        Args:
            public_id: Cloudinary public_id
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            import cloudinary.api
            
            result = cloudinary.api.resource(public_id, resource_type='auto')
            return result is not None
            
        except Exception:
            return False
    
    async def get_metadata(self, public_id: str) -> Optional[StorageFile]:
        """
        Get metadata for a file.
        
        Args:
            public_id: Cloudinary public_id
            
        Returns:
            StorageFile object or None
        """
        try:
            import cloudinary.api
            
            result = cloudinary.api.resource(public_id, resource_type='auto')
            
            return StorageFile(
                filename=public_id.split('/')[-1],
                size=result.get('bytes', 0),
                content_type=result.get('resource_type', 'image'),
                url=await self.get_url(public_id),
                path=public_id,
                created_at=datetime.fromisoformat(result.get('created_at', '').replace('Z', '+00:00')),
                etag=result.get('etag', ''),
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
        List files in Cloudinary.
        
        Args:
            prefix: Filter by public_id prefix
            limit: Maximum number of files
            
        Returns:
            List of StorageFile objects
        """
        try:
            import cloudinary.api
            
            result = cloudinary.api.resources(
                resource_type='auto',
                prefix=prefix,
                max_results=limit,
            )
            
            files = []
            for resource in result.get('resources', []):
                metadata = await self.get_metadata(resource['public_id'])
                if metadata:
                    files.append(metadata)
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def _generate_public_id(self, filename: str) -> str:
        """
        Generate a unique public_id for a file.
        
        Args:
            filename: Original filename
            
        Returns:
            Unique public_id
        """
        import uuid
        from pathlib import Path
        
        ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        
        # Organize by date
        from datetime import datetime
        date_path = datetime.utcnow().strftime("%Y/%m/%d")
        
        return f"{date_path}/{unique_name}"


__all__ = ["CloudinaryProvider"]