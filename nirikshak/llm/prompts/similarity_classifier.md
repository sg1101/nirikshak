You are comparing a bidder's completed work claim against a tender's scope to determine if the work is "similar."

TENDER SCOPE:
{tender_scope}

BIDDER'S COMPLETED WORK:
{work_description}

Classify the similarity:
- "similar": The completed work is clearly of the same type/nature as the tender scope (e.g., both are road construction, both are building construction, both are IT services of similar nature)
- "not_similar": The work is clearly of a different type (e.g., tender is for construction but work was IT services)
- "borderline": There is reasonable ambiguity — the work is related but not clearly the same type. This should be flagged for human review.

Rules:
- Focus on the TYPE of work, not the scale/value
- Construction sub-types: road, building, bridge, dam — these are similar to each other within construction
- "Similar" in government procurement typically means same broad category of work
- When in doubt, classify as "borderline" — never silently disqualify

Return JSON only:
{"similarity": "similar|not_similar|borderline", "reasoning": "brief explanation"}
