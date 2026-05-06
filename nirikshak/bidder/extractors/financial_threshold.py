"""Financial threshold evidence extractor."""

import logging
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from nirikshak.core.schemas import Criterion, CriterionType, Document, EvidenceClaim, Page
from nirikshak.bidder.extractors.base import BaseExtractor, register_extractor
from nirikshak.llm.instructor_helpers import extract_structured

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "llm" / "prompts" / "financial_extractor.md"


class FinancialEntry(BaseModel):
    fiscal_year: str
    amount: Decimal | None = None
    metric: str = "turnover"
    source_page: int = 0
    source_quote: str = ""


class FinancialExtraction(BaseModel):
    amounts: list[FinancialEntry] = Field(default_factory=list)


class FinancialThresholdExtractor(BaseExtractor):
    criterion_type = CriterionType.financial_threshold

    def extract(self, criterion, documents, pages_by_doc, doc_categories):
        docs, text = self._get_all_text(documents, pages_by_doc, doc_categories, "financial_statement")
        if not text.strip():
            return []

        prompt_template = _PROMPT_PATH.read_text()
        params = criterion.parameters
        prompt = (
            f"{prompt_template}\n\n"
            f"CRITERION: {criterion.description}\n"
            f"Required metric: {params.get('metric', 'turnover')}\n"
            f"Required period: last {params.get('period_years', 3)} fiscal years\n\n"
            f"BIDDER DOCUMENTS:\n{text}"
        )

        result = extract_structured(
            prompt=prompt,
            response_model=FinancialExtraction,
            system="You are a financial document analyst. Extract exact figures. Return JSON only.",
        )

        claims = []
        doc_id = docs[0].id if docs else documents[0].id

        for entry in result.amounts:
            if entry.amount is not None:
                claims.append(EvidenceClaim(
                    id=uuid4(),
                    bidder_id=uuid4(),  # set by caller
                    criterion_id=criterion.id,
                    extracted_value={
                        "fiscal_year": entry.fiscal_year,
                        "amount": str(entry.amount),
                        "metric": entry.metric,
                    },
                    source_doc_id=doc_id,
                    source_page=entry.source_page,
                    source_bbox=None,
                    confidence=0.0,  # set by confidence scorer
                    verifier_passed=False,  # set by verifier
                ))

        logger.info("Extracted %d financial entries for %s", len(claims), criterion.id)
        return claims


register_extractor(FinancialThresholdExtractor())
