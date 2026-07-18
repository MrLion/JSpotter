#!/usr/bin/env python3
"""
Resume Tailoring Validator — validates LLM-generated tailoring JSON before generating PDFs.

Checks:
1. EPAM is first highlight entry and is ONE employer (no client projects as separate entries)
2. Career order: EPAM → Sole IT → Infinnity (chronological descending)
3. No sole proprietor / entrepreneur / agentic trading entries
4. Bullets ≤ 15 words
5. Strength labels ≤ 4 words
6. Summary ≤ 3 sentences
7. No client-name prefixes ("Google GenAI:", "Walgreens:")
8. No pandering phrases ("directly relevant to", "well-suited for")
9. Uses "George" not "Georgii"
10. Cover letter has 3-4 body paragraphs
11. All required fields present

Usage:
  python3 validate_tailoring.py output/tailoring_results.json
"""

import json
import sys
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent

def load_candidate_config():
    config_path = BASE_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
        return cfg.get("candidate", {})
    return {}

_CANDIDATE = load_candidate_config()
CAREER_ORDER = _CANDIDATE.get("career_order", [])
CONFLATION_METRICS = _CANDIDATE.get("conflation_metrics", {})
CLIENT_KEYWORDS = _CANDIDATE.get("client_keywords", {})

BAD_KEYWORDS = ['Sole Proprietor', 'Entrepreneur', 'Agentic Trading', 'Agentic Systems']
PANDERING = ['directly relevant to', 'well-suited for', 'perfectly aligned', 'ideal candidate']
CLIENT_PREFIX_RE = re.compile(r'^(Google|Walgreens|Preventric|Cigna|GE Healthcare|COX)\s*[\-:]', re.I)

REQUIRED_FIELDS = ['url', 'company', 'title', 'tailored_summary', 'tailored_strengths',
                   'tailored_highlights', 'ats_keywords_injected', 'highlights_changed_summary', 'cover_letter']


def validate_entry(entry, idx):
    errors = []
    company = entry.get('company', f'entry {idx}')
    
    # 1. Required fields
    for field in REQUIRED_FIELDS:
        if field not in entry or not entry[field]:
            errors.append(f'{company}: missing required field "{field}"')
    
    highlights = entry.get('tailored_highlights', [])
    
    # 2. EPAM must be first
    if highlights:
        first_header = highlights[0].get('header', '')
        if 'EPAM' not in first_header:
            errors.append(f'{company}: EPAM is not the first highlight entry (got "{first_header}")')
    
    # 3. No bad entries
    for h in highlights:
        header = h.get('header', '')
        for kw in BAD_KEYWORDS:
            if kw in header:
                errors.append(f'{company}: bad entry found — "{header}"')
    
    # 4. Career order check
    headers = [h.get('header', '') for h in highlights]
    sole_idx = infinnity_idx = None
    for i, h in enumerate(headers):
        if 'Sole IT' in h or 'Senior Product Consultant' in h or 'Senior product consultant' in h:
            sole_idx = i
        if 'Infinnity' in h:
            infinnity_idx = i
    if sole_idx is not None and infinnity_idx is not None and infinnity_idx < sole_idx:
        errors.append(f'{company}: wrong order — Infinnity (pos {infinnity_idx}) before Sole IT (pos {sole_idx})')
    
    # 5. No client-name prefixes in bullets
    for h in highlights:
        for b in h.get('bullets', []):
            if CLIENT_PREFIX_RE.match(b):
                errors.append(f'{company}: client-name prefix in bullet — "{b[:50]}"')
    
    # 5b. Conflation detection — using config-driven metrics
    for h in highlights:
        for b in h.get('bullets', []):
            bullet_lower = b.lower()
            for metric, valid_sources in CONFLATION_METRICS.items():
                if metric in bullet_lower:
                    mentioned_clients = []
                    for client, keywords in CLIENT_KEYWORDS.items():
                        for kw in keywords:
                            if kw in bullet_lower:
                                mentioned_clients.append(client)
                                break
                    for client in mentioned_clients:
                        if client not in valid_sources:
                            errors.append(f'{company}: possible metric conflation — "{metric}" belongs to {valid_sources} but bullet mentions "{client}"')
    
    # 6. Bullets ≤ 25 words (formula: verb + product + scope + result + method)
    for h in highlights:
        for b in h.get('bullets', []):
            word_count = len(b.split())
            if word_count > 25:
                errors.append(f'{company}: bullet exceeds 25 words ({word_count}) — "{b[:40]}..."')
    
    # 7. Strength labels ≤ 4 words
    for s in entry.get('tailored_strengths', []):
        word_count = len(s.split())
        if word_count > 4:
            errors.append(f'{company}: strength label exceeds 4 words ({word_count}) — "{s}"')
    
    # 8. Summary ≤ 3 sentences
    summary = entry.get('tailored_summary', '')
    sentence_count = summary.count('.') + summary.count('!') + summary.count('?')
    if sentence_count > 3:
        errors.append(f'{company}: summary exceeds 3 sentences ({sentence_count})')
    
    # 9. No pandering
    for phrase in PANDERING:
        if phrase.lower() in summary.lower() or phrase.lower() in entry.get('cover_letter', '').lower():
            errors.append(f'{company}: pandering phrase found — "{phrase}"')
    
    # 10. No "Georgii"
    all_text = summary + ' ' + entry.get('cover_letter', '')
    if 'Georgii' in all_text:
        errors.append(f'{company}: uses "Georgii" instead of "George"')
    
    # 11. Cover letter paragraphs
    cover = entry.get('cover_letter', '')
    cover_normalized = cover.replace('\\n', '\n')
    paragraphs = [p for p in cover_normalized.split('\n\n') if p.strip()]
    if len(paragraphs) < 4 or len(paragraphs) > 7:
        errors.append(f'{company}: cover letter has {len(paragraphs)} paragraphs (expected 4-7 with greeting/signoff)')
    
    # 12. Dates on highlight headers
    for h in highlights:
        header = h.get('header', '')
        last_12 = header[-12:] if len(header) >= 12 else header
        if not any(c.isdigit() for c in last_12):
            errors.append(f'{company}: highlight header missing dates — "{header}"')
    
    # 13. Tools format — must be dict, not list
    tools = entry.get('tailored_tools')
    if tools is not None:
        if isinstance(tools, list):
            errors.append(f'{company}: tools returned as list (should be dict with category keys)')
        elif isinstance(tools, dict):
            for key, val in tools.items():
                if '**' in key or '**' in str(val):
                    errors.append(f'{company}: markdown asterisks in tools — "{key}"')
    
    return errors


def validate_and_fix(entry):
    """Auto-fix fixable issues. Returns (fixed_entry, changes_made)."""
    changes = []
    highlights = entry.get('tailored_highlights', [])
    
    # Remove bad entries
    clean_highlights = [h for h in highlights if not any(kw in h.get('header', '') for kw in BAD_KEYWORDS)]
    if len(clean_highlights) < len(highlights):
        changes.append('removed sole proprietor/entrepreneur entries')
    
    # Reorder based on config career_order
    if CAREER_ORDER:
        ordered = []
        used = set()
        for career_entry in CAREER_ORDER:
            keywords = [kw.lower() for kw in career_entry.get("keywords", [])]
            for i, h in enumerate(clean_highlights):
                if i in used:
                    continue
                if any(kw in h.get('header', '').lower() for kw in keywords):
                    ordered.append(h)
                    used.add(i)
        # Append any remaining highlights
        other = [h for i, h in enumerate(clean_highlights) if i not in used]
        new_order = ordered + other
    else:
        new_order = clean_highlights
    
    if [h.get('header') for h in new_order] != [h.get('header') for h in clean_highlights]:
        changes.append('reordered highlights per config career_order')
    
    entry['tailored_highlights'] = new_order
    return entry, changes


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_tailoring.py <tailoring_json> [--fix]")
        sys.exit(1)
    
    fix_mode = '--fix' in sys.argv
    filepath = sys.argv[1]
    
    with open(filepath) as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        data = [data]
    
    all_errors = []
    fixed_count = 0
    
    for idx, entry in enumerate(data):
        errors = validate_entry(entry, idx)
        if errors:
            if fix_mode:
                entry, changes = validate_and_fix(entry)
                # Re-validate after fix
                remaining = validate_entry(entry, idx)
                if remaining:
                    all_errors.extend(remaining)
                if changes:
                    fixed_count += 1
                    print(f'  FIXED: {entry.get("company", "?")} — {", ".join(changes)}')
            else:
                all_errors.extend(errors)
    
    print(f'\n{"=" * 60}')
    if fix_mode:
        print(f'Fixed: {fixed_count} entries')
    print(f'Validation errors: {len(all_errors)}')
    
    if all_errors:
        print('\nErrors:')
        for e in all_errors:
            print(f'  ❌ {e}')
    
    if fix_mode and fixed_count > 0:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f'\nSaved fixes to {filepath}')
    
    return len(all_errors)


if __name__ == '__main__':
    sys.exit(1 if main() > 0 else 0)