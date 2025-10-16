from __future__ import annotations
import os
import uuid
import re
from typing import BinaryIO
from io import BytesIO

from ..core.config import settings
from ..logging_config import get_logger

logger = get_logger(__name__)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and other security issues.

    - Removes path separators and parent directory references
    - Removes null bytes
    - Limits to alphanumeric, dots, hyphens, underscores
    - Extracts extension safely
    - Returns a safe filename or raises ValueError

    Args:
        filename: Original filename from user upload

    Returns:
        Sanitized filename with only safe characters

    Raises:
        ValueError: If filename is invalid or empty after sanitization
    """
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Get basename to remove any path components
    filename = os.path.basename(filename)

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Remove any remaining path separators (., .., /, \)
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')

    # Allow only alphanumeric, dots, hyphens, underscores
    # This prevents shell injection and other attacks
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Remove leading dots (hidden files on Unix)
    filename = filename.lstrip('.')

    # Ensure filename is not empty after sanitization
    if not filename or filename == '_':
        raise ValueError("Invalid filename after sanitization")

    return filename


class StorageService:
    def save(self, fileobj: BinaryIO, filename: str, content_type: str | None = None) -> str:
        raise NotImplementedError


class LocalStorage(StorageService):
    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, fileobj: BinaryIO, filename: str, content_type: str | None = None) -> str:
        # Sanitize filename to prevent path traversal
        safe_filename = sanitize_filename(filename)
        ext = os.path.splitext(safe_filename)[1]
        key = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(self.base_dir, key)
        with open(path, 'wb') as f:
            f.write(fileobj.read())
        # Expose via /static/uploads/<key>
        return f"/static/uploads/{key}"


class S3Storage(StorageService):
    def __init__(self, endpoint_url: str | None, access_key: str, secret_key: str, region: str | None, bucket: str) -> None:
        import boto3  # type: ignore

        self.bucket = bucket
        self.s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def _compress_image(self, fileobj: BinaryIO, content_type: str | None) -> tuple[BinaryIO, str]:
        """Compress and optimize image for storage.

        - Converts to WebP format (60-80% size reduction vs JPEG)
        - Resizes large images to max 1920x1920
        - Optimizes quality to 85%

        Returns tuple of (compressed_fileobj, new_content_type)
        """
        try:
            from PIL import Image

            # Read image
            img = Image.open(fileobj)

            # Convert RGBA to RGB for WebP compatibility
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize if too large (save bandwidth and storage)
            max_dimension = 1920
            if img.width > max_dimension or img.height > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                logger.info(
                    "image_resized",
                    original_size=f"{img.width}x{img.height}",
                    new_size=f"{img.width}x{img.height}"
                )

            # Compress to WebP format
            output = BytesIO()
            img.save(output, format='WEBP', quality=85, optimize=True, method=6)
            output.seek(0)

            original_size = fileobj.tell() if hasattr(fileobj, 'tell') else 0
            compressed_size = output.getbuffer().nbytes
            if original_size > 0:
                reduction_pct = ((original_size - compressed_size) / original_size) * 100
                logger.info(
                    "image_compressed",
                    original_size=original_size,
                    compressed_size=compressed_size,
                    reduction_percent=round(reduction_pct, 1)
                )

            return output, 'image/webp'

        except Exception as e:
            logger.warning(
                "image_compression_failed",
                error=str(e),
                error_type=type(e).__name__,
                fallback="using_original"
            )
            # Return original on error
            fileobj.seek(0)
            return fileobj, content_type or 'application/octet-stream'

    def save(self, fileobj: BinaryIO, filename: str, content_type: str | None = None) -> str:
        # Sanitize filename to prevent path traversal
        safe_filename = sanitize_filename(filename)

        # Compress images before upload (60-80% size reduction)
        if content_type and content_type.startswith('image/'):
            fileobj, content_type = self._compress_image(fileobj, content_type)
            # Change extension to .webp
            ext = '.webp'
        else:
            ext = os.path.splitext(safe_filename)[1]

        key = f"dogs/{uuid.uuid4().hex}{ext}"
        extra_args = {'ContentType': content_type} if content_type else None
        self.s3.upload_fileobj(fileobj, self.bucket, key, ExtraArgs=extra_args or {})

        # Prefer public base URL if provided (for browser access)
        public = (settings.s3_public_base_url or '').rstrip('/') if getattr(settings, 's3_public_base_url', None) else None
        if public:
            return f"{public}/{key}"
        # Else, use endpoint path-style URL
        endpoint = settings.s3_endpoint_url.rstrip('/') if settings.s3_endpoint_url else None
        if endpoint and endpoint.startswith('http'):
            return f"{endpoint}/{settings.s3_bucket}/{key}"
        # Fallback generic URL
        return f"s3://{settings.s3_bucket}/{key}"


def get_storage() -> StorageService:
    if settings.storage_backend == 's3':
        if not all([settings.s3_access_key, settings.s3_secret_key, settings.s3_bucket]):
            raise RuntimeError("S3 storage misconfigured: missing access/secret/bucket")
        return S3Storage(
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key or '',
            secret_key=settings.s3_secret_key or '',
            region=settings.s3_region,
            bucket=settings.s3_bucket or '',
        )
    # default local
    return LocalStorage(settings.storage_local_dir)
