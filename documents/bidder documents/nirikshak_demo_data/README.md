# Nirikshak Demo Data

Synthetic bidder document packets for the Nirikshak prototype demo.

## What's in this package

```
nirikshak_demo_data/
├── README.md                          ← you are here
├── generator/
│   ├── generate_bidder.py             ← main generator (YAML → 13+ PDFs)
│   ├── apply_scan_effect.py           ← turns clean PDFs into scan-look PDFs
│   ├── templates/                     ← Jinja2 HTML templates for each document type
│   └── static/styles.css
├── bidder_configs/
│   ├── tender_construction.yaml       ← THE demo's primary tender (₹50 cr CRPF construction)
│   ├── bidder_01_eligible.yaml        ← reference bidder (used as template for variants)
│   ├── bidder_02_not_eligible_turnover.yaml
│   └── bidder_K_disjunctive.yaml      ← the 80/60/40 disjunctive scenario (PRD §7)
└── output/
    ├── bidder_01/                     ← 17 PDFs — clean, typed, fully eligible reference
    ├── bidder_02/                     ← 16 PDFs — fails FIN-001 (turnover ₹2.82 cr < ₹5 cr)
    └── bidder_K/                      ← 17 PDFs — disjunctive 80/60/40 scenario, all branches pass
```

**Total: 50 PDFs across 3 bidders.**

## Why these three bidders cover the demo

| Bidder | Verdict | What it demonstrates |
|---|---|---|
| **01** | Eligible | Clean reference case. All criteria met, all documents typed. Shows the "happy path" — extraction, verifier, verdict, signed report all working end-to-end. |
| **02** | NotEligible | The cited-failure case. Turnover ₹2.82 cr avg (< ₹5 cr threshold per FIN-001). System cites failed criterion + value + document + page + rule. |
| **K**  | Eligible (disjunctive) | The wow factor (PRD §7). Five completion claims engineered so all three branches of "3 at 40% OR 2 at 60% OR 1 at 80%" are evaluable. |

This is enough to demonstrate the thesis: **AI extracts evidence, rules decide verdicts, officers approve.** The clean-vs-failed contrast covers segments 2-3 of the demo. Bidder K covers segment 4. The audit drill (segment 5) can use any of the three.

## Bidder K's disjunctive portfolio (PRD §7)

For a ₹50 cr tender, the thresholds are:
- Branch A (≥3 at ≥40% of estimated): ₹20 cr threshold
- Branch B (≥2 at ≥60%): ₹30 cr threshold
- Branch C (≥1 at ≥80%): ₹40 cr threshold

| Claim | Value | Similarity | Branches passed |
|---|---|---|---|
| 1: NTPC Karnataka office + parking | ₹22.5 cr | similar | A only |
| 2: FCI Karnataka logistics yard | ₹18.0 cr | similar | none (below 40%) |
| 3: IAF Yelahanka ops parking | ₹35.0 cr | similar | A & B |
| 4: BIAL cargo parking Phase II | ₹42.0 cr | similar | **A, B, & C** |
| 5: Embassy Manyata multi-level deck | ₹28.0 cr | borderline | needs-review on similarity |

Branch A: claims {1, 3, 4} = 3 ✓ PASS  
Branch B: claims {3, 4} = 2 ✓ PASS  
Branch C: claims {4} = 1 ✓ PASS  
Verdict: **Eligible** (criterion passes if any branch passes)

## How to regenerate

```bash
# Re-generate any bidder
python3 generator/generate_bidder.py \
    --bidder bidder_configs/bidder_01_eligible.yaml \
    --tender bidder_configs/tender_construction.yaml \
    --out output/bidder_01

# Apply scan effect to a clean PDF (severities: light, medium, heavy)
python3 generator/apply_scan_effect.py input.pdf output.pdf --severity heavy
```

## How to add more bidders later

If you want to expand beyond these three:

1. Copy `bidder_configs/bidder_01_eligible.yaml` to a new file
2. Edit fields specific to the new bidder (name, PAN, GSTIN, financials, completion_projects)
3. Run the generator (one line above)

Common variations:

- **NotEligible — turnover:** set `financials.turnover_history` averages below ₹5 cr (see bidder_02)
- **NotEligible — experience:** fewer than 3 entries in `completion_projects`
- **NotEligible — ISO expired:** set `iso.valid_until_long` to a date before submission_date
- **NotEligible — missing GST:** delete the `gstin` field
- **NeedsReview:** run their turnover cert through `apply_scan_effect.py --severity heavy` after generation

## Document types

The 13 HTML templates in `generator/templates/`:

| Document | Template | Pages |
|---|---|---|
| Cover letter / bid form | `cover_letter.html` | 2 |
| Company profile / brochure | `company_profile.html` | 2-3 |
| Audited financial statements | `audited_financials.html` | 2-3 |
| CA-issued turnover certificate | `ca_turnover_cert.html` | 1 |
| GST registration certificate | `gst_certificate.html` | 1 |
| PAN card mockup | `pan_card.html` | 1 |
| EPF + ESI registration | `epf_esi.html` | 2 |
| ISO 9001 certificate | `iso_certificate.html` | 1 |
| EMD bank guarantee | `emd_bank_guarantee.html` | 2 |
| Tender acceptance letter | `tender_acceptance.html` | 1-2 |
| Integrity pact (CVC format) | `integrity_pact.html` | 2-3 |
| CPWD enlistment certificate | `cpwd_enlistment.html` | 1 |
| Completion certificate | `completion_certificate.html` | 1-2 (one per project) |

## Honest scope notes

These are **synthetic** documents. All companies, PANs, GSTINs, bank details,
addresses, and signing officers are fictional. Format and content are designed
to mimic real Indian government tender submissions.

Realistic:
- Government and regulatory document layouts
- PAN format (5 letters + 4 digits + 1 letter)
- GSTIN format (15-character with state code 29 = Karnataka)
- Indian numbering (lakhs, crores) used throughout
- Real procuring authorities referenced (CRPF, CPWD, BSF, BWSSB, etc.)

Intentionally fake:
- All company names, individual names, contact details
- All certificate reference numbers
- All financial figures

This is appropriate for a hackathon prototype demo.
