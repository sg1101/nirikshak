"""Render PDF pages with optional bbox highlighting."""

import logging
from pathlib import Path
from uuid import UUID

import fitz  # PyMuPDF

from nirikshak.core.config import get_settings
from nirikshak.core.schemas import BBox

logger = logging.getLogger(__name__)


def render_page(
    pdf_path: Path,
    page_number: int,
    highlight_bbox: BBox | None = None,
    dpi: int = 150,
) -> bytes:
    """Render a PDF page as PNG bytes, optionally highlighting a bounding box."""
    pdf = fitz.open(pdf_path)
    page = pdf[page_number]

    if highlight_bbox:
        rect = fitz.Rect(highlight_bbox.x0, highlight_bbox.y0, highlight_bbox.x1, highlight_bbox.y1)
        highlight = page.add_highlight_annot(rect)
        highlight.set_colors(stroke=(1, 1, 0))  # yellow
        highlight.update()

    pix = page.get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("png")
    pdf.close()

    return img_bytes


def render_page_cached(
    pdf_path: Path,
    page_number: int,
    highlight_bbox: BBox | None = None,
) -> Path:
    """Render and cache a page image. Returns path to cached PNG."""
    settings = get_settings()
    cache_dir = settings.storage_dir / "renders"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Cache key based on pdf name + page + bbox
    bbox_str = f"_{highlight_bbox.x0}_{highlight_bbox.y0}_{highlight_bbox.x1}_{highlight_bbox.y1}" if highlight_bbox else ""
    cache_key = f"{pdf_path.stem}_p{page_number}{bbox_str}.png"
    cache_path = cache_dir / cache_key

    if not cache_path.exists():
        img_bytes = render_page(pdf_path, page_number, highlight_bbox)
        cache_path.write_bytes(img_bytes)

    return cache_path
