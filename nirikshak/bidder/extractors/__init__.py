"""Evidence extractors — import all to trigger registration."""

from nirikshak.bidder.extractors.base import get_extractor, register_extractor  # noqa
from nirikshak.bidder.extractors.financial_threshold import FinancialThresholdExtractor  # noqa
from nirikshak.bidder.extractors.statutory_registration import StatutoryRegistrationExtractor  # noqa
from nirikshak.bidder.extractors.quality_certification import QualityCertificationExtractor  # noqa
from nirikshak.bidder.extractors.document_checklist import DocumentChecklistExtractor  # noqa
from nirikshak.bidder.extractors.policy_compliance import PolicyComplianceExtractor  # noqa
from nirikshak.bidder.extractors.experience_count import ExperienceCountExtractor  # noqa
