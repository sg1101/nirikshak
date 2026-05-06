You are classifying a document from a bidder's submission to a government tender.

Based on the filename and the first page content, classify this document into exactly one category:

- "financial_statement": Balance sheet, P&L statement, turnover certificate, CA certificate, audited financials, solvency certificate
- "experience_certificate": Work completion certificate, work order, performance certificate, experience letter, project completion report
- "registration_certificate": GST certificate, PAN card, EPF registration, ESI registration, contractor class/category registration, trade license
- "quality_certificate": ISO certificate, BIS certificate, AERB certificate, OEM authorization, quality management certificate
- "bid_document": EMD receipt, tender acceptance letter, integrity pact, bid form, power of attorney, authorization letter
- "compliance_declaration": Make-in-India declaration, MSME certificate/declaration, non-debarment affidavit, blacklisting declaration
- "other": Company profile, cover letter, brochure, anything that doesn't fit above

Respond with JSON only:
{"category": "...", "confidence": 0.0-1.0, "reasoning": "brief explanation"}
