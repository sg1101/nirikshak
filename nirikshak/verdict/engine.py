"""Verdict engine — registry pattern, dispatches criterion to rule. NO LLM here."""

import logging
from abc import ABC, abstractmethod

from nirikshak.core.schemas import Criterion, CriterionType, EvidenceClaim, Verdict, VerdictState

logger = logging.getLogger(__name__)


class BaseRule(ABC):
    criterion_type: CriterionType

    @abstractmethod
    def evaluate(self, criterion: Criterion, evidence: list[EvidenceClaim]) -> Verdict:
        ...

    def _needs_review_verdict(self, criterion: Criterion, reason: str) -> Verdict:
        from uuid import uuid4
        return Verdict(
            id=uuid4(),
            bidder_id=uuid4(),  # set by caller
            criterion_id=criterion.id,
            state=VerdictState.needs_review,
            rule_fired=f"{self.__class__.__name__}",
            reason_template=reason,
        )

    def _eligible_verdict(self, criterion: Criterion, reason: str, evidence_ids: list = None) -> Verdict:
        from uuid import uuid4
        return Verdict(
            id=uuid4(),
            bidder_id=uuid4(),
            criterion_id=criterion.id,
            state=VerdictState.eligible,
            evidence_ids=[str(eid) for eid in (evidence_ids or [])],
            rule_fired=f"{self.__class__.__name__}",
            reason_template=reason,
        )

    def _not_eligible_verdict(self, criterion: Criterion, reason: str, evidence_ids: list = None) -> Verdict:
        from uuid import uuid4
        return Verdict(
            id=uuid4(),
            bidder_id=uuid4(),
            criterion_id=criterion.id,
            state=VerdictState.not_eligible,
            evidence_ids=[str(eid) for eid in (evidence_ids or [])],
            rule_fired=f"{self.__class__.__name__}",
            reason_template=reason,
        )


# ── Registry ──────────────────────────────────────────────────────────

_registry: dict[CriterionType, BaseRule] = {}


def register_rule(rule: BaseRule):
    _registry[rule.criterion_type] = rule


def evaluate_criterion(criterion: Criterion, evidence: list[EvidenceClaim]) -> Verdict:
    """Evaluate a single criterion against its evidence."""
    rule = _registry.get(criterion.type)
    if rule is None:
        logger.warning("No rule registered for criterion type: %s", criterion.type)
        from uuid import uuid4
        return Verdict(
            id=uuid4(),
            bidder_id=uuid4(),
            criterion_id=criterion.id,
            state=VerdictState.needs_review,
            rule_fired="NoRuleRegistered",
            reason_template=f"No evaluation rule for criterion type '{criterion.type.value}'. Needs manual review.",
        )
    return rule.evaluate(criterion, evidence)


def evaluate_all(
    criteria: list[Criterion],
    evidence_pool: dict[str, list[EvidenceClaim]],
) -> list[Verdict]:
    """Evaluate all criteria against the evidence pool."""
    verdicts = []
    for criterion in criteria:
        evidence = evidence_pool.get(criterion.id, [])
        verdict = evaluate_criterion(criterion, evidence)
        verdicts.append(verdict)
        logger.info(
            "Verdict: %s → %s (rule=%s)",
            criterion.id, verdict.state.value, verdict.rule_fired,
        )
    return verdicts
