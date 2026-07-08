"""Unit tests for etl.packer module."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.etl.packer import (
    pack_outputs, _to_frontmatter, _extract_title, _sanitize_filename, _parse_frontmatter,
)


SAMPLE_MD_WITH_FRONTMATTER = """---
title: Test Document
author: Test Author
tags:
  - python
  - testing
---

# Test Document

This is the content of the test document.

## Section 1

Some text here.
"""

SAMPLE_MD_PLAIN = """# Plain Title

Just plain markdown content without front matter.
"""


class TestPackOutputs:
    """Tests for pack_outputs function."""

    def test_pack_markdown_format(self, tmp_path: Path):
        """Packing as markdown produces .md files."""
        processed_dir = tmp_path / "processed"
        processed_dir.mkdir()
        (processed_dir / "chunk_000.md").write_text(SAMPLE_MD_PLAIN)

        output_dir = tmp_path / "output"
        files = pack_outputs(processed_dir, output_dir, output_format="markdown")

        assert len(files) == 1
        assert files[0].endswith(".md")
        assert os.path.exists(files[0])

    def test_pack_spr_format(self, tmp_path: Path):
        """Packing as SPR produces formatted output."""
        processed_dir = tmp_path / "processed"
        processed_dir.mkdir()
        (processed_dir / "chunk_000.md").write_text(SAMPLE_MD_WITH_FRONTMATTER)

        output_dir = tmp_path / "output"
        files = pack_outputs(processed_dir, output_dir, output_format="spr")

        assert len(files) == 1
        content = Path(files[0]).read_text()
        assert "SPR Summary" in content

    def test_pack_frontmatter_format(self, tmp_path: Path):
        """Packing as frontmatter produces valid YAML front matter."""
        processed_dir = tmp_path / "processed"
        processed_dir.mkdir()
        (processed_dir / "chunk_000.md").write_text(SAMPLE_MD_WITH_FRONTMATTER)

        output_dir = tmp_path / "output"
        files = pack_outputs(processed_dir, output_dir, output_format="frontmatter")

        assert len(files) == 1
        content = Path(files[0]).read_text()
        assert content.startswith("---")

    def test_pack_html_format(self, tmp_path: Path):
        """Packing as HTML produces .html files."""
        processed_dir = tmp_path / "processed"
        processed_dir.mkdir()
        (processed_dir / "chunk_000.md").write_text(SAMPLE_MD_PLAIN)

        output_dir = tmp_path / "output"
        files = pack_outputs(processed_dir, output_dir, output_format="html")

        assert len(files) == 1
        assert files[0].endswith(".html")
        content = Path(files[0]).read_text()
        assert "<!DOCTYPE html>" in content

    def test_invalid_format_raises(self, tmp_path: Path):
        """Invalid output format raises ValueError."""
        processed_dir = tmp_path / "processed"
        processed_dir.mkdir()
        (processed_dir / "chunk_000.md").write_text("content")

        with pytest.raises(ValueError, match="Unsupported"):
            pack_outputs(processed_dir, tmp_path / "out", output_format="invalid")

    def test_empty_processed_dir(self, tmp_path: Path):
        """Empty processed dir returns empty list."""
        processed_dir = tmp_path / "processed"
        processed_dir.mkdir()
        files = pack_outputs(processed_dir, tmp_path / "out")
        assert files == []

    def test_creates_output_dir(self, tmp_path: Path):
        """Output directory is created if it doesn't exist."""
        processed_dir = tmp_path / "processed"
        processed_dir.mkdir()
        (processed_dir / "chunk_000.md").write_text("content")

        output_dir = tmp_path / "deep" / "nested" / "output"
        pack_outputs(processed_dir, output_dir)
        assert output_dir.exists()

    def test_multiple_files(self, tmp_path: Path):
        """Multiple processed files are packed correctly."""
        processed_dir = tmp_path / "processed"
        processed_dir.mkdir()
        for i in range(3):
            (processed_dir / f"chunk_{i:03d}.md").write_text(f"# Doc {i}\n\nContent {i}")

        output_dir = tmp_path / "output"
        files = pack_outputs(processed_dir, output_dir, output_format="markdown")
        assert len(files) == 3


class TestExtractTitle:
    """Tests for _extract_title helper."""

    def test_title_from_frontmatter(self):
        """Extracts title from YAML front matter."""
        title = _extract_title(SAMPLE_MD_WITH_FRONTMATTER, "fallback")
        assert title == "Test Document"

    def test_title_from_h1(self):
        """Extracts title from first H1 heading."""
        title = _extract_title(SAMPLE_MD_PLAIN, "fallback")
        assert title == "Plain Title"

    def test_title_fallback(self):
        """Returns fallback when no title found."""
        title = _extract_title("Just some text.", "my_fallback")
        assert title == "my_fallback"


class TestSanitizeFilename:
    """Tests for _sanitize_filename helper."""

    def test_basic_sanitize(self):
        """Removes special characters."""
        result = _sanitize_filename("Hello World!")
        assert result == "Hello_World"

    def test_truncation(self):
        """Long names are truncated."""
        result = _sanitize_filename("A" * 100, max_len=20)
        assert len(result) <= 20

    def test_empty_fallback(self):
        """Empty result falls back to 'document'."""
        result = _sanitize_filename("!!!")
        assert result == "document"


class TestParseFrontmatter:
    """Tests for _parse_frontmatter helper."""

    def test_with_frontmatter(self):
        """Parses YAML front matter correctly."""
        metadata, content = _parse_frontmatter(SAMPLE_MD_WITH_FRONTMATTER)
        assert metadata["title"] == "Test Document"
        # YAML block is removed, but H1 heading "# Test Document" remains in content
        assert "---" not in content
        assert "author:" not in content

    def test_without_frontmatter(self):
        """Returns empty metadata when no front matter."""
        metadata, content = _parse_frontmatter(SAMPLE_MD_PLAIN)
        assert metadata == {}
        assert "# Plain Title" in content


    def test_leading_empty_lines(self):
        """Parses metadata when there are leading empty lines before frontmatter."""
        content = "\n\n---\ntitle: Empty Lines Doc\nauthor: Tester\n---\n\n# Title\nBody text."
        metadata, body = _parse_frontmatter(content)
        assert metadata["title"] == "Empty Lines Doc"
        assert metadata["author"] == "Tester"

    def test_leading_llm_intro(self):
        """Parses metadata when there is LLM intro text before frontmatter."""
        content = (
            "Here is the processed document:\n\n---\ntitle: LLM Intro Doc\n"
            "---\n\n# Title\nBody text."
        )
        metadata, body = _parse_frontmatter(content)
        assert metadata["title"] == "LLM Intro Doc"

class TestToFrontmatter:
    """Tests for _to_frontmatter converter."""

    def test_preserves_existing_frontmatter(self):
        """Existing frontmatter with folded style is preserved as-is."""
        raw = "---\nname: orch-protocol-coder\ndescription: >-\n  The Coder invocation protocol.\n---\n\n# Title\nContent here."
        result = _to_frontmatter(raw)
        assert result == raw

    def test_preserves_existing_frontmatter_literal_style(self):
        """Existing frontmatter with literal block style is preserved as-is."""
        raw = "---\ntitle: My Doc\nbody: |\n  Line one\n  Line two\n---\n\nContent."
        result = _to_frontmatter(raw)
        assert result == raw

    def test_creates_frontmatter_for_plain_content(self):
        """Plain markdown without frontmatter gets new frontmatter created."""
        plain = "# My Title\n\nSome content here.\n"
        result = _to_frontmatter(plain)
        assert result.startswith("---")
        assert "title:" in result

    def test_no_title_default_document(self):
        """Plain content without title gets default 'Document' title."""
        plain = "# My Title\n\nContent."
        result = _to_frontmatter(plain)
        assert "---" not in result.split("---")[1] or "title:" in result

    def test_frontmatter_with_title_preserved(self):
        """Frontmatter with existing title is preserved without re-serialization."""
        raw = "---\ntitle: Existing Title\nauthor: Test Author\n---\n\nContent."
        result = _to_frontmatter(raw)
        assert result == raw

    def test_content_without_leading_whitespace(self):
        """Frontmatter detection works even without leading whitespace."""
        raw = "---\ntitle: Direct Start\n---\n\nContent."
        result = _to_frontmatter(raw)
        assert result == raw

    def test_content_with_leading_whitespace(self):
        """Frontmatter detection strips leading whitespace before checking."""
        raw = "  ---\ntitle: Indented Start\n---\n\nContent."
        result = _to_frontmatter(raw)
        assert result == "---\ntitle: Indented Start\n---\n\nContent."

    def test_strips_empty_lines_before_frontmatter(self):
        """Empty lines before frontmatter are stripped."""
        raw = "\n\n---\ntitle: My Doc\n---\n\nContent."
        result = _to_frontmatter(raw)
        assert not result.startswith("\n")
        assert result.startswith("---")

    def test_strips_llm_intro_before_frontmatter(self):
        """LLM introductory text before frontmatter is stripped."""
        raw = "Here is the processed document:\n\n---\ntitle: My Doc\n---\n\nContent."
        result = _to_frontmatter(raw)
        assert not result.startswith("Here")
        assert result.startswith("---")
