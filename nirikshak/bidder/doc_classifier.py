"""Classify bidder documents by type for routing to the correct extractor."""

import json
import logging
import re
from pathlib import Path
from uuid import UUID

from nirikshak.core.schemas import Document, Page
from nirikshak.llm.client import call_llm

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "doc_classifier.md"

# Filename-based classification patterns
_FILENAME_PATTERNS = {
    "financial_statement": [
        r"balance.?sheet", r"turnover", r"p[&.]?l", r"profit.?loss",
        r"ca.?cert", r"auditor", r"financial", r"solvency",
    ],
    "experience_certificate": [
        r"completion.?cert", r"work.?order", r"experience",
        r"performance.?cert", r"project.?completion",
    ],
    "registration_certificate": [
        r"gst", r"gstin", r"pan.?card", r"pan.?cert", r"epf", r"esi",
        r"contractor.?reg", r"trade.?license", r"registration",
    ],
    "quality_certificate": [
        r"iso", r"bis", r"aerb", r"oem", r"quality",
    ],
    "bid_document": [
        r"emd", r"earnest.?money", r"tender.?accept", r"integrity.?pact",
        r"bid.?form", r"power.?of.?attorney", r"authorization",
    ],
    "compliance_declaration": [
        r"make.?in.?india", r"msme", r"udyam", r"debarment",
        r"blacklist", r"declaration", r"affidavit",
    ],
}

# Content-based classification patterns (first page text)
_CONTENT_PATTERNS = {
    "financial_statement": [
        r"balance\s+sheet", r"profit\s+(and|&)\s+loss", r"turnover",
        r"chartered\s+accountant", r"auditor", r"net\s+worth",
        r"total\s+revenue", r"gross\s+receipt",
    ],
    "experience_certificate": [
        r"completion\s+certificate", r"work\s+order", r"satisfactorily\s+completed",
        r"scope\s+of\s+work.*completed", r"performance\s+certificate",
    ],
    "registration_certificate": [
        r"goods\s+and\s+services\s+tax", r"gstin", r"permanent\s+account\s+number",
        r"employees.*provident\s+fund", r"contractor.*registration",
    ],
    "quality_certificate": [
        r"iso\s*\d{4}", r"quality\s+management\s+system", r"bureau\s+of\s+indian\s+standards",
        r"certificate\s+of\s+registration.*quality",
    ],
    "bid_document": [
        r"earnest\s+money", r"tender\s+acceptance", r"integrity\s+pact",
        r"bid\s+(security|guarantee)", r"power\s+of\s+attorney",
    ],
    "compliance_declaration": [
        r"make\s+in\s+india", r"msme", r"udyam", r"not\s+been\s+(debarred|blacklisted)",
        r"self[\-\s]?certification", r"micro.*small.*medium",
    ],
}


def _classify_by_filename(filename: str) -> str | None:
    name_lower = filename.lower()
    for category, patterns in _FILENAME_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, name_lower):
                return category
    return None


def _classify_by_content(text: str) -> str | None:
    text_lower = text[:3000].lower()
    scores = {}
    for category, patterns in _CONTENT_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, text_lower))
        if score > 0:
            scores[category] = score
    if scores:
        return max(scores, key=scores.get)
    return None


def _classify_by_llm(filename: str, first_page_text: str) -> str:
    prompt_template = _PROMPT_PATH.read_text()
    prompt = f"{prompt_template}\n\n---\nFilename: {filename}\nFirst page content:\n{first_page_text[:2000]}"
    raw = call_llm(prompt, system="You are a document classifier. Return JSON only, no markdown.")
    try:
        data = json.loads(raw)
        return data.get("category", "other")
    except (json.JSONDecodeError, KeyError):
        return "other"


def classify_bidder_documents(
    documents: list[Document],
    pages_by_doc: dict[UUID, list[Page]],
) -> dict[UUID, str]:
    """Classify each document into a category. Returns {doc_id: category}."""
    result = {}
    for doc in documents:
        # Try filename first
        category = _classify_by_filename(doc.filename)

        # Try content if filename didn't match
        if category is None:
            pages = pages_by_doc.get(doc.id, [])
            if pages:
                first_text = pages[0].text if pages else ""
                category = _classify_by_content(first_text)

        # LLM fallback
        if category is None:
            pages = pages_by_doc.get(doc.id, [])
            first_text = pages[0].text if pages else ""
            category = _classify_by_llm(doc.filename, first_text)

        result[doc.id] = category
        logger.info("Classified %s → %s", doc.filename, category)

    return result
