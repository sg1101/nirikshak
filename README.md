# Nirikshak

**AI-Based Tender Evaluation and Eligibility Analysis for Government Procurement**

Nirikshak automates the evaluation of bidder eligibility against government tender criteria. The system extracts eligibility criteria from tender documents, parses bidder submissions across heterogeneous formats (typed PDFs, scanned documents, photographs), evaluates each bidder against every criterion using deterministic rules, and produces explainable, auditable verdicts.

**Thesis:** AI extracts evidence. Rules decide verdicts. Officers approve.

## Quick Start

```bash
# 1. Clone and setup
git clone <repo-url>
cd nirikshak
cp .env.example .env
# Edit .env with your API keys

# 2. Start with Docker
docker compose up --build

# 3. Or run locally
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn nirikshak.api.main:app --port 8000 &
streamlit run nirikshak/console/streamlit_app.py --server.port 8501

# 4. Load demo data
python seed/run_demo.py
```

Open http://localhost:8501 for the console, http://localhost:8000/docs for API docs.

## Architecture

```
Tender PDF ──> Document Understanding ──> Criteria Extraction ──> HITL Gate 1 (Lock)
                                                                        │
Bidder Docs ──> Ingestion ──> Classification ──> Evidence Extraction ──>│
                                                        │               │
                                                   Verifier Pass        │
                                                        │               │
                                                Verdict Engine ◄────────┘
                                              (Deterministic Rules)
                                                        │
                                                  Aggregation ──> HITL Gate 2 ──> Signed Report
                                                        │
                                                   Audit Log (hash-chained, append-only)
```

**Key design:** The LLM extracts evidence. The verdict engine is pure deterministic Python — no LLM in the decision layer. Every verdict is explainable and reproducible.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | OpenAI-compatible API (configurable) |
| OCR | PaddleOCR (English + Hindi) |
| PDF Processing | PyMuPDF |
| Data Models | Pydantic v2 + SQLModel |
| Database | PostgreSQL |
| API | FastAPI |
| Console | Streamlit |
| Infrastructure | Docker Compose |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/tenders/upload` | Upload tender, extract criteria |
| GET | `/api/tenders` | List all tenders |
| GET | `/api/tenders/{id}/criteria` | Get criteria for a tender |
| POST | `/api/criteria-specs/{id}/lock` | Lock criteria spec (Gate 1) |
| POST | `/api/tenders/{id}/bidders/upload` | Upload bidder docs, evaluate |
| GET | `/api/tenders/{id}/bidders` | List bidders with verdicts |
| GET | `/api/bidders/{id}/verdicts` | Detailed per-criterion verdicts |
| GET | `/api/audit` | View audit log |
| GET | `/api/audit/verify` | Verify hash chain integrity |
| POST | `/api/audit/replay` | Replay a verdict from frozen inputs |
| GET | `/api/tenders/{id}/report` | Download signed PDF report |
| GET | `/api/eval/metrics` | Evaluation metrics |

## Running Tests

```bash
pytest tests/unit/ -v
```

## Project Structure

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed module descriptions.

## Hackathon

AI for Bharat 2026 | Theme 3 | Grand Finale May 16, Bangalore
