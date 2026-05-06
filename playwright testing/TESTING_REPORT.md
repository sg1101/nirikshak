# Nirikshak — End-to-End QA Testing Report

**Date:** 2026-05-06  
**Tester:** Automated QA via Playwright + API  
**Environment:** Python 3.11.7, PostgreSQL 16, Streamlit 1.57+, FastAPI  
**Demo Data:** 3 bidders (50 PDFs) from `nirikshak_demo_data`  
**Status:** ⚠️ **PASS with issues** (see findings below)

---

## Quick Summary

| Area | Result |
|------|--------|
| **Streamlit Console (7 pages)** | ✅ Working with caveats |
| **API Backend (13 endpoints)** | ✅ Working |
| **Unit Tests (71)** | ✅ **71/71 PASS** |
| **Bidder Upload Pipeline** | ⚠️ Functional but very slow |
| **LLM Extraction Quality** | ⚠️ Mixed results |
| **Evidence Verifier** | ❌ Low pass rate |
| **Audit Replay** | ⚠️ Partial |
| **PDF Reports** | ✅ All sections present |

---

## Test Data

**Tender:** E2E Test - Construction Tender (CRPF Group Centre Bangalore)  
**Value:** ₹5,00,00,000 | **Bid Date:** 2025-04-30  
**Criteria (6):** DOC-001, DOC-002, DOC-003, REG-001, EXP-001, POL-001

### Bidders Uploaded

| Bidder | Files | Aggregate | Per-Criterion Breakdown |
|--------|-------|-----------|------------------------|
| **Bidder 01** (eligible ref) | 17 | ❌ Not Eligible | DOC-001✅ DOC-002✅ DOC-003❌ REG-001✅ EXP-001✅ POL-001❌ |
| **Bidder 02** (low turnover) | 16 | ❌ Not Eligible | DOC-001✅ DOC-002✅ DOC-003❌ REG-001✅ EXP-001✅ POL-001✅ |
| **Bidder K** (disjunctive) | 17 | ❌ Not Eligible | DOC-001✅ DOC-002✅ DOC-003❌ REG-001✅ EXP-001⚠️ POL-001✅ |

⚠️ **Note:** All 3 bidders are Not Eligible primarily due to DOC-003 (Technical Bid Documents) which doesn't exist as a separate file. The demo bidder configs were designed for a different set of criteria (FIN-001, EXP-001, REG-001, QUA-001) than what the LLM extracted from the sample tender PDF.

---

## Per-Bidder Gap Analysis

### Methodology

Each bidder has an **expected profile** (from `bidder_configs/*.yaml`) and an **actual system result** (from LLM extraction + rule engine). The expected criteria are **FIN-001** (FinancialThreshold), **EXP-001** (ExperienceCount), **REG-001** (StatutoryRegistration), and **QUA-001** (QualityCertification). The system extracted **DOC-001, DOC-002, DOC-003, REG-001, EXP-001, POL-001**.

The fundamental gap: **FIN-001 and QUA-001 were never extracted** by the LLM from the tender PDF, so the turnover and ISO documents in every bidder's packet are **completely ignored**.

---

### BIDDER 01 — "ABC Constructions Private Limited" (Expected: ✅ Eligible)

**Expected (per `bidder_01_eligible.yaml`):**
| Criterion | Expected | Rationale |
|-----------|----------|-----------|
| FIN-001 | ✅ Eligible | Avg turnover ₹6.62 Cr > ₹5 Cr threshold |
| EXP-001 | ✅ Eligible | 5 completion certs ≥ 3 required |
| REG-001 | ✅ Eligible | GST 29AABCA1234C1ZK, valid |
| QUA-001 | ✅ Eligible | ISO 9001:2015, valid until Aug 2027 |
| **Aggregate** | **✅ Eligible** | All mandatory criteria met |

**Actual System Result:**
| Criterion | Actual | Gap |
|-----------|--------|-----|
| DOC-001 | ✅ Eligible | OK |
| DOC-002 | ✅ Eligible | OK |
| REG-001 | ✅ Eligible (GST: 29AABCA1234C1ZK) | OK |
| EXP-001 | ✅ Eligible (1 similar work found) | **Partial** — min_count=1 instead of 3 |
| **DOC-003** | ❌ **Not Eligible** | **FALSE FAILURE** — bidder has all docs, no "Technical Bid Documents" file |
| **POL-001** | ❌ **Not Eligible** | **FALSE FAILURE** — bidder has `11_integrity_pact.pdf` but LLM didn't extract it |
| **FIN-001** | **NOT EVALUATED** | **CRITICAL** — criterion never extracted, turnover data unused |
| **QUA-001** | **NOT EVALUATED** | **CRITICAL** — criterion never extracted, ISO cert unused |
| **Aggregate** | ❌ **Not Eligible** | **WRONG** — should be Eligible |

**Gap Summary:**
| # | Gap | Severity | Details |
|---|-----|----------|---------|
| G1 | FIN-001 not extracted → turnover evaluation skipped | **CRITICAL** | The key financial criterion from the tender is invisible. ₹6.62 Cr avg turnover goes unevaluated. |
| G2 | QUA-001 not extracted → ISO evaluation skipped | **CRITICAL** | The quality criterion is invisible. Valid ISO 9001:2015 cert goes unevaluated. |
| G3 | DOC-003 false failure | **HIGH** | No bidder has "Technical Bid Documents" as a separate file. All 3 bidders fail this. |
| G4 | POL-001 false failure for Bidder 01 | **MEDIUM** | Bidder 01 has `11_integrity_pact.pdf` but LLM extracted "No declaration found". Bidder 02 and K pass this. |
| G5 | EXP-001 min_count=1 instead of 3 | **MEDIUM** | The LLM extracted `min_count: 1` from a vague tender quote. The YAML specifies ≥3. |
| G6 | EXP-001 completion dates all 1900-01-01 | **HIGH** | Temporal filtering can't work. All 5 dates default to sentinel. |
| G7 | EXP-001 similarity = 4/5 borderline | **MEDIUM** | Only 1 of 5 claims classified as "similar". |

---

### BIDDER 02 — "Devi Constructions Private Limited" (Expected: ❌ Not Eligible — turnover)

**Expected (per `bidder_02_not_eligible_turnover.yaml`):**
| Criterion | Expected | Rationale |
|-----------|----------|-----------|
| FIN-001 | ❌ Not Eligible | Avg turnover ₹2.82 Cr < ₹5 Cr threshold |
| EXP-001 | ✅ Eligible | 4 completion certs ≥ 3 required |
| REG-001 | ✅ Eligible | GST 29AAFCD2587E1Z7, valid |
| QUA-001 | ✅ Eligible | ISO 9001:2015, valid until Feb 2027 |
| **Aggregate** | **❌ Not Eligible (FIN-001 failure)** | ↑ This is the cited reason |

**Actual System Result:**
| Criterion | Actual | Gap |
|-----------|--------|-----|
| DOC-001 | ✅ Eligible | OK |
| DOC-002 | ✅ Eligible | OK |
| REG-001 | ✅ Eligible (GST: 29AAFCD2587E1Z7) | OK |
| EXP-001 | ✅ Eligible (2 similar works found) | OK |
| **DOC-003** | ❌ **Not Eligible** | **FALSE FAILURE** |
| POL-001 | ✅ Eligible | OK |
| **FIN-001** | **NOT EVALUATED** | **CRITICAL** — turnover data unused |
| **QUA-001** | **NOT EVALUATED** | **CRITICAL** — ISO cert unused |
| **Aggregate** | ❌ **Not Eligible** | **Correct outcome, WRONG reason** |

**The demo-critical problem:** The system shows `Not Eligible` for the WRONG reason. The demo's segment 3 requires showing "Turnover ₹2.82 cr < ₹5 cr threshold per FIN-001, evidenced by CA_certificate.pdf p.1". Instead, the system shows "Technical Bid Documents not found" — which teaches the wrong lesson.

**Gap Summary:**
| # | Gap | Severity | Details |
|---|-----|----------|---------|
| G8 | FIN-001 failure reason invisible | **CRITICAL** | The turnover failure is the entire point of bidder_02. Without FIN-001 extraction, the system can't demonstrate the "cited reason" feature. |
| G9 | Wrong failure reason shown | **CRITICAL** | DOC-003 failure masks the real reason. A demo reviewer would say "so it failed because of a missing document, not because of turnover?" |
| G10 | EXP-001 min_count=2(actual) vs 3(expected) | LOW | The actual system found 2 works >= min_count=1 threshold. Would pass either way. |

---

### BIDDER K — "Karnataka Infra & Engineering Limited" (Expected: ✅ Eligible via disjunctive)

**Expected (per `bidder_K_disjunctive.yaml` & PRD §7):**
| Criterion | Expected | Rationale |
|-----------|----------|-----------|
| FIN-001 | ✅ Eligible | Avg turnover > ₹40 Cr >> ₹5 Cr |
| EXP-001 | ✅ Eligible | 5 completion certs ≥ 3 required |
| EXP-002 (disjunctive) | ✅ Eligible | All 3 branches pass (PRD §7) |
| REG-001 | ✅ Eligible | GST 29AAGCK8214Q1Z6 |
| QUA-001 | ✅ Eligible | ISO 9001:2015 |

**Disjunctive Branch Evaluation (for ₹5 Cr tender, estimated_value=50,000,000):**
| Branch | Threshold | Qualifying Claims | Expected |
|--------|-----------|-------------------|----------|
| A: ≥3 at ≥40% (₹2 Cr) | ₹2,00,00,000 | claims {1,2,3,4,5} = 5 | ✅ PASS |
| B: ≥2 at ≥60% (₹3 Cr) | ₹3,00,00,000 | claims {1,3,4,5} = 4 | ✅ PASS |
| C: ≥1 at ≥80% (₹4 Cr) | ₹4,00,00,000 | claims {1,3,4} = 3 | ✅ PASS |

(Note: For the PRD's ₹50 Cr tender, the thresholds are ₹20 Cr/₹30 Cr/₹40 Cr. The YAML specifies ₹5 Cr, making all thresholds proportionally lower.)

**Actual System Result:**
| Criterion | Actual | Gap |
|-----------|--------|-----|
| DOC-001 | ✅ Eligible | OK |
| DOC-002 | ✅ Eligible | OK |
| REG-001 | ✅ Eligible (GST: 29AAGCK8214Q1Z6) | OK |
| EXP-001 | ⚠️ **Needs Review** (0 qualifying works) | **CRITICAL FAILURE** — all 5 claims borderline, 0 passed |
| DOC-003 | ❌ **Not Eligible** | FALSE FAILURE |
| POL-001 | ✅ Eligible | OK |
| **Aggregate** | ❌ **Not Eligible** | **WRONG** — should be Eligible |

**Disjunctive deep-dive failure analysis:**
```
Extracted claims:
  Claim 1: ₹4.20 Cr, completion_date=1900-01-01, similarity=borderline
  Claim 2: ₹3.50 Cr, completion_date=1900-01-01, similarity=borderline
  Claim 3: ₹2.25 Cr, completion_date=1900-01-01, similarity=borderline
  Claim 4: ₹2.80 Cr, completion_date=1900-01-01, similarity=borderline
  Claim 5: ₹1.80 Cr, completion_date=1900-01-01, similarity=borderline

Failed: 0/5 similar, 0/5 verified, all dates default
Expected: 4/5 similar, 4/5 verified (not claim 5), proper dates

The disjunctive rule can't evaluate because:
1. No claims have a valid completion_date (all 1900-01-01) → temporal filter fails
2. All claims are "borderline" → ExperienceDisjunctiveRule needs "similar" claims
3. Verifier confirmation is 0% → below confidence threshold (85%) → needs_review
```

**Gap Summary:**
| # | Gap | Severity | Details |
|---|-----|----------|---------|
| G11 | Bidder K can't demonstrate disjunctive rule | **CRITICAL** | The entire "wow factor" is invisible. Segment 4 of the demo can't be shown. |
| G12 | All 5 claims borderline — similarity classifier broken | **HIGH** | Should be: 4 similar, 1 borderline. Actual: 0 similar, 5 borderline. |
| G13 | All 5 dates default to 1900-01-01 | **HIGH** | The completion date is the critical field for temporal window filtering. Without it, all claims are out-of-window. |
| G14 | All claims in one source document | **MEDIUM** | 5 separate PDFs but treated as one document. Verifier can't match claims to specific cert PDFs. |
| G15 | Confidence fixed at 47% for all claims | **MEDIUM** | Suspiciously identical confidence. Something is producing a hardcoded low score. |

---

### Cross-Bidder Systemic Gaps

| # | Gap | Affects | Severity |
|---|-----|---------|----------|
| G1G | FIN-001 (turnover) never extracted by LLM | All 3 bidders | **CRITICAL** |
| G2G | QUA-001 (ISO certification) never extracted by LLM | All 3 bidders | **CRITICAL** |
| G3G | DOC-003 "Technical Bid Documents" fails for all | All 3 bidders | **HIGH** |
| G6G | Completion dates all `1900-01-01` | All 3 bidders (EXP-001) | **HIGH** |
| G7G | All completion certs grouped into 1 document | All 3 bidders | **MEDIUM** |
| G8G | Similarity over-classifies as "borderline" | All 3 bidders | **MEDIUM** |
| G9G | Verifier 0% pass rate on EXP-001 claims | All 3 bidders | **HIGH** |
| G10G | Upload takes 8-15 min per bidder | Pipeline usability | **HIGH** |

### Root Cause Chain

```
tender_construction.yaml defines FIN-001, EXP-001, REG-001, QUA-001
  ↓ (but there's no matching tender PDF for LLM ingestion)
LLM extracts DIFFERENT criteria from sample_tender.pdf
  → DOC-001, DOC-002, DOC-003, REG-001, EXP-001, POL-001
  → FIN-001 and QUA-001 are MISSING
    ↓
Bidder documents designed for FIN-001/QUA-001 are USELESS
  → Turnover certs (04_*) ignored
  → ISO certs (08_*) ignored  
  → Completion dates not extracted from synthetic PDFs
  → Similarity misclassified
    ↓
All 3 bidders fail for a fake reason (DOC-003)
  → Demo narrative is broken
  → Disjunctive rule (wow factor) can't be demonstrated
```

**Required fix:** Either (a) create a tender PDF whose text matches the YAML criteria so the LLM extracts FIN-001/EXP-001/REG-001/QUA-001, or (b) bypass LLM extraction and inject the criteria programmatically for the demo.

---

## Screenshot Index

All screenshots in `/Users/shubham/Documents/nirikshak/playwright testing/`:

| # | File | Page | Status |
|---|------|------|--------|
| FT-01 | `FT_01_home.png` | Home | ✅ 3 tenders, 8 bidders |
| FT-02 | `FT_02_tender_library.png` | Tender Library | ✅ All tenders listed |
| FT-03 | `FT_03_bidder_queue.png` | Bidder Queue | ✅ 3 bidders with verdicts |
| FT-04 | `E2E_02_criteria_review.png` | Criteria Review | ✅ 6 criteria with source quotes |
| FT-05 | `E2E_05_audit_log.png` | Audit Log | ✅ 48 entries, chain valid |
| FT-06 | `E2E_06_eval_dashboard_full.png` | Eval Dashboard | ✅ All metrics displayed |
| FT-07 | `E2E_04_verdict_review.png` | Verdict Review | ❌ Session state bug |
| FT-08 | `E2E_03_bidder_queue.png` | Bidder Queue | ✅ Full data loaded |

---

## Critical Bugs Found

### Bug #4: Session State Does Not Persist Across Pages (MEDIUM)

**Location:** `streamlit_app.py` sidebar selectbox + page-level `st.session_state.get("selected_tender_id")`  

**Behavior:**
- Home page sidebar shows "Active Tender" dropdown correctly
- Tender Library "Select" button sets session state correctly
- Bidder Queue page reads the tender correctly
- **Verdict Review** and **Report Export** pages show "No tender selected" even though tender IS selected in the sidebar

**Root Cause:** Streamlit's sidebar `selectbox` with `key="selected_tender_id"` doesn't properly reinitialize from session state on certain page navigations. The selectbox defaults to the first option, which should be the most recent tender. But on Verdict Review and Report Export pages, the sidebar custom widgets (Officer Email, Active Tender) are NOT rendered at all, meaning the entire `try` block in the sidebar code is failing silently on those pages.

**Impact:** Users cannot access Verdict Review or Report Export for the selected tender through normal navigation.

**Suggested Fix:** 
1. Ensure sidebar code doesn't fail on any page (add `st.set_page_config()` only in main file)
2. Fix `initial_sidebar_state="expanded"` to persist across pages
3. Add a fallback in Verdict Review / Report Export pages to read the sidebar selectbox value

---

### Bug #5: API Returns 500 Instead of 404 for Non-Existent Resources (MEDIUM)

**Location:** `nirikshak/api/main.py`

**Examples:**
- `POST /api/criteria-specs/{id}/lock` with non-existent spec → **500 Internal Server Error** (should be 404)
- `GET /api/tenders/{id}/report` with non-existent tender → **500 Internal Server Error** (should be 404)

**Root Cause:** Missing error handling for `scalar_one_or_none()` returning `None` in lock and report endpoints.

---

### Bug #6: Evidence Extractor Fails on Completion Dates (HIGH)

**Location:** `nirikshak/bidder/extractors/experience_count.py` (or the LLM prompt)

**Behavior:** All 15 extracted completion claims across 3 bidders have `completion_date: 1900-01-01` — a sentinel/default value. The LLM cannot extract actual completion dates from the synthetic PDF completion certificates.

**Impact:** The temporal window filter (which checks if a work was completed within the required window) may fail. For Bidder K, the disjunctive rule evaluation shows `0 qualifying works found` because none of the 5 claims have valid dates or verified similarity status.

**Evidence (from Bidder K):**
```
Claim 1: value=4,20,00,000 date=1900-01-01 similarity=borderline
Claim 2: value=3,50,00,000 date=1900-01-01 similarity=borderline
Claim 3: value=2,25,00,000 date=1900-01-01 similarity=borderline
Claim 4: value=2,80,00,000 date=1900-01-01 similarity=borderline
Claim 5: value=1,80,00,000 date=1900-01-01 similarity=borderline
```

---

### Bug #7: Document Routing Groups All Completion Certs Into One Document (MEDIUM)

**Location:** `nirikshak/bidder/doc_classifier.py`

**Behavior:** Despite having 5 separate completion certificate PDFs (13_completion_cert_01 through 05.pdf), ALL 5 evidence claims for EXP-001 show the same `source_doc_id`. The document classifier routes all completion certs under one document group instead of keeping them separate.

**Impact:** Multi-document bidders lose their per-document source tracking. The verifier can't cross-reference claims to specific pages in specific PDFs.

---

### Bug #8: Similarity Classification Too Conservative (MEDIUM)

**Location:** LLM prompt in `nirikshak/llm/prompts/similarity_classifier.md`

**Behavior:** Most claims are classified as "borderline" even when they should be "similar":
- Bidder 01: 1/5 similar, 4/5 borderline
- Bidder K: 0/5 similar, 5/5 borderline

The PRD specifies that only claim 5 for Bidder K should be borderline (the Embassy Manyata multi-level deck). Claims 1-4 should be "similar".

**Impact:** The disjunctive rule fails to find qualifying works. Bidder K should be Eligible but gets Needs Review.

---

### Bug #9: Evidence Verifier Pass Rate is 0% for EXP-001 Claims (HIGH)

**Location:** `nirikshak/bidder/verifier.py`

**Behavior:** Across all 3 bidders, NO experience claims pass the verifier (0/14 verified). The verifier can't find the extracted amounts (e.g., `420000000`) or descriptions on the cited page.

**Root Cause:** The verifier checks if extracted text values appear on the cited page. But the values extracted by the LLM may be formatted differently (e.g., `4,20,00,000` vs `420000000`) or the page text extraction from the synthetic PDF may not match.

**Impact:** Confidence scores are low (47% for all EXP-001 claims), which routes them to Needs Review.

---

### Bug #10: Bidder Upload Extremely Slow (PERFORMANCE)

**Location:** `nirikshak/api/main.py:300-456` (sequential per-criterion LLM calls)

**Measurement:**
- Bidder 01 (17 files): **510 seconds** (8.5 minutes)
- Bidder 02 (16 files): **577 seconds** (9.6 minutes)
- Bidder K (17 files): **~900 seconds** (15 minutes — timed out)

**Root Cause:** The bidder upload endpoint makes sequential LLM calls for each criterion (6 criteria × multiple prompts each). There's no parallelization, and no streaming/progress feedback to the user.

**Impact:** Uploading 10 bidders would take 1.5-2.5 hours. Not viable for the demo.

---

### Bug #11: Error Page Shows Blank White Screen (LOW)

**Location:** Streamlit page routing

**Behavior:** Navigating directly to a non-existent page shows a brief "Page not found" message that clears immediately, resulting in a blank white page with just the Streamlit menu.

**Impact:** Users who try direct URL navigation (e.g., bookmarking) get a confusing blank page.

---

## Enhancement Suggestions

### E-1: Progress Feedback During Bidder Upload
Add a progress bar or streaming response during bidder upload. The spinner with no progress for 8+ minutes is a poor UX. Streamlit has `st.progress()` and `st.status()` widgets.

### E-2: Default Tender Selection on Fresh Load
When there's only one tender (common after initial setup), auto-select it rather than showing "No tender selected" on every page.

### E-3: Sidebar Tender Selector Visual Cues
Show the selected tender name consistently in the sidebar even when collapsed. Currently it only shows when the sidebar is expanded.

### E-4: Verdict Review Page — Clickable Evidence Citations
Make the evidence source_page clickable to open/preview the cited document page.

### E-5: Report Export — Preview Auto-Refresh
The report preview doesn't automatically update when bidders are evaluated (requires page refresh).

### E-6: Audit Log — Built-in Replay on Each Rule Fired Entry
Add a "Replay" button directly on each `rule_fired` audit entry row rather than requiring the user to select from a dropdown.

### E-7: Evaluation Dashboard — Filter by Tender
The Eval Dashboard currently shows metrics for ALL tenders. Add a tender selector to filter evaluations.

---

## API Performance Benchmarks

| Operation | Time | Notes |
|-----------|------|-------|
| Health check | <1s | ✅ |
| Tender upload + criteria extraction | ~30s | Includes LLM call |
| Criteria spec lock | <1s | ✅ |
| Bidder upload (17 files, 6 criteria) | **510-900s** | ❌ Extremely slow |
| Per-bidder verdict retrieval | <1s | ✅ |
| Audit log (48 entries) | <1s | ✅ |
| Chain verification | <1s | ✅ |
| Audit replay | <1s | ✅ (when criteria exist) |
| PDF report generation | <2s | ✅ |
| Eval metrics | <1s | ✅ |

---

## Edge Case Testing

| Test | Input | Expected | Actual | Result |
|------|-------|----------|--------|--------|
| Non-existent tender criteria | `0000...0000` UUID | 404 | **404** | ✅ |
| Non-existent bidder verdicts | `0000...0000` UUID | 404 | 200 (empty) | ⚠️ |
| Lock non-existent spec | `0000...0000` UUID | 404 | **500 Internal Server Error** | ❌ |
| Invalid audit replay | `"invalid"` hash | Graceful | 200 (match=false) | ✅ |
| Non-existent tender report | `0000...0000` UUID | 404 | **500 Internal Server Error** | ❌ |
| Bidder upload with 0 files | empty files list | 422 | **422** validation error | ✅ |
| Audit chain verification | GET | valid | `{"valid": true}` | ✅ |
| Health check | GET | 200 | `{"status": "ok"}` | ✅ |

**500 Error Root Causes:**
- `POST /api/criteria-specs/{id}/lock`: The endpoint doesn't check if the spec exists before trying to lock it. `session.get(CriteriaSpec, spec_id)` returns `None`, and the code calls `spec.locked_at` on `None`.
- `GET /api/tenders/{id}/report`: Same pattern — the `generate_report()` function doesn't handle the case where the tender doesn't exist in the DB despite passing UUID validation.

---

## New Bug Found: Sidebar Content Not Rendered on Sub-Pages (HIGH)

### Bug #12: Streamlit Multipage App — Custom Sidebar Content Missing on Sub-Pages

**Location:** `nirikshak/console/streamlit_app.py` (sidebar code block) + all sub-pages in `pages/`

**Behavior:**
- Home page: ✅ Shows "⚖️ Nirikshak", "AI-Based Tender Evaluation", "Officer Email", "Active Tender" dropdown in sidebar
- All sub-pages (Tender Library, Criteria Review, Bidder Queue, Verdict Review, etc.): ❌ Custom sidebar content is completely **missing** — only navigation links and Deploy button visible

**Impact:** The tender selector (`st.sidebar.selectbox` with `key="selected_tender_id"`) is only rendered on the home page. When navigating to any sub-page, `st.session_state.get("selected_tender_id")` returns `None`, causing pages like Verdict Review and Bidder Queue to show "No tender selected".

**Root Cause:** In Streamlit 1.57.0 multipage apps, custom sidebar widgets defined in `streamlit_app.py` are NOT re-rendered when navigating to a sub-page. Each sub-page runs as an independent script, and the main script's sidebar content is not inherited. The `key`-bound widgets lose their connection to session state.

**Severity:** **HIGH** — Blocks 4 of 7 pages from functioning correctly:
- Bidder Queue: "No tender selected"
- Verdict Review: "No tender selected"  
- Report Export: "No tender selected"
- Criteria Review: "No tender selected" (when navigated directly)

**Suggested Fix:** Add tender selector logic to EACH sub-page that needs it, OR use `st.query_params` to pass the tender ID across pages, OR inject the sidebar selectbox code in each sub-page.

---

## Conclusion

The Nirikshak prototype's **technical pipelines work** (upload, extraction, verdict, report, audit), but the **demo-critical narrative fails** due to a fundamental criteria mismatch.

### Expected vs Actual Demo Narrative

| Demo Segment | Expected | Actual | Status |
|-------------|----------|--------|--------|
| 1 — Upload tender → extract 4 criteria | FIN-001, EXP-001, REG-001, QUA-001 | DOC-001, DOC-002, DOC-003, REG-001, EXP-001, POL-001 | ❌ Mismatch |
| 2 — 10 bidder packets ingested | Evidence cards with source citations | Works, but evidence quality is low | ⚠️ |
| 3 — 6 Eligible / 3 Not Eligible / 1 Needs Review | Clear verdicts with cited reasons | All 3 bidders Not Eligible (false reason) | ❌ |
| 4 — Disjunctive deep-dive (Bidder K) | All 3 branches evaluated, Eligible | 0 qualifying works, Needs Review | ❌ |
| 5 — Audit drill replay | Verdict reproduced from frozen inputs | Works when criteria exist in DB | ⚠️ |
| 6 — Accuracy dashboard | Real metrics | Shows 0% bidder-level accuracy | ⚠️ |

### Critical Blockers for Demo (in priority order)

| # | Issue | Blocks |
|---|-------|--------|
| **1** | **FIN-001 not extracted** by LLM from tender PDF | Segments 2-3 (turnover evaluation) |
| **2** | **QUA-001 not extracted** by LLM from tender PDF | Quality certification evaluation |
| **3** | **DOC-003 false failure** for all bidders | Every bidder gets Not Eligible |
| **4** | **Completion dates all 1900-01-01** | Temporal filtering, disjunctive rule |
| **5** | **Upload 8-15 min per bidder** | Can't do 10 bidders in demo time |
| **6** | **Similarity classifier too conservative** | All claims "borderline" |
| **7** | **Session state resets** on Verdict Review / Report Export | 2/7 pages inaccessible |

### The data is loaded and the system runs — the best way forward for the developers:

1. **Inject criteria programmatically** — bypass LLM extraction for the demo. Use a hardcoded/seed path to create a CriteriaSpec with FIN-001, EXP-001, REG-001, QUA-001 matching the YAML config.
2. **Fix the experience extractor** — the completion date extraction and similarity classification both fail on synthetic PDFs. Either fix the prompts or run the demo on simpler native-text PDFs.
3. **Optional:** Remove DOC-003 from the criteria or add a "Technical Bid Documents" file to each bidder's packet.
4. **Increase upload parallelism** — Run per-criterion LLM calls concurrently instead of sequentially.
5. **Fix session state** — Ensure sidebar `selectbox` initializes from existing session state on all pages.
