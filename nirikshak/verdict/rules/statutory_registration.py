"""Statutory registration verdict rule — deterministic, no LLM."""

from datetime import date

from nirikshak.core.schemas import Criterion, CriterionType, EvidenceClaim
from nirikshak.verdict.engine import BaseRule, register_rule


class StatutoryRegistrationRule(BaseRule):
    criterion_type = CriterionType.statutory_registration

    def evaluate(self, criterion: Criterion, evidence: list[EvidenceClaim]):
        params = criterion.parameters
        required_type = params.get("registration_type", "").lower()
        required_class = params.get("required_class")

        verified = [e for e in evidence if e.verifier_passed and e.confidence >= 0.5]

        if not verified:
            return self._needs_review_verdict(
                criterion,
                f"No verified {required_type.upper()} registration found. Needs manual review.",
            )

        for e in verified:
            val = e.extracted_value
            if not isinstance(val, dict):
                continue

            reg_type = val.get("registration_type", "").lower()
            reg_number = val.get("registration_number", "")
            valid_until = val.get("valid_until")
            class_cat = val.get("class_category")

            # Check type matches
            if required_type and required_type not in reg_type and reg_type not in required_type:
                continue

            # Check registration number exists
            if not reg_number or len(reg_number) < 3:
                continue

            # Check class/category if required
            if required_class and class_cat:
                if required_class.lower() not in class_cat.lower():
                    return self._not_eligible_verdict(
                        criterion,
                        f"{reg_type.upper()} registration found ({reg_number}) but class '{class_cat}' "
                        f"does not match required '{required_class}'.",
                        evidence_ids=[e.id],
                    )

            # Check validity
            if valid_until:
                try:
                    expiry = date.fromisoformat(valid_until)
                    # Compare against current date as proxy (in production: bid_submission_date)
                    if expiry < date.today():
                        return self._not_eligible_verdict(
                            criterion,
                            f"{reg_type.upper()} registration ({reg_number}) expired on {valid_until}.",
                            evidence_ids=[e.id],
                        )
                except ValueError:
                    pass  # can't parse date, don't fail on this

            return self._eligible_verdict(
                criterion,
                f"Valid {reg_type.upper()} registration found: {reg_number}.",
                evidence_ids=[e.id],
            )

        return self._needs_review_verdict(
            criterion,
            f"Registration documents found but no matching {required_type.upper()} registration could be confirmed.",
        )


register_rule(StatutoryRegistrationRule())
