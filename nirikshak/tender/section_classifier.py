"""Section classifier — split tender into labeled sections (PRD §5.2)."""

import json
import logging
import re
from pathlib import Path

from nirikshak.core.schemas import LabeledSection, Page, SectionLabel
from nirikshak.llm.client import call_llm

logger = logging.getLogger(__name__)

# Heading patterns for regex-first classification
HEADING_PATTERNS = {
    "nit": [
        r"notice\s+inviting\s+tender",
        r"\bNIT\b",
        r"invitation\s+(for|to)\s+bid",
        r"tender\s+notice",
    ],
    "eligibility": [
        r"eligib(ility|le)",
        r"pre[\-\s]?qualification",
        r"qualification\s+(criteria|requirement)",
        r"conditions\s+of\s+eligibility",
        r"bidder.*shall\s+(have|possess|be)",
    ],
    "technical_specs": [
        r"technical\s+specification",
        r"scope\s+of\s+work",
        r"schedule\s+of\s+requirement",
        r"detailed\s+specification",
    ],
    "boq": [
        r"bill\s+of\s+quantit",
        r"\bBOQ\b",
        r"price\s+schedule",
        r"financial\s+bid",
        r"rate\s+analysis",
    ],
    "annexures": [
        r"annexure",
        r"appendix",
        r"proforma",
        r"format\s+(for|of)",
    ],
}

_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "section_classifier.md"


def _regex_classify(text: str) -> str | None:
    """Try to classify a text chunk by regex. Returns label or None."""
    text_lower = text[:2000].lower()  # check first 2000 chars
    for label, patterns in HEADING_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return label
    return None


def _llm_classify(text: str) -> SectionLabel:
    """Classify a text chunk using Claude."""
    prompt_template = _PROMPT_PATH.read_text()
    prompt = f"{prompt_template}\n\n---\nSECTION TEXT:\n{text[:3000]}"

    raw = call_llm(prompt, system="You are a government tender document analyzer. Return JSON only, no markdown.")
    try:
        data = json.loads(raw)
        return SectionLabel(**data)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("LLM section classification failed: %s", e)
        return SectionLabel(label="other", confidence=0.3, reasoning="LLM response parsing failed")


def classify_sections(pages: list[Page]) -> list[LabeledSection]:
    """Classify tender pages into labeled sections.

    Two-pass: regex first, LLM for unmatched chunks.
    Groups consecutive pages with the same label.
    """
    if not pages:
        return []

    # Pass 1: assign labels to each page via regex
    page_labels: list[tuple[int, str | None, str]] = []
    for page in sorted(pages, key=lambda p: p.page_number):
        label = _regex_classify(page.text)
        page_labels.append((page.page_number, label, page.text))

    # Pass 2: LLM for unlabeled pages
    for i, (pnum, label, text) in enumerate(page_labels):
        if label is None and text.strip():
            result = _llm_classify(text)
            page_labels[i] = (pnum, result.label, text)

    # Assign "other" to any still-unlabeled pages
    page_labels = [(pnum, label or "other", text) for pnum, label, text in page_labels]

    # Group consecutive pages with the same label
    sections: list[LabeledSection] = []
    current_label = None
    current_pages = []
    current_texts = []

    for pnum, label, text in page_labels:
        if label != current_label:
            if current_label is not None:
                sections.append(LabeledSection(
                    label=current_label,
                    pages=current_pages,
                    text="\n\n".join(current_texts),
                ))
            current_label = label
            current_pages = [pnum]
            current_texts = [text]
        else:
            current_pages.append(pnum)
            current_texts.append(text)

    if current_label is not None:
        sections.append(LabeledSection(
            label=current_label,
            pages=current_pages,
            text="\n\n".join(current_texts),
        ))

    logger.info(
        "Classified %d pages into %d sections: %s",
        len(pages), len(sections), [(s.label, len(s.pages)) for s in sections],
    )
    return sections
