# ============================
# WOLLOYEWA STORE BOT - STORAGE MODULE
# ============================
"""Storage providers for file uploads and media management."""

from infrastructure.storage.base import StorageException, StorageFile, StorageProvider
from infrastructure.storage.cloudinary_provider import CloudinaryProvider
from infrastructure.storage.image_processor import ImageProcessor, generate_thumbnail, process_image
from infrastructure.storage.local_provider import LocalStorageProvider
from infrastructure.storage.s3_provider import S3StorageProvider


# Provider factory
async def get_storage_provider(provider_name: str | None = None) -> StorageProvider:
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


async def upload_file(file_data: bytes, filename: str, provider: str | None = None) -> str:
    """Upload file to storage."""
    provider_instance = await get_storage_provider(provider)
    return await provider_instance.upload(file_data, filename)


async def delete_file(file_path: str, provider: str | None = None) -> bool:
    """Delete file from storage."""
    provider_instance = await get_storage_provider(provider)
    return await provider_instance.delete(file_path)


async def get_file_url(file_path: str, provider: str | None = None) -> str:
    """Get file URL."""
    provider_instance = await get_storage_provider(provider)
    return await provider_instance.get_url(file_path)


__all__ = [
    "CloudinaryProvider",
    "ImageProcessor",
    "LocalStorageProvider",
    "S3StorageProvider",
    "StorageException",
    "StorageFile",
    "StorageProvider",
    "delete_file",
    "generate_thumbnail",
    "get_file_url",
    "get_storage_provider",
    "process_image",
    "upload_file",
]
