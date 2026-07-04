"""Unit tests for etl.image_utils module."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from app.etl.image_utils import (
    ExtractedImage,
    image_to_markdown,
    images_to_base64,
)


class TestExtractedImage:
    """Tests for ExtractedImage dataclass."""

    def test_create_image(self):
        """Can create an ExtractedImage with required fields."""
        img = ExtractedImage(
            content_type="image/png",
            base64_data="abc123",
        )
        assert img.content_type == "image/png"
        assert img.base64_data == "abc123"
        assert img.filename is None
        assert img.width is None
        assert img.height is None

    def test_create_with_all_fields(self):
        """Can create with all fields populated."""
        img = ExtractedImage(
            content_type="image/jpeg",
            base64_data="xyz",
            filename="photo.jpg",
            width=800,
            height=600,
        )
        assert img.filename == "photo.jpg"
        assert img.width == 800
        assert img.height == 600


class TestImageToMarkdown:
    """Tests for image_to_markdown function."""

    def test_basic_conversion(self):
        """Converts image to inline base64 markdown."""
        img = ExtractedImage(
            content_type="image/png",
            base64_data="iVBORw0KGgo",
            filename="test.png",
        )
        result = image_to_markdown(img)
        assert result == "![test.png](data:image/png;base64,iVBORw0KGgo)"

    def test_no_filename(self):
        """Uses 'image' as default alt text when no filename."""
        img = ExtractedImage(
            content_type="image/gif",
            base64_data="R0lGODlh",
        )
        result = image_to_markdown(img)
        assert result.startswith("![image](data:image/gif;base64,")


class TestImagesToBase64:
    """Tests for images_to_base64 dispatcher."""

    def test_unsupported_format_returns_empty(self, tmp_path: Path):
        """Unsupported file format returns empty list."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello")
        result = images_to_base64(txt_file)
        assert result == []

    def test_nonexistent_file_raises(self, tmp_path: Path):
        """Nonexistent file raises an error."""
        with pytest.raises(Exception):
            images_to_base64(tmp_path / "nonexistent.pdf")
