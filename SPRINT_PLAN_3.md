# Sprint 3 — Console + HITL Gates + Integration

**Days:** 7–8 (May 12–13)
**Goal:** A fully functional Streamlit console where an officer can upload a tender, review extracted criteria (Gate 1), upload bidders, review verdicts with PDF preview (Gate 2), and see the complete flow working with seed data — the full demo narrative.

---

## Why this sprint matters

Sprints 1 and 2 proved the backend works via API. Sprint 3 makes it **visible**. The demo video walks through the Streamlit console — if it doesn't look good and flow smoothly, the backend doesn't matter. Every page must serve one of the 6 demo segments from the PRD.

---

## What we are building on

From Sprint 1+2, the API already supports:
- `POST /api/tenders/upload` → criteria extraction
- `POST /api/criteria-specs/{id}/lock` → Gate 1 lock
- `POST /api/tenders/{id}/bidders/upload` → evidence extraction + verdicts
- `GET /api/tenders/{id}/bidders` → bidder list with verdicts
- `GET /api/bidders/{id}/verdicts` → per-criterion detail with evidence
- `GET /api/audit` + `GET /api/audit/verify` → audit trail

The console pages call these APIs (or directly use the DB session for speed).

---

## Task Breakdown

### Phase 1: Shared Console Infrastructure (Day 7, first half)

**T3.1 — Console helpers + DB session for Streamlit**

Streamlit runs in its own process and can't use FastAPI's dependency injection. We need:

- `console/helpers.py`:
  - `get_db_session()` — sync SQLModel session for Streamlit (uses `DATABASE_URL_SYNC`)
  - `api_call(method, path, **kwargs)` — wrapper for calling FastAPI endpoints via httpx
  - `format_inr(amount)` — format Decimal as "₹7.5 Cr" / "₹50 L"
  - `verdict_badge(state)` — return colored badge markup for eligible/not_eligible/needs_review
  - `criterion_type_icon(type)` — return icon/label for each criterion type

- `console/streamlit_app.py` — update main page:
  - Sidebar: app title, officer identity ("officer1@crpf.gov.in"), current tender selector
  - Store selected tender_id in `st.session_state`

**Acceptance:** Shared helpers importable from all pages. Sidebar shows tender selector.

---

### Phase 2: Page 1 — Tender Library (Day 7, first half)

**T3.2 — Tender Library page (`pages/1_Tender_Library.py`)**

Demo segment: Demo opens here.

Layout:
- **Upload section**: File uploader for tender PDF + form fields (title, procuring authority, bid submission date, estimated value)
- **Upload button** → calls `POST /api/tenders/upload` → shows spinner → shows extracted criteria count
- **Tender list**: Table of all tenders with columns: Title, Authority, Date, Estimated Value, Criteria Count, Status (Draft/Locked)
- **Click a tender** → stores in session_state, redirects to Criteria Review

**Acceptance:** Upload a tender PDF → see it in the list with criteria count. Click → navigates to Gate 1.

---

### Phase 3: Page 2 — Criteria Review / Gate 1 (Day 7, second half)

**T3.3 — Criteria Review page (`pages/2_Criteria_Review.py`)**

Demo segment 1: Officer reviews criteria and locks the spec.

Layout:
- **Header**: Tender title + status (Draft/Locked)
- **Criteria cards**: For each criterion, an expandable card showing:
  - Criterion ID + type badge (e.g., "FIN-001 | Financial Threshold")
  - Description (editable text_input if unlocked)
  - Mandatory/Optional toggle
  - Parameters (editable JSON or key-value pairs if unlocked)
  - Source quote in a blockquote with page number reference
- **Edit controls** (only if spec is unlocked):
  - Edit any field inline
  - "Add Criterion" button at the bottom
  - "Remove" button on each criterion
- **Lock button**:
  - Confirmation dialog: "Locking the criteria spec makes it immutable. Proceed?"
  - Officer email field
  - On lock → calls API → shows success with content hash
  - After lock, all edit controls disappear, green "Locked" badge appears
- **Audit indicator**: Show last audit entry for this spec

**Acceptance:** See all 5 criteria from the sample tender. Edit a description. Lock the spec. After locking, fields are read-only and audit log updated.

---

### Phase 4: Page 3 — Bidder Queue (Day 7, end)

**T3.4 — Bidder Queue page (`pages/3_Bidder_Queue.py`)**

Demo segment 2: Bidder packets ingested, evidence cards appear.

Layout:
- **Upload section**:
  - Bidder name text input
  - Multi-file uploader (accepts PDF, images, DOCX)
  - "Upload & Evaluate" button → calls `POST /api/tenders/{id}/bidders/upload`
  - Progress spinner during processing
- **Bidder list**: For the current tender, show all bidders as cards:
  - Bidder name
  - Submission date
  - Document count
  - Aggregate verdict badge (Eligible / Not Eligible / Needs Review)
  - Click → navigates to Verdict Review for that bidder
- **Summary stats**:
  - Total bidders
  - Count by verdict: X Eligible, Y Not Eligible, Z Needs Review
  - Visual bar showing the distribution

**Acceptance:** Upload 3 files for a bidder → see the bidder appear with verdict badge. Summary stats update.

---

### Phase 5: Page 4 — Verdict Review / Gate 2 (Day 8, first half)

**T3.5 — Verdict Review page (`pages/4_Verdict_Review.py`)**

Demo segments 3 + 4: Per-bidder verdicts with source citations + disjunctive deep-dive.

Layout — two-column:
- **Left column (30%)**: Bidder selector
  - Dropdown or list of all bidders for the tender
  - Grouped by verdict: Needs Review first, then Not Eligible, then Eligible
  - Each shows name + verdict badge

- **Right column (70%)**: Selected bidder's evaluation
  - **Bidder header**: Name, aggregate verdict badge, submission date
  - **Per-criterion verdict cards** (one per criterion):
    - Criterion ID + type + mandatory badge
    - Verdict state (colored: green/red/yellow)
    - Rule that fired
    - Reason explanation (the reason_template from the rule)
    - **Evidence section** (expandable):
      - Each evidence claim with extracted values
      - Confidence score with visual bar
      - Verifier status (passed/failed badge)
      - Source citation: document name + page number
    - **For experience/disjunctive criteria**:
      - Show all branch evaluations in a table
      - Highlight the passing/failing branches
      - Show each claim with value, date, similarity status
  - **Gate 2 actions** (for Needs Review bidders):
    - "Accept As-Is" button
    - "Override" button with reason text_area
    - "Escalate" button
    - Each action → writes to audit log

**Acceptance:** Select a bidder → see all criterion verdicts. Evidence with citations visible. Gate 2 buttons work for Needs Review items.

---

### Phase 6: Seed Data for Demo (Day 8, second half)

**T3.6 — Create demo seed data**

Create mock bidder packets that produce the demo narrative: varied verdicts across bidders.

Generate via Python script (`seed/generate_demo_data.py`):

**Bidder set** (at minimum 4-6 bidders to tell the story):

| Bidder | Expected Verdict | Why |
|--------|-----------------|-----|
| Bidder 1: "Arun Builders" | Eligible | All docs present, GST valid, 3+ experience certs |
| Bidder 2: "Sharma Infra" | Eligible | All criteria pass |
| Bidder 3: "Metro Construction" | Not Eligible | Missing EMD receipt |
| Bidder 4: "Lakshmi Enterprises" | Not Eligible | GST expired |
| Bidder 5: "National Projects" | Needs Review | Experience certificate with borderline OCR |
| Bidder 6 (optional): "Bharat Corp" | Eligible | Clean pass |

Each bidder gets 2-4 mock PDFs generated via ReportLab.

Also create: `seed/run_demo.py` — script that uploads the tender + all bidders in sequence, producing the full demo state.

**Acceptance:** Run `python seed/run_demo.py` → all bidders evaluated → at least 2 Eligible, 1 Not Eligible, 1 Needs Review.

---

### Phase 7: Pages 5-7 — Stubs with Real Data (Day 8, end)

These pages get full implementation in Sprint 4, but we make them functional enough to show real data.

**T3.7 — Report Export stub (`pages/5_Report_Export.py`)**

- Show consolidated report preview:
  - Tender summary
  - Per-bidder verdict table
  - "Download PDF" button (placeholder — actual signed PDF in Sprint 4)

**T3.8 — Audit Log viewer (`pages/6_Audit_Log.py`)**

- Show audit log table with columns: Sequence, Timestamp, Actor, Action, Entry Hash
- "Verify Chain" button → calls API → shows valid/invalid
- Filter by action type dropdown

**T3.9 — Eval Dashboard stub (`pages/7_Eval_Dashboard.py`)**

- Placeholder with explanation: "Golden Set evaluation metrics will be populated after Sprint 4"
- Show count of tenders, bidders, verdicts processed so far

---

## Dependency Order

```
T3.1 Console helpers
  ├─> T3.2 Tender Library
  │     └─> T3.3 Criteria Review (Gate 1)
  │           └─> T3.4 Bidder Queue
  │                 └─> T3.5 Verdict Review (Gate 2)
  │
  ├─> T3.6 Seed data (can be built in parallel)
  │
  └─> T3.7 Report stub
      T3.8 Audit Log viewer
      T3.9 Eval Dashboard stub
```

---

## Sprint 3 Definition of Done

- [ ] Streamlit console has all 7 pages functional (not just stubs)
- [ ] Page 1: Upload tender → see extracted criteria count in tender list
- [ ] Page 2 (Gate 1): Review criteria with source quotes, edit fields, lock spec → audit log entry
- [ ] Page 3: Upload bidder files → see verdict badge appear → summary stats
- [ ] Page 4 (Gate 2): Two-pane layout, per-criterion verdicts with evidence, Gate 2 actions for Needs Review
- [ ] Page 6: Audit log viewer with chain verification
- [ ] Seed data produces at least 4 bidders with mixed verdicts
- [ ] `python seed/run_demo.py` populates the full demo state in one command
- [ ] The whole flow works: upload tender → lock criteria → upload bidders → review verdicts

---

## What We Are NOT Doing in Sprint 3

- No PDF bbox highlighting in page preview (nice-to-have, defer if time-constrained)
- No signed PDF report export (Sprint 4)
- No audit replay (Sprint 4)
- No Golden Set or evaluation metrics (Sprint 4)
- No disjunctive deep-dive special UI (show branch data in the verdict card, skip dedicated view)
