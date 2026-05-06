"""Unit tests for Pydantic/SQLModel schemas."""

import json
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from nirikshak.core.schemas import (
    AuditActionType,
    AuditLogEntry,
    BBox,
    Bidder,
    BidderVerdict,
    CompletedWorkClaim,
    Criterion,
    CriteriaSpec,
    CriterionType,
    DateRange,
    Document,
    EvidenceClaim,
    LabeledSection,
    MinedCriteriaList,
    MinedCriterion,
    OfficerAction,
    OfficerActionType,
    Page,
    RoutingTag,
    SectionLabel,
    Tender,
    Verdict,
    VerdictState,
)


class TestEnums:
    def test_criterion_types(self):
        assert CriterionType.financial_threshold.value == "financial_threshold"
        assert len(CriterionType) == 6

    def test_verdict_states(self):
        assert VerdictState.eligible.value == "eligible"
        assert len(VerdictState) == 3

    def test_routing_tags(self):
        assert RoutingTag.native_pdf.value == "native_pdf"
        assert len(RoutingTag) == 3


class TestPureModels:
    def test_bbox(self):
        b = BBox(x0=0, y0=0, x1=100, y1=50)
        assert b.x1 == 100
        data = b.model_dump()
        assert BBox(**data) == b

    def test_date_range(self):
        dr = DateRange(start=date(2020, 1, 1), end=date(2025, 1, 1))
        assert dr.start.year == 2020

    def test_completed_work_claim(self):
        c = CompletedWorkClaim(
            value=Decimal("22500000"),
            completion_date=date(2023, 6, 15),
            description="Road construction",
            similarity_status="similar",
            source_doc_id=uuid4(),
            source_page=4,
        )
        assert c.value == Decimal("22500000")
        serialized = c.model_dump(mode="json")
        assert CompletedWorkClaim(**serialized)

    def test_officer_action(self):
        oa = OfficerAction(
            type=OfficerActionType.override,
            reason="Turnover value manually verified",
            performed_at=datetime.utcnow(),
            performed_by="officer1@crpf.gov.in",
        )
        assert oa.type == OfficerActionType.override


class TestDBModels:
    def test_tender(self):
        t = Tender(
            title="Construction Tender",
            procuring_authority="CRPF Zone Bangalore",
            bid_submission_date=date(2025, 4, 30),
            estimated_value=Decimal("500000000"),
        )
        assert t.id is not None
        assert t.estimated_value == Decimal("500000000")

    def test_criteria_spec(self):
        spec = CriteriaSpec(tender_id=uuid4(), version=1, content_hash="abc123")
        assert spec.locked_at is None

    def test_criterion(self):
        c = Criterion(
            id="FIN-001",
            criteria_spec_id=uuid4(),
            type=CriterionType.financial_threshold,
            description="Average annual turnover >= 5 crore",
            mandatory=True,
            parameters={"threshold_amount": 50000000, "period_years": 3},
            source_page=5,
            source_quote="The bidder shall have an average annual turnover of not less than Rs. 5 crore",
        )
        assert c.mandatory is True
        assert c.parameters["threshold_amount"] == 50000000

    def test_document(self):
        d = Document(
            filename="tender.pdf",
            content_hash="abc",
            routing_tag=RoutingTag.native_pdf,
        )
        assert d.bidder_id is None
        assert d.routing_tag == RoutingTag.native_pdf

    def test_page(self):
        p = Page(
            document_id=uuid4(),
            page_number=0,
            text="Hello world",
            bboxes=[{"x0": 0, "y0": 0, "x1": 50, "y1": 10}],
        )
        assert p.text == "Hello world"

    def test_evidence_claim(self):
        ec = EvidenceClaim(
            bidder_id=uuid4(),
            criterion_id="FIN-001",
            extracted_value={"amount": 75000000, "period": "2021-2024"},
            source_doc_id=uuid4(),
            source_page=3,
            confidence=0.92,
            verifier_passed=True,
        )
        assert ec.confidence == 0.92

    def test_verdict(self):
        v = Verdict(
            bidder_id=uuid4(),
            criterion_id="FIN-001",
            state=VerdictState.eligible,
            rule_fired="FinancialThreshold.WindowedTurnover",
            reason_template="Bidder turnover of 7.5 cr exceeds threshold of 5 cr",
        )
        assert v.state == VerdictState.eligible

    def test_bidder_verdict(self):
        bv = BidderVerdict(
            bidder_id=uuid4(),
            tender_id=uuid4(),
            aggregate_state=VerdictState.not_eligible,
        )
        assert bv.finalized_at is None

    def test_audit_log_entry(self):
        e = AuditLogEntry(
            sequence=0,
            actor="system",
            action_type=AuditActionType.tender_ingested,
            payload={"tender_id": "abc"},
            payload_hash="hash1",
            previous_hash="0" * 64,
            entry_hash="hash2",
        )
        assert e.sequence == 0


class TestLLMSchemas:
    def test_mined_criterion(self):
        mc = MinedCriterion(
            suggested_id="FIN-001",
            type=CriterionType.financial_threshold,
            description="Minimum turnover",
            mandatory=True,
            parameters={"threshold_amount": 50000000},
            source_page=5,
            source_quote="turnover of 5 crore",
        )
        assert mc.type == CriterionType.financial_threshold

    def test_mined_criteria_list(self):
        mcl = MinedCriteriaList(criteria=[
            MinedCriterion(
                suggested_id="FIN-001",
                type=CriterionType.financial_threshold,
                description="test",
                source_page=1,
                source_quote="quote",
            ),
        ])
        assert len(mcl.criteria) == 1

    def test_section_label(self):
        sl = SectionLabel(label="eligibility", confidence=0.95, reasoning="Contains criteria")
        assert sl.label == "eligibility"

    def test_labeled_section(self):
        ls = LabeledSection(label="eligibility", pages=[1, 2], text="criteria text")
        assert ls.confidence == 1.0  # default


class TestJSONRoundTrip:
    def test_tender_roundtrip(self):
        t = Tender(
            title="Test",
            procuring_authority="CRPF",
            bid_submission_date=date(2025, 4, 30),
            estimated_value=Decimal("100"),
        )
        data = t.model_dump(mode="json")
        json_str = json.dumps(data)
        restored = json.loads(json_str)
        assert restored["title"] == "Test"

    def test_bbox_roundtrip(self):
        b = BBox(x0=1.5, y0=2.5, x1=100.0, y1=50.0)
        json_str = b.model_dump_json()
        restored = BBox.model_validate_json(json_str)
        assert restored == b
