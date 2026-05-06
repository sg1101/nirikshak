# Architecture

## System Overview

Nirikshak follows a strict three-layer architecture that separates AI extraction from deterministic decision-making from human oversight.

```
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT CONSOLE                         │
│  Tender Library │ Gate 1 │ Bidder Queue │ Gate 2 │ Reports  │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
┌──────────────────────────┴──────────────────────────────────┐
│                      FASTAPI (API Layer)                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Ingestion   │  │   Tender     │  │  Bidder Evidence  │  │
│  │  Pipeline    │  │   Understanding│ │  Extraction       │  │
│  │  PDF/OCR/    │  │  Section      │  │  6 typed          │  │
│  │  Vision      │  │  Classifier + │  │  extractors +     │  │
│  │             │  │  Criterion    │  │  Verifier +       │  │
│  │             │  │  Miner        │  │  Confidence       │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
│                                              │               │
│  ┌───────────────────────────────────────────┴───────────┐  │
│  │              VERDICT ENGINE (No LLM)                   │  │
│  │  6 deterministic rules + disjunctive + aggregator     │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────┴──────────────────────────────┐  │
│  │              AUDIT LOG (Hash-Chained)                  │  │
│  │  Append-only │ Tamper-evident │ Replay capability     │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    POSTGRESQL DATABASE                        │
└─────────────────────────────────────────────────────────────┘
```

## Module Map

### `nirikshak/core/`
- `schemas.py` — All Pydantic/SQLModel models (10 DB tables, 6 enums, LLM response schemas)
- `hashing.py` — SHA-256 content hashing and audit chain hashing
- `config.py` — Environment-based configuration
- `db.py` — Async database engine and session management

### `nirikshak/ingestion/`
- `pdf_text.py` — PyMuPDF text + bounding box extraction
- `ocr.py` — PaddleOCR for scanned documents
- `vision.py` — LLM vision API for photographs
- `classify.py` — Document routing orchestrator
- `page_render.py` — Page rendering with bbox highlights

### `nirikshak/tender/`
- `section_classifier.py` — Two-pass (regex + LLM) section classification
- `criterion_miner.py` — LLM-powered eligibility criteria extraction
- `criteria_spec.py` — Spec versioning, locking, audit integration

### `nirikshak/bidder/`
- `doc_classifier.py` — Classify bidder documents by type
- `extractors/` — 6 typed evidence extractors (one per criterion type)
- `verifier.py` — Cross-check extracted values against cited source
- `confidence.py` — Per-claim confidence scoring

### `nirikshak/verdict/`
- `engine.py` — Rule registry and dispatch (NO LLM)
- `rules/` — 6 deterministic verdict rules including the disjunctive experience rule
- `aggregator.py` — Bidder-level verdict aggregation

### `nirikshak/audit/`
- `chain.py` — Hash-chained append-only audit log
- `replay.py` — Verdict replay from frozen inputs
- `signer.py` — PDF report generation with digital signature

### `nirikshak/llm/`
- `client.py` — OpenAI-compatible API wrapper with caching and retries
- `instructor_helpers.py` — Pydantic structured output via Instructor
- `prompts/` — One prompt file per extraction task

## Key Design Decisions

1. **No LLM in verdict layer** — Rules are deterministic Python. The LLM extracts; Python decides. This makes verdicts reproducible and auditable.

2. **Audit log is the regulated artefact** — Not the model accuracy. The hash chain, replay capability, and append-only enforcement are what make this system suitable for government use.

3. **Needs Review over silent disqualification** — When uncertain, the system flags for human review rather than making a wrong call. This is a feature, not a limitation.

4. **Verifier catches hallucinations** — Every extracted value is cross-checked against the cited page. If the value doesn't appear on the page, the claim is flagged.

5. **Disjunctive rules evaluate ALL branches** — Not just the first passing one. The audit record carries every branch evaluation for full transparency.
