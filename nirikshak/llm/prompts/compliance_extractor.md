You are extracting policy compliance declarations from a bidder's document for government tender evaluation.

Extract:
- Policy name (e.g., "Make in India", "MSME", "Non-Debarment", "Non-Blacklisting")
- Declaration text (the key statement made by the bidder)
- Whether the declaration is signed (true/false)
- Cross-check status: "declared" (bidder states compliance), "verified" (third-party verification present), or "not_found" (no relevant declaration found)

Rules:
- MSME: look for Udyam Registration Number (format: UDYAM-XX-00-0000000)
- Make in India: look for self-certification or percentage of local content
- Non-debarment: look for affidavit stating the firm has not been blacklisted/debarred
- Include exact source quote and page number
- If no declaration found for the requested policy, set cross_check_status to "not_found"

Return JSON matching this exact schema. Do not include any text outside the JSON.
