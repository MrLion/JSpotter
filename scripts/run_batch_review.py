#!/usr/bin/env python3
"""
Batch resume review — reviews multiple resumes in one subagent call.
Reduces review API calls by up to 70% when reviewing 3-4 resumes at once.

Usage:
  python3 run_batch_review.py output/tailoring_voya_senior_v2.json output/tailoring_voya_lead_v2.json
"""

import json
import sys
from pathlib import Path


def build_batch_review_prompt(resume_paths, descs_cache_path='output/descriptions_cache.json'):
    """Build a single review prompt for multiple resumes."""
    
    with open(descs_cache_path) as f:
        descs = json.load(f)
    
    resumes = []
    for path in resume_paths:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            data = data[0]
        
        url = data.get('url', '')
        desc = descs.get(url, '')
        # Condense JD to requirements only
        desc_lines = desc.split('\n')
        req_lines = [l for l in desc_lines if any(kw in l.lower() for kw in 
            ['require', 'qualif', 'must have', 'years', 'experience', 'skill', 'preferred', 'responsib'])]
        condensed_desc = '\n'.join(req_lines[:20]) if req_lines else desc[:1500]
        
        resumes.append({
            'company': data.get('company', ''),
            'title': data.get('title', ''),
            'url': url,
            'summary': data.get('tailored_summary', ''),
            'strengths': data.get('tailored_strengths', []),
            'highlights': data.get('tailored_highlights', []),
            'tools': data.get('tailored_tools', {}),
            'cover_letter': data.get('cover_letter', '')[:500],
            'job_description_condensed': condensed_desc,
        })
    
    prompt = f"""You are reviewing {len(resumes)} tailored resumes for quality. For each resume, act as both an HR recruiter and a hiring manager. Be critical and specific.

## RESUMES TO REVIEW

"""
    for i, r in enumerate(resumes):
        prompt += f"""### Resume {i+1}: {r['company']} — {r['title']}
Job URL: {r['url']}

CONDENSED JOB DESCRIPTION:
{r['job_description_condensed']}

SUMMARY:
{r['summary']}

STRENGTHS:
{', '.join(r['strengths'])}

HIGHLIGHTS:
"""
        for h in r['highlights']:
            prompt += f"  {h.get('header', '')} ({len(h.get('bullets', []))} bullets)\n"
            for b in h.get('bullets', []):
                prompt += f"    - {b}\n"
        
        prompt += f"\nTOOLS: {json.dumps(r['tools'])}\n"
        prompt += f"\nCOVER LETTER (first 500 chars):\n{r['cover_letter']}\n\n---\n\n"
    
    prompt += f"""## SCORING INSTRUCTIONS

For EACH resume, score:

### HR / Recruiter (0-100)
1. EXPERIENCE BAR (20 pts)
2. SUMMARY SCANABILITY (20 pts)
3. RED FLAGS (20 pts)
4. ATS KEYWORD MATCH (20 pts)
5. QUANTIFIED IMPACT (20 pts)

### Hiring Manager (0-100)
1. ROLE FIT (25 pts)
2. ACHIEVEMENT DEPTH (25 pts)
3. CAREER NARRATIVE (20 pts)
4. DOMAIN CREDIBILITY (15 pts)
5. DIFFERENTIATION (15 pts)

## OUTPUT

Write a JSON ARRAY to the output file specified below. Each element should have:
{{
  "company": "<company>",
  "title": "<title>",
  "hr_score": <0-100>,
  "hr_breakdown": {{"experience_bar": "X/20 — notes", "summary_scanability": "X/20 — notes", "red_flags": "X/20 — notes", "ats_keywords": "X/20 — notes", "quantified_impact": "X/20 — notes"}},
  "hr_issues": ["issue 1", "issue 2"],
  "hr_notes": "1-2 sentence assessment",
  "hm_score": <0-100>,
  "hm_breakdown": {{"role_fit": "X/25 — notes", "achievement_depth": "X/25 — notes", "career_narrative": "X/20 — notes", "domain_credibility": "X/15 — notes", "differentiation": "X/15 — notes"}},
  "hm_issues": ["issue 1", "issue 2"],
  "hm_notes": "1-2 sentence assessment",
  "hm_interview_questions": ["question 1", "question 2"],
  "combined_score": <average>,
  "status": "PASS" or "FAIL",
  "regenerate_feedback": "If FAIL, specific fix instructions"
}}

Write the JSON array to: {Path('resume/tailored/batch_review.json').absolute()}

NOTE: If multiple resumes are for the same company, check consistency — same HR and HM will see both.
"""
    return prompt, resumes


def save_batch_reviews(batch_json_path, resumes):
    """Split batch review JSON into individual review files and convert to txt notes."""
    with open(batch_json_path) as f:
        reviews = json.load(f)
    
    output_dir = Path('resume/tailored')
    
    for review in reviews:
        company = review.get('company', 'Unknown')
        title = review.get('title', 'Role')
        
        # Find matching resume to get the file naming right
        safe_co = "".join(c for c in company if c.isalnum() or c in " -_").strip()
        safe_ti = "".join(c for c in title if c.isalnum() or c in " -_").strip()
        
        # Save review JSON (will be cleaned up by generate_pdf.py)
        review_json_path = output_dir / f"{safe_co}_{safe_ti}_review.json"
        with open(review_json_path, 'w') as f:
            json.dump(review, f, indent=2)
        
        # Also save txt notes
        hr_score = review.get('hr_score', 0)
        hm_score = review.get('hm_score', 0)
        status = review.get('status', 'PASS')
        
        notes = f"QUALITY REVIEW: {company} — {title}\n{'='*60}\n\n"
        notes += f"HR Score: {hr_score}/100\nHM Score: {hm_score}/100\nStatus: {status}\n\n"
        notes += f"HR Notes: {review.get('hr_notes', '')}\n"
        notes += f"HM Notes: {review.get('hm_notes', '')}\n\n"
        notes += "HR Issues:\n"
        for issue in review.get('hr_issues', []):
            notes += f"  - {issue}\n"
        notes += "\nHM Issues:\n"
        for issue in review.get('hm_issues', []):
            notes += f"  - {issue}\n"
        notes += "\nHM Interview Questions:\n"
        for q in review.get('hm_interview_questions', []):
            notes += f"  ? {q}\n"
        if status == 'FAIL' or hr_score < 70 or hm_score < 70:
            notes += f"\nRegenerate Feedback: {review.get('regenerate_feedback', '')}\n"
        
        notes_path = output_dir / f"{safe_co}_{safe_ti}_review_notes.txt"
        notes_path.write_text(notes)
        
        # Clean up JSON
        review_json_path.unlink()
        
        print(f"  {company} — {title}: HR={hr_score} HM={hm_score} {status}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_batch_review.py <resume1.json> <resume2.json> [resume3.json] ...")
        print("Reviews multiple resumes in one subagent call. Up to 4 resumes per batch.")
        sys.exit(1)
    
    resume_paths = sys.argv[1:]
    if len(resume_paths) > 4:
        print(f"Warning: {len(resume_paths)} resumes provided, max 4 per batch. Processing first 4.")
        resume_paths = resume_paths[:4]
    
    prompt, resumes = build_batch_review_prompt(resume_paths)
    
    # Write prompt to file for subagent dispatch
    prompt_path = Path('output/batch_review_prompt.txt')
    prompt_path.write_text(prompt)
    
    print(f"Generated batch review prompt for {len(resumes)} resumes")
    print(f"Prompt saved to: {prompt_path}")
    print(f"Dispatch to subagent with goal: 'Read the prompt at {prompt_path.absolute()} and write the review JSON array to resume/tailored/batch_review.json'")
    print()
    print("After subagent completes, run:")
    print(f"  python3 run_batch_review.py --save")


if __name__ == '__main__':
    if '--save' in sys.argv:
        save_batch_reviews(Path('resume/tailored/batch_review.json'), [])
    else:
        main()