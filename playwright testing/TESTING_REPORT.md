# Nirikshak — Final E2E QA Report

**Date:** 2026-05-07  
**Tester:** Automated QA via Playwright + API  
**Build:** `c845d6b` — "Fix 6 bugs from Playwright QA testing"  
**Data:** 3 bidders (50 PDFs), 1 tender (4 criteria)

---

## 1. Test Data

### Tender
| Field | Value |
|-------|-------|
| ID | `7ab29c57-12d4-4114-b7b3-e215cee24e79` |
| Title | CRPF Construction Tender — E2E Final Test |
| Authority | CRPF Group Centre Bangalore |
| Value | ₹5,00,00,000 |
| Bid Date | 2025-04-30 |

### Extracted Criteria (4)
| ID | Type | Mandatory | Parameters |
|----|------|-----------|------------|
| DOC-001 | document_checklist | ✅ | Tender Acceptance Letter, must be signed |
| DOC-002 | document_checklist | ✅ | EMD (Earnest Money Deposit) |
| REG-001 | statutory_registration | ✅ | GST, valid at submission |
| EXP-001 | experience_count | ✅ | **min_count=null** ⚠️, min_value=null, window_years=null |

### Bidders
| # | Name | Files | Expected | Aggregate Verdict | Upload Time |
|---|------|-------|----------|-------------------|-------------|
| 1 | ABC Constructions Pvt Ltd | 17 | Eligible | ❌ **not_eligible** | 6.3 min |
| 2 | Devi Constructions Pvt Ltd | 16 | Not Eligible (turnover) | ❌ **not_eligible** | 5.6 min |
| 3 | Karnataka Infra & Engineering Ltd | 17 | Eligible (disjunctive) | ❌ **not_eligible** | 6.2 min |

### Bidder Documents
```
/Users/shubham/Documents/nirikshak/documents/
├── bidder1/ (17 PDFs) — ABC Constructions
├── bidder2/ (16 PDFs) — Devi Constructions  
└── bidderk/ (17 PDFs) — Karnataka Infra
```

---

## 2. Per-Bidder Verdict Details

### Bidder 01 — ABC Constructions (Expected: ✅ Eligible)

| Criterion | Verdict | Evidence | Confidence | Notable |
|-----------|---------|----------|------------|---------|
| DOC-001 | ✅ eligible | 1 claim, verified | 100% | Tender Acceptance Letter found |
| DOC-002 | ✅ eligible | 1 claim, verified | 100% | EMD found |
| REG-001 | ✅ eligible | 5 claims, 5/5 verified | 95% avg | GST: 29AABCA1234C1ZK |
| **EXP-001** | ❌ **not_eligible** | **5 claims, 1/5 verified** | **57% avg** | **Reason:** "Only 5 qualifying similar works found, need **None**" |

**EXP-001 Evidence Detail (5 completion certificates extracted):**
| # | Value | Date | Similarity | Verified |
|---|-------|------|-----------|----------|
| 1 | ₹4,85,00,000 | 2023-06-30 | similar | ❌ |
| 2 | ₹3,42,00,000 | 2022-06-30 | similar | ❌ |
| 3 | ₹2,18,00,000 | 2022-06-30 | similar | ❌ |
| 4 | ₹2,95,00,000 | 2021-06-30 | similar | ❌ |
| 5 | ₹3,78,00,000 | 2020-06-30 | similar | ✅ |

### Bidder 02 — Devi Constructions (Expected: ❌ Not Eligible — turnover)

| Criterion | Verdict | Evidence | Confidence | Notable |
|-----------|---------|----------|------------|---------|
| DOC-001 | ✅ eligible | 1 claim, verified | 100% | Tender Acceptance Letter found |
| DOC-002 | ✅ eligible | 1 claim, verified | 100% | EMD found |
| REG-001 | ✅ eligible | 5 claims, 5/5 verified | 94% avg | GST: 29AAFCD2587E1Z7 |
| **EXP-001** | ❌ **not_eligible** | **4 claims, 2/4 verified** | **72% avg** | **Reason:** "Only 4 qualifying similar works found, need **None**" |

**EXP-001 Evidence Detail:**
| # | Value | Date | Similarity | Verified |
|---|-------|------|-----------|----------|
| 1 | ₹2,65,00,000 | 2023-06-30 | similar | ❌ |
| 2 | ₹1,95,00,000 | 2022-06-30 | similar | ❌ |
| 3 | ₹85,00,000 | 2021-06-30 | similar | ✅ |
| 4 | ₹1,40,00,000 | 2020-06-30 | similar | ✅ |

### Bidder K — Karnataka Infra & Engineering (Expected: ✅ Eligible — disjunctive)

| Criterion | Verdict | Evidence | Confidence | Notable |
|-----------|---------|----------|------------|---------|
| DOC-001 | ✅ eligible | 1 claim, verified | 100% | Tender Acceptance Letter found |
| DOC-002 | ✅ eligible | 1 claim, verified | 100% | EMD found |
| REG-001 | ✅ eligible | 5 claims, 5/5 verified | 95% avg | GST: 29AAGCK8214Q1Z6 |
| **EXP-001** | ❌ **not_eligible** | **5 claims, 2/5 verified** | **67% avg** | **Reason:** "Only 5 qualifying similar works found, need **None**" |

**EXP-001 Evidence Detail (disjunctive claims):**
| # | Value | Date | Similarity | Verified |
|---|-------|------|-----------|----------|
| 1 | ₹42,00,00,000 | 2024-06-30 | similar | ❌ |
| 2 | ₹35,00,00,000 | 2024-06-30 | similar | ❌ |
| 3 | ₹22,50,00,000 | 2023-06-30 | similar | ✅ |
| 4 | ₹28,00,00,000 | 2022-06-30 | similar | ✅ |
| 5 | ₹18,00,00,000 | 2021-06-30 | similar | ❌ |

---

## 3. Critical Bug Found: EXP-001 `min_count: null` Breaks Rule Engine

### Bug: ExperienceDisjunctiveRule Fails When min_count is Null

**Location:** `nirikshak/verdict/rules/experience_disjunctive.py`  
**Trigger:** LLM extracts `min_count: null` from tender PDF (doesn't find explicit "≥3 similar works" text)

**Behavior:**
- All 3 bidders have correct evidence (5/4/5 similar works with proper dates)
- But the rule returns "Only N qualifying similar works found, need **None**"
- The literal string "None" appears in the `need None` portion of the reason
- All bidders classified as `not_eligible` despite having qualifying evidence

**Evidence:**
```
EXP-001 params: {"min_count": null, "min_value": null, "similarity_required": true, "window_years": null}
Verdict reason: "Only 5 qualifying similar works found, need None."
```

**Root Cause:** The `ExperienceDisjunctiveRule.evaluate()` method:
1. Reads `criterion.parameters.get("min_count")` → returns None
2. Checks `if min_count is not None and qualifying_count < min_count` → skips (min_count is None)
3. BUT the rule still returns `not_eligible` via a different code path
4. The `reason_template` formats with `need {min_count}` where min_count=None → "need None"

**Impact:** **CRITICAL** — All 3 bidders are rejected for no valid reason. The demo narrative is broken. Previous run with `min_count=1` worked correctly.

**Fix:** Add a default value when min_count is None:
```python
min_count = criterion.parameters.get("min_count") or 1  # Default to 1 if None
# or: if min_count is None: min_count = 1
```

**This is a regression from the previous test run** where the LLM extracted `min_count: 1`. The non-deterministic LLM output produces different criterion parameters across runs.

---

## 4. UI Page Verification (All 7 Pages Working)

| # | Page | Screenshot | Sidebar | Data | Verdict |
|---|------|-----------|---------|------|---------|
| 0 | Empty Home | `E2E_00_EmptyHome.png` | ✅ Shows "No tenders yet" | 0 tenders, 0 bidders | ✅ |
| 1 | Home (with data) | `E2E_01_Home.png` | ✅ Active Tender dropdown | 1 tender, 3 bidders, 0/3 eligible | ✅ |
| 2 | Bidder Queue | `E2E_02_BidderQueue.png` | ✅ | 3 bidders with ❌ Not Eligible badges | ✅ |
| 3 | Verdict Review | `E2E_03_VerdictReview.png` | ✅ | Per-criterion verdicts + evidence + confidence bars | ✅ |
| 4 | Report Export | `E2E_04_ReportExport.png` | ✅ | All 3 bidders with per-criterion verdicts | ✅ |
| 5 | Audit Log | `E2E_05_AuditLog.png` | ✅ | 36 entries, filterable, chain verified | ✅ |
| 6 | Eval Dashboard | `E2E_06_EvalDashboard.png` | ✅ | Verifier pass rate, confidence, needs-review | ✅ |

**Sidebar Fix Confirmed:** `render_sidebar()` is called from all pages. The "Active Tender" dropdown, "Officer Email" field, and "⚖ Nirikshak" branding are visible on every page.

---

## 5. Fix Verifications (6 Bug Fixes Tested)

| Bug | Test | Result |
|-----|------|--------|
| #12 Sidebar missing | Navigate all 7 pages, check sidebar content | ✅ Works on all pages |
| #6 Dates 1900-01-01 | Check all 14 EXP-001 completion dates | ✅ All proper dates (2020-2024) |
| #8 Similarity all borderline | Check all 14 similarity classifications | ✅ All "similar" (was all "borderline") |
| #5 API 500 errors | GET/POST non-existent resources | ✅ Both return 404 |
| #9 Verifier low pass rate | Check verifier pass stats per bidder | ✅ 1-2/4-5 verified per bidder (was 0/14) |
| #7 Docs grouped | Check source_doc_ids per bidder | ⚠️ Still 1 source doc per bidder (5 completion PDFs in one group) |

| Fix # | Description | Status |
|--------|-------------|--------|
| #12 | Sidebar rendering on sub-pages | ✅ Fixed |
| #6 | Multi-format date parsing | ✅ Fixed |
| #8 | Similarity classifier defaults | ✅ Fixed |
| #5 | API 404 error handling | ✅ Fixed |
| #9 | Verifier + Indian number formats | ⚠️ Partial (20-50% pass rate) |
| #7 | Page→doc mapping per claim | ⚠️ Partial (5 PDFs still in one document group) |

---

## 6. API Endpoint Tests

| Endpoint | Status | Detail |
|----------|--------|--------|
| `GET /api/health` | ✅ 200 | `{"status": "ok"}` |
| `POST /api/tenders/upload` | ✅ 200 | 4 criteria, locked successfully |
| `GET /api/tenders` | ✅ 200 | 1 tender |
| `GET /api/tenders/{id}/criteria` | ✅ 200 | 4 criteria |
| `POST /api/criteria-specs/{id}/lock` | ✅ 200 | Locked with content hash |
| `POST /api/tenders/{id}/bidders/upload` | ✅ 200 | 3 bidders uploaded |
| `GET /api/tenders/{id}/bidders` | ✅ 200 | 3 bidders with verdicts |
| `GET /api/bidders/{id}/verdicts` | ✅ 200 | Full evidence with confidence, verifier |
| `GET /api/audit` | ✅ 200 | 36 entries |
| `GET /api/audit/verify` | ✅ 200 | Chain valid |
| `POST /api/audit/replay` | ⚠️ 200 | match=False (criterion DB lookup issue) |
| `GET /api/tenders/{id}/report` | ✅ 200 | Valid PDF, all sections present |
| `GET /api/eval/metrics` | ✅ 200 | Metrics returned |
| `POST non-existent lock` | ✅ 404 | Fixed from 500 |
| `GET non-existent report` | ✅ 404 | Fixed from 500 |

---

## 7. System Metrics

| Metric | This Run | Previous Run |
|--------|----------|-------------|
| Unit tests | **71/71** | 71/71 |
| Tenders | 1 | 1 |
| Bidders | 3 | 3 |
| Evidence claims | ~35 | 35 |
| Audit entries | **36** | 35 |
| Avg upload time | **6.0 min** | 6.1 min |
| Completion dates extracted | **100%** | 100% |
| Similarity "similar" rate | **100%** | 100% |
| Verifier pass rate (DOC) | **100%** | 100% |
| Verifier pass rate (REG) | **100%** | 100% |
| Verifier pass rate (EXP) | **20-50%** | 20-50% |
| Needs-review fraction | 0% | 0% |
| API 404 handling | **✅ Fixed** | ✅ Fixed |
| Sidebar on sub-pages | **✅ Fixed** | ✅ Fixed |
| Audit replay | ⚠️ Partial | ✅ |
| PDF report | **✅ All sections** | ✅ |

---

## 8. Remaining Issues

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| **1** | **EXP-001 min_count=null breaks rule** | **CRITICAL** | All 3 bidders get `not_eligible` with "need None" reason. LLM inconsistently extracts numeric thresholds from the tender PDF. |
| 2 | FIN-001 not extracted | Medium | Turnover criteria never extracted from tender PDF. Bidder 02's expected failure (₹2.82 Cr < ₹5 Cr) can't be demonstrated. |
| 3 | QUA-001 not extracted | Low | ISO certification criteria never extracted. ISO certs in bidder PDFs are unused. |
| 4 | EXP-001 min_count inconsistent | Medium | Across test runs: extracted as `1`, `null`, and sometimes with full window_years. Non-deterministic LLM output. |
| 5 | Verifier pass rate 20-50% on EXP-001 | Medium | Low verified claim count reduces evidence trustworthiness. |
| 6 | Upload 5-6 min per bidder | Medium | Too slow for 10+ bidder demo. Sequential LLM calls. |
| 7 | Audit replay partial | Medium | match=False for rule_fired entries (criterion lookup in DB fails). |
| 8 | REG-001 over-extraction | Low | PAN, EPF, ESI, CPWD numbers extracted as "registrations" next to GST. |
| 9 | 5 completion PDFs → 1 document group | Low | All completion certs for a bidder get the same source_doc_id. |
| 10 | EVAL metrics N/A for ground truth | Low | Ground truth bidder names don't match demo data names. |

---

## 9. Conclusion

### What Works ✅

- **All 7 Streamlit pages** render correctly with sidebar navigation
- **All 3 bidders** uploaded and evaluated (50 PDFs total)  
- **Evidence extraction quality** dramatically improved: proper dates, correct similarity classification
- **Document checklist (DOC-001/DOC-002)** and **statutory registration (REG-001)** work perfectly — 100% verifier pass rate
- **PDF report** generated with all sections and digital signature
- **Hash-chained audit log** verified valid (36 entries)
- **API 404 errors** handled correctly (fixed from 500)
- **71/71 unit tests** pass

### What Needs Fixing Before Demo

| Priority | Issue | Action |
|----------|-------|--------|
| **CRITICAL** | EXP-001 `min_count=null` breaks rule | Add `min_count = min_count or 1` fallback in experience_disjunctive.py |
| **HIGH** | Tender extraction is non-deterministic | The same PDF produces different criteria each time (min_count=1 vs null). Either fix the prompt or inject criteria programmatically. |
| **MEDIUM** | Upload speed 6 min/bidder | Parallelize LLM calls or use pre-cached extraction for demo |
| **MEDIUM** | FIN-001 never extracted | Add explicit financial threshold language to the tender PDF or inject criteria |

### Demo Readiness: ⚠️ Conditional

The system works correctly for DOC-001, DOC-002, and REG-001 criteria. The EXP-001 evidence extraction quality is good (proper dates, correct similarity, ~50% verified). But the verdict engine rejects all bidders because `min_count=null` in the rule logic.

**If the min_count bug is fixed**, all 3 bidders should get `eligible` on EXP-001, and the aggregate verdicts would become `eligible` for all three — matching the expected demo narrative (with the caveat that turnover and ISO evaluation are still missing due to FIN-001/QUA-001 not being extracted).
