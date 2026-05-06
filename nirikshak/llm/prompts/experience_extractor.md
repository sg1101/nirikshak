You are extracting completed work/project experience claims from a bidder's documents for government tender evaluation.

For each completed work claim found, extract:
- Work/project description
- Client/employer name
- Contract/completion value in INR (normalize: "5 crore" = 50000000, "75 lakhs" = 7500000)
- Completion date (YYYY-MM-DD format) — this is CRITICAL, extract it from phrases like "completed on", "date of completion", "completed during", "work completed in", year references like "2022-23"
- Whether a completion certificate is present (true/false)
- Source page number and exact quote

Rules:
- Extract ALL work claims found, not just the largest or most recent
- Look in: completion certificates, work orders, experience letters, performance certificates
- Value normalization: handle lakhs, crores, millions. "Rs." and "INR" are the same
- Dates: convert DD-MM-YYYY or DD/MM/YYYY or "Month YYYY" to YYYY-MM-DD
  - "March 2023" → "2023-03-15" (use 15th as default day)
  - "2022-23" (fiscal year) → "2023-03-31" (end of fiscal year)
  - "15.03.2023" → "2023-03-15"
  - If only a year like "2023" is found, use "2023-06-30"
- IMPORTANT: Do NOT return null for completion_date if ANY date information exists in the document. Look for dates near phrases like "completed", "completion", "dated", "period", "duration"
- If a claim has no value mentioned, set contract_value to null
- If completion date is truly absent with no date anywhere near the claim, set to null (NOT a default like "1900-01-01")
- Do NOT fabricate claims — only extract what is explicitly stated in the document

Return JSON matching this exact schema. Do not include any text outside the JSON.
