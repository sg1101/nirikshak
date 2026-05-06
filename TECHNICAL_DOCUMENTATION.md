# Nirikshak — Technical Documentation

## 1. System Overview

Nirikshak is an AI-based tender evaluation system for government procurement. It automates the evaluation of bidder eligibility against tender criteria, producing explainable, auditable verdicts suitable for formal government decision-making.

**Core Thesis:** AI extracts evidence. Rules decide verdicts. Officers approve.

**Three-layer architecture:**
1. **AI Layer** — LLM extracts structured data from unstructured documents (criteria from tenders, evidence from bidder submissions)
2. **Rule Layer** — Deterministic Python rules evaluate extracted evidence against criteria. Zero LLM involvement in decisions.
3. **Human Layer** — Officers review, edit, override via HITL gates. Every action is audit-logged.

---

## 2. Tech Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.11+ | Core runtime |
| LLM Provider | OpenAI-compatible API | OpenCode Go | Structured extraction, document understanding |
| LLM Model | qwen3.6-plus | via OpenCode | Criterion mining, evidence extraction, similarity classification |
| Structured Output | Instructor | 1.15+ | Pydantic model validation on LLM responses (JSON mode) |
| OCR | PaddleOCR | 3.5+ | Scanned document text extraction (English + Hindi) |
| PDF Processing | PyMuPDF (fitz) | 1.24+ | Text extraction, bounding boxes, page rendering |
| Data Models | Pydantic v2 + SQLModel | 2.13 / 0.0.38 | Type-safe schemas, DB round-trip |
| Database | PostgreSQL | 16 | Persistent storage, audit log integrity |
| API Framework | FastAPI | 0.136+ | REST API endpoints |
| Console | Streamlit | 1.57+ | Officer-facing UI, 7-page multipage app |
| PDF Reports | ReportLab | 4.2+ | Signed PDF report generation |
| Infrastructure | Docker Compose | v2 | Single-command deployment |
| Testing | pytest | 8.0+ | Unit and integration tests |

---

## 3. Database Schema

**10 tables**, all defined as SQLModel classes in `nirikshak/core/schemas.py`:

### Tender
Primary entity representing a government tender document.
| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier |
| title | str | Tender title |
| procuring_authority | str | Issuing authority (e.g., "CRPF Zone Bangalore") |
| bid_submission_date | date | Deadline for bid submission |
| estimated_value | Decimal(15,2) | Estimated cost in INR |
| source_pdf_id | UUID (FK, nullable) | Reference to uploaded tender Document |
| created_at | datetime | Record creation timestamp |

### CriteriaSpec
Versioned, lockable set of eligibility criteria extracted from a tender.
| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier |
| tender_id | UUID (FK → Tender) | Parent tender |
| version | int | Spec version number |
| content_hash | str | SHA-256 of serialized criteria (for audit) |
| locked_at | datetime (nullable) | When locked by officer (Gate 1) |
| locked_by | str (nullable) | Officer email who locked |

### Criterion
Individual eligibility criterion within a spec.
| Field | Type | Description |
|-------|------|-------------|
| id | str (PK) | Human-readable ID (e.g., "FIN-001", "REG-001") |
| criteria_spec_id | UUID (PK, FK → CriteriaSpec) | Parent spec |
| type | CriterionType (enum) | One of 6 types (see §4) |
| description | text | Human-readable description |
| mandatory | bool | Whether failure blocks eligibility |
| parameters | JSON | Type-specific parameters (thresholds, windows, etc.) |
| source_page | int | Page number in tender document |
| source_quote | text | Exact quote from tender |

### Bidder
Entity representing a company that submitted a bid.
| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier |
| tender_id | UUID (FK → Tender) | Parent tender |
| name | str | Company name |
| submission_date | datetime | When documents were uploaded |

### Document
A single file (PDF, image, DOCX) from a tender or bidder submission.
| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier |
| bidder_id | UUID (FK, nullable) | If bidder document |
| tender_id | UUID (FK, nullable) | If tender document |
| filename | str | Original filename |
| content_hash | str | SHA-256 of file bytes (for audit replay) |
| routing_tag | RoutingTag (enum) | native_pdf / scanned_pdf / photo_certificate |
| created_at | datetime | Upload timestamp |

### Page
Individual page of a document with extracted text and bounding boxes.
| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier |
| document_id | UUID (FK → Document) | Parent document |
| page_number | int | Zero-indexed page number |
| text | text | Extracted text content |
| bboxes | JSON | List of word-level bounding boxes [{x0, y0, x1, y1}] |

### EvidenceClaim
A piece of evidence extracted from a bidder's document, linked to a specific criterion.
| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier |
| bidder_id | UUID (FK → Bidder) | Which bidder |
| criterion_id | str | Which criterion (e.g., "FIN-001") |
| extracted_value | JSON | Type-specific extracted data |
| source_doc_id | UUID (FK → Document) | Source document |
| source_page | int | Page where evidence was found |
| source_bbox | JSON (nullable) | Bounding box of cited region |
| confidence | float | 0.0–1.0 confidence score |
| verifier_passed | bool | Whether round-trip verification succeeded |
| created_at | datetime | Extraction timestamp |

### Verdict
Per-criterion evaluation result for a bidder.
| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier |
| bidder_id | UUID (FK → Bidder) | Which bidder |
| criterion_id | str | Which criterion |
| state | VerdictState (enum) | eligible / not_eligible / needs_review |
| evidence_ids | JSON | List of EvidenceClaim IDs used |
| rule_fired | str | Which rule produced this verdict |
| reason_template | text | Human-readable explanation |
| officer_action | JSON (nullable) | Gate 2 action or branch evaluations |
| created_at | datetime | Verdict timestamp |

### BidderVerdict
Aggregated verdict for a bidder across all criteria.
| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier |
| bidder_id | UUID (FK → Bidder) | Which bidder |
| tender_id | UUID (FK → Tender) | Which tender |
| aggregate_state | VerdictState (enum) | Overall eligibility |
| finalized_at | datetime (nullable) | When officer finalized |
| created_at | datetime | Aggregation timestamp |

### AuditLogEntry
Append-only, hash-chained audit trail entry.
| Field | Type | Description |
|-------|------|-------------|
| sequence | int (PK) | Monotonic sequence number |
| timestamp | datetime | UTC timestamp |
| actor | str | "system" or officer email |
| action_type | AuditActionType (enum) | One of 9 action types |
| payload | JSON | Action-specific data |
| payload_hash | str | SHA-256 of serialized payload |
| previous_hash | str | Hash of previous entry (or genesis hash) |
| entry_hash | str | SHA-256 of (sequence + timestamp + actor + action_type + payload_hash + previous_hash) |

**Audit protection:** PostgreSQL RULEs block UPDATE and DELETE on the auditlogentry table:
```sql
CREATE RULE audit_no_update AS ON UPDATE TO auditlogentry DO INSTEAD NOTHING;
CREATE RULE audit_no_delete AS ON DELETE TO auditlogentry DO INSTEAD NOTHING;
```

---

## 4. Criterion Types and Their Pipelines

### 4.1 Six Criterion Types

| Type | ID Prefix | Example | Extractor | Rule |
|------|-----------|---------|-----------|------|
| `financial_threshold` | FIN | "Annual turnover >= 5 crore" | Extracts amounts by fiscal year | Compares average against threshold |
| `experience_count` | EXP | "3 similar works in last 5 years" | Extracts work claims + similarity | Simple count or disjunctive branch evaluation |
| `statutory_registration` | REG | "Valid GST registration" | Extracts registration number, validity | Checks existence + type match + expiry |
| `quality_certification` | QUA | "ISO 9001 certificate" | Extracts cert name, version, expiry | Checks match (with equivalence table) + expiry |
| `document_checklist` | DOC | "EMD receipt submitted" | Checks presence, signature, date | Present + signed + dated as required |
| `policy_compliance` | POL | "Non-debarment declaration" | Extracts declaration + signed status | Declaration exists + signed |

### 4.2 Extraction Pipeline (per criterion)

```
Bidder Documents
  → Document Classifier (regex + LLM fallback)
    → Route to correct extractor based on document category
      → LLM extraction with Pydantic response model (via Instructor)
        → Verifier pass (check extracted values appear on cited page)
          → Confidence scorer (verifier + source quality + completeness)
            → EvidenceClaim stored in DB
```

### 4.3 Verdict Pipeline (per criterion)

```
Criterion + Evidence Claims
  → Rule Registry lookup (CriterionType → Rule class)
    → Rule.evaluate(criterion, evidence) — PURE PYTHON, NO LLM
      → Verdict (eligible / not_eligible / needs_review)
        → Audit log entry (rule_fired)
```

### 4.4 Aggregation

```
All per-criterion Verdicts
  → Separate mandatory vs optional criteria
    → Any mandatory not_eligible → bidder not_eligible
    → Any mandatory needs_review (no not_eligible) → bidder needs_review
    → All mandatory eligible → bidder eligible
    → Optional failures noted but don't block
```

---

## 5. Disjunctive Experience Rule (Centerpiece)

Handles criteria like: "3 similar works at >= 40% of estimated cost; OR 2 at >= 60%; OR 1 at >= 80%, in last 7 years."

**Algorithm:**
1. Parse branches from criterion parameters: `[{count: 3, percentage: 40}, {count: 2, percentage: 60}, {count: 1, percentage: 80}]`
2. Compute temporal window: end = last day of month before bid invitation, start = end - window_years
3. Filter claims to window (by completion_date)
4. Filter to "similar" claims (borderline → flag)
5. For each branch: threshold = percentage * estimated_cost / 100, count qualifying claims >= threshold
6. Branch passes if qualifying count >= required count
7. **Criterion passes if ANY branch passes** (disjunctive OR)
8. **ALL branch evaluations stored in audit** (not just the winner)

**Implementation:** `nirikshak/verdict/rules/experience_disjunctive.py`
**Tests:** `tests/unit/test_disjunctive.py` — 15 exhaustive test cases

---

## 6. Audit System

### 6.1 Hash Chain

Each entry's hash depends on the previous entry's hash, creating a tamper-evident chain:
```
entry_hash = SHA-256(sequence | timestamp | actor | action_type | payload_hash | previous_hash)
```

Genesis entry uses `previous_hash = "0" * 64`.

### 6.2 Nine Action Types

| Action Type | When | Key Payload Fields |
|-------------|------|-------------------|
| `tender_ingested` | Tender PDF uploaded | tender_id, document content hash |
| `criteria_extracted` | After criterion mining | criteria_spec_id, content_hash, criteria_count |
| `criteria_locked` | Officer commits Gate 1 | locked criteria_spec hash, officer email |
| `bidder_ingested` | Bidder packet uploaded | bidder_id, document content hashes |
| `evidence_extracted` | Per criterion per bidder | criterion_id, claims_count, verified_count |
| `rule_fired` | Verdict engine | criterion_id, rule name, verdict state |
| `bidder_verdict` | Aggregator | bidder_id, aggregate state |
| `officer_review` | Gate 2 action | bidder_id, action, reason |
| `report_finalized` | Report generated | report content hash |

### 6.3 Replay (Audit Drill)

Given an audit entry hash:
1. Fetch the entry, extract bidder_id and criterion_id
2. Trace the chain backward to find all related entries
3. Re-load the locked CriteriaSpec and bidder evidence from DB
4. Re-run the verdict rule
5. Compare recomputed verdict vs historical → match or divergence

**Implementation:** `nirikshak/audit/replay.py`

---

## 7. LLM Integration

### 7.1 Client Architecture

All LLM calls go through `nirikshak/llm/client.py`:
- Uses OpenAI Python SDK with configurable base URL
- Supports text (`call_llm`) and vision (`call_llm_vision`) calls
- **Response caching**: SHA-256(system + prompt + model + temperature) → file cache in `storage/llm_cache/`
- **Retry with backoff**: 3 attempts with exponential wait on rate limits
- **Temperature 0.0** for reproducibility

### 7.2 Structured Output

Uses Instructor library in **JSON mode** (`instructor.Mode.JSON`):
- Defines Pydantic response models for each extraction task
- LLM returns JSON matching the schema
- Instructor validates and retries on parse failure (max 2 retries)

Note: JSON mode is used instead of tool_choice because the OpenCode Go provider's thinking-mode models don't support `tool_choice=required`.

### 7.3 Ten Prompt Files

| Prompt | Purpose | Location |
|--------|---------|----------|
| `section_classifier.md` | Classify tender sections (nit/eligibility/specs/boq/annexures) | Regex-first, LLM fallback |
| `criterion_miner.md` | Extract eligibility criteria with typed parameters | Returns MinedCriteriaList |
| `doc_classifier.md` | Classify bidder documents by category | Regex-first, LLM fallback |
| `financial_extractor.md` | Extract turnover/net worth amounts by fiscal year | Returns FinancialExtraction |
| `statutory_extractor.md` | Extract registration numbers, validity dates | Returns RegistrationExtractionList |
| `quality_extractor.md` | Extract certificate name, version, expiry | Returns CertificationExtractionList |
| `checklist_extractor.md` | Check document presence, signature, date | Returns ChecklistExtraction |
| `compliance_extractor.md` | Extract policy declarations | Returns ComplianceExtraction |
| `experience_extractor.md` | Extract completed work claims | Returns ExperienceExtraction |
| `similarity_classifier.md` | Compare work description to tender scope | Returns similar/not_similar/borderline |

---

## 8. Verifier and Confidence Scoring

### 8.1 Verifier (`bidder/verifier.py`)

Cross-checks extracted values against the cited source page:
- For numeric values: checks if the amount appears on the page (tolerant of Indian formatting: "7,50,00,000" vs "75000000")
- For text values: case-insensitive substring match on the cited page
- For amounts: also checks crore/lakh text representations
- **Fails if**: key extracted values don't appear on the cited page → claim flagged, criterion routes to Needs Review

### 8.2 Confidence Scorer (`bidder/confidence.py`)

Score = weighted sum (0.0–1.0):
- **Verifier pass** (0.5 weight): binary — did values round-trip?
- **Source quality** (0.3 weight): native_pdf = 0.3, scanned_pdf = 0.15–0.3 (scaled by OCR confidence), photo = 0.1
- **Extraction completeness** (0.2 weight): fraction of non-null fields in extracted_value

Claims with confidence < 0.85 (configurable) on mandatory criteria → Needs Review.

---

## 9. API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/health` | Health check | None |
| POST | `/api/tenders/upload` | Upload tender PDF, extract criteria | Multipart form |
| GET | `/api/tenders` | List all tenders | None |
| GET | `/api/tenders/{id}/criteria` | Get criteria spec for a tender | None |
| POST | `/api/criteria-specs/{id}/lock` | Lock criteria spec (Gate 1) | Form: officer_email |
| POST | `/api/tenders/{id}/bidders/upload` | Upload bidder docs, evaluate | Multipart form |
| GET | `/api/tenders/{id}/bidders` | List bidders with aggregate verdicts | None |
| GET | `/api/bidders/{id}/verdicts` | Per-criterion verdicts with evidence | None |
| GET | `/api/audit` | Full audit log | None |
| GET | `/api/audit/verify` | Verify hash chain integrity | None |
| POST | `/api/audit/replay` | Replay a verdict from frozen inputs | Form: entry_hash |
| GET | `/api/tenders/{id}/report` | Download signed PDF report | None |
| GET | `/api/eval/metrics` | Evaluation metrics vs golden set | None |

---

## 10. Streamlit Console Pages

| Page | File | Demo Segment | Purpose |
|------|------|-------------|---------|
| Home | `streamlit_app.py` | — | Dashboard metrics, tender selector, officer identity |
| 1 | `1_Tender_Library.py` | Opens here | Upload tender, list tenders, navigate |
| 2 | `2_Criteria_Review.py` | Segment 1 | Gate 1: review criteria, edit, lock |
| 3 | `3_Bidder_Queue.py` | Segment 2 | Upload bidders, verdict badges, stats |
| 4 | `4_Verdict_Review.py` | Segments 3+4 | Gate 2: two-pane verdict review, evidence, actions |
| 5 | `5_Report_Export.py` | Segment 5 | Download signed PDF report |
| 6 | `6_Audit_Log.py` | Segment 5 | Audit trail viewer, chain verification, replay |
| 7 | `7_Eval_Dashboard.py` | Segment 6 | Three-layer accuracy, needs-review fraction |

---

## 11. Signed PDF Report

Generated by `nirikshak/audit/signer.py` using ReportLab:

**Contents:**
1. Cover page: tender title, authority, evaluation date
2. Criteria summary table: all criteria with type, description, mandatory flag
3. Per-bidder verdict sections: name, aggregate verdict, per-criterion table with rule + reason
4. Digital signature block: HMAC-SHA256 of report content hash

**Signature:** Self-signed using HMAC with a prototype key. Production would use a CCA-licensed Digital Signature Certificate per the IT Act, 2000.

---

## 12. Evaluation Framework

### 12.1 Golden Set

Hand-curated ground truth in `golden_set/ground_truth.yaml`:
- 1 tender, 5 bidders, 25 bidder-criterion pairs
- Expected verdicts labeled per criterion and per bidder

### 12.2 Three-Layer Metrics

| Layer | What | Status |
|-------|------|--------|
| OCR character-level | CER on extracted text | Not measured (prototype uses native PDFs) |
| Field-level extraction | Verifier pass rate as proxy | Measured |
| Verdict-level agreement | Accuracy vs ground truth | Measured |
| Needs-Review fraction | Calibration metric | Measured |

### 12.3 Honest Caveats

- Prototype test set: 1 tender, 5 bidders — too small for statistical significance
- OCR accuracy not measured (no scanned documents in test set)
- Production calibration requires ~200 real evaluations

---

## 13. Configuration

All configuration via environment variables (loaded from `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://nirikshak:nirikshak@localhost:5432/nirikshak` | Async DB connection |
| `DATABASE_URL_SYNC` | `postgresql://nirikshak:nirikshak@localhost:5432/nirikshak` | Sync DB (Streamlit) |
| `OPENAI_API_KEY` | — | LLM API key |
| `OPENAI_BASE_URL` | `https://opencode.ai/zen/go/v1` | LLM API base URL |
| `LLM_MODEL` | `qwen3.6-plus` | Model for extraction |
| `STORAGE_DIR` | `./storage` | File storage path |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## 14. Project Structure

```
nirikshak/
  core/           schemas.py, hashing.py, config.py, db.py
  ingestion/      pdf_text.py, ocr.py, vision.py, classify.py, page_render.py
  tender/         section_classifier.py, criterion_miner.py, criteria_spec.py
  bidder/         doc_classifier.py, verifier.py, confidence.py
    extractors/   base.py + 6 typed extractors
  verdict/        engine.py, aggregator.py
    rules/        6 rule files incl. experience_disjunctive.py
  audit/          chain.py, replay.py, signer.py
  llm/            client.py, instructor_helpers.py, prompts/ (10 files)
  eval/           golden_set.py, metrics.py
  api/            main.py (FastAPI, 13 endpoints)
  console/        streamlit_app.py, helpers.py, pages/ (7 pages)
tests/unit/       test_schemas.py, test_hashing.py, test_audit_chain.py,
                  test_disjunctive.py, test_verdict_engine.py
seed/             generate_demo_data.py, run_demo.py
golden_set/       ground_truth.yaml
docs/             ARCHITECTURE.md, HONEST_SCOPE.md
```

**Total:** ~50 Python source files, 10 prompt files, 71 unit tests.
