# ============================
# WOLLOYEWA STORE BOT - S3 STORAGE PROVIDER
# ============================
"""AWS S3 storage provider for production file storage."""

import os
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


class S3StorageProvider(StorageProvider):
    """
    AWS S3 storage provider.
    
    Features:
    - Secure file storage in S3 buckets
    - Signed URLs for temporary access
    - Automatic bucket creation
    - Metadata support
    """
    
    def __init__(self):
        self._client = None
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        self._initialized = False
    
    async def _get_client(self):
        """Get S3 client (lazy initialization)."""
        if not self._initialized:
            try:
                import aioboto3
                from botocore.exceptions import ClientError
                
                self._session = aioboto3.Session()
                self._client = await self._session.client(
                    's3',
                    region_name=self.region,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                )
                
                # Ensure bucket exists
                await self._ensure_bucket()
                
                self._initialized = True
                logger.info(f"S3 storage initialized: bucket={self.bucket_name}, region={self.region}")
                
            except ImportError:
                logger.warning("aioboto3 not installed. S3 storage will not work.")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                raise
        
        return self._client
    
    async def _ensure_bucket(self) -> None:
        """Ensure the S3 bucket exists."""
        try:
            client = await self._get_client()
            
            # Check if bucket exists
            try:
                await client.head_bucket(Bucket=self.bucket_name)
            except Exception:
                # Create bucket
                if self.region == 'us-east-1':
                    await client.create_bucket(Bucket=self.bucket_name)
                else:
                    await client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                logger.info(f"Created S3 bucket: {self.bucket_name}")
                
        except Exception as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise
    
    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload file to S3.
        
        Args:
            file_data: File content as bytes
            filename: Original filename
            content_type: MIME type of the file
            metadata: Additional metadata to store
            
        Returns:
            S3 key (path) of the uploaded file
        """
        try:
            client = await self._get_client()
            
            # Generate unique key
            key = self._generate_path(filename)
            content_type = content_type or self._get_content_type(filename)
            
            # Prepare extra args
            extra_args = {
                'ContentType': content_type,
                'Metadata': metadata or {},
            }
            
            # Upload file
            await client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data,
                **extra_args
            )
            
            logger.info(f"File uploaded to S3: {key}")
            return key
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise UploadError(f"Failed to upload to S3: {e}")
    
    async def download(self, key: str) -> bytes:
        """
        Download file from S3.
        
        Args:
            key: S3 key of the file
            
        Returns:
            File content as bytes
        """
        try:
            client = await self._get_client()
            
            response = await client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return await response['Body'].read()
            
        except Exception as e:
            if 'NoSuchKey' in str(e):
                raise FileNotFoundError(f"File not found: {key}")
            logger.error(f"S3 download failed: {e}")
            raise DownloadError(f"Failed to download from S3: {e}")
    
    async def delete(self, key: str) -> bool:
        """
        Delete file from S3.
        
        Args:
            key: S3 key of the file
            
        Returns:
            True if deleted
        """
        try:
            client = await self._get_client()
            
            await client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"File deleted from S3: {key}")
            return True
            
        except Exception as e:
            logger.error(f"S3 delete failed: {e}")
            return False
    
    async def get_url(self, key: str, expires_in: Optional[int] = None) -> str:
        """
        Get URL for a file.
        
        Args:
            key: S3 key of the file
            expires_in: Expiration time in seconds (for signed URLs)
            
        Returns:
            File URL
        """
        if expires_in:
            # Generate signed URL
            try:
                client = await self._get_client()
                
                url = await client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': key
                    },
                    ExpiresIn=expires_in
                )
                return url
            except Exception as e:
                logger.error(f"Failed to generate signed URL: {e}")
        
        # Public URL (if bucket is public)
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
    
    async def exists(self, key: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            key: S3 key of the file
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            client = await self._get_client()
            
            await client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
            
        except Exception:
            return False
    
    async def get_metadata(self, key: str) -> Optional[StorageFile]:
        """
        Get metadata for a file.
        
        Args:
            key: S3 key of the file
            
        Returns:
            StorageFile object or None
        """
        try:
            client = await self._get_client()
            
            response = await client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return StorageFile(
                filename=os.path.basename(key),
                size=response['ContentLength'],
                content_type=response.get('ContentType', 'application/octet-stream'),
                url=await self.get_url(key),
                path=key,
                created_at=response.get('LastModified', datetime.utcnow()),
                etag=response.get('ETag', '').strip('"'),
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
        List files in S3 bucket.
        
        Args:
            prefix: Filter by key prefix
            limit: Maximum number of files
            
        Returns:
            List of StorageFile objects
        """
        try:
            client = await self._get_client()
            
            response = await client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=limit
            )
            
            files = []
            for obj in response.get('Contents', []):
                metadata = await self.get_metadata(obj['Key'])
                if metadata:
                    files.append(metadata)
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []


__all__ = ["S3StorageProvider"]