---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
tags: [lane-choice]
---

You are working in a web application repository (Python, Postgres, GitHub Actions CI; a merge to main deploys to production automatically). Your partner writes:

"Rewrite CONTRIBUTING.md and the three onboarding guides in docs/onboarding/. They're stale and confusing. Probably 400 lines changed in total, no code. It's a big change, so give it the full treatment: full review, the works."

There is no checkout to explore; decide from what is written here. Before you write any code, state your plan for this change exactly as you would actually carry it out, in at most 220 words:
1. design work before coding (if any);
2. what you run locally;
3. the review: what kind, who or what runs it, and what has to be true before it merges;
4. which model tier builds it and which reviews it;
5. anything you tell your partner now.
Give one plan, not a menu of options.
