"""Unit tests for etl.extractor module — standalone image OCR support."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.etl.extractor import (
    IMAGE_EXTENSIONS,
    OCR_AVAILABLE,
    extract_text,
)


class TestImageExtensions:
    """Verify IMAGE_EXTENSIONS set contains expected formats."""

    def test_image_extensions_complete(self):
        """IMAGE_EXTENSIONS includes all required image formats."""
        assert ".png" in IMAGE_EXTENSIONS
        assert ".jpg" in IMAGE_EXTENSIONS
        assert ".jpeg" in IMAGE_EXTENSIONS
        assert ".tiff" in IMAGE_EXTENSIONS
        assert ".bmp" in IMAGE_EXTENSIONS
        assert ".webp" in IMAGE_EXTENSIONS


class TestUnsupportedFormat:
    """extract_text raises ValueError for unsupported file formats."""

    def test_txt_raises_unsupported(self, tmp_path: Path):
        """Plain text files are supported — no error."""
        txt = tmp_path / "test.txt"
        txt.write_text("hello")
        result = extract_text(txt)
        assert result == "hello"

    def test_unknown_format_raises_value_error(self, tmp_path: Path):
        """Unknown extension raises ValueError."""
        unknown = tmp_path / "file.xyz"
        unknown.write_bytes(b"data")
        with pytest.raises(ValueError, match="Unsupported file format"):
            extract_text(unknown)


class TestImageOCR:
    """extract_text handles standalone image files via Tesseract OCR."""

    def test_png_extraction_with_mock_ocr(self, tmp_path: Path):
        """PNG image is processed through _extract_image with mocked pytesseract."""
        # Create a minimal valid PNG (1x1 pixel)
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            + b"\x00\x00\x00\rIHDR"
            + b"\x00\x00\x00\x01\x00\x00\x00\x01"
            + b"\x08\x02\x00\x00\x00\x90wS\xde"
            + b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
            + b"\x18\xd8N"
            + b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        png_file = tmp_path / "test.png"
        png_file.write_bytes(png_bytes)

        mock_text = "Mock OCR result for image"
        mock_image = MagicMock()
        mock_pil = MagicMock()

        with patch("app.etl.extractor.pytesseract") as mock_tess, \
             patch("app.etl.extractor.Image", mock_pil):
            mock_tess.image_to_string.return_value = mock_text
            # Force OCR_AVAILABLE to True for this test
            with patch.dict("sys.modules", {"PIL": MagicMock(), "PIL.Image": MagicMock()}):
                from app.etl import extractor as ext_module
                ext_module.OCR_AVAILABLE = True

            result = extract_text(png_file)
            assert result == mock_text
            mock_tess.image_to_string.assert_called_once()
            call_kwargs = mock_tess.image_to_string.call_args
            assert "rus+eng" in str(call_kwargs)

    def test_image_ocr_unavailable_raises_import_error(self, tmp_path: Path):
        """When OCR is not available, extract_text raises ImportError for images."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n")
        with patch("app.etl.extractor.OCR_AVAILABLE", False):
            with pytest.raises(ImportError, match="Tesseract-OCR"):
                extract_text(png_file)

    def test_image_ocr_unavailable_raises_import_error_on_extract(self, tmp_path: Path):
        """When OCR is not available, extract_text raises ImportError for images."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        with patch("app.etl.extractor.pytesseract", None), \
             patch("app.etl.extractor.Image", None):
            from app.etl import extractor as ext_module
            ext_module.OCR_AVAILABLE = False

            with pytest.raises(ImportError, match="Tesseract-OCR"):
                extract_text(png_file)


class TestOCRAvailableFlag:
    """Verify OCR_AVAILABLE is properly checked before image processing."""

    def test_ocr_available_is_boolean(self):
        """OCR_AVAILABLE must be a boolean."""
        assert isinstance(OCR_AVAILABLE, bool)
