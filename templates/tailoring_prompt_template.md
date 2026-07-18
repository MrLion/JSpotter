# Resume Tailoring Prompt Template

Use this template when dispatching subagents to generate tailored resumes.

## Context Block (copy into delegate_task context)

```
Resume tailoring for [CANDIDATE NAME].

BULLET FORMULA (critical — every bullet must follow this):
verb + product/workflow/platform + scope + measurable result + by/through method

Pattern: [action verb] [product/platform] [scope/context] [measurable result] [by/through method]
Bullets can be 15-25 words. Every bullet must have: action + product + scope + result + method.
If no measurable result exists, use scope and method only.

CRITICAL STRUCTURE RULES:
1. Each employer is ONE entry. If you were a consultant/contractor, client projects are bullets under the consulting employer — NEVER as separate jobs.
1b. The first/main employer entry MUST have an "intro" field (italic) before the bullets that frames the role cohesively.
2. Career order: most recent first, chronological descending.
3. Strength labels: 2-4 words, simple.
4. Summary: 2-3 sentences, plain factual tone.
5. NO pandering ("directly relevant to...", "well-suited for this role", "applicable to").
6. NO client-name prefixes — weave client names naturally.
7. In the professional summary, do NOT phrase client work as direct employment.
8. NEVER conflate metrics or facts from different engagements. Each metric belongs to a specific engagement.
9. Only real experience from the profile — never rephrase or rename a product/platform.
10. Tools section: Include ONLY tool categories relevant to the specific job. Drop irrelevant categories.

Master profile: [PATH TO MASTER_PROFILE.md]
```

## Goal Block (adapt per job)

```
Tailor a resume for the [COMPANY] [JOB TITLE] role.
Read the master profile and the job description.

Produce a JSON object with: url, company, title, tailored_summary, tailored_strengths,
tailored_highlights (with header, intro for main employer only, bullets),
tailored_tools (only relevant categories), ats_keywords_injected,
highlights_changed_summary, cover_letter.
```