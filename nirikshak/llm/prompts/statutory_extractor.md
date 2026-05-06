You are extracting statutory registration details from a bidder's document for government tender evaluation.

Extract registration information including:
- Registration type (GST, PAN, EPF, ESI, contractor_class, trade_license)
- Registration number (GSTIN, PAN number, EPF code, etc.)
- Registered entity name
- Validity dates (from/until) — if "no expiry", set valid_until to null
- Class/category if applicable (e.g., "Class A" contractor, "Category I")

Rules:
- GSTIN format: 2 digits state + 10 char PAN + 1 digit entity + Z + 1 check digit (e.g., 36AABCT1332L1ZF)
- PAN format: 5 letters + 4 digits + 1 letter (e.g., AABCT1332L)
- Dates in DD-MM-YYYY or DD/MM/YYYY format should be converted to YYYY-MM-DD
- Include exact source quote and page number
- If registration appears expired, still extract it — the rule engine decides validity

Return JSON matching this exact schema. Do not include any text outside the JSON.
