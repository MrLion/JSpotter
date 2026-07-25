# Resume Tailoring Prompt Template

Use this template when dispatching subagents to generate tailored resumes.

## Context Block (copy into delegate_task context)

```
Resume tailoring for George Mishchenko.

BULLET FORMULA (critical — every bullet must follow this):
verb + product/workflow/platform + scope + measurable result + by/through method

Reference examples:
"Shipped 5 production AI agents cutting implementation time 65% and support volume 25% across 30K B2B customers / 6M users by converting top case-trigger categories into self-service flows."
"Delivered 4 foundational platform capabilities within 20 months for 9M daily customers across 8,000 stores by leading cross-functional discovery with SAP, Twilio, and MS Dynamics SMEs."

Pattern: [action verb] [product/platform] [scope/context] [measurable result] [by/through method]
Bullets can be 25-35 words. Every bullet must have: action + product + scope + result + method. If no measurable result exists, use scope and method only.

CRITICAL STRUCTURE RULES:
1. EPAM Systems is ONE employer (Sep 2020-May 2026). Client projects (Google, Walgreens, Preventric, Cigna, COX, GE Healthcare, Vertex) are bullets under that single entry. NEVER present client projects as separate jobs.
1b. The EPAM entry MUST have an intro line (italic) before the bullets that frames the role cohesively. Use "Led product strategy, discovery, and delivery across multiple enterprise client engagements spanning AI/ML, healthcare, and finance, maintaining 95% delivery rate." as a reference — NOT "Managed product delivery" (the candidate was a Product Manager, not a Delivery Manager). The word "multiple" is important — it signals variety, not a single assignment. Bullets should be grouped by theme (GenAI together, healthcare together, transformation together) — not jumping between clients randomly. In bullets, use "for a [client] engagement" or "at a leading [industry] chain" instead of "at Google" or "at Walgreens" to avoid reading as direct employment.
2. Career order: EPAM (2020-2026) first, then Clark University MSc IT (Jun 2019-Aug 2020) as a brief bridge entry, then Sole IT as "Principal Product Manager" (2016-2019), then Infinnity (2010-2016). Chronological descending — most recent first.
2b. Clark University entry must be ONE bullet only, factual: "Completed Master of Science in Information Technology, bridging from entrepreneurial leadership to enterprise product management." Do NOT invent additional bullets about data systems, architecture, analytics, or coursework. Clark is a bridge entry — not a work experience.
3. No sole proprietor / entrepreneur / agentic trading entries.
4. Strength labels: 2-4 words, simple ("Product management", not "AI/ML Product Strategy Portfolio Leadership")
5. Summary: 2-3 sentences, plain factual tone
7. NO pandering ("directly relevant to...", "well-suited for this role", "applicable to")
8. NO client-name prefixes ("Google GenAI:", "Walgreens:") — weave client names naturally
8b. In the professional summary, do NOT phrase client work as direct employment. Use "for a [client] engagement" or "at a leading [industry] chain" instead of "at Google" or "at Walgreens" — which reads as direct employment. The career highlights section shows EPAM as the employer; the summary should not contradict that.
8c. NEVER conflate metrics or facts from different engagements in the summary or bullets. Each metric belongs to a specific engagement (see Source tags in case study index). For example: "13M patients" belongs to Infinnity EHR integration in Europe, NOT Walgreens. "8,000 stores" belongs to Walgreens, NOT Infinnity. "Salesforce Marketing Cloud" belongs to COX Automotive fleet management, NOT healthcare enrollment. Do not merge metrics, tools, or domains from different engagements into a single claim. If referencing a metric in the summary, it must be traceable to the correct engagement.
9. Use "George" not "Georgii"
10. Only real experience from the profile — never conflate metrics from one engagement with another. Metrics belong to the engagement they describe (see Source tags in case study index). Never rephrase or rename a product/platform to make it sound more relevant to the target job. A fleet management platform is a fleet management platform — not a "marketing platform." Describe what it IS, not what sounds good. Job titles MUST match the master profile exactly — never inflate, never change. "Product Manager" stays "Product Manager," never "Senior Product Manager" or "Director." Dates MUST match the master profile exactly — never change "May 2026" to "Present" or vice versa. Background checks will surface any discrepancy.
11. Tools section: Include ONLY tool categories relevant to the specific job. Drop categories that have no overlap with job requirements.
12. Include dates on all highlight headers.
13. Use read_file and write_file tools for reading/writing JSON files. Do NOT write custom Python scripts (.py files) to disk. If you must run code, clean up any temp files you create before finishing. For example:
    - Healthcare job: include Healthcare Standards, all other categories
    - Marketing tech job: drop Healthcare Standards, keep Product & Delivery, AI/LLM, Data & Analytics, Platforms & Integrations
    - Fintech job: drop Healthcare Standards, emphasize Platforms & Integrations and Data & Analytics
    - If a category is included, adjust the tools listed within it to match what the job asks for

Master profile: /Users/mintmrlion/Documents/Job hunting/resume/MASTER_PROFILE.md (READ THIS — it has the updated formula-style bullets in Section 3, tools in Section 5, and ATS keywords in Section 8)
```

## Goal Block (adapt per job)

```
Tailor a resume for the [COMPANY] [JOB TITLE] role. Read the master profile at /Users/mintmrlion/Documents/Job hunting/resume/MASTER_PROFILE.md. Read the job description from [JSON FILE PATH] (find the [COMPANY] entry).

Produce a single JSON object with these fields:
- url, company, title
- tailored_summary: 2-3 sentences, plain factual tone
- tailored_strengths: array of 7-8 simple labels (2-4 words each)
- tailored_highlights: array of 3-4 objects with "header" and "bullets". FIRST must be EPAM as one entry with 4-5 bullets using the formula. Other entries: Sole IT, Infinnity.
- tailored_tools: object with ONLY categories relevant to this job (Product & Delivery, AI/LLM, Data & Analytics, Platforms & Integrations, Healthcare Standards) — adjust tools within each category to match what the job asks for
- ats_keywords_injected: array of ATS keywords from the job posting naturally present
- highlights_changed_summary: 1 sentence
- cover_letter: 3-4 paragraphs, professional, no pandering. Do NOT include a closing (no "Sincerely," "Thank you for your consideration," or name at the end) — the PDF generator adds a standard business closing automatically.

Write the JSON object to /Users/mintmrlion/Documents/Job hunting/output/[FILENAME].json
```