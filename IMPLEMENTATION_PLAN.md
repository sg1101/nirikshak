# Nirikshak — Implementation Plan

**Timeline:** May 6 – May 15 (10 build days) | **Demo day:** May 16, Bangalore
**Thesis:** AI extracts evidence. Rules decide verdicts. Officers approve.

---

## Sprint Overview

| Sprint | Days | Theme | Exit Criterion |
|--------|------|-------|----------------|
| S1 | 1–3 | Foundation + Core Infrastructure | `docker compose up` works, schemas in DB, audit log writes, PDF ingestion works, Claude client functional, tender understanding extracts criteria |
| S2 | 4–6 | Evidence Extraction + Verdict Engine | All 6 extractors, verifier, verdict engine with all rules incl. disjunctive, bidder-level aggregation |
| S3 | 7–8 | Console + HITL Gates + Integration | Streamlit 7-page app, Gate 1 + Gate 2 functional, all 10 bidders end-to-end, seed data |
| S4 | 9–10 | Audit Replay, Eval, Report, Polish | Signed report, audit drill, Golden Set, eval dashboard, video, docs, submission |

---

## Hard Checkpoints

If we slip, we cut scope, not quality.

| Checkpoint | Deadline | Fallback |
|-----------|----------|----------|
| Tender → criteria extraction works end-to-end | End of Day 3 | Simplify section classifier to regex-only, skip ambiguous-chunk Claude call |
| All 6 extractors + verdict engine produce correct verdicts | End of Day 6 | Drop PolicyCompliance type; simplify Bidder K to 3 claims |
| All 10 bidders end-to-end with UI | End of Day 8 | Drop to 6 bidders (4E/1NE/1NR), still tells the story |
| Replay + report + video | End of Day 10 | Hard-code replay for recording; document as limitation |

---

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| LLM | Claude Sonnet (API) | Structured output, vision, Hindi support |
| OCR | PaddleOCR | English + Hindi, bbox output, open-source |
| PDF | PyMuPDF (fitz) | Fast text + bbox extraction, page rendering |
| Schemas | Pydantic v2 + SQLModel | Type safety, DB round-trip, structured LLM output |
| DB | Postgres 16 + pgvector | Audit log integrity (RULE no-update), future embedding search |
| Console | Streamlit | Fast prototyping, multipage, PDF preview widget |
| API | FastAPI | Clean endpoint layer for console <> backend |
| Infra | Docker Compose | Single `docker compose up` for judges |
| Testing | pytest | Unit + integration |
| Structured LLM | Instructor | Pydantic schema -> Claude structured output |

---

## Risk Mitigations

1. **Claude API rate limits** — Cache all extraction results in Postgres after first run; demo replays from cache
2. **OCR failures on Hindi** — Demo bidders primarily English; Hindi-only as stretch case
3. **Disjunctive off-by-one** — Exhaustive unit tests frozen by Day 6
4. **Replay non-determinism** — Pin model versions, freeze prompts, replay from cached extractions
5. **Network at venue** — Cache everything before Bangalore; demo runs fully from cache
6. **Low Golden Set numbers** — Curate straightforward tenders; harder cases route to Needs Review (honest)

---

Detailed sprint plans live in `SPRINT_PLAN_<N>.md` files.
