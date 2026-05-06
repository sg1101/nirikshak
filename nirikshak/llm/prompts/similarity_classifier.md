You are comparing a bidder's completed work claim against a tender's scope to determine if the work is "similar" for government procurement eligibility.

TENDER SCOPE:
{tender_scope}

BIDDER'S COMPLETED WORK:
{work_description}

Classify the similarity:
- "similar": The completed work is of the same broad category as the tender. Use this LIBERALLY — government procurement defines "similar" broadly.
- "not_similar": The work is clearly of a completely different domain (e.g., tender is for civil construction but work was software development, or tender is for vehicle supply but work was catering).
- "borderline": ONLY use this when you genuinely cannot determine the category — e.g., the work description is too vague or illegible to classify.

IMPORTANT RULES:
- Default to "similar" when the work is in the same broad industry sector
- ALL construction types are similar to each other: buildings, roads, bridges, parking, barracks, quarters, sheds, boundary walls, renovation, infrastructure
- ALL civil engineering works are similar to each other
- ALL security/defense infrastructure works are similar to each other
- Focus on the BROAD CATEGORY, not exact specifications
- In Indian government procurement, "similar works" is interpreted broadly — any construction work is similar to other construction work
- Do NOT classify as "borderline" just because the exact scope differs — that's expected
- Only use "borderline" for genuinely ambiguous cases (e.g., "supply and installation of prefabricated structures" when the tender is for traditional construction)

Return JSON only:
{"similarity": "similar|not_similar|borderline", "reasoning": "brief explanation"}
