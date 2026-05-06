"""All Pydantic / SQLModel schemas for Nirikshak — PRD §6."""

from __future__ import annotations

import enum
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlmodel import Column, Field as SQLField, SQLModel
from sqlalchemy import JSON, Text, BigInteger


# ── Enums ──────────────────────────────────────────────────────────────


class CriterionType(str, enum.Enum):
    financial_threshold = "financial_threshold"
    experience_count = "experience_count"
    statutory_registration = "statutory_registration"
    quality_certification = "quality_certification"
    document_checklist = "document_checklist"
    policy_compliance = "policy_compliance"


class VerdictState(str, enum.Enum):
    eligible = "eligible"
    not_eligible = "not_eligible"
    needs_review = "needs_review"


class RoutingTag(str, enum.Enum):
    native_pdf = "native_pdf"
    scanned_pdf = "scanned_pdf"
    photo_certificate = "photo_certificate"


class OfficerActionType(str, enum.Enum):
    accept = "accept"
    override = "override"
    re_extract = "re_extract"
    escalate = "escalate"


class AuditActionType(str, enum.Enum):
    tender_ingested = "tender_ingested"
    criteria_extracted = "criteria_extracted"
    criteria_locked = "criteria_locked"
    bidder_ingested = "bidder_ingested"
    evidence_extracted = "evidence_extracted"
    rule_fired = "rule_fired"
    bidder_verdict = "bidder_verdict"
    officer_review = "officer_review"
    report_finalized = "report_finalized"


# ── Pure Pydantic (not DB-backed) ─────────────────────────────────────


class BBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class DateRange(BaseModel):
    start: date
    end: date


class CompletedWorkClaim(BaseModel):
    value: Decimal
    completion_date: date
    description: str
    similarity_status: str = "unknown"  # similar | not_similar | borderline
    source_doc_id: UUID
    source_page: int
    source_bbox: BBox | None = None


class OfficerAction(BaseModel):
    type: OfficerActionType
    reason: str | None = None
    performed_at: datetime
    performed_by: str


# ── DB-backed models ──────────────────────────────────────────────────


class Tender(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    title: str
    procuring_authority: str
    bid_submission_date: date
    estimated_value: Decimal = SQLField(max_digits=15, decimal_places=2)
    source_pdf_id: UUID | None = SQLField(default=None)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)


class CriteriaSpec(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    tender_id: UUID = SQLField(foreign_key="tender.id")
    version: int = 1
    content_hash: str = ""
    locked_at: datetime | None = None
    locked_by: str | None = None


class Criterion(SQLModel, table=True):
    id: str = SQLField(primary_key=True)
    criteria_spec_id: UUID = SQLField(foreign_key="criteriaspec.id", primary_key=True)
    type: CriterionType
    description: str = SQLField(sa_column=Column(Text))
    mandatory: bool = True
    parameters: dict = SQLField(default_factory=dict, sa_column=Column(JSON))
    source_page: int = 0
    source_quote: str = SQLField(default="", sa_column=Column(Text))


class Bidder(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    tender_id: UUID = SQLField(foreign_key="tender.id")
    name: str
    submission_date: datetime = SQLField(default_factory=datetime.utcnow)


class Document(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    bidder_id: UUID | None = SQLField(default=None, foreign_key="bidder.id")
    tender_id: UUID | None = SQLField(default=None, foreign_key="tender.id")
    filename: str
    content_hash: str = ""
    routing_tag: RoutingTag = RoutingTag.native_pdf
    created_at: datetime = SQLField(default_factory=datetime.utcnow)


class Page(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    document_id: UUID = SQLField(foreign_key="document.id")
    page_number: int
    text: str = SQLField(default="", sa_column=Column(Text))
    bboxes: list = SQLField(default_factory=list, sa_column=Column(JSON))


class EvidenceClaim(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    bidder_id: UUID = SQLField(foreign_key="bidder.id")
    criterion_id: str
    extracted_value: dict = SQLField(default_factory=dict, sa_column=Column(JSON))
    source_doc_id: UUID = SQLField(foreign_key="document.id")
    source_page: int = 0
    source_bbox: dict | None = SQLField(default=None, sa_column=Column(JSON))
    confidence: float = 0.0
    verifier_passed: bool = False
    created_at: datetime = SQLField(default_factory=datetime.utcnow)


class Verdict(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    bidder_id: UUID = SQLField(foreign_key="bidder.id")
    criterion_id: str
    state: VerdictState
    evidence_ids: list = SQLField(default_factory=list, sa_column=Column(JSON))
    rule_fired: str = ""
    reason_template: str = SQLField(default="", sa_column=Column(Text))
    officer_action: dict | None = SQLField(default=None, sa_column=Column(JSON))
    created_at: datetime = SQLField(default_factory=datetime.utcnow)


class BidderVerdict(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    bidder_id: UUID = SQLField(foreign_key="bidder.id")
    tender_id: UUID = SQLField(foreign_key="tender.id")
    aggregate_state: VerdictState
    finalized_at: datetime | None = None
    created_at: datetime = SQLField(default_factory=datetime.utcnow)


class AuditLogEntry(SQLModel, table=True):
    sequence: int = SQLField(sa_column=Column(BigInteger, primary_key=True, autoincrement=False))
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)
    actor: str  # "system" or officer email
    action_type: AuditActionType
    payload: dict = SQLField(default_factory=dict, sa_column=Column(JSON))
    payload_hash: str = ""
    previous_hash: str = ""
    entry_hash: str = ""


# ── LLM response schemas (used with instructor) ──────────────────────


class MinedCriterion(BaseModel):
    """Schema for criterion miner LLM output."""
    suggested_id: str
    type: CriterionType
    description: str
    mandatory: bool = True
    parameters: dict = Field(default_factory=dict)
    source_page: int
    source_quote: str


class MinedCriteriaList(BaseModel):
    """Wrapper for a list of mined criteria."""
    criteria: list[MinedCriterion]


class SectionLabel(BaseModel):
    """Schema for section classifier LLM output."""
    label: str  # nit | eligibility | technical_specs | boq | annexures | other
    confidence: float
    reasoning: str


class LabeledSection(BaseModel):
    """A classified section of a tender document."""
    label: str
    pages: list[int]
    text: str
    confidence: float = 1.0
