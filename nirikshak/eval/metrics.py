"""Evaluation metrics — verdict agreement, evidence quality, needs-review fraction."""

import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from nirikshak.core.schemas import (
    Bidder, BidderVerdict, EvidenceClaim, Verdict, VerdictState,
)
from nirikshak.eval.golden_set import load_ground_truth

logger = logging.getLogger(__name__)


async def compute_metrics(session: AsyncSession) -> dict:
    """Compute evaluation metrics against the golden set and overall stats."""

    # Load ground truth
    gt = load_ground_truth()
    gt_bidders = {b["name"]: b for b in gt.get("bidders", [])}

    # Load actual data
    all_bidders = (await session.execute(select(Bidder))).scalars().all()
    all_bv = (await session.execute(select(BidderVerdict))).scalars().all()
    all_verdicts = (await session.execute(select(Verdict))).scalars().all()
    all_evidence = (await session.execute(select(EvidenceClaim))).scalars().all()

    bv_by_bidder = {bv.bidder_id: bv for bv in all_bv}
    verdicts_by_bidder = {}
    for v in all_verdicts:
        verdicts_by_bidder.setdefault(v.bidder_id, []).append(v)

    # ── Verdict-level agreement ───────────────────────────────────────

    bidder_matches = 0
    bidder_total = 0
    criterion_matches = 0
    criterion_total = 0

    per_bidder_results = []

    for bidder in all_bidders:
        gt_entry = gt_bidders.get(bidder.name)
        if not gt_entry:
            continue

        bidder_total += 1
        bv = bv_by_bidder.get(bidder.id)
        actual_agg = bv.aggregate_state.value if bv else "unknown"
        expected_agg = gt_entry["expected_verdict"]

        agg_match = actual_agg == expected_agg
        if agg_match:
            bidder_matches += 1

        # Per-criterion
        gt_criteria = gt_entry.get("criteria", {})
        actual_verdicts = verdicts_by_bidder.get(bidder.id, [])
        actual_by_crit = {v.criterion_id: v.state.value for v in actual_verdicts}

        crit_results = {}
        for crit_id, expected_state in gt_criteria.items():
            criterion_total += 1
            actual_state = actual_by_crit.get(crit_id, "missing")
            if actual_state == expected_state:
                criterion_matches += 1
                crit_results[crit_id] = {"expected": expected_state, "actual": actual_state, "match": True}
            else:
                crit_results[crit_id] = {"expected": expected_state, "actual": actual_state, "match": False}

        per_bidder_results.append({
            "bidder_name": bidder.name,
            "expected_verdict": expected_agg,
            "actual_verdict": actual_agg,
            "match": agg_match,
            "criteria": crit_results,
        })

    # ── Needs-Review fraction ─────────────────────────────────────────

    total_verdicts = len(all_verdicts)
    nr_count = sum(1 for v in all_verdicts if v.state == VerdictState.needs_review)
    nr_fraction = nr_count / total_verdicts if total_verdicts > 0 else 0

    # ── Evidence quality ──────────────────────────────────────────────

    total_evidence = len(all_evidence)
    verified_count = sum(1 for e in all_evidence if e.verifier_passed)
    avg_confidence = (sum(e.confidence for e in all_evidence) / total_evidence) if total_evidence > 0 else 0

    return {
        "verdict_agreement": {
            "bidder_level": {
                "matches": bidder_matches,
                "total": bidder_total,
                "accuracy": bidder_matches / bidder_total if bidder_total > 0 else None,
            },
            "criterion_level": {
                "matches": criterion_matches,
                "total": criterion_total,
                "accuracy": criterion_matches / criterion_total if criterion_total > 0 else None,
            },
            "per_bidder": per_bidder_results,
        },
        "needs_review_fraction": {
            "count": nr_count,
            "total": total_verdicts,
            "fraction": nr_fraction,
        },
        "evidence_quality": {
            "total_claims": total_evidence,
            "verified": verified_count,
            "verifier_pass_rate": verified_count / total_evidence if total_evidence > 0 else None,
            "avg_confidence": avg_confidence,
        },
        "test_set_size": {
            "tenders": 1,
            "bidders": bidder_total,
            "criterion_pairs": criterion_total,
        },
    }
