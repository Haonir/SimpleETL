"""Image extraction and Base64 encoding utilities for docx and PDF files."""

from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractedImage:
    """Represents an image extracted from a document."""
    content_type: str  # e.g. "image/png", "image/jpeg"
    base64_data: str   # Base64-encoded image content
    filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


def images_from_docx(file_path: str | Path) -> list[ExtractedImage]:
    """Extract all images from a .docx file and encode as Base64.
    
    Uses python-docx to access inline shapes and relationship parts.
    
    Args:
        file_path: Path to the .docx file.
        
    Returns:
        List of ExtractedImage objects with Base64-encoded data.
        
    Raises:
        ImportError: If python-docx is not installed.
    """
    try:
        import docx
    except ImportError:
        raise ImportError(
            "python-docx is required for image extraction. "
            "Install with: pip install python-docx"
        )
    
    images: list[ExtractedImage] = []
    doc = docx.Document(str(file_path))
    
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            try:
                blob = rel.target_part.blob
                content_type = rel.target_part.content_type
                
                # Determine extension from content type
                ext_map = {
                    "image/png": "png",
                    "image/jpeg": "jpeg",
                    "image/gif": "gif",
                    "image/bmp": "bmp",
                    "image/tiff": "tiff",
                }
                ext = ext_map.get(content_type, "png")
                
                b64 = base64.b64encode(blob).decode("utf-8")
                
                # Try to get dimensions for PNG/JPEG
                width, height = _get_image_dimensions(blob, content_type)
                
                img = ExtractedImage(
                    content_type=content_type,
                    base64_data=b64,
                    filename=f"image_{len(images):03d}.{ext}",
                    width=width,
                    height=height,
                )
                images.append(img)
                logger.debug("Extracted image: %s (%s, %d bytes)", img.filename, content_type, len(blob))
            except Exception as e:
                logger.warning("Failed to extract image from docx rel %s: %s", rel.rId, e)
    
    logger.info("Extracted %d images from %s", len(images), file_path)
    return images


def images_from_pdf(file_path: str | Path) -> list[ExtractedImage]:
    """Extract all images from a PDF file and encode as Base64.
    
    Uses PyMuPDF (fitz) to extract embedded images from each page.
    
    Args:
        file_path: Path to the PDF file.
        
    Returns:
        List of ExtractedImage objects with Base64-encoded data.
        
    Raises:
        ImportError: If PyMuPDF is not installed.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF is required for PDF image extraction. "
            "Install with: pip install PyMuPDF"
        )
    
    images: list[ExtractedImage] = []
    doc = fitz.open(str(file_path))
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        
        for img_idx, img_info in enumerate(image_list):
            try:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                
                if base_image is None:
                    continue
                
                blob = base_image["image"]
                ext = base_image.get("ext", "png")
                width = base_image.get("width")
                height = base_image.get("height")
                
                # Determine content type from extension
                ct_map = {
                    "png": "image/png",
                    "jpeg": "image/jpeg",
                    "jpg": "image/jpeg",
                    "jxr": "image/jxr",
                    "jpx": "image/jpx",
                    "bmp": "image/bmp",
                    "tiff": "image/tiff",
                }
                content_type = ct_map.get(ext, f"image/{ext}")
                
                b64 = base64.b64encode(blob).decode("utf-8")
                
                img = ExtractedImage(
                    content_type=content_type,
                    base64_data=b64,
                    filename=f"page{page_num+1}_img{img_idx+1}.{ext}",
                    width=width,
                    height=height,
                )
                images.append(img)
                logger.debug("Extracted image from page %d: %s", page_num + 1, img.filename)
            except Exception as e:
                logger.warning("Failed to extract image xref=%d from page %d: %s", xref, page_num + 1, e)
    
    doc.close()
    logger.info("Extracted %d images from %s", len(images), file_path)
    return images


def image_to_markdown(img: ExtractedImage) -> str:
    """Convert an ExtractedImage to a markdown image tag with inline Base64.
    
    Returns:
        Markdown string like: ![image](data:image/png;base64,iVBOR...)
    """
    return f"![{img.filename or 'image'}](data:{img.content_type};base64,{img.base64_data})"


def images_to_base64(file_path: str | Path) -> list[ExtractedImage]:
    """Extract images from a file (docx or PDF) and encode as Base64.
    
    Auto-detects file type by extension.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        List of ExtractedImage objects. Empty list if format not supported or no images found.
    """
    ext = Path(file_path).suffix.lower()
    
    if ext in (".docx", ".doc"):
        return images_from_docx(file_path)
    elif ext == ".pdf":
        return images_from_pdf(file_path)
    else:
        logger.debug("No image extraction supported for format: %s", ext)
        return []


def _get_image_dimensions(blob: bytes, content_type: str) -> tuple[Optional[int], Optional[int]]:
    """Try to get image dimensions from raw bytes. Returns (width, height) or (None, None)."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(blob))
        return img.size  # (width, height)
    except Exception:
        return None, None
