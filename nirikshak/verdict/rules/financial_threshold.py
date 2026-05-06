"""Financial threshold verdict rule — deterministic, no LLM."""

from decimal import Decimal

from nirikshak.core.schemas import Criterion, CriterionType, EvidenceClaim
from nirikshak.verdict.engine import BaseRule, register_rule


class FinancialThresholdRule(BaseRule):
    criterion_type = CriterionType.financial_threshold

    def evaluate(self, criterion: Criterion, evidence: list[EvidenceClaim]):
        params = criterion.parameters
        threshold = Decimal(str(params.get("threshold_amount", 0)))
        period_years = params.get("period_years", 3)
        metric = params.get("metric", "turnover")

        # Filter to verified evidence
        verified = [e for e in evidence if e.verifier_passed and e.confidence >= 0.5]

        if not verified:
            return self._needs_review_verdict(
                criterion,
                f"No verified financial evidence found for {metric}. Needs manual review.",
            )

        # Extract amounts
        amounts = []
        for e in verified:
            val = e.extracted_value
            if isinstance(val, dict) and val.get("amount"):
                try:
                    amounts.append(Decimal(str(val["amount"])))
                except Exception:
                    pass

        if not amounts:
            return self._needs_review_verdict(
                criterion,
                f"Financial documents found but no {metric} amounts could be extracted.",
            )

        avg = sum(amounts) / len(amounts)

        if avg >= threshold:
            return self._eligible_verdict(
                criterion,
                f"Average {metric} of INR {avg:,.0f} over {len(amounts)} year(s) "
                f"meets threshold of INR {threshold:,.0f}.",
                evidence_ids=[e.id for e in verified],
            )
        else:
            return self._not_eligible_verdict(
                criterion,
                f"Average {metric} of INR {avg:,.0f} over {len(amounts)} year(s) "
                f"is below threshold of INR {threshold:,.0f}.",
                evidence_ids=[e.id for e in verified],
            )


register_rule(FinancialThresholdRule())
