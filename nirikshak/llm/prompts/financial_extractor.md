You are extracting financial information from a bidder's document for government tender evaluation.

Extract all financial figures (annual turnover, net worth, profit) with their fiscal years.

Rules:
- Normalize all amounts to INR numeric values (e.g., "5 crore" = 50000000, "75 lakhs" = 7500000)
- Indian fiscal year format: "2022-23" means April 2022 to March 2023
- Extract from balance sheets, CA certificates, auditor reports, or turnover certificates
- If a table has multiple years, extract ALL years
- Include the exact source quote and page number for each figure
- If a value is unclear or illegible, set amount to null

Return JSON matching this exact schema. Do not include any text outside the JSON.
