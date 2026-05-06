"""Bidder-level verdict aggregation — PRD §5.4."""

import logging
from uuid import uuid4

from nirikshak.core.schemas import BidderVerdict, Criterion, Verdict, VerdictState

logger = logging.getLogger(__name__)


def aggregate_verdicts(
    verdicts: list[Verdict],
    criteria: list[Criterion],
    bidder_id=None,
    tender_id=None,
) -> BidderVerdict:
    """Aggregate per-criterion verdicts into a bidder-level verdict.

    Rules:
    - Any mandatory criterion not_eligible → bidder not_eligible
    - Any mandatory criterion needs_review (and none not_eligible) → bidder needs_review
    - All mandatory criteria eligible → bidder eligible
    - Optional criteria don't affect the bidder verdict
    """
    mandatory_ids = {c.id for c in criteria if c.mandatory}

    mandatory_verdicts = [v for v in verdicts if v.criterion_id in mandatory_ids]
    mandatory_states = [v.state for v in mandatory_verdicts]

    if VerdictState.not_eligible in mandatory_states:
        aggregate = VerdictState.not_eligible
        failed = [v for v in mandatory_verdicts if v.state == VerdictState.not_eligible]
        logger.info(
            "Bidder NOT ELIGIBLE: failed mandatory criteria: %s",
            [v.criterion_id for v in failed],
        )
    elif VerdictState.needs_review in mandatory_states:
        aggregate = VerdictState.needs_review
        review = [v for v in mandatory_verdicts if v.state == VerdictState.needs_review]
        logger.info(
            "Bidder NEEDS REVIEW: uncertain criteria: %s",
            [v.criterion_id for v in review],
        )
    else:
        aggregate = VerdictState.eligible
        logger.info("Bidder ELIGIBLE: all mandatory criteria passed")

    return BidderVerdict(
        id=uuid4(),
        bidder_id=bidder_id or uuid4(),
        tender_id=tender_id or uuid4(),
        aggregate_state=aggregate,
    )
