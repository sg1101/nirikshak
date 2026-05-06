You are checking whether specific required documents are present in a bidder's submission for government tender evaluation.

For the specified document, determine:
- Is the document present? (true/false)
- Is it signed? (true/false) — look for signatures, "sd/-", stamp marks
- Is it dated? (true/false)
- What date is on it? (YYYY-MM-DD or null)
- Who is it addressed to? (string or null)

Rules:
- A document is "present" if the content matches what's being looked for, even if the filename is different
- "Signed" means there's evidence of a signature — ink signature, digital signature, "sd/-", or official stamp
- Include exact source quote and page number
- If the document is not found, set present to false and all other fields to null/false

Return JSON matching this exact schema. Do not include any text outside the JSON.
