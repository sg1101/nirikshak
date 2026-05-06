# Sprint 2 — Evidence Extraction + Verdict Engine

**Days:** 4–6 (May 9–11)
**Goal:** Given a locked CriteriaSpec and a set of bidder documents, extract evidence for every criterion type, verify it, then run deterministic rules to produce per-criterion and per-bidder verdicts — including the disjunctive experience rule (the demo centerpiece).

---

## Why this sprint matters

Sprint 1 proved: "we can understand a tender." Sprint 2 proves: "we can evaluate a bidder." This is the core thesis — LLM extracts evidence, deterministic Python decides verdicts. The verdict engine has zero LLM calls by design. If this sprint is solid, Sprint 3 is just UI and Sprint 4 is polish.

---

## What we are building on

From Sprint 1, we already have:
- All Pydantic/SQLModel schemas (EvidenceClaim, Verdict, BidderVerdict, CompletedWorkClaim)
- Audit log (append_entry, verify_chain)
- LLM client with caching (OpenCode Go / qwen3.6-plus via OpenAI-compatible API)
- Instructor structured output (JSON mode)
- Document ingestion pipeline (PDF text + bboxes, OCR, vision, routing)
- FastAPI app with tender upload endpoint

---

## Task Breakdown

### Phase 1: Bidder Document Classification (Day 4, first half)

**T2.1 — Bidder document classifier (`bidder/doc_classifier.py`)**

Given a bidder's set of documents, classify each into categories so the right extractor runs on the right document.

Function: `classify_bidder_documents(documents: list[Document], pages_by_doc: dict[UUID, list[Page]]) -> dict[UUID, str]`

Classification categories:
- `financial_statement` — balance sheet, P&L, turnover certificate, CA certificate
- `experience_certificate` — completion certificate, work order, performance certificate
- `registration_certificate` — GST, PAN, EPF, ESI, contractor registration
- `quality_certificate` — ISO, BIS, AERB, OEM certificate
- `bid_document` — EMD receipt, tender acceptance letter, integrity pact, bid form
- `compliance_declaration` — Make-in-India, MSME, non-debarment declaration
- `other` — company profile, cover letter, etc.

Approach:
1. Regex pass on filename (e.g., "GST_Certificate.pdf" → registration_certificate)
2. Regex pass on first-page text (keywords: "balance sheet", "completion certificate", "GST", "ISO")
3. LLM fallback for unclassified documents (send first 1000 chars)

Prompt: `llm/prompts/doc_classifier.md`

**Acceptance:** Given a folder with mixed documents, correctly classifies at least 80% by filename/content regex alone. LLM catches the rest.

---

### Phase 2: Evidence Extractors — 6 types (Day 4 second half – Day 5)

Each extractor follows the same pattern:
```python
class BaseExtractor:
    criterion_type: CriterionType

    def extract(self, criterion: Criterion, documents: list[Document],
                pages_by_doc: dict, doc_categories: dict) -> list[EvidenceClaim]
```

Each extractor:
1. Filters documents to the relevant category
2. Sends document text + criterion parameters to LLM with a typed Pydantic response model
3. Returns EvidenceClaim objects with source citations (doc_id, page, bbox)

---

**T2.2 — Base extractor interface (`bidder/extractors/base.py`)**

Abstract base class:
```python
class BaseExtractor(ABC):
    criterion_type: CriterionType

    @abstractmethod
    def extract(self, criterion, documents, pages_by_doc, doc_categories) -> list[EvidenceClaim]

    def _filter_docs(self, documents, doc_categories, target_category) -> list[Document]
    def _get_text_for_doc(self, doc, pages_by_doc) -> str
```

Plus an extractor registry: `get_extractor(criterion_type: CriterionType) -> BaseExtractor`

**Acceptance:** Registry returns correct extractor for each of the 6 types.

---

**T2.3 — Financial threshold extractor (`bidder/extractors/financial_threshold.py`)**

Extracts: turnover / net worth values from financial documents.

LLM response schema:
```python
class FinancialExtraction(BaseModel):
    amounts: list[FinancialEntry]

class FinancialEntry(BaseModel):
    fiscal_year: str          # e.g., "2022-23"
    amount: Decimal           # in INR, normalized
    metric: str               # "turnover" | "net_worth" | "profit"
    source_page: int
    source_quote: str
```

Maps to EvidenceClaim with:
- `extracted_value`: `{"amounts": [...], "average": X, "period": "2021-2024"}`
- Source citation from the LLM response

Prompt: `llm/prompts/financial_extractor.md`

**Acceptance:** Given a CA certificate showing turnover of 7.5 cr for 3 years, extracts correct amounts with page citation.

---

**T2.4 — Statutory registration extractor (`bidder/extractors/statutory_registration.py`)**

Extracts: registration numbers, class/category, validity dates.

LLM response schema:
```python
class RegistrationExtraction(BaseModel):
    registration_type: str    # "GST" | "PAN" | "EPF" | "ESI" | "contractor_class"
    registration_number: str
    registered_name: str
    valid_from: str | None    # date or null
    valid_until: str | None
    class_category: str | None  # e.g., "Class A" for contractor registration
    source_page: int
    source_quote: str
```

Prompt: `llm/prompts/statutory_extractor.md`

**Acceptance:** Given a GST certificate PDF, extracts GSTIN, validity, registered name.

---

**T2.5 — Quality certification extractor (`bidder/extractors/quality_certification.py`)**

Extracts: certificate ID, version, scope, expiry.

LLM response schema:
```python
class CertificationExtraction(BaseModel):
    cert_name: str            # "ISO 9001"
    cert_version: str | None  # "2015"
    cert_id: str | None       # certificate number
    issuing_body: str
    scope: str | None
    issue_date: str | None
    expiry_date: str | None
    source_page: int
    source_quote: str
```

Prompt: `llm/prompts/quality_extractor.md`

**Acceptance:** Given an ISO certificate, extracts version (2008 vs 2015), expiry, scope.

---

**T2.6 — Document checklist extractor (`bidder/extractors/document_checklist.py`)**

Extracts: presence of specific documents, whether signed/dated.

LLM response schema:
```python
class ChecklistExtraction(BaseModel):
    document_name: str
    present: bool
    signed: bool
    dated: bool
    date_found: str | None
    addressed_to: str | None
    source_page: int
    source_quote: str
```

Prompt: `llm/prompts/checklist_extractor.md`

**Acceptance:** Given bid documents, correctly identifies EMD receipt presence, whether tender acceptance letter is signed.

---

**T2.7 — Policy compliance extractor (`bidder/extractors/policy_compliance.py`)**

Extracts: declarations, MSME status, debarment status.

LLM response schema:
```python
class ComplianceExtraction(BaseModel):
    policy_name: str
    declaration_text: str
    declaration_signed: bool
    cross_check_status: str   # "declared" | "verified" | "not_found"
    source_page: int
    source_quote: str
```

Prompt: `llm/prompts/compliance_extractor.md`

**Acceptance:** Given an MSME declaration, extracts policy name and declaration status.

---

**T2.8 — Experience count extractor (`bidder/extractors/experience_count.py`)**

THE most complex extractor. Extracts completed work claims from experience certificates.

LLM response schema:
```python
class ExperienceExtraction(BaseModel):
    claims: list[WorkClaimExtraction]

class WorkClaimExtraction(BaseModel):
    work_description: str
    client_name: str
    contract_value: Decimal    # in INR
    completion_date: str       # YYYY-MM-DD
    completion_cert_present: bool
    source_page: int
    source_quote: str
```

After extraction, each claim needs **similarity classification** — is this work "similar" to the tender's scope?

Similarity classifier (`llm/prompts/similarity_classifier.md`):
- Input: tender scope description + claim work description
- Output: `similar` | `not_similar` | `borderline`
- `borderline` → routes criterion to Needs Review

Maps to `CompletedWorkClaim` objects (already in schemas).

Prompt: `llm/prompts/experience_extractor.md`

**Acceptance:** Given 3 completion certificates, extracts value/date/description for each, classifies similarity.

---

### Phase 3: Verifier + Confidence (Day 5, second half)

**T2.9 — Verifier pass (`bidder/verifier.py`)**

Re-checks extracted values against the cited source region.

Function: `verify_claim(claim: EvidenceClaim, pages_by_doc: dict) -> EvidenceClaim`

Logic:
1. Look up the cited page text from `pages_by_doc[claim.source_doc_id][claim.source_page]`
2. Check that key extracted values appear in the cited page text:
   - For financial: the amount (with tolerance for formatting: "7,50,00,000" vs "75000000")
   - For registration: the registration number
   - For dates: the date value
3. If round-trip check fails → set `verifier_passed = False`
4. If the cited page has no matching text → set `verifier_passed = False`

Claims with `verifier_passed = False` are dropped from evidence; criterion routes to Needs Review.

**Acceptance:** A correct extraction passes verification. A hallucinated value (amount not on page) fails verification.

---

**T2.10 — Confidence scorer (`bidder/confidence.py`)**

Function: `score_confidence(claim: EvidenceClaim, ocr_confidence: float | None) -> float`

Confidence = weighted combination:
- `verifier_passed`: 0.0 or 0.5 (binary — did the value round-trip?)
- `ocr_confidence`: 0.0–0.3 weight (from PaddleOCR, or 0.3 if native PDF)
- `extraction_heuristic`: 0.0–0.2 (source_quote length > 20 chars, page > 0, etc.)

If confidence < `settings.confidence_threshold` (0.85) on a mandatory criterion → Needs Review.

**Acceptance:** Native PDF with verifier pass → confidence > 0.85. Scanned PDF with OCR errors → confidence < 0.85.

---

### Phase 4: Verdict Engine (Day 6, first half)

**T2.11 — Verdict engine framework (`verdict/engine.py`)**

Registry pattern — each CriterionType maps to a Rule class.

```python
class BaseRule(ABC):
    @abstractmethod
    def evaluate(self, criterion: Criterion, evidence: list[EvidenceClaim]) -> Verdict

_registry: dict[CriterionType, BaseRule] = {}

def register_rule(criterion_type: CriterionType, rule: BaseRule)
def evaluate_criterion(criterion: Criterion, evidence: list[EvidenceClaim]) -> Verdict
def evaluate_all(criteria: list[Criterion], evidence_pool: dict[str, list[EvidenceClaim]]) -> list[Verdict]
```

Key design: **NO LLM in this layer.** All rules are deterministic Python. The LLM's job ended at extraction.

**Acceptance:** `evaluate_criterion` dispatches to correct rule. Missing rule → Needs Review verdict.

---

**T2.12 — Financial threshold rule (`verdict/rules/financial_threshold.py`)**

Logic:
1. From criterion parameters: get `threshold_amount`, `period_years`, `metric`
2. From evidence: get list of amounts by fiscal year
3. Compute average over the required window
4. If average >= threshold → Eligible
5. If average < threshold → Not Eligible
6. If no evidence or confidence too low → Needs Review

Reason template: "Average {metric} of INR {avg} over {period} years {passes/fails} threshold of INR {threshold}"

**Acceptance:** Turnover 7.5 cr avg vs 5 cr threshold → Eligible. Turnover 3 cr → Not Eligible.

---

**T2.13 — Statutory registration rule (`verdict/rules/statutory_registration.py`)**

Logic:
1. Check registration exists in evidence
2. Check registration type matches (GST, PAN, etc.)
3. If `required_class` in parameters → check class/category matches
4. Check validity: `valid_until` >= bid_submission_date (or no expiry)
5. All pass → Eligible. Any fail → Not Eligible. Missing/unclear → Needs Review.

**Acceptance:** Valid GST with matching number → Eligible. Expired GST → Not Eligible.

---

**T2.14 — Quality certification rule (`verdict/rules/quality_certification.py`)**

Logic:
1. Check certificate exists in evidence
2. Check cert_name matches (with equivalence table: ISO 9001:2008 == ISO 9001:2015)
3. Check expiry: not expired at bid submission date
4. Pass → Eligible. Expired or wrong cert → Not Eligible. Unclear → Needs Review.

Equivalence table (hardcoded):
```python
CERT_EQUIVALENCES = {
    "ISO 9001": ["ISO 9001:2008", "ISO 9001:2015", "ISO 9001:2024"],
    "ISO 14001": ["ISO 14001:2004", "ISO 14001:2015"],
}
```

**Acceptance:** ISO 9001:2008 satisfies "ISO 9001" requirement → Eligible.

---

**T2.15 — Document checklist rule (`verdict/rules/document_checklist.py`)**

Logic:
1. Check document is present (present == True in evidence)
2. If `must_be_signed` in parameters → check signed == True
3. If `must_be_dated` → check dated == True
4. All pass → Eligible. Missing or unsigned → Not Eligible. Unclear → Needs Review.

**Acceptance:** EMD present and signed → Eligible. Missing EMD → Not Eligible.

---

**T2.16 — Policy compliance rule (`verdict/rules/policy_compliance.py`)**

Logic:
1. Check declaration exists
2. Check declaration_signed == True
3. If cross_check available → verify against known lists
4. Declared and signed → Eligible. Missing → Not Eligible. Unsigned → Needs Review.

**Acceptance:** Signed MSME declaration → Eligible. Missing declaration → Not Eligible.

---

### Phase 5: The Disjunctive Experience Rule — Centerpiece (Day 6, second half)

**T2.17 — Experience disjunctive rule (`verdict/rules/experience_disjunctive.py`)**

THE demo wow-factor. This handles criteria like:
"3 similar works at >= 40% of estimated cost; OR 2 at >= 60%; OR 1 at >= 80%, in last 7 years"

Logic:
1. Parse criterion parameters for branches: `[{count: 3, percentage: 40}, {count: 2, percentage: 60}, {count: 1, percentage: 80}]`
2. Get `window_years` and compute temporal window from tender's `bid_submission_date`
3. Get estimated cost from tender
4. For each CompletedWorkClaim in evidence:
   a. Filter by temporal window (completion_date within window)
   b. Filter by similarity (only "similar" claims; "borderline" → flag)
5. For each branch, compute threshold = percentage * estimated_cost / 100
6. Count claims meeting the threshold
7. Branch passes if count >= required count
8. **Criterion passes if ANY branch passes** (disjunctive OR)
9. **Audit record carries ALL branch evaluations**, not just the winner

Also handles simple (non-disjunctive) experience criteria:
- If parameters have `min_count` + `min_value` (no `branches`), it's a simple count rule
- Count similar claims meeting min_value → compare against min_count

Verdict explanation includes all branches and all claims with their status.

**Acceptance:**
- Bidder K with 5 claims: 3 pass 40% threshold → Branch A passes → Eligible
- Bidder with 1 claim at 50% → Branch A fails, Branch B fails, Branch C fails → Not Eligible
- Borderline similarity on any claim → Needs Review
- Exhaustive unit tests cover all branch combinations

---

### Phase 6: Bidder-Level Aggregation + API (Day 6, end)

**T2.18 — Bidder verdict aggregator (`verdict/aggregator.py`)**

Function: `aggregate_verdicts(verdicts: list[Verdict], criteria: list[Criterion]) -> BidderVerdict`

Logic (per PRD §5.4):
- Any mandatory criterion `not_eligible` → bidder `not_eligible`
- Any mandatory criterion `needs_review` (and none `not_eligible`) → bidder `needs_review`
- All mandatory criteria `eligible` → bidder `eligible`
- Optional criterion failures appear in report but don't change bidder verdict

**Acceptance:** 4 mandatory eligible + 1 optional not_eligible → bidder Eligible. 1 mandatory not_eligible → bidder Not Eligible.

---

**T2.19 — Bidder evaluation pipeline + API endpoints**

Wire the full bidder evaluation flow:
```
upload_bidder(tender_id, name, files)
  -> ingest_bidder_packet(folder)
  -> classify_bidder_documents(documents)
  -> for each criterion in locked spec:
       extractor = get_extractor(criterion.type)
       claims = extractor.extract(criterion, docs, pages, categories)
       claims = [verify_claim(c) for c in claims]
       claims = [score_confidence(c) for c in claims]
       -> save EvidenceClaims to DB
       -> audit log: evidence_extracted
  -> for each criterion:
       verdict = evaluate_criterion(criterion, claims)
       -> save Verdict to DB
       -> audit log: rule_fired
  -> aggregate_verdicts -> BidderVerdict
  -> audit log: bidder_verdict
  -> return results
```

FastAPI endpoints:
- `POST /api/tenders/{tender_id}/bidders/upload` — upload bidder packet, run evaluation
- `GET /api/tenders/{tender_id}/bidders` — list bidders with verdicts
- `GET /api/bidders/{bidder_id}/verdicts` — per-criterion verdicts with evidence

**Acceptance:** Upload a bidder packet → get per-criterion verdicts with evidence citations + overall verdict.

---

### Phase 7: LLM Prompts (throughout)

**T2.20 — All extraction prompts**

Create prompt files:
- `llm/prompts/doc_classifier.md`
- `llm/prompts/financial_extractor.md`
- `llm/prompts/statutory_extractor.md`
- `llm/prompts/quality_extractor.md`
- `llm/prompts/checklist_extractor.md`
- `llm/prompts/compliance_extractor.md`
- `llm/prompts/experience_extractor.md`
- `llm/prompts/similarity_classifier.md`

Each prompt must:
- Be specific about the output JSON schema
- Include examples of Indian document formats (lakhs, crores, DD-MM-YYYY dates)
- Instruct the LLM to return null for unclear fields (never hallucinate)
- Require source_page and source_quote for every extraction

---

### Phase 8: Tests (Day 6, end)

**T2.21 — Unit tests**

`tests/unit/test_disjunctive.py` — EXHAUSTIVE (the wow-factor rule):
- All 3 branches pass → Eligible
- Only Branch A passes → Eligible
- Only Branch C passes → Eligible
- No branch passes → Not Eligible
- Borderline similarity → Needs Review
- Claims outside temporal window filtered out
- Off-by-one on window boundary dates
- Zero claims → Needs Review
- Exact threshold boundary (== vs >)

`tests/unit/test_verdict_engine.py`:
- Each rule produces correct verdict for clear pass/fail cases
- Aggregator: all eligible → eligible, one not_eligible → not_eligible, one needs_review → needs_review
- Optional criteria don't block

`tests/unit/test_verifier.py`:
- Correct value on page → passes
- Value not on page → fails
- Indian number formatting tolerance

---

## Dependency Order

```
T2.1 Doc classifier
  └─> T2.2 Base extractor
       ├─> T2.3 Financial extractor
       ├─> T2.4 Statutory extractor
       ├─> T2.5 Quality extractor
       ├─> T2.6 Checklist extractor
       ├─> T2.7 Compliance extractor
       └─> T2.8 Experience extractor (depends on similarity classifier)
            │
            └─> T2.9 Verifier ──> T2.10 Confidence scorer
                                     │
T2.11 Verdict engine framework ◄─────┘
  ├─> T2.12 Financial rule
  ├─> T2.13 Statutory rule
  ├─> T2.14 Quality cert rule
  ├─> T2.15 Checklist rule
  ├─> T2.16 Compliance rule
  └─> T2.17 Disjunctive experience rule (centerpiece)
       │
       └─> T2.18 Aggregator ──> T2.19 Pipeline + API
                                  │
                                  └─> T2.21 Tests
```

---

## Sprint 2 Definition of Done

- [ ] All 6 evidence extractors produce EvidenceClaims with source citations
- [ ] Verifier catches hallucinated values (value not on cited page)
- [ ] Confidence scorer routes low-confidence extractions to Needs Review
- [ ] Verdict engine: all 6 rules produce correct verdicts (deterministic, no LLM)
- [ ] Disjunctive experience rule evaluates all branches, carries all in audit record
- [ ] Aggregator: mandatory not_eligible → bidder not_eligible; needs_review propagates; optional doesn't block
- [ ] `POST /api/tenders/{tender_id}/bidders/upload` returns per-criterion verdicts end-to-end
- [ ] `pytest tests/unit/test_disjunctive.py` — all pass (exhaustive)
- [ ] `pytest tests/unit/test_verdict_engine.py` — all pass
- [ ] No bidder is silently disqualified — every NotEligible has cited evidence

---

## What We Are NOT Doing in Sprint 2

- No Streamlit UI for verdicts (Sprint 3, Gate 2)
- No PDF bbox highlighting in UI (Sprint 3)
- No seed data for 10 demo bidders (Sprint 3)
- No audit replay (Sprint 4)
- No signed report export (Sprint 4)
