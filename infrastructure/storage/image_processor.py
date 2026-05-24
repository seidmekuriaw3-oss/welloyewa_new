# ============================
# WOLLOYEWA STORE BOT - IMAGE PROCESSOR
# ============================
"""Image processing utilities for resizing, optimization, and thumbnails."""

from typing import Optional, Tuple, Union
from io import BytesIO
from PIL import Image, ImageOps, ImageFilter

from core.logger import logger
from core.constants import MAX_IMAGE_SIZE_BYTES, ALLOWED_IMAGE_TYPES


class ImageProcessor:
    """
    Image processing utilities.
    
    Features:
    - Resize and crop images
    - Generate thumbnails
    - Optimize image quality
    - Convert between formats
    - Apply watermarks
    """
    
    # Default settings
    DEFAULT_QUALITY = 85
    DEFAULT_THUMBNAIL_SIZE = (300, 300)
    MAX_DIMENSION = 2000
    
    @classmethod
    def get_image_dimensions(cls, image_data: bytes) -> Tuple[int, int]:
        """Get image dimensions (width, height)."""
        try:
            with Image.open(BytesIO(image_data)) as img:
                return img.size
        except Exception as e:
            logger.error(f"Failed to get image dimensions: {e}")
            return (0, 0)
    
    @classmethod
    def get_image_format(cls, image_data: bytes) -> Optional[str]:
        """Get image format."""
        try:
            with Image.open(BytesIO(image_data)) as img:
                return img.format.lower()
        except Exception as e:
            logger.error(f"Failed to get image format: {e}")
            return None
    
    @classmethod
    def resize(
        cls,
        image_data: bytes,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        maintain_aspect: bool = True,
    ) -> bytes:
        """
        Resize image to fit within dimensions.
        
        Args:
            image_data: Original image bytes
            max_width: Maximum width (default MAX_DIMENSION)
            max_height: Maximum height (default MAX_DIMENSION)
            maintain_aspect: Whether to maintain aspect ratio
            
        Returns:
            Resized image bytes
        """
        max_w = max_width or cls.MAX_DIMENSION
        max_h = max_height or cls.MAX_DIMENSION
        
        try:
            with Image.open(BytesIO(image_data)) as img:
                original_format = img.format
                
                # Convert RGBA to RGB for JPEG
                if original_format in ('PNG', 'JPEG') and img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
                # Resize
                if maintain_aspect:
                    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                else:
                    img = img.resize((max_w, max_h), Image.Resampling.LANCZOS)
                
                # Save to bytes
                output = BytesIO()
                save_format = 'JPEG' if original_format in ('JPEG', 'JPG') else 'PNG'
                img.save(output, format=save_format, quality=cls.DEFAULT_QUALITY, optimize=True)
                
                return output.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to resize image: {e}")
            return image_data
    
    @classmethod
    def crop(
        cls,
        image_data: bytes,
        left: int,
        top: int,
        right: int,
        bottom: int,
    ) -> bytes:
        """
        Crop image to specified rectangle.
        
        Args:
            image_data: Original image bytes
            left: Left coordinate
            top: Top coordinate
            right: Right coordinate
            bottom: Bottom coordinate
            
        Returns:
            Cropped image bytes
        """
        try:
            with Image.open(BytesIO(image_data)) as img:
                cropped = img.crop((left, top, right, bottom))
                
                output = BytesIO()
                cropped.save(output, format=img.format, quality=cls.DEFAULT_QUALITY)
                return output.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to crop image: {e}")
            return image_data
    
    @classmethod
    def crop_center(cls, image_data: bytes, size: Tuple[int, int]) -> bytes:
        """
        Crop image from center to specified size.
        
        Args:
            image_data: Original image bytes
            size: Target size (width, height)
            
        Returns:
            Cropped image bytes
        """
        target_width, target_height = size
        
        try:
            with Image.open(BytesIO(image_data)) as img:
                width, height = img.size
                
                # Calculate crop box
                left = (width - target_width) // 2
                top = (height - target_height) // 2
                right = left + target_width
                bottom = top + target_height
                
                cropped = img.crop((left, top, right, bottom))
                
                output = BytesIO()
                cropped.save(output, format=img.format, quality=cls.DEFAULT_QUALITY)
                return output.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to crop image from center: {e}")
            return image_data
    
    @classmethod
    def generate_thumbnail(
        cls,
        image_data: bytes,
        size: Tuple[int, int] = None,
        crop: bool = True,
    ) -> bytes:
        """
        Generate thumbnail from image.
        
        Args:
            image_data: Original image bytes
            size: Target size (width, height)
            crop: Whether to crop to exact size
            
        Returns:
            Thumbnail bytes
        """
        size = size or cls.DEFAULT_THUMBNAIL_SIZE
        target_width, target_height = size
        
        try:
            with Image.open(BytesIO(image_data)) as img:
                if crop:
                    # Calculate crop box for center crop
                    img_ratio = img.width / img.height
                    target_ratio = target_width / target_height
                    
                    if img_ratio > target_ratio:
                        # Crop width
                        new_width = int(target_ratio * img.height)
                        offset = (img.width - new_width) // 2
                        img = img.crop((offset, 0, offset + new_width, img.height))
                    else:
                        # Crop height
                        new_height = int(img.width / target_ratio)
                        offset = (img.height - new_height) // 2
                        img = img.crop((0, offset, img.width, offset + new_height))
                    
                    img = img.resize(size, Image.Resampling.LANCZOS)
                else:
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Apply sharpening for better quality
                img = img.filter(ImageFilter.UnsharpMask(radius=0.5, percent=50))
                
                output = BytesIO()
                img.save(output, format='JPEG', quality=75, optimize=True)
                
                return output.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return image_data
    
    @classmethod
    def optimize(
        cls,
        image_data: bytes,
        quality: Optional[int] = None,
        max_size_bytes: int = MAX_IMAGE_SIZE_BYTES,
    ) -> bytes:
        """
        Optimize image for web.
        
        Args:
            image_data: Original image bytes
            quality: JPEG quality (1-100)
            max_size_bytes: Maximum file size
            
        Returns:
            Optimized image bytes
        """
        quality = quality or cls.DEFAULT_QUALITY
        
        try:
            with Image.open(BytesIO(image_data)) as img:
                original_format = img.format
                output_format = 'JPEG' if original_format in ('JPEG', 'JPG') else 'PNG'
                
                # Resize if too large
                if img.width > cls.MAX_DIMENSION or img.height > cls.MAX_DIMENSION:
                    img.thumbnail((cls.MAX_DIMENSION, cls.MAX_DIMENSION), Image.Resampling.LANCZOS)
                
                output = BytesIO()
                save_kwargs = {'optimize': True}
                
                if output_format == 'JPEG':
                    save_kwargs['quality'] = quality
                    save_kwargs['progressive'] = True
                elif output_format == 'PNG':
                    save_kwargs['compress_level'] = 6
                
                img.save(output, format=output_format, **save_kwargs)
                optimized = output.getvalue()
                
                # Reduce quality if still too large
                if len(optimized) > max_size_bytes and output_format == 'JPEG':
                    for q in [70, 60, 50]:
                        output = BytesIO()
                        img.save(output, format='JPEG', quality=q, optimize=True, progressive=True)
                        compressed = output.getvalue()
                        if len(compressed) <= max_size_bytes:
                            optimized = compressed
                            break
                
                return optimized
                
        except Exception as e:
            logger.error(f"Failed to optimize image: {e}")
            return image_data


async def process_image(
    image_data: bytes,
    resize: Optional[Tuple[int, int]] = None,
    thumbnail: bool = False,
    optimize: bool = True,
) -> bytes:
    """
    Process image with common operations.
    
    Args:
        image_data: Original image bytes
        resize: Target size (width, height) for resizing
        thumbnail: Whether to generate thumbnail
        optimize: Whether to optimize image
        
    Returns:
        Processed image bytes
    """
    result = image_data
    
    if resize:
        result = ImageProcessor.resize(result, max_width=resize[0], max_height=resize[1])
    
    if thumbnail:
        result = ImageProcessor.generate_thumbnail(result)
    
    if optimize:
        result = ImageProcessor.optimize(result)
    
    return result


async def generate_thumbnail(
    image_data: bytes,
    size: Tuple[int, int] = (300, 300),
) -> bytes:
    """Generate thumbnail from image."""
    return ImageProcessor.generate_thumbnail(image_data, size)


__all__ = [
    "ImageProcessor",
    "process_image",
    "generate_thumbnail",
]