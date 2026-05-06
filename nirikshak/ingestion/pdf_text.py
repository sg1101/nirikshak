"""PDF text and bounding box extraction via PyMuPDF."""

import logging
from pathlib import Path
from uuid import uuid4

import fitz  # PyMuPDF

from nirikshak.core.hashing import content_hash
from nirikshak.core.schemas import BBox, Document, Page, RoutingTag

logger = logging.getLogger(__name__)


def extract_pdf(file_path: Path, tender_id=None, bidder_id=None) -> Document:
    """Extract text and bboxes from a PDF. Returns an unsaved Document with Pages."""
    raw_bytes = file_path.read_bytes()
    doc_hash = content_hash(raw_bytes)

    pdf = fitz.open(file_path)
    pages = []
    total_chars = 0

    for page_num in range(len(pdf)):
        page = pdf[page_num]
        text = page.get_text("text")
        total_chars += len(text)

        # Extract word-level bounding boxes
        words = page.get_text("words")  # list of (x0, y0, x1, y1, word, block, line, word_n)
        bboxes = [
            BBox(x0=w[0], y0=w[1], x1=w[2], y1=w[3]).model_dump()
            for w in words
        ]

        pages.append(Page(
            id=uuid4(),
            document_id=uuid4(),  # placeholder, set after Document created
            page_number=page_num,
            text=text,
            bboxes=bboxes,
        ))

    pdf.close()

    # Determine routing tag
    avg_chars = total_chars / max(len(pages), 1)
    routing_tag = RoutingTag.native_pdf if avg_chars >= 100 else RoutingTag.scanned_pdf

    document = Document(
        id=uuid4(),
        tender_id=tender_id,
        bidder_id=bidder_id,
        filename=file_path.name,
        content_hash=doc_hash,
        routing_tag=routing_tag,
    )

    # Fix page document_id references
    for p in pages:
        p.document_id = document.id

    logger.info(
        "Extracted PDF: %s, %d pages, avg %.0f chars/page, tag=%s",
        file_path.name, len(pages), avg_chars, routing_tag.value,
    )
    return document, pages
