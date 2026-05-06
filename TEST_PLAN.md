# Nirikshak — Test Plan

This document contains all manual and integration tests for the Nirikshak prototype. Tests are organized by user flow and can be executed through the Streamlit UI at http://localhost:8501.

## Prerequisites

Before running tests, ensure:
1. PostgreSQL is running locally on port 5432
2. API is running: `source .venv/bin/activate && uvicorn nirikshak.api.main:app --port 8000`
3. Streamlit is running: `streamlit run nirikshak/console/streamlit_app.py --server.port 8501`
4. `.env` file has a valid `OPENAI_API_KEY`
5. A sample tender PDF is available (e.g., `/Users/shubham/Downloads/sample_tender.pdf`)

Alternatively, run `python seed/run_demo.py` to auto-populate demo data for tests that require existing data.

---

## Test Suite 1: Tender Upload and Criteria Extraction

### TC-1.1: Upload a tender PDF

**Steps:**
1. Open http://localhost:8501
2. Click **"Tender Library"** in the sidebar
3. In the "Upload New Tender" section:
   - Enter Title: `Test Construction Tender`
   - Enter Procuring Authority: `CRPF Zone Bangalore`
   - Set Bid Submission Date: `2025-04-30`
   - Set Estimated Value: `500000000`
   - Upload your sample tender PDF
4. Click **"Upload & Extract Criteria"**
5. Wait for the spinner to complete

**Expected Result:**
- Green success message showing the number of extracted criteria (e.g., "Extracted 5 eligibility criteria")
- Tender appears in the list below with title, authority, value, criteria count, and "Draft" status

**Pass Criteria:** Criteria count > 0, tender visible in list.

---

### TC-1.2: Verify extracted criteria are correct

**Steps:**
1. After TC-1.1, click **"Select"** on the uploaded tender
2. Click **"Criteria Review"** in the sidebar

**Expected Result:**
- Page shows tender title and "Draft" status
- Each criterion card shows:
  - Criterion ID (e.g., DOC-001, REG-001, EXP-001)
  - Type badge (Document, Registration, Experience, etc.)
  - Mandatory/Optional badge
  - Description text
  - Expandable source citation with page number and exact quote from the tender

**Pass Criteria:** At least 3 criteria displayed, each with a source quote and page number.

---

### TC-1.3: Verify tender appears in sidebar selector

**Steps:**
1. After TC-1.1, check the sidebar

**Expected Result:**
- "Active Tender" dropdown shows the uploaded tender
- Tender is auto-selected

**Pass Criteria:** Tender name visible in sidebar dropdown.

---

## Test Suite 2: Gate 1 — Criteria Review and Lock

### TC-2.1: Edit a criterion description (before lock)

**Steps:**
1. Navigate to **Criteria Review** page
2. Confirm status shows "Draft"
3. Find any criterion card
4. Modify the description text in the text area

**Expected Result:**
- Text area is editable
- Changes are visible in the field

**Pass Criteria:** Description field is editable when spec is unlocked.

---

### TC-2.2: Lock the criteria spec

**Steps:**
1. Navigate to **Criteria Review** page
2. Scroll to the bottom "Lock Criteria Spec" section
3. Confirm the warning message is displayed
4. Confirm officer email is shown (e.g., "officer1@crpf.gov.in")
5. Click **"Lock Criteria Spec"**

**Expected Result:**
- Balloons animation plays
- Green success message with:
  - Locked by: officer email
  - Content Hash (truncated)
  - Timestamp
- Page reloads showing "Locked" badge (green)
- All description fields become read-only (no text areas)

**Pass Criteria:** Status changes to "Locked", fields become read-only, content hash displayed.

---

### TC-2.3: Verify lock is irreversible

**Steps:**
1. After TC-2.2, check the Criteria Review page

**Expected Result:**
- No "Lock" button visible
- Info message: "This criteria spec was locked on [date] by [officer]"
- No edit controls (text areas, checkboxes) on any criterion
- Prompt to proceed to Bidder Queue

**Pass Criteria:** No way to edit or re-lock. Lock is permanent.

---

## Test Suite 3: Bidder Upload and Evaluation

### TC-3.1: Upload a bidder with all required documents

**Steps:**
1. Navigate to **Bidder Queue** page
2. Enter Bidder Name: `Arun Builders Pvt Ltd`
3. Upload 3 PDF files:
   - A GST certificate
   - An EMD receipt / tender acceptance letter
   - An experience/completion certificate
4. Click **"Upload & Evaluate"**
5. Wait for spinner (may take 30-60 seconds for LLM calls)

**Expected Result:**
- Success message with aggregate verdict (Eligible / Not Eligible / Needs Review)
- Per-criterion breakdown shown below the success message
- Bidder appears in the list with verdict badge
- Summary stats update (Total Bidders, Eligible count, etc.)

**Pass Criteria:** Bidder appears in list with verdict. Per-criterion results shown.

---

### TC-3.2: Upload a bidder with missing documents

**Steps:**
1. Navigate to **Bidder Queue**
2. Enter Bidder Name: `Incomplete Bidder`
3. Upload only 1 file: a GST certificate (no EMD, no experience)
4. Click **"Upload & Evaluate"**

**Expected Result:**
- Verdict should be **Not Eligible** or **Needs Review**
- Missing document criteria (DOC-001, DOC-002) should show "Not Eligible"
- GST criterion (REG-001) may show "Eligible" if certificate is valid

**Pass Criteria:** System correctly identifies missing documents. No silent disqualification — every "Not Eligible" shows a reason.

---

### TC-3.3: Verify summary statistics

**Steps:**
1. After uploading 2+ bidders, check the Bidder Queue page

**Expected Result:**
- "Total Bidders" shows correct count
- Eligible / Not Eligible / Needs Review counts are accurate
- Progress bar shows eligible fraction
- Bidders sorted: Needs Review first, then Not Eligible, then Eligible

**Pass Criteria:** Stats match actual bidder verdicts. Sort order correct.

---

## Test Suite 4: Gate 2 — Verdict Review

### TC-4.1: View per-criterion verdicts

**Steps:**
1. Navigate to **Verdict Review** page
2. Click on a bidder name in the left panel

**Expected Result:**
- Right panel shows:
  - Bidder name and aggregate verdict badge
  - Per-criterion cards, each with:
    - Criterion ID and type
    - Verdict state (green/red/yellow)
    - Rule name (e.g., "DocumentChecklistRule")
    - Human-readable reason
  - Submission date

**Pass Criteria:** All criteria from the spec have a verdict. Each verdict has a reason.

---

### TC-4.2: Expand evidence details

**Steps:**
1. On the Verdict Review page, select a bidder
2. Expand the "Evidence" section on any criterion card

**Expected Result:**
- Shows each evidence claim with:
  - Extracted values as JSON (e.g., registration_number, amount, present/signed)
  - Source page number
  - Confidence progress bar (0-100%)
  - Verifier status badge (Verified / Not verified)

**Pass Criteria:** Evidence claims show extracted values with page citations and confidence scores.

---

### TC-4.3: Gate 2 actions for Needs Review items

**Steps:**
1. On Verdict Review, find a bidder with a "Needs Review" criterion
   (If none exist, upload a bidder with borderline/ambiguous documents)
2. Look for the "Gate 2 Actions" section on the Needs Review criterion

**Expected Result:**
- Three buttons visible: "Accept As-Is", "Override" (with reason field), "Escalate"
- Clicking "Accept As-Is" shows success message
- Clicking "Override" without a reason shows warning
- Clicking "Override" with a reason shows success
- Clicking "Escalate" shows info message

**Pass Criteria:** All three action buttons work. Override requires a reason.

---

### TC-4.4: Verify no silent disqualification

**Steps:**
1. On Verdict Review, select a bidder with "Not Eligible" verdict
2. Check every "Not Eligible" criterion

**Expected Result:**
- Every "Not Eligible" criterion shows:
  - The specific rule that fired
  - A reason citing the evidence (e.g., "Document 'EMD' not found" or "GST expired on 2023-03-31")
  - Evidence claims (or explicit "no evidence found")
- No criterion shows "Not Eligible" without an explanation

**Pass Criteria:** Zero silent disqualifications. Every failure has a cited reason.

---

## Test Suite 5: Report Export

### TC-5.1: View report preview

**Steps:**
1. Navigate to **Report Export** page

**Expected Result:**
- Tender summary section: title, authority, estimated value, bid date, spec hash
- Per-bidder expandable sections, each showing:
  - Bidder name and verdict
  - Per-criterion details

**Pass Criteria:** Report preview shows all bidders and their verdicts.

---

### TC-5.2: Download signed PDF report

**Steps:**
1. On Report Export page, click **"Generate & Download Signed PDF Report"**
2. Wait for generation
3. Click the "Click to Save PDF" download button

**Expected Result:**
- PDF file downloads successfully
- Open the PDF and verify it contains:
  - Cover page with tender details
  - Criteria summary table
  - Per-bidder verdict sections with reasons
  - Digital signature block with content hash and HMAC signature
  - Footer: "Generated by Nirikshak | Prototype"

**Pass Criteria:** Valid PDF with all sections. Signature block present.

---

## Test Suite 6: Audit Log

### TC-6.1: View audit trail

**Steps:**
1. Navigate to **Audit Log** page

**Expected Result:**
- Table showing audit entries with: Sequence, Timestamp, Actor, Action, Hash
- Entries include: tender_ingested, criteria_extracted, criteria_locked, bidder_ingested, evidence_extracted, rule_fired, bidder_verdict
- Entries are in chronological order (newest first in table)

**Pass Criteria:** Multiple audit entry types visible. Entries correspond to actions taken.

---

### TC-6.2: Verify hash chain integrity

**Steps:**
1. On Audit Log page, click **"Verify Chain Integrity"**

**Expected Result:**
- Green message: "Audit chain is valid — no tampering detected"

**Pass Criteria:** Chain verification passes.

---

### TC-6.3: Filter audit entries

**Steps:**
1. On Audit Log page, use the "Filter by action type" multiselect
2. Deselect all types, then select only "rule_fired"

**Expected Result:**
- Table shows only rule_fired entries
- Entry count updates (e.g., "5 of 20")

**Pass Criteria:** Filter works correctly.

---

### TC-6.4: View entry detail

**Steps:**
1. On Audit Log page, select an entry from the "Select entry by sequence" dropdown

**Expected Result:**
- Shows: Sequence, Timestamp, Actor, Action type
- Shows: Entry Hash, Previous Hash, Payload Hash (full hashes)
- Shows: Payload as formatted JSON

**Pass Criteria:** All fields populated. Hashes are 64-character hex strings.

---

### TC-6.5: Replay a verdict (Audit Drill)

**Steps:**
1. On Audit Log page, filter to "rule_fired" entries
2. Select a rule_fired entry from the dropdown
3. Scroll down to the "Audit Drill — Replay Verdict" section
4. Click **"Replay This Verdict"**

**Expected Result:**
- Green message: "Verdict reproduced successfully!"
- Shows historical verdict and recomputed verdict (should match)
- "Chain of events" expandable shows the full sequence of entries for that bidder+criterion
- "Recomputed reasoning" shows the rule's explanation

**Pass Criteria:** Match = True. Historical and recomputed verdicts are identical.

---

## Test Suite 7: Evaluation Dashboard

### TC-7.1: View system statistics

**Steps:**
1. Navigate to **Evaluation Dashboard** page

**Expected Result:**
- System Statistics: Tenders, Bidders, Evidence Claims, Audit Entries counts
- All counts > 0 (if demo data loaded)

**Pass Criteria:** Counts are non-zero and plausible.

---

### TC-7.2: View verdict agreement metrics

**Steps:**
1. On Eval Dashboard, scroll to "Verdict-Level Agreement"

**Expected Result:**
- Bidder-Level Accuracy: percentage (or "N/A" if ground truth names don't match)
- Criterion-Level Accuracy: percentage
- Per-bidder breakdown showing expected vs actual verdicts
- Mismatches highlighted

**Pass Criteria:** Metrics displayed. If using `run_demo.py` data, accuracy should be > 50%.

---

### TC-7.3: View needs-review fraction

**Steps:**
1. On Eval Dashboard, scroll to "Needs-Review Fraction"

**Expected Result:**
- Rate shown as percentage
- Interpretation: warning if too low (<5%) or too high (>40%), success if in range
- Caption explaining what the metric means

**Pass Criteria:** Fraction displayed with honest interpretation.

---

## Test Suite 8: End-to-End Integration

### TC-8.1: Full flow from upload to report

**Steps:**
1. Start from a fresh database (or clear existing data)
2. **Tender Library**: Upload a tender PDF → verify criteria extracted
3. **Criteria Review**: Review criteria → Lock the spec
4. **Bidder Queue**: Upload 3 different bidders with varying document quality:
   - Bidder A: all documents (expect Eligible)
   - Bidder B: missing EMD (expect Not Eligible)
   - Bidder C: only GST certificate (expect Not Eligible or Needs Review)
5. **Verdict Review**: Check each bidder's per-criterion verdicts
6. **Report Export**: Download signed PDF
7. **Audit Log**: Verify chain → Replay one verdict
8. **Eval Dashboard**: Check metrics

**Expected Result:**
- Complete flow works without errors
- Bidder A has more Eligible criteria than B or C
- Report contains all 3 bidders
- Audit chain is valid
- Replay matches

**Pass Criteria:** All 7 pages functional end-to-end. No crashes, no silent disqualifications.

---

### TC-8.2: One-click demo setup

**Steps:**
1. Ensure API is running at http://localhost:8000
2. Run: `python seed/run_demo.py`
3. Open http://localhost:8501

**Expected Result:**
- Script outputs progress for each bidder upload
- Each bidder gets a verdict (mix of Eligible, Not Eligible, Needs Review)
- Audit chain verification passes
- Script prints "Demo setup complete!"
- Console shows populated data across all pages

**Pass Criteria:** Script completes without error. Console shows demo data.

---

## Test Suite 9: Automated Unit Tests

### TC-9.1: Run full test suite

**Steps:**
```bash
source .venv/bin/activate
pytest tests/unit/ -v
```

**Expected Result:**
- 71 tests pass
- Test breakdown:
  - `test_schemas.py`: 22 tests (model creation, validation, round-trip)
  - `test_hashing.py`: 9 tests (determinism, chain hashing)
  - `test_audit_chain.py`: 4 tests (append, verify, chain links, bidder filter)
  - `test_disjunctive.py`: 15 tests (all branch combos, window, thresholds, edge cases)
  - `test_verdict_engine.py`: 21 tests (all 6 rules + aggregator)

**Pass Criteria:** 71/71 pass. Zero failures.

---

## Test Suite 10: Edge Cases and Error Handling

### TC-10.1: Upload non-PDF file as tender

**Steps:**
1. On Tender Library, try uploading a .txt or .jpg file

**Expected Result:**
- File uploader should restrict to PDF (type filter)
- If bypassed, system should error gracefully

**Pass Criteria:** No crash. Clear error message.

---

### TC-10.2: Upload bidder without selecting a tender

**Steps:**
1. Clear session state (open in incognito/new tab)
2. Go directly to Bidder Queue

**Expected Result:**
- Warning: "No tender selected. Go to Tender Library and select a tender first."

**Pass Criteria:** Clear guidance, no crash.

---

### TC-10.3: Attempt to upload bidder before locking criteria

**Steps:**
1. Upload a tender (criteria spec is "Draft")
2. Go to Bidder Queue and upload a bidder

**Expected Result:**
- System auto-locks the spec OR shows an error requiring lock first
- Evaluation proceeds after auto-lock

**Pass Criteria:** System handles gracefully. No orphaned bidder without verdicts.

---

### TC-10.4: Upload empty/corrupt PDF

**Steps:**
1. Create a 0-byte file named `empty.pdf`
2. Try uploading as tender or bidder document

**Expected Result:**
- Error message (not a crash)
- System remains functional for subsequent uploads

**Pass Criteria:** Graceful error handling. System recovers.

---

## Quick Smoke Test Checklist

For a fast verification that the system is working:

- [ ] http://localhost:8000/api/health returns `{"status": "ok"}`
- [ ] http://localhost:8501 loads the Streamlit console
- [ ] Sidebar shows tender selector (if data exists)
- [ ] Tender Library page loads without errors
- [ ] Criteria Review page shows criteria (if tender selected)
- [ ] Bidder Queue page loads without errors
- [ ] Verdict Review page loads without errors
- [ ] Audit Log page shows entries and "Verify Chain" works
- [ ] Eval Dashboard page loads with metrics
- [ ] `pytest tests/unit/ -v` — 71/71 pass
