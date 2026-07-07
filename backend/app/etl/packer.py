"""Pack processed .md files into final output formats.

Supports 4 output formats:
- spr: Custom markdown with YAML-style meta block + SPR sections
- frontmatter: Valid YAML Front Matter via python-frontmatter
- markdown: Raw markdown content
- html: HTML converted from markdown via the `markdown` library
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import frontmatter
except ImportError:
    frontmatter = None

try:
    import markdown as markdown_lib
except ImportError:
    markdown_lib = None


def pack_outputs(
    processed_dir: str | Path,
    output_dir: str | Path,
    base_name: str = "chunk",
    output_format: str = "spr",
    log_callback: Optional[callable] = None,
) -> list[str]:
    """Pack processed files into the specified output format.
    
    Args:
        processed_dir: Directory containing processed .md files.
        output_dir: Directory to write final output files.
        base_name: Prefix for input filenames.
        output_format: One of 'spr', 'frontmatter', 'markdown', 'html'.
        log_callback: Optional logging callback.
        
    Returns:
        List of output file paths created.
        
    Raises:
        ValueError: If output_format is not supported.
    """
    if output_format not in ("spr", "frontmatter", "markdown", "html"):
        raise ValueError(
            f"Unsupported output format: '{output_format}'. "
            f"Must be one of: spr, frontmatter, markdown, html"
        )
    
    processed_dir = Path(processed_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)



    # Find processed files
    processed_files = sorted(
        f for f in processed_dir.iterdir()
        if f.is_file() and f.name.startswith(base_name) and f.suffix == ".md"
    )
    
    if not processed_files:
        return []
    
    output_files: list[str] = []
    
    for idx, proc_path in enumerate(processed_files):
        with open(proc_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
        
        # Generate output filename
        title = _extract_title(raw_content, proc_path.stem)
        clean_title = _sanitize_filename(title)
        file_idx = idx + 1
        final_filename = f"{file_idx:02d}_{clean_title}"
        
        # Format content based on output_format
        if output_format == "markdown":
            content = raw_content
            ext = ".md"
        elif output_format == "html":
            content = _to_html(raw_content)
            ext = ".html"
        elif output_format == "frontmatter":
            content = _to_frontmatter(raw_content)
            ext = ".md"
        else:  # spr
            content = _to_spr(raw_content)
            ext = ".md"
        
        output_path = output_dir / f"{final_filename}{ext}"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        output_files.append(str(output_path))
    
    if log_callback:
        log_callback(f"✅ Packed {len(output_files)} files to {output_dir}")
    
    return output_files


# ── Format converters ─────────────────────────────────────────────────────────


def _to_spr(raw_content: str) -> str:
    """Convert to SPR format: YAML meta block + structured sections."""
    metadata, content = _parse_frontmatter(raw_content)
    
    title = metadata.pop("title", "Document")
    
    # Build meta block
    meta_lines = []
    for key, value in metadata.items():
        if key.lower() in ("теги", "tags"):
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        meta_lines.append(f"* **{key.title()}:** {value}")
    
    # Tags separately
    tags_list = metadata.get("теги", metadata.get("tags", []))
    if isinstance(tags_list, list) and tags_list:
        formatted_tags = ", ".join([f"#{str(t).strip()}" for t in tags_list])
        meta_lines.append(f"* **Tags:** {formatted_tags}")
    
    meta_block = "\n".join(meta_lines) if meta_lines else "* _No metadata available_"
    
    return (
        f"# {title}\n\n"
        f"## 🧠 SPR Summary\n"
        f"{meta_block}\n\n"
        f"---\n\n"
        f"## 📄 Full Fragment Text\n"
        f"{content}"
    )


def _to_frontmatter(raw_content: str) -> str:
    """Convert to valid YAML Front Matter format."""
    if frontmatter is None:
        raise ImportError(
            "python-frontmatter is required for frontmatter format. "
            "Install with: pip install python-frontmatter"
        )
    
    metadata, content = _parse_frontmatter(raw_content)
    
    title = metadata.pop("title", "Document")
    metadata["title"] = title
    
    post = frontmatter.Post(content, **metadata)
    return frontmatter.dumps(post)


def _to_html(raw_content: str) -> str:
    """Convert markdown content to HTML."""
    if markdown_lib is None:
        raise ImportError(
            "markdown library is required for HTML format. "
            "Install with: pip install markdown"
        )
    
    # Extract metadata for HTML header
    metadata, content = _parse_frontmatter(raw_content)
    title = metadata.get("title", "Document")
    
    # Convert markdown to HTML
    html_body = markdown_lib.markdown(content, extensions=["extra", "codehilite", "toc"])
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_escape_html(title)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.6; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; }}
        h2 {{ color: #34495e; }}
        code {{ background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 3px; }}
        pre {{ background: #f8f8f8; padding: 1rem; border-radius: 5px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #3498db; margin: 0; padding-left: 1rem; color: #555; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML front matter from markdown content.
    
    Returns:
        Tuple of (metadata_dict, content_without_frontmatter).
    """
    if frontmatter is not None:
        try:
            post = frontmatter.loads(content)
            return post.metadata, post.content
        except Exception:
            pass
    
    # Fallback: manual parsing
    metadata = {}
    body = content
    
    # Try to find YAML block between --- markers
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if match:
        yaml_block = match.group(1)
        body = match.group(2)
        
        for line in yaml_block.split("\n"):
            if ":" in line:
                key = line.split(":", 1)[0].strip().lstrip("- ")
                val = line.split(":", 1)[1].strip().strip("\"'")
                if key and val:
                    metadata[key] = val
    
    return metadata, body


def _extract_title(content: str, fallback: str) -> str:
    """Extract title from markdown content (first H1 or metadata)."""
    # Try metadata
    metadata, _ = _parse_frontmatter(content)
    if "title" in metadata:
        return metadata["title"]

    # Try first H1
    match = re.match(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Strip chunk suffix like _000, _001 etc.
    clean_fallback = re.sub(r"_\d+$", "", fallback)
    return clean_fallback or "document"


def _sanitize_filename(title: str, max_len: int = 40) -> str:
    """Sanitize a string for use as a filename."""
    clean = "".join(c if c.isalnum() or c in " _-" else "" for c in title).strip()
    clean = clean.replace(" ", "_")
    
    if len(clean) > max_len:
        truncated = clean[:max_len]
        clean = truncated.rsplit("_", 1)[0] if "_" in truncated else truncated
    
    return clean or "document"


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
