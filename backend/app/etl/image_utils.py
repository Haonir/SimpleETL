"""Image utility functions for dimension detection (OCR-only pipeline)."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _get_image_dimensions(blob: bytes, content_type: str) -> tuple[Optional[int], Optional[int]]:
    """Try to get image dimensions from raw bytes. Returns (width, height) or (None, None)."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(blob))
        return img.size  # (width, height)
    except Exception:
        return None, None
