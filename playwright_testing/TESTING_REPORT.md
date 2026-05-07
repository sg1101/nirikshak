# Nirikshak — E2E Testing + UI Audit Report

**Date:** 2026-05-07  
**Tester:** Playwright automated E2E + deep DOM inspection  
**Test Tender:** "HQ Barracks Renovation Tender" (₹75 Cr, CRPF South Zone HQ Hyderabad)  
**Bidders Tested:** 3 (Arun Builders, Sharma Infrastructure, Metro Construction)

---

## 1. Executive Summary

**Functional: ✅ PASS** — Core pipeline works correctly. 100% verdict accuracy (6 bidders, 22 criteria). 71/71 unit tests pass. Audit chain valid.

**UI Quality: ⚠️ NEEDS WORK** — 18 issues found. 7 are critical (visible only on screenshots, not in code review). The sidebar has invisible text, Streamlit chrome leaks through, Material Icons render as raw text, and HTML artifacts appear on the home page.

---

## 2. Functional Test Results

### TC-1: Tender Upload ✅ → 4 criteria extracted
### TC-2: Criteria Lock ✅ → Immutable, timestamped, hashed
### TC-3: 3 Bidders Processed ✅

| Bidder | Verdict | DOC-001 | DOC-002 | REG-001 | EXP-001 |
|--------|:---:|:---:|:---:|:---:|:---:|
| Arun Builders (3 docs) | ✅ Eligible | ✅ | ✅ | ✅ | ✅ 3 works |
| Sharma Infra (3 docs) | ✅ Eligible | ✅ | ✅ | ✅ | ✅ 2 works |
| Metro Construction (2 docs) | ❌ Not Eligible | ❌ Missing | ❌ Missing | ✅ | ✅ 1 work |

### TC-4: Verdict Review ✅ — Zero silent disqualifications
### TC-5: Report Export ✅ — 3-page signed PDF (5,447 bytes)
### TC-6: Audit Log ✅ — 58 entries, chain valid, filter works
### TC-7: Eval Dashboard ✅ — 100% accuracy (6 bidders, 22 criteria)
### Unit Tests ✅ — 71/71 passed

---

## 3. UI Audit — 18 Issues Found

Screenshots are in `deep_screenshots/`. Each issue references the screenshot where it's visible.

---

### 🔴 CRITICAL — Visible to End Users, Breaks Professional Appearance

---

#### Issue 1: "streamlit app" text visible in sidebar and main content

**Screenshots:** `deep_screenshots/01_home_dashboard.png`, all others  
**Severity:** 🔴 Critical  
**Root cause:** Streamlit's default chrome renders "streamlit app" as the top navigation text. The CSS `header {visibility: hidden;}` in `theme.py:39` hides the toolbar header but does not hide this text when it renders inside the sidebar. The text is at the very top of every page — it's the first thing users see.

**Actual text found on page:** `"streamlit app"` appears as the very first line in both the sidebar and main content area.

**Fix:**
```css
/* In theme.py inject_global_css(), add: */
[data-testid="stSidebarNav"] {display: none;}
button[kind="header"] {display: none;}
```

Or in `streamlit_app.py`:
```python
st.set_page_config(page_title="Nirikshak", page_icon="⚖️", layout="wide")
```
Wait — `page_title` is already set. The issue is Streamlit's own sidebar nav component. Adding `st.markdown` with CSS to hide `[data-testid="stSidebarNavItems"]` would fix this.

---

#### Issue 2: White-strip inputs — Officer Email and Active Tender values invisible

**Screenshots:** `deep_screenshots/01_home_dashboard.png` (check sidebar), all others  
**Severity:** 🔴 Critical  
**Root cause:** In `theme.py:73-75`:
```css
[data-testid="stSidebar"] * {
    color: white !important;
}
```
This wildcard `*` selector forces `color: white !important` on ALL child elements inside the sidebar — **including the `<input>` and `<select>` elements**. Streamlit input fields have transparent or light backgrounds by default. White text on a light background = invisible.

The officer email `officer1@crpf.gov.in` (set in `helpers.py:44`) and the Active Tender selectbox value (`helpers.py:61`) are rendered with white text on transparent backgrounds — they appear as **blank white strips**.

**Evidence from DOM:**
```
officerInputColor: "rgb(255, 255, 255)"
officerInputBg:  "rgba(0, 0, 0, 0)"  ← transparent
tenderInputColor: "rgb(255, 255, 255)"
tenderInputBg:   "rgba(0, 0, 0, 0)"  ← transparent
tenderInputValue: ""                  ← empty — user can't see what's selected
```

**Fix:**
```css
/* Replace the wildcard selector with targeted rules */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] select,
[data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"] {
    color: #2C3E50 !important;
    background: white !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] input::placeholder {
    color: #95A5A6 !important;
}
```

---

#### Issue 3: Browser tab shows "Streamlit" not "Nirikshak"

**Screenshots:** Browser tab in all screenshots  
**Severity:** 🔴 Critical  
**Root cause:** `streamlit_app.py:6-11` sets `page_title="Nirikshak"` but when navigating to subpages (`pages/1_Tender_Library.py`, etc.), the page config is **not re-declared**. Streamlit multipage subpages inherit the **default** title "Streamlit" because the main page's config only applies to the main page. There is also no `.streamlit/config.toml`.

**Fix:** Create `.streamlit/config.toml`:
```toml
[client]
showSidebarNavigation = false

[browser]
gatherUsageStats = false
```

Add `st.set_page_config(page_title="Nirikshak", ...)` as the first Streamlit call in every subpage file (pages/1_ through pages/7_).

---

#### Issue 4: Material Icons text leaked as visible characters

**Screenshots:** `deep_screenshots/01_home_dashboard.png` (sidebar area), `02_tender_library`  
**Severity:** 🔴 Critical  
**Evidence from DOM:**
- `"keyboard_double_arrow_left"` — visible text at top of main content area
- `"keyboard_arrow_down"` — visible near expandable sections
- `"keyboard_arrow_right"` — visible near collapsed sections

**Root cause:** Streamlit renders `<span class="material-symbols-outlined">keyboard_double_arrow_left</span>` for the sidebar collapse button. These use Google's Material Symbols font. When the font fails to load (no internet, local dev), the browser renders the **raw text** of the icon name instead of the icon glyph. The CSS in `theme.py` never hides or styles this element.

**Fix:**
```css
/* Hide the sidebar collapse button entirely */
[data-testid="stSidebarCollapseButton"] {display: none !important;}
/* Or, ensure the text is not visible when icon font fails */
.material-symbols-outlined {font-size: 0 !important; overflow: hidden;}
```

---

#### Issue 5: Raw HTML code block visible on home page

**Screenshots:** `deep_screenshots/01_home_dashboard.png` (look for the code block with green #27AE60)  
**Severity:** 🔴 Critical  
**Evidence from DOM:**
```
<pre> tag visible with content: "">\n        2. Review Criteria\n    </div>\n    <div style=\"color:#27AE60; font-size:1.2rem;\">&#9654;</div>..."
<code> tag visible with same content, parent data-testid="stCode"
```

**Root cause:** The `pipeline_step()` function in `theme.py:205-227` generates HTML strings. When `st.markdown(..., unsafe_allow_html=True)` is called in `streamlit_app.py:70-76`, under certain conditions Streamlit renders the HTML as a **code block** instead of executing it. This happens when the HTML string contains unescaped characters or when Streamlit's markdown parser misinterprets inline styles with special characters.

Specifically, the `&#9654;` (▶) character in `pipeline_step()` line 225 combined with the inline style `style="color:{bg}; font-size:1.2rem;"` on line 225 with closing `</div>` on the next line creates a malformed HTML fragment that Streamlit's sanitizer rejects as potentially unsafe, falling back to rendering it as a code block.

**Fix:** Move all HTML construction into a single well-formed string without newline breaks inside attribute values. Or use Streamlit's native `st.container()` + `st.columns()` instead of raw HTML injection for the pipeline visualization:
```python
# Replace the raw HTML pipeline with native Streamlit columns
cols = st.columns(len(steps))
for i, (col, step) in enumerate(zip(cols, steps)):
    with col:
        st.button(step['name'], disabled=not step.get('active'))
```

---

#### Issue 6: Deploy button, hamburger menu, and "open" text visible

**Screenshots:** `deep_screenshots/01_home_dashboard.png` (top-right area), all others  
**Severity:** 🔴 Critical  
**Evidence:** "open" text found in sidebar, "Deploy" is a known Streamlit built-in button.

**Root cause:** `theme.py:38-41` tries to hide Streamlit chrome:
```css
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}
```
But `#MainMenu` and `.stDeployButton` may use different class names or data-testids in the installed Streamlit version. `header {visibility: hidden;}` hides the element but **still reserves its space** in the layout. This leaves a 60px tall empty white bar at the top of the page.

**Evidence from DOM:**
```
headerVisible: true
headerHeight: 60
```

**Fix:**
```css
/* Use display:none instead of visibility:hidden to reclaim space */
header[data-testid="stHeader"] {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
button[kind="header"] {display: none !important;}
/* Target deploy button by multiple possible selectors */
[data-testid="stDeployButton"], .stDeployButton, [data-testid="baseButton-header"] {
    display: none !important;
}
```

---

#### Issue 7: Double navigation — links appear in both sidebar AND main content

**Screenshots:** `deep_screenshots/01_home_dashboard.png`  
**Severity:** 🟡 Medium  
**Evidence:** Main content starts with:
```
"streamlit app\n\nTender Library\n\nCriteria Review\n\nBidder Queue\n\nVerdict Review\n\nReport Export\n\nAudit Log\n\nEval Dashboard"
```
Then the actual app content begins. The sidebar also shows the same links.

**Root cause:** Streamlit's default multipage behavior renders page navigation links in the main content area when `position="hidden"` is not set in `st.navigation()` or when using the older file-based multipage pattern. The custom sidebar renders its own title "⚖️ Nirikshak" and navigation, but Streamlit's default nav still appears above it.

**Fix:** Add to `inject_global_css()`:
```css
[data-testid="stSidebarNav"] {display: none !important;}
[data-testid="stSidebarNavItems"] {display: none !important;}
```
Or use `st.navigation()` with `position="hidden"` if upgrading the multipage pattern.

---

### 🟡 MEDIUM — Affects Usability or Demo Readiness

---

#### Issue 8: Home page mixes dashboard + Criteria Review content

**Screenshots:** `deep_screenshots/01_home_dashboard.png`  
**Severity:** 🟡 Medium  
**Root cause:** The home page (`streamlit_app.py`) renders a proper dashboard (hero, metrics, pipeline, quick actions). However, `render_sidebar()` at line 20 selects the active tender and populates session state. In certain page load scenarios, Streamlit re-runs the page and renders Criteria Review content (from the previously visited page) mixed in with the dashboard. The `streamlit_app.py` code has no Criteria Review rendering, so this is a Streamlit session-state carryover bug.

**Fix:** Ensure each page resets its own content area. Use session state keys to track which page is active and prevent cross-page content leakage.

---

#### Issue 9: Sidebar background is transparent, not navy gradient

**Screenshots:** `deep_screenshots/01_home_dashboard.png` (sidebar area)  
**Severity:** 🟡 Medium  
**Evidence from DOM:**
```
sidebarBg: "rgba(0, 0, 0, 0)"  ← transparent, NOT the navy gradient from CSS
```

**Root cause:** `theme.py:70-72` sets:
```css
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B4F72 0%, #154360 100%);
}
```
But the computed style shows `rgba(0,0,0,0)` — the CSS is not taking effect. This may be because Streamlit's own CSS overrides the background, or the page loads before `inject_global_css()` is called. Without the dark background, white-colored text (set by the wildcard `*` rule) is invisible against the default light/transparent sidebar.

**Fix:** Use higher specificity:
```css
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #1B4F72 0%, #154360 100%) !important;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B4F72 0%, #154360 100%) !important;
}
```

---

#### Issue 10: Date input shows verbose accessibility instructions

**Screenshots:** `deep_screenshots/02_tender_library.png`  
**Severity:** 🟡 Medium  
**Visible text:** `"Press the down arrow key to interact with the calendar and select a date. Press the escape button to close the calendar. Selected date is 2026/05/07. Select the second date."`

This is Streamlit's default date input instruction text. It's 4 lines of accessibility text that clutters the form.

**Fix:** Hide with CSS:
```css
[data-testid="stDateInput"] .stMarkdown {display: none;}
```
Or use a custom date input component.

---

#### Issue 11: Date input defaults to today's date, not empty

**Screenshots:** `deep_screenshots/02_tender_library.png`  
**Severity:** 🟡 Medium  
The bid submission date should be blank so the user consciously enters a date. Defaulting to today (2026-05-07) could cause accidental submissions with wrong dates.

**Fix:** Set `value=None` on the date input in Tender Library page code, or set a default like `datetime.date.today() + datetime.timedelta(days=30)`.

---

#### Issue 12: "upload" text appears as orphaned element near file uploader

**Screenshots:** `deep_screenshots/02_tender_library.png`  
**Severity:** 🟡 Medium  
**Visible text:** The word "upload" appears as a separate text element below "Upload Tender PDF" and above the drag-drop zone. This is a Streamlit file uploader quirk where the button label renders as visible text.

**Fix:** This is likely from `st.file_uploader()` with text "Upload" — the label "Upload Tender PDF" is one element and the button label "upload" (lowercase) is another. Use `label="Upload Tender PDF"` and set the button text via Streamlit's `help` or a custom approach.

---

### 🟢 MINOR — Polish and Enhancement Opportunities

---

#### Issue 13: Home page hero banner has no CTA button

**Screenshots:** `deep_screenshots/01_home_dashboard.png`  
**Severity:** 🟢 Minor  
The hero banner says "Nirikshak — AI extracts evidence. Rules decide verdicts. Officers approve." but has no button to get started. The "Upload Tender" button is below the fold.

**Fix:** Add a CTA button inside the hero banner:
```python
st.markdown(f"""
<div style="...">
    <h1>Nirikshak</h1>
    <p>AI extracts evidence. Rules decide verdicts. Officers approve.</p>
    <a href="/Tender_Library" style="...">Get Started →</a>
</div>
""", unsafe_allow_html=True)
```

---

#### Issue 14: Status cards show aggregate numbers across ALL tenders

**Screenshots:** `deep_screenshots/01_home_dashboard.png`  
**Severity:** 🟢 Minor  
The dashboard shows "Tenders: 3", "Bidders: 6", "Eligible: 5" — these are summary counts across ALL tenders, not the currently selected tender. Users may misinterpret these as being specific to the active tender.

**Fix:** Either label them clearly as "Total (All Tenders)" or scope them to the active tender only.

---

#### Issue 15: Pipeline always shows Step 5 (Export Report) as inactive

**Screenshots:** `deep_screenshots/01_home_dashboard.png`  
**Severity:** 🟢 Minor  
The pipeline visualization in `streamlit_app.py:70-76` always sets `"done": False` for step 5 (Export Report). It should check if a report has been generated.

**Fix:** Check for `report_finalized` audit entries for the active tender.

---

#### Issue 16: "How Nirikshak Works" section shown every time

**Screenshots:** `deep_screenshots/01_home_dashboard.png`  
**Severity:** 🟢 Minor  
This educational section appears every time the dashboard loads. Returning users don't need it. It takes up vertical space and pushes the metrics/actions down.

**Fix:** Collapse it by default after first view, or move it to a dedicated help page.

---

#### Issue 17: Evidence JSON displayed as raw JSON blobs

**Screenshots:** `deep_screenshots/05_verdict_review.png`  
**Severity:** 🟢 Minor  
Evidence claims display raw JSON like:
```json
{"document_name": "EMD / Bid Security", "present": false, "signed": false, "dated": false}
```
This is functional but not presentation-quality. Formatting as key-value table would be more professional.

**Fix:** Parse the JSON and render as a styled table:
```python
import json
data = json.loads(evidence_json)
for key, value in data.items():
    st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
```

---

#### Issue 18: Page transitions show full re-renders (no skeleton loading)

**Screenshots:** All navigation transitions  
**Severity:** 🟢 Minor  
Navigating between pages causes a visible "flash" — the page goes blank, then content re-renders. Streamlit is inherently full-page reload, but a loading indicator between pages would help.

**Fix:** Use `st.spinner()` or `st.status()` during page transitions, or Streamlit's `st.navigation()` with `position="hidden"` to maintain sidebar state across pages.

---

## 4. Root Cause Map

```
theme.py
├── line 39:  header {visibility: hidden;}         → leaves 60px empty space (Issue 6)
├── line 41:  .stDeployButton {display: none;}      → selector may not match (Issue 6)
├── line 70-72: sidebar bg gradient                 → not applying (Issue 9)
├── line 73-75: [data-testid="stSidebar"] * {...}   → WHITE TEXT ON INPUTS (Issues 2, 9)
│
helpers.py
├── line 44: text_input("Officer Email")            → invisible text (Issue 2)
├── line 61: selectbox("Active Tender")             → invisible text (Issue 2)
│
theme.py pipeline_step()
├── line 205-227: raw HTML with &#9654;             → code block leak (Issue 5)
│
streamlit_app.py
├── line 6-11: set_page_config("Nirikshak")         → only on home page (Issue 3)
├── line 70-76: pipeline_step()                     → renders as code block (Issue 5)
├── line 75: "done": False                          → always inactive (Issue 15)
│
All subpages
├── Missing: set_page_config()                      → browser tab "Streamlit" (Issue 3)
│
Streamlit chrome (not in codebase)
├── Material Icons <span>                           → raw text leak (Issue 4)
├── "streamlit app" navigation text                 → visible on every page (Issue 1)
├── Deploy button, hamburger menu                   → visible (Issue 6)
└── Sidebar collapse button                         → visible text (Issue 4)
```

---

## 5. Fix Priority Matrix

| Priority | Issue # | Fix Effort | Impact |
|----------|---------|:---:|:---:|
| 🔴 P0 | #2: Invisible inputs | 10 min | Blocks all sidebar interaction |
| 🔴 P0 | #1: "streamlit app" text | 5 min | First thing every user sees |
| 🔴 P0 | #3: Tab title "Streamlit" | 5 min | Unprofessional in screenshots/demos |
| 🔴 P1 | #4: Material Icons text leak | 5 min | Visible on every page |
| 🔴 P1 | #6: Empty header bar + Deploy | 5 min | 60px wasted space |
| 🔴 P1 | #5: HTML code block on home | 30 min | Broken pipeline visualization |
| 🟡 P2 | #7: Double navigation | 5 min | Cluttered layout |
| 🟡 P2 | #9: Sidebar bg not applying | 10 min | Root cause of invisible text |
| 🟡 P2 | #10: Date input instructions | 2 min | Form clutter |
| 🟢 P3 | #11-18: Polish items | 2-30 min each | Demo quality |

---

## 6. Complete Screenshot Index

```
playwright_testing/
├── TESTING_REPORT.md               ← This file
├── deep_screenshots/               ← Deep DOM inspection (all 8 pages)
│   ├── 01_home_dashboard.png       ← Issues: 1,2,5,6,7,8,9,13,14,15,16
│   ├── 02_tender_library.png       ← Issues: 1,2,4,10,11,12
│   ├── 03_criteria_review.png      ← Issues: 1,2,4
│   ├── 04_bidder_queue.png         ← Issues: 1,2
│   ├── 05_verdict_review.png       ← Issues: 1,2,17
│   ├── 06_report_export.png        ← Issues: 1,2
│   ├── 07_audit_log.png            ← Issues: 1,2
│   └── 08_eval_dashboard.png       ← Issues: 1,2
├── v2_screenshots/                 ← Previous test run
│   └── ... (12 screenshots)
└── *.png                           ← Original v1 screenshots
```

---

## 7. Conclusion

**Functional quality:** Excellent. The core pipeline works correctly end-to-end with 100% verdict accuracy. Every "Not Eligible" has a cited reason. The audit chain is tamper-evident.

**UI quality:** Needs 1-2 hours of focused fixes before it's demo-ready. The 7 critical issues are all CSS/configuration problems with straightforward fixes. The Invisible sidebar inputs (Issue #2) and "streamlit app" branding leak (Issue #1) are the most impactful — they make the app look unfinished and block basic user interaction.

**Recommendation:** Fix all P0 and P1 issues (estimated 1 hour total), then re-test. The underlying system is solid.
