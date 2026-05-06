You are analyzing a section of a government tender document. Classify this section into exactly one category:

- "nit": Notice Inviting Tender — the advertisement/invitation section with tender number, dates, and basic info
- "eligibility": Eligibility criteria, qualification requirements, pre-qualification conditions for bidders
- "technical_specs": Technical specifications, scope of work, schedule of requirements, detailed work description
- "boq": Bill of Quantities, price schedule, financial bid format, rate analysis
- "annexures": Annexures, appendices, formats, proformas, templates to be filled
- "other": Anything that doesn't clearly fit the above categories (general conditions, payment terms, etc.)

Consider the content, not just headings. Eligibility sections discuss what a bidder must have (turnover, experience, registrations, certificates). Technical specs discuss what must be built/delivered. BOQ discusses quantities and prices.

Respond with JSON only:
{"label": "...", "confidence": 0.0-1.0, "reasoning": "one sentence explaining why"}
