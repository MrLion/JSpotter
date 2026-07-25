#!/usr/bin/env python3
"""
Resume Quality Gate — scores tailored resume JSON and rejects low-quality entries.

Scoring (100 pts):
1. Formula compliance (25 pts) — every bullet has verb + product + scope + result/method
2. No conflation (20 pts) — metrics not mismatched across engagements
3. Structure rules (20 pts) — EPAM first, correct order, intro line, no bad entries
4. No pandering / direct employment framing (15 pts)
5. ATS keyword match (10 pts) — keywords present in job posting
6. Summary quality (10 pts) — 2-3 sentences, plain tone, no claims

Threshold: 75/100. Below = reject and regenerate.

Usage:
  python3 quality_gate.py output/regenerate_results_1.json
  python3 quality_gate.py output/tailoring_klaviyo_v6.json
"""

import json
import sys
import re
from pathlib import Path

BAD_KEYWORDS = ['Sole Proprietor', 'Entrepreneur', 'Agentic Trading', 'Agentic Systems']
PANDERING = ['directly relevant to', 'well-suited for', 'perfectly aligned', 'ideal candidate', 'applicable to']

# Metrics that belong to specific engagements
METRIC_TO_SOURCE = {
    '13m patients': ['infinnity', 'google'],
    '13 million': ['infinnity', 'google'],
    '61%': ['google'],
    '91%': ['google'],
    '$30m': ['google'],
    '$30 million': ['google'],
    '10x': ['infinnity'],
    '10 times': ['infinnity'],
    '3,500': ['infinnity'],
    '10,000+': ['infinnity'],
    '2,000+': ['sole_it'],
    '30% inbound': ['sole_it'],
    '9m daily': ['walgreens'],
    '8,000 stores': ['walgreens'],
    '65k+': ['cox'],
    '70% adoption': ['vertex'],
    '50k clients': ['vertex'],
    '95% cost': ['ge_healthcare'],
    '$70m': ['ge_healthcare'],
    '4m+': ['ge_healthcare'],
    '4 million': ['ge_healthcare'],
    '80% nps': ['preventric'],
    '10%': ['cox'],
    '35% to 75%': ['cox'],
    '40%': ['walgreens'],
    '40k+': ['walgreens'],
}

CLIENT_KEYWORDS = {
    'google': ['google', 'corpfinance', 'docce'],
    'walgreens': ['walgreens', 'pharmacy chain', '9m daily', '8,000 stores'],
    'preventric': ['preventric', 'wearable bpm', 'vascular'],
    'cox': ['cox', 'fleet management', 'automotive', '65k+'],
    'cigna': ['cigna', 'medicare advantage', 'hcsc', 'divestiture'],
    'ge_healthcare': ['ge healthcare', 'edison', 'ultrasound', 'iot', '4m+', 'aws hcls'],
    'vertex': ['vertex', 'tax research', 'ontology', '50k clients'],
    'sole_it': ['sole it', 'messenger', 'photo stock', 'b2b haas'],
    'infinnity': ['infinnity', '10x', 'ehrintegration', '13m patients', 'ambulatory'],
}

CLIENT_NAMES_IN_PROFILE = {
    'google': 'Google CorpFinance',
    'walgreens': 'Walgreens',
    'preventric': 'Preventric',
    'cox': 'COX Automotive',
    'cigna': 'Cigna',
    'ge_healthcare': 'GE Healthcare',
    'vertex': 'Vertex',
    'sole_it': 'Sole IT',
    'infinnity': 'Infinnity',
}


def score_entry(entry, job_desc=''):
    """Score a single resume entry. Returns (score, issues)."""
    issues = []
    score = 100
    company = entry.get('company', '?')
    summary = entry.get('tailored_summary', '')
    highlights = entry.get('tailored_highlights', [])
    strengths = entry.get('tailored_strengths', [])
    cover_letter = entry.get('cover_letter', '')
    all_text = summary + ' ' + cover_letter + ' ' + ' '.join(
        b for h in highlights for b in h.get('bullets', [])
    )
    all_text_lower = all_text.lower()

    # === 1. Formula compliance (25 pts) ===
    formula_score = 25
    for h in highlights:
        for b in h.get('bullets', []):
            words = b.split()
            word_count = len(words)
            if word_count > 35:
                formula_score -= 1
                issues.append(f'{company}: bullet over 35 words ({word_count})')
            # Check for verb at start — expanded list
            if words and words[0].lower() not in [
                'launched', 'shipped', 'delivered', 'improved', 'increased', 'reduced',
                'defined', 'developed', 'directed', 'modernized', 'drove', 'built',
                'migrated', 'reached', 'owned', 'grew', 'optimized', 'specified',
                'led', 'created', 'designed', 'managed', 'established', 'expanded',
                'partnered', 'collaborated', 'facilitated', 'analyzed', 'introduced',
                'standardized', 'conducted', 'mentored', 'advised', 'ensured',
                'attained', 'scaled', 'transformed', 'identified', 'completed',
                'won', 'generated', 'secured', 'unlocked', 'launched', 'drives',
                'shaping', 'accelerated', 'spearheaded', 'championed', 'negotiated',
                'presented', 'executed', 'implemented', 'prototyped', 'piloted',
                'architected', 'authored', 'published', 'presented', 'trained',
                'evaluated', 'measured', 'tested', 'validated', 'released',
            ]:
                formula_score -= 2
                issues.append(f'{company}: bullet may not start with action verb — "{words[0]}"')
    formula_score = max(0, formula_score)
    score -= (25 - formula_score)

    # === 2. No conflation (20 pts) ===
    conflation_score = 20
    for h in highlights:
        for b in h.get('bullets', []):
            b_lower = b.lower()
            # Check if metrics from one engagement appear alongside another engagement's name
            mentioned_clients = []
            for client, keywords in CLIENT_KEYWORDS.items():
                for kw in keywords:
                    if kw in b_lower:
                        mentioned_clients.append(client)
                        break
            mentioned_clients = list(set(mentioned_clients))
            
            for metric, valid_sources in METRIC_TO_SOURCE.items():
                if metric in b_lower:
                    for client in mentioned_clients:
                        if client not in valid_sources:
                            conflation_score -= 5
                            issues.append(f'{company}: CONFLATION — "{metric}" belongs to {valid_sources} but bullet references "{client}"')
    
    # Also check summary for conflation — but per-sentence (summary legitimately references multiple engagements)
    summary_sentences = re.split(r'[.!?]+', summary)
    for sentence in summary_sentences:
        sentence_lower = sentence.lower().strip()
        if not sentence_lower:
            continue
        mentioned_clients_sentence = []
        for client, keywords in CLIENT_KEYWORDS.items():
            for kw in keywords:
                if kw in sentence_lower:
                    mentioned_clients_sentence.append(client)
                    break
        mentioned_clients_sentence = list(set(mentioned_clients_sentence))
        for metric, valid_sources in METRIC_TO_SOURCE.items():
            if metric in sentence_lower:
                for client in mentioned_clients_sentence:
                    if client not in valid_sources:
                        conflation_score -= 5
                        issues.append(f'{company}: SUMMARY CONFLATION — "{metric}" belongs to {valid_sources} but sentence references "{client}"')
    
    conflation_score = max(0, conflation_score)
    score -= (20 - conflation_score)

    # === 3. Structure rules (20 pts) ===
    structure_score = 20
    if not highlights:
        structure_score -= 20
        issues.append(f'{company}: no highlights')
    else:
        first_header = highlights[0].get('header', '')
        if 'EPAM' not in first_header:
            structure_score -= 10
            issues.append(f'{company}: EPAM is not first highlight')
        
        # Check for bad entries
        for h in highlights:
            header = h.get('header', '')
            for kw in BAD_KEYWORDS:
                if kw in header:
                    structure_score -= 5
                    issues.append(f'{company}: bad entry — "{header}"')
        
        # Check career order
        headers = [h.get('header', '') for h in highlights]
        sole_idx = infinnity_idx = None
        for idx, h in enumerate(headers):
            if 'Sole IT' in h or 'Principal Product Manager' in h:
                sole_idx = idx
            if 'Infinnity' in h:
                infinnity_idx = idx
        if sole_idx is not None and infinnity_idx is not None and infinnity_idx < sole_idx:
            structure_score -= 5
            issues.append(f'{company}: wrong order — Infinnity before Sole IT')
        
        # Check EPAM intro
        if highlights and 'EPAM' in highlights[0].get('header', ''):
            if not highlights[0].get('intro'):
                structure_score -= 3
                issues.append(f'{company}: EPAM entry missing intro line')
    
    structure_score = max(0, structure_score)
    score -= (20 - structure_score)

    # === 4. No pandering / direct employment (15 pts) ===
    pander_score = 15
    for phrase in PANDERING:
        if phrase in all_text_lower:
            pander_score -= 5
            issues.append(f'{company}: pandering phrase — "{phrase}"')
    
    # Check summary for direct employment framing
    if re.search(r'\bat (Google|Walgreens|Cigna|COX|GE Healthcare|Preventric|Vertex)\b', summary):
        pander_score -= 5
        issues.append(f'{company}: summary implies direct employment at client')
    
    if 'Georgii' in all_text:
        pander_score -= 3
        issues.append(f'{company}: uses "Georgii" instead of "George"')
    
    pander_score = max(0, pander_score)
    score -= (15 - pander_score)

    # === 5. ATS keyword match (10 pts) ===
    ats_keywords = entry.get('ats_keywords_injected', [])
    ats_score = 10
    if len(ats_keywords) < 5:
        ats_score -= 5
        issues.append(f'{company}: only {len(ats_keywords)} ATS keywords')
    # Check if keywords actually appear in the text
    missing_kw = 0
    for kw in ats_keywords[:10]:
        if kw.lower() not in all_text_lower:
            missing_kw += 1
    if missing_kw > 3:
        ats_score -= 3
        issues.append(f'{company}: {missing_kw} ATS keywords not found in text')
    ats_score = max(0, ats_score)
    score -= (10 - ats_score)

    # === 6. Summary quality (10 pts) ===
    summary_score = 10
    sentence_count = summary.count('.') + summary.count('!') + summary.count('?')
    if sentence_count > 4:
        summary_score -= 3
        issues.append(f'{company}: summary too long ({sentence_count} sentences)')
    if sentence_count < 2:
        summary_score -= 3
        issues.append(f'{company}: summary too short ({sentence_count} sentences)')
    # Check strength label word count
    for s in strengths:
        if len(s.split()) > 4:
            summary_score -= 1
            issues.append(f'{company}: strength label too long — "{s}"')
    summary_score = max(0, summary_score)
    score -= (10 - summary_score)

    return score, issues


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 quality_gate.py <tailoring_json> [threshold]")
        sys.exit(1)
    
    threshold = 75
    # Read from config if available
    try:
        with open("config.json") as f:
            cfg = json.load(f)
        threshold = cfg.get("resume_tailoring", {}).get("quality_gate_threshold", 75)
    except:
        pass
    if len(sys.argv) >= 3:
        threshold = int(sys.argv[2])
    
    filepath = sys.argv[1]
    with open(filepath) as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        data = [data]
    
    passed = []
    failed = []
    
    for idx, entry in enumerate(data):
        score, issues = score_entry(entry)
        company = entry.get('company', f'entry {idx}')
        status = 'PASS' if score >= threshold else 'FAIL'
        
        print(f'{status} {company:<25} {score:>3}/100')
        if issues:
            for issue in issues:
                print(f'  ⚠ {issue}')
        
        if score >= threshold:
            passed.append(entry)
        else:
            failed.append(entry)
    
    print(f'\n{"=" * 60}')
    print(f'Passed: {len(passed)}/{len(data)} (threshold: {threshold})')
    print(f'Failed: {len(failed)}/{len(data)}')
    
    if failed:
        print(f'\nFailed entries (need regeneration):')
        for entry in failed:
            print(f'  - {entry.get("company", "?")} — {entry.get("title", "?")}')
        print(f'  URLs:')
        for entry in failed:
            print(f'    {entry.get("url", "?")}')
    
    return len(failed)


if __name__ == '__main__':
    sys.exit(1 if main() > 0 else 0)