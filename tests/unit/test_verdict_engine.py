"""Unit tests for verdict engine rules and aggregator."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from nirikshak.core.schemas import (
    Criterion, CriterionType, EvidenceClaim, VerdictState,
)
from nirikshak.verdict.engine import evaluate_criterion
import nirikshak.verdict.rules  # noqa: trigger registration
from nirikshak.verdict.aggregator import aggregate_verdicts

DOC_ID = uuid4()


def _claim(criterion_id: str, value: dict, verified=True, confidence=0.9) -> EvidenceClaim:
    return EvidenceClaim(
        id=uuid4(),
        bidder_id=uuid4(),
        criterion_id=criterion_id,
        extracted_value=value,
        source_doc_id=DOC_ID,
        source_page=1,
        confidence=confidence,
        verifier_passed=verified,
    )


def _criterion(cid: str, ctype: CriterionType, params: dict, mandatory=True) -> Criterion:
    return Criterion(
        id=cid,
        criteria_spec_id=uuid4(),
        type=ctype,
        description="Test criterion",
        mandatory=mandatory,
        parameters=params,
        source_page=1,
        source_quote="test",
    )


# ── Financial threshold tests ─────────────────────────────────────────


class TestFinancialThreshold:
    def test_above_threshold(self):
        c = _criterion("FIN-001", CriterionType.financial_threshold,
                        {"threshold_amount": 50000000, "period_years": 3, "metric": "turnover"})
        evidence = [
            _claim("FIN-001", {"amount": "75000000", "fiscal_year": "2022-23", "metric": "turnover"}),
            _claim("FIN-001", {"amount": "80000000", "fiscal_year": "2023-24", "metric": "turnover"}),
        ]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.eligible

    def test_below_threshold(self):
        c = _criterion("FIN-001", CriterionType.financial_threshold,
                        {"threshold_amount": 50000000, "period_years": 3, "metric": "turnover"})
        evidence = [
            _claim("FIN-001", {"amount": "30000000", "fiscal_year": "2022-23", "metric": "turnover"}),
        ]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.not_eligible

    def test_no_evidence(self):
        c = _criterion("FIN-001", CriterionType.financial_threshold,
                        {"threshold_amount": 50000000})
        v = evaluate_criterion(c, [])
        assert v.state == VerdictState.needs_review

    def test_unverified_evidence_ignored(self):
        c = _criterion("FIN-001", CriterionType.financial_threshold,
                        {"threshold_amount": 50000000})
        evidence = [
            _claim("FIN-001", {"amount": "999000000"}, verified=False),
        ]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.needs_review


# ── Statutory registration tests ──────────────────────────────────────


class TestStatutoryRegistration:
    def test_valid_gst(self):
        c = _criterion("REG-001", CriterionType.statutory_registration,
                        {"registration_type": "GST", "valid_at_submission": True})
        evidence = [
            _claim("REG-001", {
                "registration_type": "GST",
                "registration_number": "36AABCT1332L1ZF",
                "valid_until": "2027-03-31",
            }),
        ]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.eligible

    def test_expired_registration(self):
        c = _criterion("REG-001", CriterionType.statutory_registration,
                        {"registration_type": "GST"})
        evidence = [
            _claim("REG-001", {
                "registration_type": "GST",
                "registration_number": "36AABCT1332L1ZF",
                "valid_until": "2020-03-31",
            }),
        ]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.not_eligible


# ── Quality certification tests ───────────────────────────────────────


class TestQualityCertification:
    def test_matching_cert(self):
        c = _criterion("QUA-001", CriterionType.quality_certification,
                        {"cert_name": "ISO 9001", "accepted_versions": ["2008", "2015"]})
        evidence = [
            _claim("QUA-001", {
                "cert_name": "ISO 9001",
                "cert_version": "2015",
                "expiry_date": "2027-12-31",
                "issuing_body": "Bureau Veritas",
            }),
        ]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.eligible

    def test_old_version_equivalent(self):
        """ISO 9001:2008 should satisfy ISO 9001 requirement via equivalence table."""
        c = _criterion("QUA-001", CriterionType.quality_certification,
                        {"cert_name": "ISO 9001"})
        evidence = [
            _claim("QUA-001", {
                "cert_name": "ISO 9001",
                "cert_version": "2008",
                "expiry_date": "2027-12-31",
                "issuing_body": "TUV",
            }),
        ]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.eligible

    def test_expired_cert(self):
        c = _criterion("QUA-001", CriterionType.quality_certification,
                        {"cert_name": "ISO 9001"})
        evidence = [
            _claim("QUA-001", {
                "cert_name": "ISO 9001",
                "cert_version": "2015",
                "expiry_date": "2020-01-01",
                "issuing_body": "TUV",
            }),
        ]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.not_eligible


# ── Document checklist tests ──────────────────────────────────────────


class TestDocumentChecklist:
    def test_present_and_signed(self):
        c = _criterion("DOC-001", CriterionType.document_checklist,
                        {"document_name": "EMD Receipt", "must_be_signed": True})
        evidence = [_claim("DOC-001", {"present": True, "signed": True})]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.eligible

    def test_present_but_unsigned(self):
        c = _criterion("DOC-001", CriterionType.document_checklist,
                        {"document_name": "EMD Receipt", "must_be_signed": True})
        evidence = [_claim("DOC-001", {"present": True, "signed": False})]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.not_eligible

    def test_missing_document(self):
        c = _criterion("DOC-001", CriterionType.document_checklist,
                        {"document_name": "EMD Receipt"})
        evidence = [_claim("DOC-001", {"present": False})]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.not_eligible

    def test_no_evidence(self):
        c = _criterion("DOC-001", CriterionType.document_checklist,
                        {"document_name": "EMD Receipt"})
        v = evaluate_criterion(c, [])
        assert v.state == VerdictState.not_eligible


# ── Policy compliance tests ───────────────────────────────────────────


class TestPolicyCompliance:
    def test_signed_declaration(self):
        c = _criterion("POL-001", CriterionType.policy_compliance,
                        {"policy_name": "Non-Debarment"})
        evidence = [_claim("POL-001", {
            "cross_check_status": "declared",
            "declaration_signed": True,
        })]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.eligible

    def test_missing_declaration(self):
        c = _criterion("POL-001", CriterionType.policy_compliance,
                        {"policy_name": "Non-Debarment"})
        evidence = [_claim("POL-001", {
            "cross_check_status": "not_found",
            "declaration_signed": False,
        })]
        v = evaluate_criterion(c, evidence)
        assert v.state == VerdictState.not_eligible


# ── Aggregator tests ──────────────────────────────────────────────────


class TestAggregator:
    def _make_verdicts(self, states: list[tuple[str, VerdictState, bool]]):
        from nirikshak.core.schemas import Verdict
        criteria = []
        verdicts = []
        for cid, state, mandatory in states:
            criteria.append(_criterion(cid, CriterionType.document_checklist, {}, mandatory=mandatory))
            verdicts.append(Verdict(
                id=uuid4(), bidder_id=uuid4(), criterion_id=cid,
                state=state, rule_fired="test", reason_template="test",
            ))
        return verdicts, criteria

    def test_all_eligible(self):
        verdicts, criteria = self._make_verdicts([
            ("C1", VerdictState.eligible, True),
            ("C2", VerdictState.eligible, True),
            ("C3", VerdictState.eligible, True),
        ])
        bv = aggregate_verdicts(verdicts, criteria)
        assert bv.aggregate_state == VerdictState.eligible

    def test_one_not_eligible(self):
        verdicts, criteria = self._make_verdicts([
            ("C1", VerdictState.eligible, True),
            ("C2", VerdictState.not_eligible, True),
            ("C3", VerdictState.eligible, True),
        ])
        bv = aggregate_verdicts(verdicts, criteria)
        assert bv.aggregate_state == VerdictState.not_eligible

    def test_one_needs_review(self):
        verdicts, criteria = self._make_verdicts([
            ("C1", VerdictState.eligible, True),
            ("C2", VerdictState.needs_review, True),
            ("C3", VerdictState.eligible, True),
        ])
        bv = aggregate_verdicts(verdicts, criteria)
        assert bv.aggregate_state == VerdictState.needs_review

    def test_not_eligible_beats_needs_review(self):
        verdicts, criteria = self._make_verdicts([
            ("C1", VerdictState.not_eligible, True),
            ("C2", VerdictState.needs_review, True),
        ])
        bv = aggregate_verdicts(verdicts, criteria)
        assert bv.aggregate_state == VerdictState.not_eligible

    def test_optional_failure_doesnt_block(self):
        verdicts, criteria = self._make_verdicts([
            ("C1", VerdictState.eligible, True),
            ("C2", VerdictState.not_eligible, False),  # optional
        ])
        bv = aggregate_verdicts(verdicts, criteria)
        assert bv.aggregate_state == VerdictState.eligible

    def test_optional_needs_review_doesnt_block(self):
        verdicts, criteria = self._make_verdicts([
            ("C1", VerdictState.eligible, True),
            ("C2", VerdictState.needs_review, False),  # optional
        ])
        bv = aggregate_verdicts(verdicts, criteria)
        assert bv.aggregate_state == VerdictState.eligible
