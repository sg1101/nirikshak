"""Claude vision API for photograph / certificate extraction."""

import json
import logging
from pathlib import Path

from nirikshak.llm.client import call_llm_vision

logger = logging.getLogger(__name__)

VISION_CERTIFICATE_PROMPT = """You are reading a photograph of a physical certificate or document.
Extract the following fields as accurately as possible:
- issuer: the organization that issued this certificate
- issue_date: the date of issue (YYYY-MM-DD format)
- recipient_name: the person or company the certificate is issued to
- validity: expiry date (YYYY-MM-DD) or "no expiry" or "unclear"
- full_text: complete text content as you can read it

If any field is unclear or partially illegible, set it to null and explain in a "notes" field.
Return JSON only, no markdown fences."""

VISION_PAGE_PROMPT = """Read this document page image. Extract all visible text as accurately as possible.
Return JSON with two fields:
- "text": the full text content
- "confidence": your confidence in the accuracy (0.0 to 1.0)
Return JSON only, no markdown fences."""


def extract_certificate(image_bytes: bytes) -> dict:
    """Extract structured fields from a certificate photo."""
    raw = call_llm_vision(
        images=[image_bytes],
        prompt=VISION_CERTIFICATE_PROMPT,
        system="You are a precise document reader. Return only valid JSON.",
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Vision certificate extraction returned non-JSON, wrapping as text")
        return {"full_text": raw, "notes": "Response was not valid JSON"}


def vision_page(image_bytes: bytes) -> tuple[str, float]:
    """Extract text from a general page image via Claude vision."""
    raw = call_llm_vision(
        images=[image_bytes],
        prompt=VISION_PAGE_PROMPT,
        system="You are a precise document reader. Return only valid JSON.",
    )
    try:
        data = json.loads(raw)
        return data.get("text", raw), data.get("confidence", 0.5)
    except json.JSONDecodeError:
        return raw, 0.3
