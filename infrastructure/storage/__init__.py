# ============================
# WOLLOYEWA STORE BOT - STORAGE MODULE
# ============================
"""Storage providers for file uploads and media management."""

from infrastructure.storage.base import StorageProvider, StorageFile, StorageException
from infrastructure.storage.local_provider import LocalStorageProvider
from infrastructure.storage.s3_provider import S3StorageProvider
from infrastructure.storage.cloudinary_provider import CloudinaryProvider
from infrastructure.storage.image_processor import ImageProcessor, process_image, generate_thumbnail

# Provider factory
async def get_storage_provider(provider_name: str = None) -> StorageProvider:
    """
    Get storage provider instance.
    
    Args:
        provider_name: Provider name (local, s3, cloudinary)
        
    Returns:
        StorageProvider instance
    """
    provider_name = provider_name or "local"
    
    if provider_name == "s3":
        return S3StorageProvider()
    elif provider_name == "cloudinary":
        return CloudinaryProvider()
    else:
        return LocalStorageProvider()


async def upload_file(file_data: bytes, filename: str, provider: str = None) -> str:
    """Upload file to storage."""
    provider_instance = await get_storage_provider(provider)
    return await provider_instance.upload(file_data, filename)


async def delete_file(file_path: str, provider: str = None) -> bool:
    """Delete file from storage."""
    provider_instance = await get_storage_provider(provider)
    return await provider_instance.delete(file_path)


async def get_file_url(file_path: str, provider: str = None) -> str:
    """Get file URL."""
    provider_instance = await get_storage_provider(provider)
    return await provider_instance.get_url(file_path)


__all__ = [
    "StorageProvider",
    "StorageFile",
    "StorageException",
    "LocalStorageProvider",
    "S3StorageProvider",
    "CloudinaryProvider",
    "ImageProcessor",
    "process_image",
    "generate_thumbnail",
    "get_storage_provider",
    "upload_file",
    "delete_file",
    "get_file_url",
]