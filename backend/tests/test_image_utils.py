"""Unit tests for etl.image_utils module (OCR-only pipeline)."""

from __future__ import annotations

import io
import struct
import zlib
from pathlib import Path

import pytest

from app.etl.image_utils import _get_image_dimensions


def _make_minimal_png(width: int = 10, height: int = 5) -> bytes:
    """Create a minimal valid PNG in memory."""
    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)
    raw = b""
    for y in range(height):
        raw += b"\x00" + bytes(width)
    idat = chunk(b"IDAT", _zlib_compress(raw))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def _zlib_compress(data: bytes) -> bytes:
    """Minimal zlib compression (DEFLATE)."""
    import zlib
    return zlib.compress(data, 1)


class TestGetImageDimensions:
    """Tests for _get_image_dimensions function."""

    def test_valid_png(self):
        """Returns dimensions for a valid PNG."""
        png_bytes = _make_minimal_png(width=200, height=300)
        width, height = _get_image_dimensions(png_bytes, "image/png")
        assert width == 200
        assert height == 300

    def test_invalid_input(self):
        """Returns (None, None) for invalid input."""
        result = _get_image_dimensions(b"not an image", "image/png")
        assert result == (None, None)
