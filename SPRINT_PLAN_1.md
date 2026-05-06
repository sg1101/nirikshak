# Sprint 1 — Foundation + Core Infrastructure

**Days:** 1–3 (May 6–8)
**Goal:** From empty repo to a working foundation where a tender PDF goes in and structured criteria come out, with every action audit-logged and the whole thing running in Docker.

---

## Why this sprint matters

Everything in Sprints 2–4 depends on what we build here. The verdict engine needs schemas. The extractors need the Claude client and ingestion pipeline. The console needs the DB. The audit drill needs the hash chain. If Sprint 1 is solid, the rest is assembly. If it's shaky, we fight the foundation for 7 more days.

---

## Task Breakdown

### Phase 1: Project Scaffold (Day 1, first half)

**T1.1 — Repository + dependency setup**
- Initialize git repo
- `pyproject.toml` with all dependencies:
  - Core: `pydantic>=2.0`, `sqlmodel`, `asyncpg`, `alembic`
  - LLM: `anthropic`, `instructor`
  - PDF: `PyMuPDF` (fitz), `Pillow`
  - OCR: `paddleocr`, `paddlepaddle`
  - Web: `fastapi`, `uvicorn`, `streamlit`
  - Infra: `python-dotenv`, `tenacity` (retries)
  - Test: `pytest`, `pytest-asyncio`
- `.env.example`:
  ```
  ANTHROPIC_API_KEY=
  DATABASE_URL=postgresql+asyncpg://nirikshak:nirikshak@localhost:5432/nirikshak
  STORAGE_DIR=./storage
  LOG_LEVEL=INFO
  ```
- `.gitignore` (Python, .env, storage/, __pycache__, .mypy_cache)
- `Dockerfile` (Python 3.11-slim, install deps, copy source)
- `docker-compose.yml`:
  - `db`: Postgres 16 with pgvector extension, health check
  - `app`: our Python service (FastAPI), depends_on db
  - `console`: Streamlit, depends_on app
  - Shared volume for `./storage` (PDFs, rendered pages)
  - Network linking all services

**Acceptance:** `docker compose up --build` starts all 3 services without errors.

---

**T1.2 — Directory structure**

Create the full module tree per PRD section 11:

```
nirikshak/
  __init__.py
  core/
    __init__.py
    schemas.py          # All Pydantic/SQLModel models
    hashing.py          # SHA-256 content hashing
    config.py           # Settings from env
    db.py               # SQLModel engine + session factory
  ingestion/
    __init__.py
    pdf_text.py         # PyMuPDF text + bbox extraction
    ocr.py              # PaddleOCR wrapper
    vision.py           # Claude vision for photos
    classify.py         # Routing tag detection
    page_render.py      # Render page with bbox highlights
  tender/
    __init__.py
    section_classifier.py
    criterion_miner.py
    criteria_spec.py
  bidder/
    __init__.py
    doc_classifier.py
    extractors/
      __init__.py
      base.py
      financial_threshold.py
      experience_count.py
      statutory_registration.py
      quality_certification.py
      document_checklist.py
      policy_compliance.py
    verifier.py
    confidence.py
  verdict/
    __init__.py
    engine.py
    rules/
      __init__.py
      financial_threshold.py
      experience_disjunctive.py
      statutory_registration.py
      quality_certification.py
      document_checklist.py
      policy_compliance.py
    aggregator.py
  audit/
    __init__.py
    chain.py
    signer.py
    replay.py
  llm/
    __init__.py
    client.py
    instructor_helpers.py
    prompts/
      section_classifier.md
      criterion_miner.md
      financial_extractor.md
      experience_extractor.md
      similarity_classifier.md
      statutory_extractor.md
      quality_extractor.md
      checklist_extractor.md
      compliance_extractor.md
      vision_certificate.md
  eval/
    __init__.py
    golden_set.py
    runner.py
    metrics.py
  api/
    __init__.py
    main.py             # FastAPI app
  console/
    streamlit_app.py
    pages/
      1_Tender_Library.py
      2_Criteria_Review.py
      3_Bidder_Queue.py
      4_Verdict_Review.py
      5_Report_Export.py
      6_Audit_Log.py
      7_Eval_Dashboard.py
tests/
  __init__.py
  unit/
    __init__.py
    test_schemas.py
    test_hashing.py
    test_audit_chain.py
    test_disjunctive.py
  integration/
    __init__.py
    test_e2e_construction.py
seed/
  construction_tender.pdf
  10_bidders/
  bidder_K/
golden_set/
  ground_truth.yaml
docs/
  ARCHITECTURE.md
  DEMO_SCRIPT.md
  HONEST_SCOPE.md
storage/              # .gitkeep only, actual files gitignored
```

Each `__init__.py` is empty for now. Module files start as stubs with a docstring only — no placeholder code that will confuse later implementation.

**Acceptance:** `tree nirikshak/` matches the structure above. All imports resolve (no circular deps).

---

### Phase 2: Core Data Layer (Day 1, second half)

**T1.3 — Pydantic/SQLModel schemas (`core/schemas.py`)**

Implement every model from PRD section 6. These are the contracts the entire system uses.

```
Enums:
  CriterionType      — financial_threshold | experience_count | statutory_registration |
                       quality_certification | document_checklist | policy_compliance
  VerdictState        — eligible | not_eligible | needs_review
  RoutingTag          — native_pdf | scanned_pdf | photo_certificate
  OfficerActionType   — accept | override | re_extract | escalate
  AuditActionType     — tender_ingested | criteria_extracted | criteria_locked |
                       bidder_ingested | evidence_extracted | rule_fired |
                       bidder_verdict | officer_review | report_finalized

DB-backed models (SQLModel with table=True):
  Tender              — id (UUID PK), title, procuring_authority, bid_submission_date,
                       estimated_value (Decimal), source_pdf_id (UUID FK)
  CriteriaSpec        — id, tender_id (FK), version (int), content_hash, locked_at, locked_by
  Criterion           — id (str, e.g. "FIN-001"), criteria_spec_id (FK), type (enum),
                       description, mandatory (bool), parameters (JSON),
                       source_page (int), source_quote (str)
  Bidder              — id, tender_id (FK), name, submission_date
  Document            — id, bidder_id (nullable FK), tender_id (nullable FK), filename,
                       content_hash, routing_tag (enum)
  Page                — id, document_id (FK), page_number, text, bboxes (JSON)
  EvidenceClaim       — id, bidder_id (FK), criterion_id (str), extracted_value (JSON),
                       source_doc_id (FK), source_page (int), source_bbox (JSON),
                       confidence (float), verifier_passed (bool)
  Verdict             — id, bidder_id (FK), criterion_id (str), state (enum),
                       evidence_ids (JSON list), rule_fired (str),
                       reason_template (str), officer_action (JSON nullable)
  BidderVerdict       — id, bidder_id (FK), aggregate_state (enum), finalized_at (nullable)
  AuditLogEntry       — sequence (int PK), timestamp, actor, action_type (enum),
                       payload_hash, previous_hash, entry_hash

Pure Pydantic (not in DB, used for passing data):
  BBox                — x0, y0, x1, y1 (all float)
  CompletedWorkClaim  — value (Decimal), completion_date (date), description (str),
                       similarity_status (similar|not_similar|borderline),
                       source_doc_id, source_page, source_bbox
  OfficerAction       — type (enum), reason (str optional), performed_at, performed_by
  DateRange           — start (date), end (date)
```

Implementation notes:
- Use `uuid4` default factories for all UUID PKs
- All `Decimal` fields use `max_digits=15, decimal_places=2`
- JSON fields use `sa_column(Column(JSON))` for SQLModel compatibility
- `AuditLogEntry` has a unique constraint on `sequence` and the table must have Postgres RULEs blocking UPDATE/DELETE (applied in migration)

**Acceptance:** `from nirikshak.core.schemas import *` works. Unit test creates each model, serializes to JSON, deserializes back. No validation errors on valid data. Validation errors on invalid data (e.g., negative confidence, invalid enum).

---

**T1.4 — Hashing utilities (`core/hashing.py`)**

Three functions:
- `content_hash(data: bytes) -> str` — SHA-256 hex digest of raw bytes
- `content_hash_json(obj: BaseModel) -> str` — deterministic JSON serialization (sorted keys, no whitespace) then SHA-256
- `chain_hash(sequence: int, timestamp: str, actor: str, action_type: str, payload_hash: str, previous_hash: str) -> str` — SHA-256 of concatenated fields (the audit chain hash)

Implementation notes:
- JSON serialization must be deterministic: `json.dumps(obj.model_dump(), sort_keys=True, separators=(',', ':'))`
- The genesis entry (sequence=0) uses `previous_hash = "0" * 64`

**Acceptance:** Unit test: hash same content twice → same hash. Different content → different hash. Chain hash with known inputs produces expected output (pin one test vector).

---

**T1.5 — Config (`core/config.py`)**

Pydantic `BaseSettings` class loading from `.env`:
- `database_url: str`
- `anthropic_api_key: str`
- `storage_dir: Path = Path("./storage")`
- `log_level: str = "INFO"`
- `claude_model: str = "claude-sonnet-4-20250514"` (pinned for reproducibility)
- `ocr_languages: list[str] = ["en", "hi"]`
- `confidence_threshold: float = 0.85`

Singleton pattern: `get_settings()` returns cached instance.

**Acceptance:** Loading with valid `.env` works. Missing required fields raise clear errors.

---

**T1.6 — Database setup (`core/db.py`)**

- SQLModel `create_engine` with the configured `database_url`
- Async session factory using `async_sessionmaker`
- `init_db()` function: creates all tables, applies the audit log protection RULE
- The audit RULE:
  ```sql
  CREATE RULE audit_no_update AS ON UPDATE TO auditlogentry DO INSTEAD NOTHING;
  CREATE RULE audit_no_delete AS ON DELETE TO auditlogentry DO INSTEAD NOTHING;
  ```

**Acceptance:** `init_db()` creates all tables in Postgres. Attempting `UPDATE auditlogentry SET ...` silently does nothing (row unchanged). Attempting `DELETE FROM auditlogentry` silently does nothing.

---

### Phase 3: Audit Log (Day 2, first half)

**T1.7 — Hash-chained audit log (`audit/chain.py`)**

Core functions:
- `append_entry(session, actor: str, action_type: AuditActionType, payload: BaseModel) -> AuditLogEntry`
  - Computes `payload_hash` from payload
  - Fetches the last entry's `entry_hash` as `previous_hash` (or genesis hash if first)
  - Computes `entry_hash` via `chain_hash()`
  - Inserts and returns the entry
- `verify_chain(session) -> tuple[bool, int | None]`
  - Reads all entries in sequence order
  - Recomputes each `entry_hash` and checks it matches stored value
  - Returns (True, None) if valid, or (False, first_broken_sequence) if tampered
- `get_entries_for_bidder(session, bidder_id: UUID) -> list[AuditLogEntry]`
  - Filters by payload content (bidder_id in payload)
- `get_entries_for_criterion(session, bidder_id: UUID, criterion_id: str) -> list[AuditLogEntry]`

Implementation notes:
- The `append_entry` function must be serialized (no concurrent appends) — use a Postgres advisory lock or SELECT FOR UPDATE on the last entry
- Payload is serialized to JSON before hashing, stored in a separate `payload` JSON column for queryability

**Acceptance:**
- Append 10 entries → `verify_chain()` returns True
- Manually tamper with one entry's `payload_hash` in the DB (bypass RULE via direct SQL in test) → `verify_chain()` returns (False, tampered_sequence)
- `get_entries_for_bidder` returns only entries for that bidder

---

### Phase 4: Claude API Client (Day 2, second half)

**T1.8 — Claude client wrapper (`llm/client.py`)**

A thin wrapper around the `anthropic` SDK:
- `call_claude(prompt: str, system: str | None, model: str | None, max_tokens: int = 4096, temperature: float = 0.0) -> str`
- `call_claude_vision(images: list[bytes], prompt: str, system: str | None) -> str` — for photo certificates
- Built-in retry with exponential backoff using `tenacity` (retry on rate limit, 3 attempts)
- Response caching: hash(prompt + model + temperature) → check DB/filesystem cache before calling API
  - Cache key: SHA-256 of (system + prompt + model + str(temperature))
  - Cache store: `storage/llm_cache/` as JSON files
  - Cache hit → return cached response, no API call
  - This is critical for demo reliability and cost control

**Acceptance:** Call Claude with a simple prompt → get response. Call again with same prompt → response served from cache (no API call, verify via mock).

---

**T1.9 — Structured output helpers (`llm/instructor_helpers.py`)**

Using the `instructor` library for Pydantic-validated LLM responses:
- `extract_structured(prompt: str, response_model: type[T], system: str | None) -> T`
  - Wraps the Anthropic client with instructor
  - Returns a validated Pydantic model instance
  - On validation failure, retries with the validation error in the prompt (instructor handles this)
- `extract_structured_vision(images: list[bytes], prompt: str, response_model: type[T]) -> T`

Implementation notes:
- Use `instructor.from_anthropic()` to patch the client
- Pin `max_retries=2` for validation retries
- Temperature always 0.0 for reproducibility
- Caching still applies (cache the raw response, validate on retrieval)

**Acceptance:** Call with a prompt asking for a Criterion-shaped output → get back a valid Criterion Pydantic model. Call with deliberately invalid instructions → instructor retries and either succeeds or raises a clear error.

---

### Phase 5: PDF Ingestion Pipeline (Day 2, second half → Day 3, first half)

**T1.10 — PDF text extraction (`ingestion/pdf_text.py`)**

Function: `extract_pdf(file_path: Path) -> Document`
- Open PDF with PyMuPDF
- Per page:
  - Extract text blocks with bounding boxes (fitz `get_text("dict")`)
  - Build `Page` objects with `page_number`, `text` (concatenated blocks), `bboxes` (list of BBox from word-level spans)
- Compute `content_hash` of the entire PDF bytes
- Set `routing_tag`:
  - If average chars-per-page >= 100 → `native_pdf`
  - Else → `scanned_pdf`
- Return a `Document` with all pages populated

**Acceptance:** Feed a typed PDF → get Document with text on every page, bboxes populated, tag = native_pdf. Feed a scanned PDF → tag = scanned_pdf, text is sparse/empty.

---

**T1.11 — OCR wrapper (`ingestion/ocr.py`)**

Function: `ocr_page(page_image: bytes) -> tuple[str, list[BBox], float]`
- Initialize PaddleOCR with `lang="en"` (add Hindi if available)
- Run OCR on the page image
- Return: extracted text, word-level bounding boxes, average confidence score
- Also: `ocr_document(doc: Document) -> Document` — for each page tagged as needing OCR, run `ocr_page` and update the page's text + bboxes

Implementation notes:
- PaddleOCR returns `[[[bbox], (text, confidence)], ...]` per line
- Convert PaddleOCR bbox format (4 corner points) to our BBox (x0, y0, x1, y1) by taking min/max
- Store per-word confidence for downstream use in the confidence scorer

**Acceptance:** Feed a scanned page image → get text back with bboxes. Confidence score is between 0 and 1.

---

**T1.12 — Photo/certificate vision extraction (`ingestion/vision.py`)**

Function: `extract_certificate(image_bytes: bytes) -> dict`
- Send image to Claude vision API with prompt from `llm/prompts/vision_certificate.md`
- Prompt asks: "Read this certificate/document. Return: issuer, issue_date, recipient_name, validity, full_text"
- Return structured dict with extracted fields
- Also: `vision_page(image_bytes: bytes) -> tuple[str, float]` — simpler version that just returns text + confidence for general photo pages

The prompt (`llm/prompts/vision_certificate.md`):
```
You are reading a photograph of a physical certificate or document.
Extract the following fields as accurately as possible:
- issuer: the organization that issued this certificate
- issue_date: the date of issue (YYYY-MM-DD format)
- recipient_name: the person or company the certificate is issued to
- validity: expiry date or "no expiry" or "unclear"
- full_text: complete text content as you can read it

If any field is unclear or partially illegible, set it to null and explain in a "notes" field.
Return JSON only.
```

**Acceptance:** Feed a photo of a certificate → get structured dict with fields populated. Illegible fields return null with notes.

---

**T1.13 — Document routing + orchestrator (`ingestion/classify.py`)**

Function: `ingest_document(file_path: Path) -> Document`

The main entry point for ingestion. Routes based on file type and content:

1. If file is `.pdf`:
   - Run `extract_pdf()` to get the Document
   - If `routing_tag == scanned_pdf` → run `ocr_document()` to fill in text
2. If file is `.jpg`, `.jpeg`, `.png`:
   - Create a Document with `routing_tag = photo_certificate`
   - Create one Page per image
   - Run `vision_page()` for text extraction
3. If file is `.docx`:
   - Use `python-docx` to extract text (simple paragraph concatenation)
   - Create Document with `routing_tag = native_pdf` (misnomer but functionally same)
4. Compute `content_hash` of the source file
5. Save document to DB via session
6. Emit `tender_ingested` or `bidder_ingested` audit log entry

Also: `ingest_bidder_packet(bidder_id: UUID, folder: Path) -> list[Document]` — ingest all files in a bidder's folder.

**Acceptance:** Ingest a typed PDF → Document in DB with text. Ingest a scanned PDF → OCR'd text in DB. Ingest a JPEG → vision-extracted text. Audit log entry written for each.

---

**T1.14 — Page renderer (`ingestion/page_render.py`)**

Function: `render_page_with_highlight(document_id: UUID, page_number: int, highlight_bbox: BBox | None) -> bytes`
- Load the source PDF from storage
- Render the page as a PNG image using PyMuPDF (`page.get_pixmap()`)
- If `highlight_bbox` provided, draw a semi-transparent yellow rectangle over that region
- Return PNG bytes
- Cache rendered images in `storage/renders/`

This is used later by the Streamlit console for PDF preview with citation highlighting.

**Acceptance:** Render a page → get a valid PNG. Render with a bbox → visible yellow highlight in the right region.

---

### Phase 6: Tender Understanding (Day 3)

**T1.15 — Section classifier (`tender/section_classifier.py`)**

Function: `classify_sections(document: Document) -> list[LabeledSection]`

Where `LabeledSection` is:
```python
class LabeledSection(BaseModel):
    label: str  # "nit" | "eligibility" | "technical_specs" | "boq" | "annexures" | "other"
    pages: list[int]
    text: str
    confidence: float
```

Two-pass approach:
1. **Regex pass:** Scan page texts for heading patterns:
   - "Notice Inviting Tender" / "NIT" → nit
   - "Eligibility" / "Eligible" / "Qualification" / "Pre-Qualification" → eligibility
   - "Technical Specification" / "Schedule of Requirements" → technical_specs
   - "Bill of Quantities" / "BOQ" / "Price Schedule" → boq
   - "Annexure" / "Appendix" / "Format" → annexures
   - Group consecutive pages under the same heading
2. **LLM pass** (for chunks not matched by regex):
   - Send unclassified chunks to Claude with structured output
   - Prompt: `llm/prompts/section_classifier.md`
   - Ask Claude to classify each chunk into one of the label categories

The prompt (`llm/prompts/section_classifier.md`):
```
You are analyzing a section of a government tender document. Classify this section into exactly one category:

- "nit": Notice Inviting Tender — the advertisement/invitation section
- "eligibility": Eligibility criteria, qualification requirements, conditions for bidders
- "technical_specs": Technical specifications, scope of work, schedule of requirements
- "boq": Bill of Quantities, price schedule, financial bid format
- "annexures": Annexures, appendices, formats, proformas
- "other": Anything that doesn't fit the above categories

Respond with JSON: {"label": "...", "confidence": 0.0-1.0, "reasoning": "..."}
```

**Acceptance:** Feed the demo construction tender → sections labeled correctly. Eligibility section identified with the 4 criteria inside it.

---

**T1.16 — Criterion miner (`tender/criterion_miner.py`)**

Function: `mine_criteria(sections: list[LabeledSection], tender: Tender) -> list[Criterion]`

Takes the sections labeled "eligibility" and extracts structured criteria:

1. Concatenate all eligibility section text
2. Send to Claude with Pydantic structured output (via instructor)
3. The response model:
   ```python
   class MinedCriterion(BaseModel):
       suggested_id: str  # e.g., "FIN-001"
       type: CriterionType
       description: str  # human-readable
       mandatory: bool
       parameters: dict  # type-specific, e.g., {"threshold": 50000000, "window_years": 3}
       source_page: int
       source_quote: str  # exact quote from tender
   ```
4. Auto-assign IDs by type prefix: FIN-001, EXP-001, REG-001, QUA-001, DOC-001, POL-001
5. Return list of Criterion objects

The prompt (`llm/prompts/criterion_miner.md`):
```
You are analyzing the eligibility section of a government tender document.

Extract every eligibility criterion as a structured object. For each criterion:
1. Classify its type:
   - financial_threshold: turnover, net worth, credit limits
   - experience_count: completed works, similar projects, years of experience
   - statutory_registration: GST, PAN, EPF, ESI, contractor class/category
   - quality_certification: ISO, AERB, OEM certificates
   - document_checklist: EMD, bid security, acceptance letters, integrity pacts
   - policy_compliance: Make-in-India, MSME, debarment declarations

2. Determine if it is mandatory or optional. Assume mandatory unless explicitly stated as optional/desirable/preferred.

3. Extract type-specific parameters:
   - financial_threshold: {threshold_amount, currency, period_years, metric (turnover/net_worth)}
   - experience_count: {min_count, min_value, similarity_required, window_years} OR for disjunctive: {branches: [{count, percentage}...], window_years, window_anchor}
   - statutory_registration: {registration_type, required_class, valid_at_date}
   - quality_certification: {cert_name, accepted_versions, scope}
   - document_checklist: {document_name, must_be_signed, must_be_dated}
   - policy_compliance: {policy_name, declaration_type}

4. Include the exact quote from the source and the page number where it appears.

IMPORTANT: Do NOT invent criteria. Only extract what is explicitly stated in the text. If a criterion is ambiguous, still extract it but note the ambiguity in the description.

Return a JSON array of criteria.
```

**Acceptance:** Feed the construction tender eligibility section → get 4 criteria (FIN-001, EXP-001, REG-001, QUA-001) with correct types, mandatory=True, correct parameters, source quotes.

---

**T1.17 — Criteria spec builder (`tender/criteria_spec.py`)**

Functions:
- `build_spec(tender_id: UUID, criteria: list[Criterion]) -> CriteriaSpec`
  - Create CriteriaSpec v1 with all mined criteria
  - Compute content_hash of the criteria list
  - Save to DB
  - Emit `criteria_extracted` audit entry
- `lock_spec(spec_id: UUID, officer_email: str) -> CriteriaSpec`
  - Set `locked_at` and `locked_by`
  - Recompute and freeze content_hash
  - Emit `criteria_locked` audit entry
  - After lock, spec is immutable for downstream processing
- `get_locked_spec(tender_id: UUID) -> CriteriaSpec | None`
  - Return the latest locked spec for a tender, or None

**Acceptance:** Build spec → get CriteriaSpec in DB with correct hash. Lock it → locked_at set, audit entry written. Attempt to modify after lock → error raised.

---

**T1.18 — End-to-end tender pipeline (`tender/__init__.py` or `api/main.py`)**

Wire the full flow:
```
upload_tender(file: UploadFile)
  → ingest_document(file)
  → classify_sections(document)
  → mine_criteria(eligibility_sections, tender)
  → build_spec(tender_id, criteria)
  → return CriteriaSpec
```

FastAPI endpoint: `POST /api/tenders/upload`
- Accepts multipart file upload
- Returns: `{ tender_id, criteria_spec: { criteria: [...], content_hash } }`

**Acceptance:** Upload the demo construction tender PDF via API → get back 4 correctly typed criteria with source quotes. Audit log shows `tender_ingested` → `criteria_extracted` chain. Entire flow completes in < 60 seconds.

---

### Phase 7: Tests (throughout, but finalized Day 3)

**T1.19 — Unit tests**

`tests/unit/test_schemas.py`:
- Create each model with valid data → no error
- Create with invalid data (bad enum, negative confidence, missing required) → ValidationError
- Serialize to JSON and back → round-trip equality

`tests/unit/test_hashing.py`:
- Same input → same hash (deterministic)
- Different input → different hash
- Chain hash with pinned test vector

`tests/unit/test_audit_chain.py`:
- Append entries → verify_chain passes
- Tamper → verify_chain catches it
- Query by bidder/criterion returns correct subset

`tests/unit/test_ingestion.py` (requires test fixtures):
- Native PDF → correct routing tag + text extraction
- Page render → valid PNG output

`tests/unit/test_tender_understanding.py` (requires Claude API or mocked):
- Section classifier on known tender → correct labels
- Criterion miner on known eligibility text → correct criteria count and types

**Acceptance:** `pytest tests/unit/ -v` — all green.

---

## Dependency Order (critical path)

```
T1.1 Scaffold
  └─► T1.2 Directory structure
       └─► T1.3 Schemas ─────────────────────────────┐
            └─► T1.4 Hashing                          │
                 └─► T1.5 Config                       │
                      └─► T1.6 DB setup                │
                           └─► T1.7 Audit log          │
                                │                      │
                                │   T1.8 Claude client ◄┘
                                │     └─► T1.9 Instructor helpers
                                │          │
                                ▼          ▼
                           T1.10 PDF extraction
                             └─► T1.11 OCR
                             └─► T1.12 Vision
                             └─► T1.13 Routing + orchestrator
                             └─► T1.14 Page renderer
                                   │
                                   ▼
                           T1.15 Section classifier
                             └─► T1.16 Criterion miner
                                  └─► T1.17 Criteria spec builder
                                       └─► T1.18 E2E pipeline
                                            └─► T1.19 Tests
```

---

## Sprint 1 Definition of Done

All of these must be true before moving to Sprint 2:

- [ ] `docker compose up` starts Postgres + FastAPI + Streamlit without errors
- [ ] All Pydantic schemas validate correctly (unit tests pass)
- [ ] Audit log hash chain is append-only and tamper-evident (unit tests pass)
- [ ] Claude API client works with caching (manual test + unit test with mock)
- [ ] PDF ingestion handles native PDFs with text + bbox extraction
- [ ] OCR pipeline works on scanned PDF pages
- [ ] Vision extraction works on photograph certificates
- [ ] Section classifier correctly identifies eligibility section in demo tender
- [ ] Criterion miner extracts 4 criteria from demo tender with correct types
- [ ] CriteriaSpec can be built, hashed, and locked with audit trail
- [ ] `POST /api/tenders/upload` returns criteria from a tender PDF end-to-end
- [ ] `pytest tests/unit/ -v` passes all tests
- [ ] Demo construction tender goes from upload → 4 extracted criteria in < 60 seconds

---

## What We Are NOT Doing in Sprint 1

- No Streamlit UI beyond the skeleton (that's Sprint 3)
- No bidder evidence extraction (Sprint 2)
- No verdict engine or rules (Sprint 2)
- No report export or audit replay (Sprint 4)
- No seed data curation beyond one test tender (Sprint 3)
- No Golden Set or evaluation metrics (Sprint 4)
