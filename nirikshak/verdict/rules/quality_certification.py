"""Quality certification verdict rule — deterministic, no LLM."""

from datetime import date

from nirikshak.core.schemas import Criterion, CriterionType, EvidenceClaim
from nirikshak.verdict.engine import BaseRule, register_rule

# Equivalence table for certificate versions
CERT_EQUIVALENCES = {
    "iso 9001": ["iso 9001", "iso 9001:2008", "iso 9001:2015", "iso 9001:2024"],
    "iso 14001": ["iso 14001", "iso 14001:2004", "iso 14001:2015"],
    "iso 45001": ["iso 45001", "iso 45001:2018", "ohsas 18001"],
    "iso 27001": ["iso 27001", "iso 27001:2013", "iso 27001:2022"],
}


def _cert_matches(required: str, found: str, accepted_versions: list | None) -> bool:
    """Check if a found certificate matches the requirement."""
    req_lower = required.lower().strip()
    found_lower = found.lower().strip()

    # Direct match
    if req_lower in found_lower or found_lower in req_lower:
        return True

    # Equivalence table match
    for base, equivalents in CERT_EQUIVALENCES.items():
        if req_lower in base or base in req_lower:
            if any(eq in found_lower or found_lower in eq for eq in equivalents):
                return True

    # Check accepted versions
    if accepted_versions:
        for ver in accepted_versions:
            if str(ver).lower() in found_lower:
                return True

    return False


class QualityCertificationRule(BaseRule):
    criterion_type = CriterionType.quality_certification

    def evaluate(self, criterion: Criterion, evidence: list[EvidenceClaim]):
        params = criterion.parameters
        required_cert = params.get("cert_name", "")
        accepted_versions = params.get("accepted_versions")

        verified = [e for e in evidence if e.verifier_passed and e.confidence >= 0.5]

        if not verified:
            return self._needs_review_verdict(
                criterion,
                f"No verified {required_cert} certificate found. Needs manual review.",
            )

        for e in verified:
            val = e.extracted_value
            if not isinstance(val, dict):
                continue

            cert_name = val.get("cert_name", "")
            cert_version = val.get("cert_version", "")
            expiry = val.get("expiry_date")

            full_cert = f"{cert_name}:{cert_version}" if cert_version else cert_name

            if not _cert_matches(required_cert, full_cert, accepted_versions):
                continue

            # Check expiry
            if expiry:
                try:
                    expiry_date = date.fromisoformat(expiry)
                    if expiry_date < date.today():
                        return self._not_eligible_verdict(
                            criterion,
                            f"{full_cert} certificate found but expired on {expiry}.",
                            evidence_ids=[e.id],
                        )
                except ValueError:
                    pass

            return self._eligible_verdict(
                criterion,
                f"Valid {full_cert} certificate found (issued by {val.get('issuing_body', 'unknown')}).",
                evidence_ids=[e.id],
            )

        return self._not_eligible_verdict(
            criterion,
            f"Certificates found but none match required {required_cert}.",
            evidence_ids=[e.id for e in verified],
        )


register_rule(QualityCertificationRule())
