# Resume Review Prompt Template

Use this template for LLM-based resume quality review (Gate 2).

## HR / Recruiter Review (0-100)

1. EXPERIENCE BAR (20 pts): Does the candidate meet required years and seniority?
2. SUMMARY SCANABILITY (20 pts): Clear value proposition in 6 seconds?
3. RED FLAGS (20 pts): Job hopping, gaps, title inconsistencies, unbelievable claims?
4. ATS KEYWORD MATCH (20 pts): Key job terms appear naturally in resume?
5. QUANTIFIED IMPACT (20 pts): Specific, believable metrics showing scope and results?

## Hiring Manager Review (0-100)

1. ROLE FIT (25 pts): Direct evidence for the role's top 3 priorities.
2. ACHIEVEMENT DEPTH (25 pts): Believable, specific, relevant achievements?
3. CAREER NARRATIVE (20 pts): Does the career story make sense? Growth visible?
4. DOMAIN CREDIBILITY (15 pts): Does the candidate understand the industry/domain?
5. DIFFERENTIATION (15 pts): What makes this candidate memorable?

## Output Format

```json
{
  "company": "<company>",
  "hr_score": <0-100>,
  "hm_score": <0-100>,
  "combined_score": <average>,
  "threshold": 70,
  "status": "PASS" | "FAIL",
  "hr_issues": [...],
  "hm_issues": [...],
  "regenerate_feedback": "If FAIL, specific fix instructions"
}
```

## Passing Threshold

Both HR score AND HM score must be ≥ 70.