#!/usr/bin/env python3
"""
Human Review Dispatcher — sends resume JSON + job description to LLM for HR + Hiring Manager review.

Usage:
  python3 run_review.py output/tailoring_klaviyo_v6.json
  python3 run_review.py output/regenerate_results_1.json

Outputs review JSON files to resume/tailored/<company>_review.json
The review files are consumed by generate_pdf.py as Gate 2.
"""

import json
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "resume" / "tailored"


def build_review_prompt(resume_json, job_desc):
    """Build the review prompt for a single resume."""
    return f"""You are reviewing a tailored resume for quality. Act as two reviewers: an HR recruiter and a hiring manager.

## RESUME JSON
{json.dumps(resume_json, indent=2)[:8000]}

## JOB DESCRIPTION
{job_desc[:3000]}

## INSTRUCTIONS

### HR / Recruiter Review (0-100)
Score on:
1. EXPERIENCE BAR (20 pts): Does the candidate meet required years and seniority?
2. SUMMARY SCANABILITY (20 pts): Clear value proposition in 6 seconds?
3. RED FLAGS (20 pts): Job hopping, gaps, title inconsistencies, unbelievable claims?
4. ATS KEYWORD MATCH (20 pts): Key job terms appear naturally in resume?
5. QUANTIFIED IMPACT (20 pts): Specific, believable metrics showing scope and results?

### Hiring Manager Review (0-100)
Score on:
1. ROLE FIT (25 pts): Direct evidence for the role's top 3 priorities — not transferable skills, direct evidence.
2. ACHIEVEMENT DEPTH (25 pts): Believable, specific, relevant achievements? Would you ask follow-up questions?
3. CAREER NARRATIVE (20 pts): Does the career story make sense? Growth visible?
4. DOMAIN CREDIBILITY (15 pts): Does the candidate understand the industry/domain?
5. DIFFERENTIATION (15 pts): What makes this candidate memorable vs other applicants?

## OUTPUT
Write a single JSON object to {OUTPUT_DIR / f"{resume_json.get('company', 'unknown')}_review.json"}:

{{
  "company": "<company>",
  "title": "<title>",
  "hr_score": <0-100>,
  "hr_breakdown": {{
    "experience_bar": <score>/20,
    "summary_scanability": <score>/20,
    "red_flags": <score>/20,
    "ats_keywords": <score>/20,
    "quantified_impact": <score>/20
  }},
  "hr_issues": ["specific issue 1", ...],
  "hr_notes": "1-2 sentence assessment",
  "hm_score": <0-100>,
  "hm_breakdown": {{
    "role_fit": <score>/25,
    "achievement_depth": <score>/25,
    "career_narrative": <score>/20,
    "domain_credibility": <score>/15,
    "differentiation": <score>/15
  }},
  "hm_issues": ["specific issue 1", ...],
  "hm_notes": "1-2 sentence assessment",
  "hm_interview_questions": ["what would you ask?"],
  "combined_score": <average of hr_score and hm_score>,
  "threshold": 70,
  "status": "PASS" or "FAIL",
  "regenerate_feedback": "If FAIL, specific instructions for what to fix"
}}
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_review.py <tailoring_json>")
        print("This script outputs review prompt files. Dispatch them to subagents for LLM review.")
        sys.exit(1)
    
    with open(sys.argv[1]) as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        data = [data]
    
    # Load job descriptions
    desc_cache = {}
    desc_path = Path("output/descriptions_cache.json")
    if desc_path.exists():
        with open(desc_path) as f:
            desc_cache = json.load(f)
    
    prompts_dir = Path("output/review_prompts")
    prompts_dir.mkdir(exist_ok=True)
    
    for entry in data:
        company = entry.get('company', 'Unknown')
        url = entry.get('url', '')
        job_desc = desc_cache.get(url, entry.get('description', ''))
        
        prompt = build_review_prompt(entry, job_desc)
        safe_co = "".join(c for c in company if c.isalnum() or c in " -_").strip()
        prompt_path = prompts_dir / f"{safe_co}_review_prompt.txt"
        prompt_path.write_text(prompt)
    
    print(f"Generated {len(data)} review prompts in {prompts_dir}/")
    print(f"Dispatch each to a subagent for LLM review.")
    print(f"Review JSON files will be written to {OUTPUT_DIR}/<company>_review.json")


if __name__ == "__main__":
    main()