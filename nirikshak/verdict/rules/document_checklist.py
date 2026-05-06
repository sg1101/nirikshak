"""Document checklist verdict rule — deterministic, no LLM."""

from nirikshak.core.schemas import Criterion, CriterionType, EvidenceClaim
from nirikshak.verdict.engine import BaseRule, register_rule


class DocumentChecklistRule(BaseRule):
    criterion_type = CriterionType.document_checklist

    def evaluate(self, criterion: Criterion, evidence: list[EvidenceClaim]):
        params = criterion.parameters
        must_be_signed = params.get("must_be_signed", False)
        must_be_dated = params.get("must_be_dated", False)
        doc_name = params.get("document_name", criterion.description)

        if not evidence:
            return self._not_eligible_verdict(
                criterion,
                f"Required document '{doc_name}' not found in submission.",
            )

        for e in evidence:
            val = e.extracted_value
            if not isinstance(val, dict):
                continue

            present = val.get("present", False)

            if not present:
                return self._not_eligible_verdict(
                    criterion,
                    f"Required document '{doc_name}' not found in submission.",
                    evidence_ids=[e.id],
                )

            if must_be_signed and not val.get("signed", False):
                return self._not_eligible_verdict(
                    criterion,
                    f"Document '{doc_name}' is present but not signed (signature required).",
                    evidence_ids=[e.id],
                )

            if must_be_dated and not val.get("dated", False):
                return self._not_eligible_verdict(
                    criterion,
                    f"Document '{doc_name}' is present but not dated (date required).",
                    evidence_ids=[e.id],
                )

            return self._eligible_verdict(
                criterion,
                f"Document '{doc_name}' is present"
                + (", signed" if must_be_signed else "")
                + (", dated" if must_be_dated else "")
                + ".",
                evidence_ids=[e.id],
            )

        return self._needs_review_verdict(
            criterion,
            f"Could not determine presence of '{doc_name}'. Needs manual review.",
        )


register_rule(DocumentChecklistRule())
