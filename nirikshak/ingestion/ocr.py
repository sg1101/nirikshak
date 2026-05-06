"""PaddleOCR wrapper for scanned documents."""

import logging
from uuid import uuid4

from nirikshak.core.schemas import BBox, Page

logger = logging.getLogger(__name__)

_ocr_engine = None


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    return _ocr_engine


def ocr_page_image(image_path_or_array) -> tuple[str, list[dict], float]:
    """Run OCR on a single page image.

    Returns: (text, bboxes_as_dicts, average_confidence)
    """
    engine = get_ocr_engine()
    result = engine.ocr(image_path_or_array, cls=True)

    if not result or not result[0]:
        return "", [], 0.0

    lines = result[0]
    text_parts = []
    bboxes = []
    confidences = []

    for line in lines:
        points, (text, conf) = line
        text_parts.append(text)
        confidences.append(conf)

        # Convert 4-corner points to BBox (x0, y0, x1, y1)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        bboxes.append(BBox(
            x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys),
        ).model_dump())

    full_text = "\n".join(text_parts)
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    return full_text, bboxes, avg_conf


def ocr_document_pages(pages: list[Page], pdf_path) -> list[Page]:
    """Run OCR on pages that have little/no text. Mutates pages in place."""
    import fitz

    pdf = fitz.open(pdf_path)
    for page in pages:
        if len(page.text.strip()) < 50:  # needs OCR
            fitz_page = pdf[page.page_number]
            pix = fitz_page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")

            # PaddleOCR can take a file path or numpy array
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(img_bytes)
                tmp_path = f.name

            try:
                text, bboxes, conf = ocr_page_image(tmp_path)
                page.text = text
                page.bboxes = bboxes
                logger.info("OCR'd page %d: %d chars, conf=%.2f", page.page_number, len(text), conf)
            finally:
                os.unlink(tmp_path)

    pdf.close()
    return pages
