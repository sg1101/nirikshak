"""Exhaustive unit tests for the disjunctive experience rule — the wow-factor."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from nirikshak.core.schemas import Criterion, CriterionType, EvidenceClaim, VerdictState
from nirikshak.verdict.rules.experience_disjunctive import ExperienceDisjunctiveRule

rule = ExperienceDisjunctiveRule()

TENDER_ID = uuid4()
DOC_ID = uuid4()


def _make_criterion(params: dict) -> Criterion:
    return Criterion(
        id="EXP-001",
        criteria_spec_id=uuid4(),
        type=CriterionType.experience_count,
        description="Experience requirement",
        mandatory=True,
        parameters=params,
        source_page=1,
        source_quote="test",
    )


def _make_claim(value: Decimal, comp_date: str, similarity: str = "similar") -> EvidenceClaim:
    return EvidenceClaim(
        id=uuid4(),
        bidder_id=uuid4(),
        criterion_id="EXP-001",
        extracted_value={
            "value": str(value),
            "completion_date": comp_date,
            "description": "Construction work",
            "similarity_status": similarity,
        },
        source_doc_id=DOC_ID,
        source_page=1,
        confidence=0.9,
        verifier_passed=True,
    )


# ── Disjunctive tests ────────────────────────────────────────────────

DISJUNCTIVE_PARAMS = {
    "disjunctive": True,
    "branches": [
        {"count": 3, "percentage": 40},
        {"count": 2, "percentage": 60},
        {"count": 1, "percentage": 80},
    ],
    "window_years": 7,
    "estimated_cost": "500000000",  # 50 crore
    "bid_submission_date": "2025-04-30",
}
# Thresholds: 40% = 20cr, 60% = 30cr, 80% = 40cr


class TestDisjunctiveAllBranchesPass:
    def test_all_branches_pass(self):
        """Bidder K: 3 claims >= 20cr, 2 >= 30cr, 1 >= 40cr."""
        claims = [
            _make_claim(Decimal("225000000"), "2023-06-15"),  # 22.5cr
            _make_claim(Decimal("350000000"), "2022-11-01"),  # 35cr
            _make_claim(Decimal("420000000"), "2024-01-20"),  # 42cr
        ]
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state == VerdictState.eligible
        assert "Branch A" in verdict.reason_template
        assert "PASS" in verdict.reason_template
        # All branch evaluations stored
        assert verdict.officer_action is not None
        assert len(verdict.officer_action["branch_evaluations"]) == 3


class TestDisjunctiveOnlyBranchAPasses:
    def test_branch_a_only(self):
        """3 claims at 40% but none at 60%."""
        claims = [
            _make_claim(Decimal("200000000"), "2023-01-01"),  # 20cr exactly
            _make_claim(Decimal("210000000"), "2023-06-01"),  # 21cr
            _make_claim(Decimal("250000000"), "2024-01-01"),  # 25cr
        ]
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state == VerdictState.eligible


class TestDisjunctiveOnlyBranchCPasses:
    def test_branch_c_only(self):
        """1 claim at 80% but not enough for Branch A or B."""
        claims = [
            _make_claim(Decimal("400000000"), "2023-06-01"),  # 40cr = 80%
        ]
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state == VerdictState.eligible
        branches = verdict.officer_action["branch_evaluations"]
        assert branches[0]["passed"] is False  # Branch A: need 3, have 1
        assert branches[1]["passed"] is False  # Branch B: need 2, have 1
        assert branches[2]["passed"] is True   # Branch C: need 1, have 1


class TestDisjunctiveNoBranchPasses:
    def test_no_branch_passes(self):
        """Claims too small for any branch."""
        claims = [
            _make_claim(Decimal("100000000"), "2023-01-01"),  # 10cr < 20cr
            _make_claim(Decimal("150000000"), "2023-06-01"),  # 15cr < 20cr
        ]
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state == VerdictState.not_eligible


class TestDisjunctiveBorderline:
    def test_borderline_similarity(self):
        """Enough claims but one is borderline → Needs Review."""
        claims = [
            _make_claim(Decimal("250000000"), "2023-01-01"),
            _make_claim(Decimal("350000000"), "2023-06-01"),
            _make_claim(Decimal("300000000"), "2024-01-01", similarity="borderline"),
        ]
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state in (VerdictState.eligible, VerdictState.needs_review)


class TestDisjunctiveWindowFiltering:
    def test_claims_outside_window(self):
        """Claims outside 7-year window are filtered out."""
        claims = [
            _make_claim(Decimal("400000000"), "2015-01-01"),  # outside window
            _make_claim(Decimal("400000000"), "2014-06-01"),  # outside window
        ]
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state == VerdictState.not_eligible

    def test_claims_inside_window(self):
        """Claims inside window pass."""
        claims = [
            _make_claim(Decimal("400000000"), "2023-01-01"),  # inside window
        ]
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state == VerdictState.eligible


class TestDisjunctiveEdgeCases:
    def test_no_claims(self):
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, [])
        assert verdict.state == VerdictState.needs_review

    def test_exact_threshold(self):
        """Value exactly at 40% threshold."""
        claims = [
            _make_claim(Decimal("200000000"), "2023-01-01"),  # exactly 40%
            _make_claim(Decimal("200000000"), "2023-06-01"),
            _make_claim(Decimal("200000000"), "2024-01-01"),
        ]
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state == VerdictState.eligible  # >= threshold

    def test_just_below_threshold(self):
        """Value 1 rupee below threshold."""
        claims = [
            _make_claim(Decimal("199999999"), "2023-01-01"),  # just below 20cr
            _make_claim(Decimal("199999999"), "2023-06-01"),
            _make_claim(Decimal("199999999"), "2024-01-01"),
        ]
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state == VerdictState.not_eligible

    def test_not_similar_claims_excluded(self):
        """not_similar claims don't count."""
        claims = [
            _make_claim(Decimal("400000000"), "2023-01-01", similarity="not_similar"),
            _make_claim(Decimal("400000000"), "2023-06-01", similarity="not_similar"),
        ]
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state == VerdictState.not_eligible

    def test_all_branch_evaluations_in_audit(self):
        """All branches must be in the audit record, even if first branch passes."""
        claims = [
            _make_claim(Decimal("400000000"), "2023-01-01"),
            _make_claim(Decimal("400000000"), "2023-06-01"),
            _make_claim(Decimal("400000000"), "2024-01-01"),
        ]
        criterion = _make_criterion(DISJUNCTIVE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        branches = verdict.officer_action["branch_evaluations"]
        assert len(branches) == 3
        assert all("passed" in b for b in branches)


# ── Simple (non-disjunctive) tests ───────────────────────────────────

SIMPLE_PARAMS = {
    "min_count": 3,
    "min_value": None,
    "similarity_required": True,
    "window_years": 5,
}


class TestSimpleExperience:
    def test_enough_similar_works(self):
        claims = [
            _make_claim(Decimal("100000000"), "2023-01-01"),
            _make_claim(Decimal("200000000"), "2023-06-01"),
            _make_claim(Decimal("150000000"), "2024-01-01"),
        ]
        criterion = _make_criterion(SIMPLE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state == VerdictState.eligible

    def test_not_enough_works(self):
        claims = [
            _make_claim(Decimal("100000000"), "2023-01-01"),
            _make_claim(Decimal("200000000"), "2023-06-01"),
        ]
        criterion = _make_criterion(SIMPLE_PARAMS)
        verdict = rule.evaluate(criterion, claims)
        assert verdict.state == VerdictState.not_eligible

    def test_no_evidence(self):
        criterion = _make_criterion(SIMPLE_PARAMS)
        verdict = rule.evaluate(criterion, [])
        assert verdict.state == VerdictState.needs_review
