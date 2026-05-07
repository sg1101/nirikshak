# UI Redesign Plan — Demo-Ready Streamlit Console

## Current Problems

Looking at the screenshots, the UI has these issues for a demo:

1. **No visual identity** — plain white background, no branding, no color theme
2. **Home page is just a list** — no visual hierarchy, no workflow guidance
3. **Verdict cards are flat** — no color-coded status, verdicts don't pop visually
4. **Sidebar is cluttered** — officer email + tender selector + branding all jumbled
5. **No status pipeline visualization** — can't see at-a-glance where you are in the flow
6. **Tables are plain** — no row highlighting, no color for pass/fail
7. **Bidder Queue lacks visual impact** — no verdict distribution chart
8. **Evidence sections feel raw** — JSON dumps, no structured presentation

## Design Approach

Use Streamlit's custom CSS injection (`st.markdown` with `unsafe_allow_html`) + better component choices. Stay within Streamlit's capabilities — no React components.

**Color palette:**
- Primary: `#1B4F72` (deep navy — government authority)
- Success: `#27AE60` (green — eligible)
- Danger: `#E74C3C` (red — not eligible)
- Warning: `#F39C12` (amber — needs review)
- Surface: `#F8F9FA` (light gray backgrounds)
- Accent: `#2C3E50` (dark headers)

---

## Task Breakdown

### T-UI.1 — Global theme + CSS injection

Create `console/theme.py` with reusable CSS:
- Custom font (system sans-serif stack)
- Colored metric cards with icons
- Verdict badges as colored pills (not just emoji)
- Styled containers with left-border color accents
- Hide Streamlit's deploy button and hamburger menu for clean demo
- Custom sidebar styling (dark background, white text)

### T-UI.2 — Home page redesign

Current: title + 3 plain metrics + text list
Redesigned:
- Hero banner with gradient background and thesis tagline
- 4 metric cards in colored containers (Tenders, Bidders, Eligible, Needs Review)
- Pipeline status: visual 5-step flow (Upload → Review → Evaluate → Verdict → Report) with current step highlighted
- Quick action buttons: "Upload Tender" and "Review Verdicts"

### T-UI.3 — Tender Library redesign

Current: expander with form + plain list
Redesigned:
- Upload form in a styled card with clear CTA
- Tender cards with colored left border (green=locked, amber=draft)
- Each card shows: title, authority, value, criteria count, status pill
- Estimated value formatted prominently

### T-UI.4 — Criteria Review (Gate 1) redesign

Current: plain cards with JSON parameters
Redesigned:
- Stepper header showing Gate 1 status
- Criterion cards with colored left-border by type (financial=blue, registration=purple, experience=orange, etc.)
- Parameters shown as key-value tags, not raw JSON
- Source citation in a styled quote block with page badge
- Lock button as a prominent action bar at bottom with warning styling

### T-UI.5 — Bidder Queue redesign

Current: form + plain list + basic metrics
Redesigned:
- Verdict distribution as a horizontal stacked bar (green/red/amber)
- Bidder cards with large verdict pill badge
- Upload form collapsed by default when bidders exist
- Each bidder card shows: name, verdict badge, doc count, submission time
- Color-coded borders: green=eligible, red=not eligible, amber=needs review

### T-UI.6 — Verdict Review (Gate 2) redesign — THE DEMO SHOWPIECE

Current: two columns, flat criterion cards
Redesigned:
- Left panel: bidder list as styled cards with verdict color
- Right panel: bidder header with large colored verdict banner
- Per-criterion cards with:
  - Colored status stripe (green/red/amber) on the left
  - Rule name as a styled code badge
  - Reason in a highlighted callout box
  - Evidence section with structured table (not JSON dump)
  - Confidence as a colored progress bar (green >85%, amber 50-85%, red <50%)
  - Verifier badge: green checkmark or red warning
- Gate 2 action buttons styled as a prominent action bar

### T-UI.7 — Audit Log redesign

Current: plain table + dropdown
Redesigned:
- Chain status banner at top (green "Chain Valid" or red "Tampered")
- Timeline view instead of raw table — each entry as a timeline node
- Color-coded by action type
- Replay button styled prominently on rule_fired entries
- Entry detail in a styled modal/expander

### T-UI.8 — Eval Dashboard redesign

Current: plain metrics
Redesigned:
- Three-layer cards with visual gauges
- Verdict agreement shown as a confusion-matrix style grid
- Needs-review fraction as a gauge with zones (too low / optimal / too high)
- Honest scope disclaimer in a styled info banner

---

## Implementation Order

1. **T-UI.1** — Theme (everything else depends on it)
2. **T-UI.2** — Home (first thing judges see)
3. **T-UI.6** — Verdict Review (demo centerpiece)
4. **T-UI.5** — Bidder Queue (second most viewed)
5. **T-UI.4** — Criteria Review
6. **T-UI.3** — Tender Library
7. **T-UI.7** — Audit Log
8. **T-UI.8** — Eval Dashboard
