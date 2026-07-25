# Resume Tailoring Prompt Template

Use this template when dispatching subagents to generate tailored resumes.
Copy the Context Block into `delegate_task(context=...)` and adapt the Goal Block per job.

## Context Block (copy into delegate_task context)

```
Resume tailoring for [CANDIDATE NAME].

BULLET FORMULA (critical — every bullet must follow this):
verb + product/workflow/platform + scope + measurable result + by/through method

Reference examples:
"[Action verb] [product/platform] [scope/context] [measurable result] [by/through method]."
"[Action verb] [product/platform] [scope/context] [measurable result] [by/through method]."

Pattern: [action verb] [product/platform] [scope/context] [measurable result] [by/through method]
Bullets can be 25-35 words. Every bullet must have: action + product + scope + result + method.
If no measurable result exists, use scope and method only.

CRITICAL STRUCTURE RULES:
1. [PRIMARY EMPLOYER] is ONE employer ([START DATE]–[END DATE]). Client projects are bullets under that single entry. NEVER present client projects as separate jobs.
1b. The [PRIMARY EMPLOYER] entry MUST have an intro line (italic) before the bullets that frames the role cohesively. Use a single sentence summarizing the candidate's role and delivery record as a reference — NOT a generic title. The word "multiple" signals variety, not a single assignment. Bullets should be grouped by theme — not jumping between clients randomly. In bullets, use "for a [client] engagement" or "at a leading [industry] chain" instead of "at [CLIENT]" to avoid reading as direct employment.
2. Career order: Most recent first. Follow the career_order array in config.json.
2b. Education/bridge entries must be ONE bullet only, factual. Do NOT invent additional bullets about data systems, architecture, analytics, or coursework. Bridge entries are not work experience.
3. No sole proprietor / entrepreneur / side-project entries unless explicitly requested.
4. Strength labels: 2-4 words, simple (e.g. "Product management", not "AI/ML Product Strategy Portfolio Leadership").
5. Summary: 2-3 sentences, plain factual tone.
7. NO pandering ("directly relevant to...", "well-suited for this role", "applicable to").
8. NO client-name prefixes ("[CLIENT] [PRODUCT]:") — weave client names naturally.
8b. In the professional summary, do NOT phrase client work as direct employment. Use "for a [client] engagement" or "at a leading [industry] chain" instead of "at [CLIENT]" — which reads as direct employment. The career highlights section shows the employer; the summary should not contradict that.
8c. NEVER conflate metrics or facts from different engagements in the summary or bullets. Each metric belongs to a specific engagement. Do not merge metrics, tools, or domains from different engagements into a single claim. If referencing a metric in the summary, it must be traceable to the correct engagement.
9. Use the candidate's preferred name (see config.json).
10. Only real experience from the profile — never conflate metrics from one engagement with another. Metrics belong to the engagement they describe. Never rephrase or rename a product/platform to make it sound more relevant to the target job. Describe what it IS, not what sounds good. Job titles MUST match the master profile exactly — never inflate, never change. Dates MUST match the master profile exactly — never change end dates to "Present" or vice versa. Background checks will surface any discrepancy.
11. Tools section: Include ONLY tool categories relevant to the specific job. Drop categories that have no overlap with job requirements. Return as JSON dict (NOT list), no markdown asterisks.
12. Include dates on all highlight headers.
13. Use read_file and write_file tools for reading/writing JSON files. Do NOT write custom Python scripts (.py files) to disk. If you must run code, clean up any temp files you create before finishing.
14. cover_letter: 3-4 paragraphs, professional, no pandering. Do NOT include a closing (no "Sincerely," "Thank you for your consideration," or name at the end) — the PDF generator adds a standard business closing automatically.

Master profile: [PATH TO MASTER_PROFILE.md] (READ THIS — it has the formula-style bullets, tools, and ATS keywords)
```

## Goal Block (adapt per job)

```
Tailor a resume for the [COMPANY] [JOB TITLE] role. Read the master profile at [PATH].
Read the job description from [JSON CACHE FILE] (find the [COMPANY] entry).

Produce a single JSON object with these fields:
- url, company, title
- tailored_summary: 2-3 sentences, plain factual tone
- tailored_strengths: array of 7-8 simple labels (2-4 words each)
- tailored_highlights: array of 3-4 objects with "header" and "bullets". FIRST must be the primary employer as one entry with 4-5 bullets using the formula.
- tailored_tools: object with ONLY categories relevant to this job — dict format, NOT a list. Adjust tools within each category to match what the job asks for.
- ats_keywords_injected: array of ATS keywords from the job posting naturally present
- highlights_changed_summary: 1 sentence
- cover_letter: 3-4 paragraphs, professional, no pandering. Do NOT include a closing — the PDF generator adds a standard business closing automatically.

Write the JSON object to [OUTPUT PATH].json
```