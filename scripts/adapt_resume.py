#!/usr/bin/env python3
"""
Same-company resume adapter — generates a second resume variant from a base resume.
Only adapts summary, strengths, and title. Bullets stay identical.

Saves ~50% tokens vs full generation for paired roles at the same company.

Usage:
  python3 adapt_resume.py output/tailoring_voya_senior_v2.json "Lead AI Product Manager" "https://www.linkedin.com/jobs/view/lead-ai-product-manager-at-voya-financial-4431725677" output/tailoring_voya_lead_v3.json
"""

import json
import sys
from pathlib import Path


def build_adapt_prompt(base_path, new_title, new_url, output_path, descs_cache_path='output/descriptions_cache.json'):
    """Build a lightweight prompt that adapts an existing resume for a different role at the same company."""
    
    with open(base_path) as f:
        base = json.load(f)
    if isinstance(base, list):
        base = base[0]
    
    with open(descs_cache_path) as f:
        descs = json.load(f)
    
    new_desc = descs.get(new_url, '')
    # Condense to requirements only
    desc_lines = new_desc.split('\n')
    req_lines = [l for l in desc_lines if any(kw in l.lower() for kw in
        ['require', 'qualif', 'must have', 'years', 'experience', 'skill', 'preferred', 'responsib'])]
    condensed_desc = '\n'.join(req_lines[:20]) if req_lines else new_desc[:1500]
    
    prompt = f"""You are adapting an existing tailored resume for a DIFFERENT role at the SAME company.

The base resume is already written. You only need to adjust:
1. tailored_summary — rewrite for the new role's focus
2. tailored_strengths — adjust labels to match new role emphasis
3. title — update to new role title
4. url — update to new role URL
5. cover_letter — rewrite for new role

DO NOT change:
- tailored_highlights (bullets stay identical — same person, same experience)
- tailored_tools (same company, same relevance)
- ats_keywords_injected (adjust only if new role has different keywords)
- highlights_changed_summary

## BASE RESUME
Company: {base.get('company', '')}
Title: {base.get('title', '')}

Current summary:
{base.get('tailored_summary', '')}

Current strengths:
{json.dumps(base.get('tailored_strengths', []))}

## NEW ROLE
Title: {new_title}
URL: {new_url}

CONDENSED JOB DESCRIPTION:
{condensed_desc}

## OUTPUT

Read the base resume at {Path(base_path).absolute()}
Modify only the fields listed above.
Write the complete JSON object to {Path(output_path).absolute()}

Keep all bullets, highlights structure, tools, and career order identical to the base.
"""
    return prompt


def main():
    if len(sys.argv) < 5:
        print("Usage: python3 adapt_resume.py <base_resume.json> <new_title> <new_url> <output_path>")
        print()
        print("Example:")
        print("  python3 adapt_resume.py output/tailoring_voya_senior_v2.json 'Lead AI Product Manager' 'https://linkedin.com/jobs/view/...' output/tailoring_voya_lead_v3.json")
        sys.exit(1)
    
    base_path = sys.argv[1]
    new_title = sys.argv[2]
    new_url = sys.argv[3]
    output_path = sys.argv[4]
    
    prompt = build_adapt_prompt(base_path, new_title, new_url, output_path)
    
    prompt_path = Path('output/adapt_prompt.txt')
    prompt_path.write_text(prompt)
    
    print(f"Adaptation prompt generated")
    print(f"Base: {base_path}")
    print(f"New role: {new_title}")
    print(f"Output: {output_path}")
    print(f"Prompt: {prompt_path}")
    print()
    print(f"Dispatch to subagent with goal: 'Read the prompt at {prompt_path.absolute()} and write the adapted resume JSON to {Path(output_path).absolute()}'")
    print()
    print("Token savings: ~50% vs full generation (no master profile read, no bullet generation)")


if __name__ == '__main__':
    main()