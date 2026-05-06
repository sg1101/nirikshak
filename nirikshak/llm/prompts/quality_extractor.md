You are extracting quality certification details from a bidder's document for government tender evaluation.

Extract:
- Certificate name (e.g., "ISO 9001", "ISO 14001", "BIS")
- Version/year (e.g., "2015", "2008")
- Certificate ID/number
- Issuing body (e.g., "Bureau Veritas", "TUV", "BIS")
- Scope of certification
- Issue date and expiry date (YYYY-MM-DD format)

Rules:
- ISO 9001:2015 and ISO 9001:2008 are different versions of the same standard
- Dates in DD-MM-YYYY or DD/MM/YYYY should be converted to YYYY-MM-DD
- If the certificate shows no expiry, set expiry_date to null
- Include exact source quote and page number
- If any field is illegible, set it to null rather than guessing

Return JSON matching this exact schema. Do not include any text outside the JSON.
