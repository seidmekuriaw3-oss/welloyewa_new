# ============================
# WOLLOYEWA STORE BOT - MEDIA OPTIMIZER
# ============================
"""Image and media optimization utilities."""

import io
import os
import hashlib
from typing import Optional, Tuple, Union
from dataclasses import dataclass
from PIL import Image, ImageOps, ImageFilter

from core.logger import logger
from core.constants import MAX_IMAGE_SIZE_BYTES, ALLOWED_IMAGE_TYPES


@dataclass
class OptimizedImage:
    """Result of image optimization."""
    
    data: bytes
    format: str
    width: int
    height: int
    size_bytes: int
    mime_type: str
    thumbnail_data: Optional[bytes] = None


class MediaOptimizer:
    """
    Image optimization and processing utilities.
    
    Supports:
    - Resizing and scaling
    - Compression
    - Format conversion
    - Thumbnail generation
    - Watermarking
    """
    
    # Quality settings (1-100)
    JPEG_QUALITY = 85
    PNG_OPTIMIZE = True
    WEBP_QUALITY = 80
    
    # Size limits
    MAX_WIDTH = 2000
    MAX_HEIGHT = 2000
    THUMBNAIL_SIZE = (300, 300)
    
    def __init__(self, quality: int = 85, max_size: Tuple[int, int] = (2000, 2000)):
        self.quality = quality
        self.max_width, self.max_height = max_size
    
    @classmethod
    def get_image_dimensions(cls, image_data: bytes) -> Tuple[int, int]:
        """Get image dimensions from bytes."""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                return img.size
        except Exception as e:
            logger.error(f"Failed to get image dimensions: {e}")
            return (0, 0)
    
    @classmethod
    def detect_format(cls, image_data: bytes) -> Optional[str]:
        """Detect image format from bytes."""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                return img.format.lower()
        except Exception:
            return None
    
    def resize_image(
        self,
        image_data: bytes,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        maintain_aspect: bool = True,
    ) -> bytes:
        """
        Resize image to fit within dimensions.
        
        Args:
            image_data: Original image bytes
            max_width: Maximum width (default self.max_width)
            max_height: Maximum height (default self.max_height)
            maintain_aspect: Whether to maintain aspect ratio
            
        Returns:
            Resized image bytes
        """
        max_w = max_width or self.max_width
        max_h = max_height or self.max_height
        
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                original_format = img.format
                
                # Convert RGBA to RGB for JPEG
                if original_format == 'PNG' and img.mode == 'RGBA':
                    # Create white background for transparency
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
                output = io.BytesIO()
                save_format = 'JPEG' if original_format in ['JPEG', 'JPG'] else 'PNG'
                img.save(output, format=save_format, quality=self.quality, optimize=True)
                
                return output.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to resize image: {e}")
            return image_data
    
    def compress_image(
        self,
        image_data: bytes,
        quality: Optional[int] = None,
        format: Optional[str] = None,
    ) -> bytes:
        """
        Compress image to reduce file size.
        
        Args:
            image_data: Original image bytes
            quality: JPEG/WebP quality (1-100)
            format: Output format (jpeg, png, webp)
            
        Returns:
            Compressed image bytes
        """
        quality = quality or self.quality
        
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                original_format = img.format
                output_format = format or original_format
                output_format = output_format.upper()
                
                # Handle transparency for PNG
                if output_format == 'PNG' and img.mode == 'RGBA':
                    img = img.convert('RGBA')
                elif output_format in ('JPEG', 'JPG') and img.mode in ('RGBA', 'P'):
                    # Convert to RGB for JPEG
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        rgb_img.paste(img, mask=img.split()[3])
                    else:
                        rgb_img.paste(img)
                    img = rgb_img
                    output_format = 'JPEG'
                
                output = io.BytesIO()
                
                save_kwargs = {'optimize': True}
                if output_format in ('JPEG', 'JPG'):
                    save_kwargs['quality'] = quality
                    save_kwargs['progressive'] = True
                elif output_format == 'WEBP':
                    save_kwargs['quality'] = quality
                elif output_format == 'PNG':
                    save_kwargs['compress_level'] = 6
                
                img.save(output, format=output_format, **save_kwargs)
                compressed = output.getvalue()
                
                # Return original if compression didn't help
                if len(compressed) >= len(image_data):
                    return image_data
                
                return compressed
                
        except Exception as e:
            logger.error(f"Failed to compress image: {e}")
            return image_data
    
    def generate_thumbnail(
        self,
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
        size = size or self.THUMBNAIL_SIZE
        target_width, target_height = size
        
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert mode if needed
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
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
                
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=75, optimize=True)
                
                return output.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return image_data
    
    def add_watermark(
        self,
        image_data: bytes,
        watermark_text: str,
        opacity: int = 128,
    ) -> bytes:
        """
        Add text watermark to image.
        
        Args:
            image_data: Original image bytes
            watermark_text: Text to add as watermark
            opacity: Opacity of watermark (0-255)
            
        Returns:
            Watermarked image bytes
        """
        try:
            from PIL import ImageDraw, ImageFont
            
            with Image.open(io.BytesIO(image_data)) as img:
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Create overlay for watermark
                overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                
                # Try to load a font
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
                except (OSError, IOError):
                    font = ImageFont.load_default()
                
                # Calculate text position (bottom right)
                bbox = draw.textbbox((0, 0), watermark_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                position = (
                    img.width - text_width - 20,
                    img.height - text_height - 20,
                )
                
                # Draw watermark
                draw.text(position, watermark_text, fill=(255, 255, 255, opacity), font=font)
                
                # Composite overlay
                watermarked = Image.alpha_composite(img, overlay)
                
                # Convert back to RGB
                background = Image.new('RGB', watermarked.size, (255, 255, 255))
                background.paste(watermarked, mask=watermarked.split()[3])
                
                output = io.BytesIO()
                background.save(output, format='JPEG', quality=self.quality)
                
                return output.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to add watermark: {e}")
            return image_data
    
    def optimize(
        self,
        image_data: bytes,
        generate_thumbnail: bool = True,
        max_size_bytes: int = MAX_IMAGE_SIZE_BYTES,
    ) -> OptimizedImage:
        """
        Full image optimization pipeline.
        
        Args:
            image_data: Original image bytes
            generate_thumbnail: Whether to generate thumbnail
            max_size_bytes: Maximum allowed file size
            
        Returns:
            OptimizedImage object with processed data
        """
        # Detect format and dimensions
        with Image.open(io.BytesIO(image_data)) as img:
            original_format = img.format
            width, height = img.size
            mime_type = f"image/{original_format.lower()}"
        
        # Resize if needed
        if width > self.max_width or height > self.max_height:
            image_data = self.resize_image(image_data)
        
        # Compress
        compressed = self.compress_image(image_data)
        
        # Compress more if still too large
        if len(compressed) > max_size_bytes:
            # Reduce quality progressively
            for quality in [70, 60, 50]:
                compressed = self.compress_image(compressed, quality=quality)
                if len(compressed) <= max_size_bytes:
                    break
        
        # Generate thumbnail if requested
        thumbnail = None
        if generate_thumbnail:
            thumbnail = self.generate_thumbnail(compressed)
        
        # Get final dimensions
        with Image.open(io.BytesIO(compressed)) as img:
            final_width, final_height = img.size
        
        return OptimizedImage(
            data=compressed,
            format=original_format,
            width=final_width,
            height=final_height,
            size_bytes=len(compressed),
            mime_type=mime_type,
            thumbnail_data=thumbnail,
        )
    
    @staticmethod
    def generate_filename(original_filename: str, prefix: str = "") -> str:
        """Generate a unique filename for uploaded media."""
        name, ext = os.path.splitext(original_filename)
        ext = ext.lower()
        
        # Generate hash of content for uniqueness
        timestamp = str(int(__import__('time').time()))
        unique_id = hashlib.md5(f"{name}{timestamp}".encode()).hexdigest()[:12]
        
        if prefix:
            return f"{prefix}_{unique_id}{ext}"
        return f"{unique_id}{ext}"
    
    @staticmethod
    def validate_image(image_data: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate image file.
        
        Args:
            image_data: Image bytes to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        if len(image_data) > MAX_IMAGE_SIZE_BYTES:
            max_mb = MAX_IMAGE_SIZE_BYTES // (1024 * 1024)
            return False, f"Image too large. Maximum size: {max_mb}MB"
        
        # Try to open as image
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Check format
                if img.format.lower() not in [t.split('/')[-1] for t in ALLOWED_IMAGE_TYPES]:
                    return False, f"Unsupported image format. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
                
                # Check dimensions
                width, height = img.size
                if width < 100 or height < 100:
                    return False, "Image too small. Minimum size: 100x100 pixels"
                
                if width > 5000 or height > 5000:
                    return False, "Image too large. Maximum size: 5000x5000 pixels"
                
                return True, None
                
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"


# Global media optimizer instance
media_optimizer = MediaOptimizer()


def optimize_image(image_data: bytes, **kwargs) -> OptimizedImage:
    """Convenience function for image optimization."""
    return media_optimizer.optimize(image_data, **kwargs)


def generate_thumbnail(image_data: bytes, size: Tuple[int, int] = None) -> bytes:
    """Convenience function for thumbnail generation."""
    return media_optimizer.generate_thumbnail(image_data, size)


def get_image_dimensions(image_data: bytes) -> Tuple[int, int]:
    """Convenience function to get image dimensions."""
    return MediaOptimizer.get_image_dimensions(image_data)


def compress_image(image_data: bytes, quality: int = 85) -> bytes:
    """Compress image to reduce file size."""
    return media_optimizer.compress_image(image_data, quality=quality)


__all__ = [
    "MediaOptimizer",
    "OptimizedImage",
    "media_optimizer",
    "optimize_image",
    "generate_thumbnail",
    "get_image_dimensions",
    "compress_image",
]