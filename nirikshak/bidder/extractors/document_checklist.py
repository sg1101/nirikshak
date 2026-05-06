"""Document checklist evidence extractor."""

import logging
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from nirikshak.core.schemas import CriterionType, EvidenceClaim
from nirikshak.bidder.extractors.base import BaseExtractor, register_extractor
from nirikshak.llm.instructor_helpers import extract_structured

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "llm" / "prompts" / "checklist_extractor.md"


class ChecklistExtraction(BaseModel):
    document_name: str = ""
    present: bool = False
    signed: bool = False
    dated: bool = False
    date_found: str | None = None
    addressed_to: str | None = None
    source_page: int = 0
    source_quote: str = ""


class DocumentChecklistExtractor(BaseExtractor):
    criterion_type = CriterionType.document_checklist

    def extract(self, criterion, documents, pages_by_doc, doc_categories):
        # Search across bid_documents and all docs for checklist items
        docs, text = self._get_all_text(documents, pages_by_doc, doc_categories, "bid_document")
        if not text.strip():
            # Fall back to all documents
            docs = documents
            texts = []
            for doc in docs:
                texts.append(f"=== {doc.filename} ===\n{self._get_text_for_doc(doc, pages_by_doc)}")
            text = "\n\n".join(texts)[:12000]

        prompt_template = _PROMPT_PATH.read_text()
        params = criterion.parameters
        prompt = (
            f"{prompt_template}\n\n"
            f"CRITERION: {criterion.description}\n"
            f"Looking for document: {params.get('document_name', criterion.description)}\n"
            f"Must be signed: {params.get('must_be_signed', False)}\n"
            f"Must be dated: {params.get('must_be_dated', False)}\n\n"
            f"BIDDER DOCUMENTS:\n{text}"
        )

        result = extract_structured(
            prompt=prompt,
            response_model=ChecklistExtraction,
            system="You are checking document completeness for a tender bid. Return JSON only.",
        )

        doc_id = docs[0].id if docs else documents[0].id

        claim = EvidenceClaim(
            id=uuid4(),
            bidder_id=uuid4(),
            criterion_id=criterion.id,
            extracted_value={
                "document_name": result.document_name,
                "present": result.present,
                "signed": result.signed,
                "dated": result.dated,
                "date_found": result.date_found,
                "addressed_to": result.addressed_to,
            },
            source_doc_id=doc_id,
            source_page=result.source_page,
            confidence=0.0,
            verifier_passed=False,
        )

        logger.info("Checklist check for %s: present=%s", criterion.id, result.present)
        return [claim]


register_extractor(DocumentChecklistExtractor())
