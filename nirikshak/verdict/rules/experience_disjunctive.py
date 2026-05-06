"""Experience disjunctive verdict rule — THE centerpiece. Deterministic, no LLM.

Handles criteria like:
  "3 similar works at >= 40% of estimated cost; OR 2 at >= 60%; OR 1 at >= 80%"

Also handles simple (non-disjunctive) experience criteria:
  "At least 3 similar projects completed in last 5 years"
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from nirikshak.core.schemas import Criterion, CriterionType, EvidenceClaim, Verdict, VerdictState
from nirikshak.verdict.engine import BaseRule, register_rule

logger = logging.getLogger(__name__)


def _parse_claims(evidence: list[EvidenceClaim]) -> list[dict]:
    """Extract CompletedWorkClaim data from evidence claims."""
    claims = []
    for e in evidence:
        val = e.extracted_value
        if not isinstance(val, dict):
            continue
        claims.append({
            "value": Decimal(str(val.get("value", 0))),
            "completion_date": val.get("completion_date", "1900-01-01"),
            "description": val.get("description", ""),
            "similarity_status": val.get("similarity_status", "unknown"),
            "evidence_id": str(e.id),
        })
    return claims


def _compute_window(bid_submission_date: date, window_years: int) -> tuple[date, date]:
    """Compute temporal window ending the last day of the month before bid invitation."""
    # End: last day of month previous to bid month
    first_of_bid_month = bid_submission_date.replace(day=1)
    window_end = first_of_bid_month - timedelta(days=1)
    # Start: window_years before window_end
    window_start = window_end.replace(year=window_end.year - window_years)
    return window_start, window_end


def _filter_by_window(claims: list[dict], window_start: date, window_end: date) -> list[dict]:
    """Filter claims to those within the temporal window."""
    filtered = []
    for c in claims:
        try:
            comp_date = date.fromisoformat(str(c["completion_date"]))
        except (ValueError, TypeError):
            continue
        if window_start <= comp_date <= window_end:
            filtered.append(c)
    return filtered


class ExperienceDisjunctiveRule(BaseRule):
    criterion_type = CriterionType.experience_count

    def evaluate(self, criterion: Criterion, evidence: list[EvidenceClaim]) -> Verdict:
        params = criterion.parameters
        is_disjunctive = params.get("disjunctive", False) or "branches" in params

        if is_disjunctive:
            return self._evaluate_disjunctive(criterion, evidence)
        else:
            return self._evaluate_simple(criterion, evidence)

    def _evaluate_simple(self, criterion: Criterion, evidence: list[EvidenceClaim]) -> Verdict:
        """Simple: at least N similar works of value >= V in last W years."""
        params = criterion.parameters
        min_count = params.get("min_count") or 1  # default 1 if None/null/0
        min_value = Decimal(str(params.get("min_value", 0))) if params.get("min_value") else None
        window_years = params.get("window_years") or 7  # default 7 if None

        claims = _parse_claims(evidence)
        if not claims:
            return self._needs_review_verdict(
                criterion,
                "No experience claims found. Needs manual review.",
            )

        # Check for borderline similarity
        has_borderline = any(c["similarity_status"] == "borderline" for c in claims)

        # Filter to similar claims
        similar = [c for c in claims if c["similarity_status"] == "similar"]

        # Apply value filter if specified
        if min_value and min_value > 0:
            qualifying = [c for c in similar if c["value"] >= min_value]
        else:
            qualifying = similar

        if min_count and len(qualifying) >= min_count:
            return self._eligible_verdict(
                criterion,
                f"{len(qualifying)} similar completed works found"
                + (f" (each >= INR {min_value:,.0f})" if min_value else "")
                + f", meeting requirement of {min_count}.",
                evidence_ids=[c["evidence_id"] for c in qualifying],
            )
        elif has_borderline:
            return self._needs_review_verdict(
                criterion,
                f"{len(qualifying)} qualifying works found (need {min_count}). "
                f"Some claims have borderline similarity — needs manual review.",
            )
        else:
            return self._not_eligible_verdict(
                criterion,
                f"Only {len(qualifying)} qualifying similar works found, "
                f"need {min_count}.",
                evidence_ids=[c["evidence_id"] for c in qualifying],
            )

    def _evaluate_disjunctive(self, criterion: Criterion, evidence: list[EvidenceClaim]) -> Verdict:
        """Disjunctive: multiple branches with OR logic."""
        params = criterion.parameters
        branches = params.get("branches", [])
        window_years = params.get("window_years", 7)
        # estimated_cost comes from tender, passed via parameters
        estimated_cost = Decimal(str(params.get("estimated_cost", 0)))

        claims = _parse_claims(evidence)
        if not claims:
            return self._needs_review_verdict(
                criterion,
                "No experience claims found. Needs manual review.",
            )

        # Compute temporal window
        bid_date_str = params.get("bid_submission_date", str(date.today()))
        try:
            bid_date = date.fromisoformat(bid_date_str)
        except ValueError:
            bid_date = date.today()
        window_start, window_end = _compute_window(bid_date, window_years)

        # Filter by window
        windowed = _filter_by_window(claims, window_start, window_end)

        # Check for borderline similarity
        has_borderline = any(c["similarity_status"] == "borderline" for c in windowed)

        # Filter to similar only
        similar = [c for c in windowed if c["similarity_status"] == "similar"]

        # Evaluate each branch
        branch_results = []
        any_pass = False

        for branch in branches:
            count_required = branch.get("count", 1)
            percentage = Decimal(str(branch.get("percentage", 0)))
            threshold = estimated_cost * percentage / 100

            qualifying = [c for c in similar if c["value"] >= threshold]

            passed = len(qualifying) >= count_required
            if passed:
                any_pass = True

            branch_results.append({
                "count_required": count_required,
                "percentage": float(percentage),
                "threshold": float(threshold),
                "qualifying_count": len(qualifying),
                "qualifying_claims": [c["evidence_id"] for c in qualifying],
                "passed": passed,
            })

        # Build explanation
        branch_text = []
        for i, br in enumerate(branch_results):
            status = "PASS" if br["passed"] else "FAIL"
            branch_text.append(
                f"Branch {chr(65+i)} (>={br['count_required']} at >={br['percentage']:.0f}%): "
                f"{br['qualifying_count']} claims meet threshold INR {br['threshold']:,.0f} → {status}"
            )

        explanation = (
            f"Window: {window_start} to {window_end}\n"
            f"Estimated cost: INR {estimated_cost:,.0f}\n"
            f"Similar claims in window: {len(similar)}\n"
            + "\n".join(branch_text)
        )

        if any_pass:
            verdict = Verdict(
                id=uuid4(),
                bidder_id=uuid4(),
                criterion_id=criterion.id,
                state=VerdictState.eligible,
                evidence_ids=[c["evidence_id"] for c in similar],
                rule_fired="ExperienceDisjunctiveRule",
                reason_template=f"ELIGIBLE — at least one branch passes.\n{explanation}",
            )
        elif has_borderline:
            verdict = Verdict(
                id=uuid4(),
                bidder_id=uuid4(),
                criterion_id=criterion.id,
                state=VerdictState.needs_review,
                evidence_ids=[c["evidence_id"] for c in windowed],
                rule_fired="ExperienceDisjunctiveRule",
                reason_template=f"NEEDS REVIEW — no branch passes but borderline claims present.\n{explanation}",
            )
        else:
            verdict = Verdict(
                id=uuid4(),
                bidder_id=uuid4(),
                criterion_id=criterion.id,
                state=VerdictState.not_eligible,
                evidence_ids=[c["evidence_id"] for c in similar],
                rule_fired="ExperienceDisjunctiveRule",
                reason_template=f"NOT ELIGIBLE — no branch passes.\n{explanation}",
            )

        # Store all branch evaluations in the verdict for audit
        verdict.officer_action = {"branch_evaluations": branch_results}
        return verdict


register_rule(ExperienceDisjunctiveRule())
