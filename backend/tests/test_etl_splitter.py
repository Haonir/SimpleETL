"""Unit tests for etl.splitter module."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.etl.splitter import split_to_chunks, list_chunks, get_chunk_count


class TestSplitToChunks:
    """Tests for split_to_chunks function."""

    def test_basic_split(self, tmp_path: Path):
        """Splitting a short text produces one chunk."""
        text = "Hello world. This is a test."
        chunks = split_to_chunks(text, tmp_path, chunk_size=1000, chunk_overlap=100)
        assert len(chunks) == 1
        assert chunks[0].endswith(".md")

    def test_large_text_multiple_chunks(self, tmp_path: Path):
        """Splitting a large text produces multiple chunks."""
        text = "word " * 5000  # ~25000 chars
        chunks = split_to_chunks(text, tmp_path, chunk_size=5000, chunk_overlap=500)
        assert len(chunks) > 1

    def test_chunks_are_saved_as_files(self, tmp_path: Path):
        """Each chunk is saved as a .md file."""
        text = "First paragraph.\n\nSecond paragraph.\n\n" * 100
        chunk_files = split_to_chunks(text, tmp_path, chunk_size=500, chunk_overlap=50, base_name="test")
        for fp in chunk_files:
            assert os.path.exists(fp)
            assert fp.endswith(".md")

    def test_chunk_naming_convention(self, tmp_path: Path):
        """Chunks are named with zero-padded indices."""
        text = "word " * 2000
        chunk_files = split_to_chunks(text, tmp_path, chunk_size=500, chunk_overlap=50, base_name="doc")
        for i, fp in enumerate(chunk_files):
            assert f"doc_{i:03d}.md" in fp

    def test_empty_text_raises(self, tmp_path: Path):
        """Empty text raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            split_to_chunks("", tmp_path)

    def test_whitespace_only_text_raises(self, tmp_path: Path):
        """Whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            split_to_chunks("   \n\t  ", tmp_path)

    def test_creates_output_dir(self, tmp_path: Path):
        """Output directory is created if it doesn't exist."""
        out_dir = tmp_path / "new_dir" / "subdir"
        split_to_chunks("Hello world", out_dir)
        assert out_dir.exists()

    def test_custom_base_name(self, tmp_path: Path):
        """Custom base_name is used in filenames."""
        text = "word " * 2000
        chunk_files = split_to_chunks(text, tmp_path, chunk_size=500, chunk_overlap=50, base_name="custom")
        for fp in chunk_files:
            assert "custom_" in os.path.basename(fp)


class TestListChunks:
    """Tests for list_chunks function."""

    def test_list_empty_dir(self, tmp_path: Path):
        """Empty directory returns empty list."""
        assert list_chunks(tmp_path) == []

    def test_list_nonexistent_dir(self, tmp_path: Path):
        """Nonexistent directory returns empty list."""
        assert list_chunks(tmp_path / "nope") == []

    def test_list_with_chunks(self, tmp_path: Path):
        """Lists chunk files sorted by name."""
        # Create some chunk files
        for i in range(3):
            (tmp_path / f"chunk_{i:03d}.md").write_text(f"chunk {i}")
        (tmp_path / "other.txt").write_text("not a chunk")

        chunks = list_chunks(tmp_path)
        assert len(chunks) == 3
        assert all("chunk_" in c for c in chunks)

    def test_list_with_custom_base_name(self, tmp_path: Path):
        """Filters by custom base_name."""
        (tmp_path / "doc_000.md").write_text("a")
        (tmp_path / "chunk_000.md").write_text("b")
        chunks = list_chunks(tmp_path, base_name="doc")
        assert len(chunks) == 1


class TestGetChunkCount:
    """Tests for get_chunk_count function."""

    def test_count_empty(self, tmp_path: Path):
        """Empty directory returns 0."""
        assert get_chunk_count(tmp_path) == 0

    def test_count_with_chunks(self, tmp_path: Path):
        """Returns correct count."""
        for i in range(5):
            (tmp_path / f"chunk_{i:03d}.md").write_text(f"chunk {i}")
        assert get_chunk_count(tmp_path) == 5
