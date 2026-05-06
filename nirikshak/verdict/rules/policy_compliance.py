"""Policy compliance verdict rule — deterministic, no LLM."""

from nirikshak.core.schemas import Criterion, CriterionType, EvidenceClaim
from nirikshak.verdict.engine import BaseRule, register_rule


class PolicyComplianceRule(BaseRule):
    criterion_type = CriterionType.policy_compliance

    def evaluate(self, criterion: Criterion, evidence: list[EvidenceClaim]):
        params = criterion.parameters
        policy_name = params.get("policy_name", criterion.description)

        if not evidence:
            return self._not_eligible_verdict(
                criterion,
                f"No declaration found for policy '{policy_name}'.",
            )

        for e in evidence:
            val = e.extracted_value
            if not isinstance(val, dict):
                continue

            status = val.get("cross_check_status", "not_found")
            signed = val.get("declaration_signed", False)

            if status == "not_found":
                return self._not_eligible_verdict(
                    criterion,
                    f"No declaration found for policy '{policy_name}'.",
                    evidence_ids=[e.id],
                )

            if not signed:
                return self._needs_review_verdict(
                    criterion,
                    f"Declaration for '{policy_name}' found but not signed. Needs manual review.",
                )

            return self._eligible_verdict(
                criterion,
                f"Signed declaration for '{policy_name}' found (status: {status}).",
                evidence_ids=[e.id],
            )

        return self._needs_review_verdict(
            criterion,
            f"Compliance documents present but status unclear for '{policy_name}'.",
        )


register_rule(PolicyComplianceRule())
