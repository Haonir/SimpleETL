"""Text and image extraction from documents (.txt, .md, .docx, .pdf).

Supports:
- Plain text files (.txt, .md)
- Word documents (.docx) via python-docx
- PDF documents (.pdf) via PyMuPDF with optional Tesseract OCR

No imports from core/ — self-contained backend module.
"""

from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.etl.image_utils import ExtractedImage, images_to_base64

logger = logging.getLogger(__name__)

# Optional dependencies — graceful fallback
try:
    import docx
except ImportError:
    docx = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pytesseract
    from PIL import Image
    pytesseract.get_tesseract_version()
    OCR_AVAILABLE = True
except Exception:
    pytesseract = None
    Image = None
    OCR_AVAILABLE = False


@dataclass
class ExtractionResult:
    """Result of document extraction."""
    text: str
    images: list[ExtractedImage] = field(default_factory=list)
    file_path: str = ""
    file_type: str = ""


def extract_text(file_path: str | Path, log_callback: Optional[callable] = None) -> str:
    """Extract text content from a file.
    
    Auto-detects file type by extension and delegates to the appropriate extractor.
    
    Args:
        file_path: Path to the file.
        log_callback: Optional logging callback.
        
    Returns:
        Extracted text content.
        
    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file format is not supported.
        Exception: If extraction fails.
    """
    file_path = str(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    ext = Path(file_path).suffix.lower()
    
    if ext in (".txt", ".md"):
        return _extract_plain(file_path)
    elif ext in (".docx", ".doc"):
        return _extract_docx(file_path, log_callback)
    elif ext == ".pdf":
        return _extract_pdf(file_path, log_callback)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def extract_images(file_path: str | Path, log_callback: Optional[callable] = None) -> list[ExtractedImage]:
    """Extract images from a document file.
    
    Only supported for .docx and .pdf formats.
    
    Args:
        file_path: Path to the file.
        log_callback: Optional logging callback.
        
    Returns:
        List of ExtractedImage objects. Empty list for unsupported formats.
    """
    try:
        return images_to_base64(file_path)
    except ImportError as e:
        if log_callback:
            log_callback(f"⚠️ Image extraction unavailable: {e}")
        return []
    except Exception as e:
        if log_callback:
            log_callback(f"⚠️ Failed to extract images: {e}")
        return []


def extract_all(
    file_path: str | Path,
    log_callback: Optional[callable] = None,
) -> ExtractionResult:
    """Extract both text and images from a document.
    
    Args:
        file_path: Path to the file.
        log_callback: Optional logging callback.
        
    Returns:
        ExtractionResult with text and images.
    """
    file_path = str(file_path)
    ext = Path(file_path).suffix.lower()
    
    text = extract_text(file_path, log_callback)
    images = extract_images(file_path, log_callback)
    
    if images and log_callback:
        log_callback(f"📷 Extracted {len(images)} images from {Path(file_path).name}")
    
    return ExtractionResult(
        text=text,
        images=images,
        file_path=file_path,
        file_type=ext.lstrip("."),
    )


# ── Internal extractors ──────────────────────────────────────────────────────


def _extract_plain(file_path: str) -> str:
    """Extract text from plain text files (.txt, .md)."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def _extract_docx(file_path: str, log_callback: Optional[callable] = None) -> str:
    """Extract text from Word documents (.docx) via python-docx."""
    if docx is None:
        raise ImportError(
            "python-docx is required for .docx files. "
            "Install with: pip install python-docx"
        )
    
    if log_callback:
        log_callback("Reading Word document...")
    
    try:
        document = docx.Document(file_path)
        paragraphs = [p.text for p in document.paragraphs]
        text = "\n".join(paragraphs)
        
        if not text.strip():
            # Try extracting from tables as fallback
            table_text = []
            for table in document.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text for cell in row.cells)
                    if row_text.strip():
                        table_text.append(row_text)
            if table_text:
                text = "\n".join(table_text)
        
        return text
    except Exception as e:
        raise Exception(
            f"Failed to read Word document. "
            f"If it's an old .doc format, convert to .docx first. Error: {e}"
        )


def _extract_pdf(file_path: str, log_callback: Optional[callable] = None) -> str:
    """Extract text from PDF files via PyMuPDF, with optional OCR fallback."""
    if fitz is None:
        raise ImportError(
            "PyMuPDF is required for .pdf files. "
            "Install with: pip install PyMuPDF"
        )
    
    if log_callback:
        log_callback("Reading PDF document...")
    
    try:
        doc = fitz.open(file_path)
        pages_text = []
        ocr_used = False
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            
            if text.strip():
                pages_text.append(text)
            elif OCR_AVAILABLE:
                if log_callback:
                    log_callback(f"  Page {page_num + 1}: no text found, running OCR...")
                ocr_text = _ocr_pdf_page(page)
                if ocr_text:
                    pages_text.append(ocr_text)
                    ocr_used = True
                else:
                    if log_callback:
                        log_callback(f"  ⚠️ Page {page_num + 1}: OCR returned no text")
            else:
                if log_callback:
                    log_callback(
                        f"  ⚠️ Page {page_num + 1}: no text found "
                        f"(install Tesseract-OCR for scanned PDFs)"
                    )
        
        doc.close()
        
        if ocr_used and log_callback:
            log_callback("✅ OCR recognition complete.")
        
        return "\n".join(pages_text)
    except Exception as e:
        raise Exception(f"Failed to read PDF file: {e}")


def _ocr_pdf_page(page) -> str:
    """Recognize text on a PDF page via Tesseract OCR."""
    if not OCR_AVAILABLE:
        return ""
    
    try:
        pix = page.get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang="rus+eng")
        return text.strip()
    except Exception as e:
        logger.warning("OCR failed on PDF page: %s", e)
        return ""
