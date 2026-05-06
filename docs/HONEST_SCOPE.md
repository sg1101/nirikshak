# Honest Scope — What We Built and What We Deferred

## Delivered in Prototype

- **Thesis architecture**: LLM extracts evidence, deterministic rules decide verdicts, officers approve via HITL gates
- **HITL Gate 1**: Officer reviews, edits, and locks extracted criteria before evaluation proceeds
- **HITL Gate 2**: Officer reviews verdicts, can accept, override, or escalate Needs-Review cases
- **Source-grounded citations**: Every evidence claim references a specific document, page, and quoted text
- **Verifier pass**: Extracted values are cross-checked against the cited page — hallucinated values are caught
- **Hash-chained audit log**: Append-only, tamper-evident, with replay capability
- **Audit drill**: Any verdict can be reproduced from frozen inputs months after the evaluation
- **6 criterion types**: FinancialThreshold, ExperienceCount, StatutoryRegistration, QualityCertification, DocumentChecklist, PolicyCompliance
- **Disjunctive experience rule**: Handles "3 at 40% OR 2 at 60% OR 1 at 80%" with all branches evaluated and stored
- **Verdict-level accuracy reporting**: Honest metrics with test set size and explicit caveats
- **Needs-Review fraction**: System surfaces ambiguity instead of silently disqualifying
- **Signed PDF report**: Consolidated evaluation report with digital signature block

## Deferred to Phase 2

| Feature | Reason |
|---------|--------|
| Joint Venture aggregation rules | Complex edge case; requires JV-specific document parsing |
| Forgery / image-tampering detection | Requires forensic image analysis; out of scope for evaluation prototype |
| Indic language coverage beyond Hindi | PaddleOCR supports Hindi; other Indic scripts route to Needs Review |
| Hierarchical multi-page balance-sheet parsing | Simple typed balance sheets supported; complex tables route to Needs Review |
| Production-grade React console | Streamlit is sufficient for prototype; React for production |
| True DSC signing with CCA-licensed certificate | Self-signed with explanation; production requires CCA DSC |
| On-prem LLM serving | Using cloud API for prototype; swap path documented for Qwen2.5-VL on-prem |
| Multi-tenant deployment, RBAC, SSO | Single-tenant prototype; production needs full auth |
| Live CPPP API integration | No access; using redacted PDFs |

## Why This Matters

Calling out what is deferred is a feature, not a bug. Government procurement systems must be honest about their limitations. A system that silently claims to handle everything is less trustworthy than one that explicitly says "here is what I handle, here is what I don't, and here is what I flag for a human."
