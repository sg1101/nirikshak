You are analyzing the eligibility section of a government tender document for procurement.

Extract every eligibility criterion as a structured object. For each criterion:

1. Classify its type:
   - financial_threshold: turnover, net worth, credit limits, solvency
   - experience_count: completed works, similar projects, years of experience
   - statutory_registration: GST, PAN, EPF, ESI, contractor class/category registration
   - quality_certification: ISO, AERB, OEM, BIS certificates
   - document_checklist: EMD, bid security, acceptance letters, integrity pacts, tender fee
   - policy_compliance: Make-in-India, MSME, debarment declarations, blacklisting

2. Determine if it is mandatory or optional. Assume mandatory unless explicitly stated as optional, desirable, or preferred.

3. Extract type-specific parameters as a dict:
   - financial_threshold: {"threshold_amount": number, "currency": "INR", "period_years": number, "metric": "turnover" or "net_worth"}
   - experience_count: {"min_count": number, "min_value": number or null, "similarity_required": true/false, "window_years": number}
     For disjunctive criteria (e.g., "3 works at 40% OR 2 at 60% OR 1 at 80%"):
     {"branches": [{"count": 3, "percentage": 40}, {"count": 2, "percentage": 60}, {"count": 1, "percentage": 80}], "window_years": number, "disjunctive": true}
   - statutory_registration: {"registration_type": "GST"/"PAN"/etc, "required_class": str or null, "valid_at_submission": true}
   - quality_certification: {"cert_name": "ISO 9001", "accepted_versions": ["2008", "2015"], "scope": str or null}
   - document_checklist: {"document_name": str, "must_be_signed": true/false, "must_be_dated": true/false}
   - policy_compliance: {"policy_name": str, "declaration_type": str}

4. Assign a suggested ID using the prefix convention:
   FIN-001, FIN-002, ... for financial_threshold
   EXP-001, EXP-002, ... for experience_count
   REG-001, REG-002, ... for statutory_registration
   QUA-001, QUA-002, ... for quality_certification
   DOC-001, DOC-002, ... for document_checklist
   POL-001, POL-002, ... for policy_compliance

5. Include the exact source_quote from the tender and the page number.

IMPORTANT:
- Do NOT invent criteria that are not in the text.
- Extract criteria exactly as stated — do not modify thresholds or conditions.
- If a criterion is ambiguous, still extract it but note the ambiguity in the description.
- Financial amounts: normalize to numeric values in INR (e.g., "5 crore" = 50000000).
