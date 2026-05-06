"""FastAPI application — API endpoints for Nirikshak."""

import logging
import shutil
import tempfile
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nirikshak.audit.chain import append_entry, verify_chain
from nirikshak.core.db import get_session, init_db
from nirikshak.core.schemas import (
    AuditActionType,
    Bidder,
    BidderVerdict,
    CriteriaSpec,
    Criterion,
    Document,
    EvidenceClaim,
    Page,
    Tender,
    Verdict,
    AuditLogEntry,
)
from nirikshak.ingestion.classify import ingest_document, ingest_bidder_packet
from nirikshak.tender.criteria_spec import build_spec, get_criteria_for_spec, get_locked_spec, lock_spec
from nirikshak.tender.criterion_miner import mine_criteria
from nirikshak.tender.section_classifier import classify_sections
from nirikshak.bidder.doc_classifier import classify_bidder_documents
from nirikshak.bidder.extractors import get_extractor
from nirikshak.bidder.verifier import verify_claim
from nirikshak.bidder.confidence import apply_confidence
from nirikshak.verdict.engine import evaluate_criterion
import nirikshak.verdict.rules  # noqa: trigger rule registration
from nirikshak.verdict.aggregator import aggregate_verdicts

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    await init_db()
    logger.info("Nirikshak API started")
    yield


app = FastAPI(title="Nirikshak", version="0.1.0", lifespan=lifespan)


# ── Health ────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ── Tender Upload + Processing ────────────────────────────────────────


@app.post("/api/tenders/upload")
async def upload_tender(
    file: UploadFile = File(...),
    title: str = Form("Untitled Tender"),
    procuring_authority: str = Form("Unknown"),
    bid_submission_date: str = Form("2025-04-30"),
    estimated_value: str = Form("0"),
    session: AsyncSession = Depends(get_session),
):
    """Upload a tender PDF, extract criteria, return CriteriaSpec."""
    # Save uploaded file to temp
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        # Create tender record
        tender = Tender(
            id=uuid4(),
            title=title,
            procuring_authority=procuring_authority,
            bid_submission_date=date.fromisoformat(bid_submission_date),
            estimated_value=Decimal(estimated_value),
        )
        session.add(tender)
        await session.flush()

        # Ingest document
        document, pages = ingest_document(tmp_path, tender_id=tender.id)
        tender.source_pdf_id = document.id
        session.add(document)
        for p in pages:
            session.add(p)
        await session.flush()

        # Audit: tender ingested
        await append_entry(session, "system", AuditActionType.tender_ingested, {
            "tender_id": str(tender.id),
            "document_hash": document.content_hash,
            "filename": document.filename,
        })

        # Classify sections
        sections = classify_sections(pages)

        # Mine criteria
        criteria = mine_criteria(sections, tender)

        if not criteria:
            await session.commit()
            return {
                "tender_id": str(tender.id),
                "document_id": str(document.id),
                "criteria_spec": None,
                "message": "No eligibility criteria found",
            }

        # Build spec
        spec = await build_spec(session, tender.id, criteria)

        await session.commit()

        return {
            "tender_id": str(tender.id),
            "document_id": str(document.id),
            "criteria_spec": {
                "id": str(spec.id),
                "version": spec.version,
                "content_hash": spec.content_hash,
                "criteria": [
                    {
                        "id": c.id,
                        "type": c.type.value,
                        "description": c.description,
                        "mandatory": c.mandatory,
                        "parameters": c.parameters,
                        "source_page": c.source_page,
                        "source_quote": c.source_quote,
                    }
                    for c in criteria
                ],
            },
        }

    finally:
        tmp_path.unlink(missing_ok=True)


# ── Tender List + Detail ──────────────────────────────────────────────


@app.get("/api/tenders")
async def list_tenders(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Tender).order_by(Tender.created_at.desc()))
    tenders = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "title": t.title,
            "procuring_authority": t.procuring_authority,
            "bid_submission_date": t.bid_submission_date.isoformat(),
            "estimated_value": str(t.estimated_value),
        }
        for t in tenders
    ]


@app.get("/api/tenders/{tender_id}/criteria")
async def get_tender_criteria(tender_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(CriteriaSpec).where(CriteriaSpec.tender_id == tender_id).order_by(CriteriaSpec.version.desc()).limit(1)
    )
    spec = result.scalar_one_or_none()
    if not spec:
        raise HTTPException(status_code=404, detail="No criteria spec found")

    criteria = await get_criteria_for_spec(session, spec.id)
    return {
        "spec_id": str(spec.id),
        "version": spec.version,
        "content_hash": spec.content_hash,
        "locked": spec.locked_at is not None,
        "locked_at": spec.locked_at.isoformat() if spec.locked_at else None,
        "locked_by": spec.locked_by,
        "criteria": [
            {
                "id": c.id,
                "type": c.type.value,
                "description": c.description,
                "mandatory": c.mandatory,
                "parameters": c.parameters,
                "source_page": c.source_page,
                "source_quote": c.source_quote,
            }
            for c in criteria
        ],
    }


# ── Add Criteria to Spec ───────────────────────────────────────────────


@app.post("/api/criteria-specs/{spec_id}/add-criteria")
async def add_criteria_to_spec(
    spec_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Add seed criteria (FIN-001, QUA-001) to an existing spec. For demo setup."""
    from nirikshak.core.schemas import CriterionType

    result = await session.execute(select(CriteriaSpec).where(CriteriaSpec.id == spec_id))
    spec = result.scalar_one_or_none()
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    if spec.locked_at is not None:
        raise HTTPException(status_code=400, detail="Spec is locked, cannot add criteria")

    # Check which criteria already exist
    existing = await session.execute(select(Criterion).where(Criterion.criteria_spec_id == spec_id))
    existing_ids = {c.id for c in existing.scalars().all()}

    added = []

    if "FIN-001" not in existing_ids:
        fin = Criterion(
            id="FIN-001",
            criteria_spec_id=spec_id,
            type=CriterionType.financial_threshold,
            description="Average annual turnover of not less than Rs. 5 Crore in the last 3 financial years",
            mandatory=True,
            parameters={"threshold_amount": 50000000, "currency": "INR", "period_years": 3, "metric": "turnover"},
            source_page=0,
            source_quote="The bidder shall have an average annual turnover of not less than Rs. 5 Crore (Rupees Five Crore) during the last three financial years ending 31st March.",
        )
        session.add(fin)
        added.append("FIN-001")

    if "QUA-001" not in existing_ids:
        qua = Criterion(
            id="QUA-001",
            criteria_spec_id=spec_id,
            type=CriterionType.quality_certification,
            description="Valid ISO 9001 certification (version 2008 or 2015)",
            mandatory=True,
            parameters={"cert_name": "ISO 9001", "accepted_versions": ["2008", "2015"], "scope": None},
            source_page=0,
            source_quote="The bidder shall possess a valid ISO 9001 Quality Management System certification from an accredited body.",
        )
        session.add(qua)
        added.append("QUA-001")

    await session.flush()
    await session.commit()

    return {"spec_id": str(spec_id), "added_criteria": added}


# ── Lock Criteria Spec ────────────────────────────────────────────────


@app.post("/api/criteria-specs/{spec_id}/lock")
async def lock_criteria_spec(
    spec_id: UUID,
    officer_email: str = Form("officer1@crpf.gov.in"),
    session: AsyncSession = Depends(get_session),
):
    try:
        spec = await lock_spec(session, spec_id, officer_email)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await session.commit()
    return {
        "spec_id": str(spec.id),
        "locked_at": spec.locked_at.isoformat(),
        "locked_by": spec.locked_by,
        "content_hash": spec.content_hash,
    }


# ── Audit Log ─────────────────────────────────────────────────────────


@app.get("/api/audit")
async def get_audit_log(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(AuditLogEntry).order_by(AuditLogEntry.sequence.asc()))
    entries = result.scalars().all()
    return [
        {
            "sequence": e.sequence,
            "timestamp": e.timestamp.isoformat(),
            "actor": e.actor,
            "action_type": e.action_type.value,
            "payload": e.payload,
            "entry_hash": e.entry_hash,
        }
        for e in entries
    ]


@app.get("/api/audit/verify")
async def verify_audit_chain(session: AsyncSession = Depends(get_session)):
    valid, broken_at = await verify_chain(session)
    return {"valid": valid, "broken_at_sequence": broken_at}


@app.post("/api/audit/replay")
async def replay_audit_entry(
    entry_hash: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    from nirikshak.audit.replay import replay_verdict
    result = await replay_verdict(entry_hash, session)
    return result.model_dump()


# ── Report ────────────────────────────────────────────────────────────


@app.get("/api/tenders/{tender_id}/report")
async def download_report(tender_id: UUID, session: AsyncSession = Depends(get_session)):
    from nirikshak.audit.signer import generate_report
    from fastapi.responses import Response

    try:
        pdf_bytes = await generate_report(tender_id, session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Audit entry
    from nirikshak.core.hashing import content_hash
    await append_entry(session, "system", AuditActionType.report_finalized, {
        "tender_id": str(tender_id),
        "report_hash": content_hash(pdf_bytes),
    })
    await session.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=nirikshak_report_{str(tender_id)[:8]}.pdf"},
    )


# ── Eval Metrics ──────────────────────────────────────────────────────


@app.get("/api/eval/metrics")
async def get_eval_metrics(session: AsyncSession = Depends(get_session)):
    from nirikshak.eval.metrics import compute_metrics
    return await compute_metrics(session)


# ── Bidder Upload + Evaluation ────────────────────────────────────────


@app.post("/api/tenders/{tender_id}/bidders/upload")
async def upload_bidder(
    tender_id: UUID,
    files: list[UploadFile] = File(...),
    bidder_name: str = Form("Unknown Bidder"),
    session: AsyncSession = Depends(get_session),
):
    """Upload bidder documents, extract evidence, evaluate against criteria, return verdicts."""
    from nirikshak.core.schemas import EvidenceClaim as ECModel, Verdict as VModel, BidderVerdict as BVModel

    # Get tender
    result = await session.execute(select(Tender).where(Tender.id == tender_id))
    tender = result.scalar_one_or_none()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Get locked criteria spec
    spec = await get_locked_spec(session, tender_id)
    if not spec:
        # Auto-lock if only one spec exists
        result = await session.execute(
            select(CriteriaSpec).where(CriteriaSpec.tender_id == tender_id).order_by(CriteriaSpec.version.desc()).limit(1)
        )
        spec = result.scalar_one_or_none()
        if spec and spec.locked_at is None:
            spec = await lock_spec(session, spec.id, "system@auto")
            await session.flush()
        if not spec:
            raise HTTPException(status_code=400, detail="No criteria spec found. Upload tender first.")

    criteria = await get_criteria_for_spec(session, spec.id)

    # Create bidder
    bidder = Bidder(id=uuid4(), tender_id=tender_id, name=bidder_name)
    session.add(bidder)
    await session.flush()

    # Ingest all uploaded files
    all_documents = []
    all_pages = []
    tmp_paths = []
    try:
        for f in files:
            suffix = Path(f.filename or "doc.pdf").suffix
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, prefix=f"{f.filename}_") as tmp:
                shutil.copyfileobj(f.file, tmp)
                tmp_paths.append(Path(tmp.name))

            doc, pages = ingest_document(tmp_paths[-1], tender_id=tender_id, bidder_id=bidder.id)
            doc.bidder_id = bidder.id
            session.add(doc)
            for p in pages:
                session.add(p)
            all_documents.append(doc)
            all_pages.extend(pages)

        await session.flush()

        # Audit: bidder ingested
        await append_entry(session, "system", AuditActionType.bidder_ingested, {
            "tender_id": str(tender_id),
            "bidder_id": str(bidder.id),
            "bidder_name": bidder_name,
            "document_count": len(all_documents),
            "document_hashes": [d.content_hash for d in all_documents],
        })

        # Build pages lookup
        pages_by_doc = {}
        for p in all_pages:
            pages_by_doc.setdefault(p.document_id, []).append(p)

        # Classify documents
        doc_categories = classify_bidder_documents(all_documents, pages_by_doc)

        # Extract evidence for each criterion
        evidence_pool: dict[str, list] = {}
        for criterion in criteria:
            extractor = get_extractor(criterion.type)
            if not extractor:
                logger.warning("No extractor for criterion type: %s", criterion.type)
                evidence_pool[criterion.id] = []
                continue

            claims = extractor.extract(criterion, all_documents, pages_by_doc, doc_categories)

            # Set bidder_id and verify + score confidence
            for claim in claims:
                claim.bidder_id = bidder.id
                claim = verify_claim(claim, pages_by_doc)
                claim = apply_confidence(claim, routing_tag=all_documents[0].routing_tag if all_documents else None)
                session.add(claim)

            evidence_pool[criterion.id] = claims

            # Audit: evidence extracted
            await append_entry(session, "system", AuditActionType.evidence_extracted, {
                "tender_id": str(tender_id),
                "bidder_id": str(bidder.id),
                "criterion_id": criterion.id,
                "claims_count": len(claims),
                "verified_count": sum(1 for c in claims if c.verifier_passed),
            })

        await session.flush()

        # Run verdict engine
        verdicts = []
        for criterion in criteria:
            evidence = evidence_pool.get(criterion.id, [])
            verdict = evaluate_criterion(criterion, evidence)
            verdict.bidder_id = bidder.id
            session.add(verdict)
            verdicts.append(verdict)

            # Audit: rule fired
            await append_entry(session, "system", AuditActionType.rule_fired, {
                "tender_id": str(tender_id),
                "bidder_id": str(bidder.id),
                "criterion_id": criterion.id,
                "rule": verdict.rule_fired,
                "state": verdict.state.value,
            })

        # Aggregate
        bidder_verdict = aggregate_verdicts(verdicts, criteria, bidder_id=bidder.id, tender_id=tender_id)
        session.add(bidder_verdict)

        # Audit: bidder verdict
        await append_entry(session, "system", AuditActionType.bidder_verdict, {
            "tender_id": str(tender_id),
            "bidder_id": str(bidder.id),
            "aggregate_state": bidder_verdict.aggregate_state.value,
        })

        await session.commit()

        return {
            "bidder_id": str(bidder.id),
            "bidder_name": bidder_name,
            "aggregate_verdict": bidder_verdict.aggregate_state.value,
            "per_criterion": [
                {
                    "criterion_id": v.criterion_id,
                    "state": v.state.value,
                    "rule_fired": v.rule_fired,
                    "reason": v.reason_template,
                    "evidence_count": len(evidence_pool.get(v.criterion_id, [])),
                }
                for v in verdicts
            ],
            "document_categories": {str(k): v for k, v in doc_categories.items()},
        }

    finally:
        for p in tmp_paths:
            p.unlink(missing_ok=True)


@app.get("/api/tenders/{tender_id}/bidders")
async def list_bidders(tender_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Bidder).where(Bidder.tender_id == tender_id))
    bidders = result.scalars().all()

    bidder_verdicts = {}
    for b in bidders:
        vr = await session.execute(
            select(BidderVerdict).where(BidderVerdict.bidder_id == b.id).limit(1)
        )
        bv = vr.scalar_one_or_none()
        bidder_verdicts[b.id] = bv

    return [
        {
            "id": str(b.id),
            "name": b.name,
            "submission_date": b.submission_date.isoformat(),
            "aggregate_verdict": bidder_verdicts[b.id].aggregate_state.value if bidder_verdicts.get(b.id) else None,
        }
        for b in bidders
    ]


@app.get("/api/bidders/{bidder_id}/verdicts")
async def get_bidder_verdicts(bidder_id: UUID, session: AsyncSession = Depends(get_session)):
    from nirikshak.core.schemas import Verdict as VModel, EvidenceClaim as ECModel

    result = await session.execute(select(VModel).where(VModel.bidder_id == bidder_id))
    verdicts = result.scalars().all()

    result = await session.execute(select(ECModel).where(ECModel.bidder_id == bidder_id))
    all_evidence = result.scalars().all()
    evidence_by_criterion = {}
    for e in all_evidence:
        evidence_by_criterion.setdefault(e.criterion_id, []).append(e)

    return {
        "bidder_id": str(bidder_id),
        "verdicts": [
            {
                "criterion_id": v.criterion_id,
                "state": v.state.value,
                "rule_fired": v.rule_fired,
                "reason": v.reason_template,
                "evidence": [
                    {
                        "id": str(e.id),
                        "extracted_value": e.extracted_value,
                        "source_page": e.source_page,
                        "confidence": e.confidence,
                        "verifier_passed": e.verifier_passed,
                    }
                    for e in evidence_by_criterion.get(v.criterion_id, [])
                ],
            }
            for v in verdicts
        ],
    }
