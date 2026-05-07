# Nirikshak — 5-Minute Demo Script

**Setup:** All data pre-loaded (tender + 3 bidders already processed). Streamlit console open at http://localhost:8501. Screen recording running.

**Tone:** Speak to a procurement officer or IAS panel — not a developer audience. Focus on the problem, the solution, and why they can trust it. Technical details only where they build trust.

---

## SEGMENT 1: The Problem (0:00 – 0:30)

**[Screen: Home page with hero banner]**

> "Every year, government organisations like CRPF issue hundreds of tenders. For each tender, a committee manually reads through hundreds of pages of bidder documents — checking turnover figures, registration certificates, experience letters — against the tender's eligibility criteria."

> "This process takes days. Two evaluators can reach different conclusions from the same documents. And when an auditor questions a decision months later, there's no structured trail to follow."

> "Nirikshak solves this. Our thesis is simple:"

**[Point to the tagline on screen]**

> "AI extracts evidence. Rules decide verdicts. Officers approve."

> "The AI reads documents. But it never makes the decision — that's deterministic code. And the officer always has the final say."

---

## SEGMENT 2: Upload & Criteria Extraction (0:30 – 1:15)

**[Navigate to: Tender Library]**

> "Let's start with a real CRPF tender — repair and maintenance work at Group Centre Bangalore. This is a 26-page tender document."

**[Show the uploaded tender in the list — already processed]**

> "When an officer uploads this PDF, the system does two things automatically. First, it classifies the document — identifying which pages contain the Notice Inviting Tender, which contain eligibility conditions, which are the Bill of Quantities."

> "Then from the eligibility sections, it extracts structured criteria."

**[Navigate to: Criteria Review page]**

> "Here's what the AI extracted — four eligibility criteria. Each one has a type, a description, and — this is important — the exact quote from the tender and the page number where it found it."

**[Expand one source citation]**

> "The officer doesn't trust the AI blindly. They see the original text, verify it's correct, and can edit anything before locking."

**[Point to the Lock badge]**

> "Once locked, this criteria spec gets a cryptographic hash and an audit log entry. It cannot be changed. Every bidder will be evaluated against exactly this set of criteria."

---

## SEGMENT 3: Bidder Evaluation (1:15 – 2:00)

**[Navigate to: Bidder Queue]**

> "Now the bidders. We've processed three construction companies — each submitted 15 to 17 documents. GST certificates, EMD receipts, tender acceptance letters, completion certificates."

**[Show the summary metrics — Eligible / Not Eligible counts]**

> "The system classified each document, extracted evidence for each criterion, and ran the verdict rules. Two bidders are Eligible. One is Not Eligible."

> "Notice: Metro Construction is marked Not Eligible. Let's see why."

**[Click "Review Verdicts" on Metro Construction]**

---

## SEGMENT 4: Verdict Review — The Trust Layer (2:00 – 3:00)

**[On: Verdict Review page, Metro Construction selected]**

> "This is the heart of Nirikshak. Every verdict is explainable."

**[Point to the red Not Eligible banner]**

> "Metro Construction failed on two criteria: DOC-001 and DOC-002. The system tells us exactly why."

**[Point to DOC-001 card]**

> "Required document — EMD or Bid Security — not found in submission. That's the rule that fired: DocumentChecklistRule. No EMD receipt in their uploaded files."

> "Now, critically — the system did NOT silently disqualify them. It shows the rule, the reason, and the evidence it checked. The officer can verify this."

**[Switch to Arun Builders — Eligible]**

> "Compare with Arun Builders — all four criteria green. GST certificate found and verified. Completion certificates extracted with values and dates."

**[Expand Evidence section on EXP-001]**

> "Three completed works extracted — each with the contract value, the completion date, and a confidence score. The verifier cross-checked: did the extracted value actually appear on the cited page? Green checkmark means yes."

> "This is the key design decision: the AI extracts, but deterministic Python code decides. There is no LLM in the verdict layer. Every rule is traceable, reproducible, and auditable."

---

## SEGMENT 5: The Audit Trail (3:00 – 3:45)

**[Navigate to: Audit Log]**

> "Every action in Nirikshak is logged in a tamper-evident audit chain."

**[Click Verify Chain Integrity]**

> "Each entry has a cryptographic hash that depends on the previous entry — like blockchain, but simpler. If anyone modifies a past entry, the chain breaks. We just verified it's intact."

**[Show the entry list — filter to "rule_fired"]**

> "We can see every verdict the system produced: which rule fired, which bidder, which criterion, what the result was."

**[Select a rule_fired entry, click Replay]**

> "This is the audit drill. Months from now, a CAG auditor asks: 'Why did this bidder fail this criterion?' We click Replay. The system re-loads the locked criteria, re-loads the bidder's documents by their content hash, re-runs the exact same rule, and — green checkmark — produces the same verdict."

> "The verdict is reproducible from frozen inputs. This is what makes the system suitable for formal government procurement."

---

## SEGMENT 6: Report & Metrics (3:45 – 4:30)

**[Navigate to: Report Export]**

> "The officer can export a signed PDF report — tender summary, per-bidder verdicts with reasons, criteria spec hash, and a digital signature."

**[Click Generate & Download]**

> "This is the regulated artefact. A procurement committee can sign off on this."

**[Navigate to: Eval Dashboard]**

> "Finally, transparency about what the system can and cannot do."

**[Show the three-layer metrics]**

> "We measure accuracy at three layers: OCR quality, field-level extraction, and verdict-level agreement against hand-labeled ground truth."

**[Point to the Needs-Review fraction]**

> "This number tells the honest story. If it's too low, the system is over-confident — making calls it shouldn't. If it's too high, it's dodging hard cases. We aim for the range where genuine ambiguity concentrates."

**[Point to the Scope & Caveats section]**

> "We explicitly call out what's measured, what's not, and what production calibration would require. No inflated headline numbers."

---

## SEGMENT 7: Closing (4:30 – 5:00)

**[Navigate back to: Home page]**

> "Nirikshak is built around a trustworthiness constraint, not an accuracy headline."

> "AI reads the documents — but every extraction is verifiable. Deterministic rules make the decisions — not the model. Officers review and approve — the system never acts alone. And the audit log — not the model accuracy — is the regulated artefact this system stakes its credibility on."

> "Three layers of trust: AI extracts. Rules decide. Officers approve."

**[Hold on the home page hero banner for 3 seconds]**

---

## Key Points to Hit (cheat sheet)

If the panel asks questions, these are the strongest talking points:

| Question | Answer |
|----------|--------|
| "How do you prevent AI hallucination?" | Every extracted value is cross-checked against the cited page by the verifier. The LLM never makes the eligibility decision — only extracts. |
| "What if the system is wrong?" | Every uncertain case routes to Needs Review. No silent disqualification. The officer always has the final say at Gate 2. |
| "Can this be audited?" | Hash-chained audit log with replay capability. Any verdict can be reproduced from frozen inputs months later. |
| "Why not just use ChatGPT?" | We separated extraction from decision-making. The verdict engine is pure Python — no LLM. This makes it deterministic, reproducible, and auditable. A chat interface can't guarantee any of that. |
| "What about scanned documents?" | PaddleOCR for scanned PDFs, Claude Vision for photographs. If OCR confidence is low, the claim routes to Needs Review instead of guessing. |
| "Is this production-ready?" | This is a prototype. Production would need CCA-licensed digital signatures, on-premise LLM deployment, multi-tenant auth, and ~200 real evaluations to calibrate thresholds. We document all of this in HONEST_SCOPE.md. |
| "How long does evaluation take?" | Criteria extraction: ~30 seconds. Per-bidder evaluation: 5-8 minutes (sequential LLM calls). Verdict rules: instant. Production would parallelize the LLM calls. |

---

## Pre-Demo Checklist

- [ ] API running at http://localhost:8000 (check `/api/health`)
- [ ] Streamlit running at http://localhost:8501
- [ ] At least 1 tender uploaded with locked criteria
- [ ] At least 3 bidders evaluated (mix of Eligible / Not Eligible)
- [ ] Audit log has entries (check Audit Log page)
- [ ] Screen recording tool ready
- [ ] Browser zoom at 90-100% (fits all content without scrolling)
- [ ] Incognito/clean browser tab (no stale session state)
