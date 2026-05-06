"""Base extractor interface and registry."""

from abc import ABC, abstractmethod
from uuid import UUID

from nirikshak.core.schemas import Criterion, CriterionType, Document, EvidenceClaim, Page


class BaseExtractor(ABC):
    criterion_type: CriterionType

    @abstractmethod
    def extract(
        self,
        criterion: Criterion,
        documents: list[Document],
        pages_by_doc: dict[UUID, list[Page]],
        doc_categories: dict[UUID, str],
    ) -> list[EvidenceClaim]:
        ...

    def _filter_docs(
        self,
        documents: list[Document],
        doc_categories: dict[UUID, str],
        target_category: str,
    ) -> list[Document]:
        """Filter documents to a specific category."""
        return [d for d in documents if doc_categories.get(d.id) == target_category]

    def _get_text_for_doc(self, doc: Document, pages_by_doc: dict[UUID, list[Page]]) -> str:
        """Get concatenated text for a document with page markers."""
        pages = sorted(pages_by_doc.get(doc.id, []), key=lambda p: p.page_number)
        parts = []
        for p in pages:
            parts.append(f"--- Page {p.page_number} ---\n{p.text}")
        return "\n\n".join(parts)

    def _get_all_text(
        self,
        documents: list[Document],
        pages_by_doc: dict[UUID, list[Page]],
        doc_categories: dict[UUID, str],
        target_category: str,
    ) -> tuple[list[Document], str]:
        """Get filtered docs and combined text."""
        docs = self._filter_docs(documents, doc_categories, target_category)
        if not docs:
            # Fall back to all documents
            docs = documents
        texts = []
        for doc in docs:
            texts.append(f"=== Document: {doc.filename} (ID: {doc.id}) ===\n{self._get_text_for_doc(doc, pages_by_doc)}")
        return docs, "\n\n".join(texts)[:12000]  # cap for LLM context


# ── Registry ──────────────────────────────────────────────────────────

_registry: dict[CriterionType, BaseExtractor] = {}


def register_extractor(extractor: BaseExtractor):
    _registry[extractor.criterion_type] = extractor


def get_extractor(criterion_type: CriterionType) -> BaseExtractor | None:
    return _registry.get(criterion_type)
