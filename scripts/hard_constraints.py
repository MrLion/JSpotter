#!/usr/bin/env python3
"""
Hard-constraint gates — deal-breaker checks run BEFORE job scoring.

A job that fails any gate is never scored or prioritized; it gets
Recommendation = "SKIP: <reason>" in the journal instead. This prevents a
high skills match from papering over a fundamental constraint (compensation
floor, excessive experience requirement, citizenship/clearance blocker).

ALL thresholds come from config.json → hard_constraints. A missing key or
null value disables that gate, so old configs keep working unchanged.
Configurable keys:
  comp_floor, max_years_required, text_blockers, salary_sanity.{min_annual,max_annual}

The only literals in this module are fallback defaults (used when a config
key is absent) and structural parsing patterns (salary formats) — every
behavioral threshold is overridable via config.

Gates:
  comp_floor          — minimum acceptable annual salary (USD). Salary is
                        taken from the journal Salary Estimate column (filled
                        from Adzuna non-predicted salaries) or parsed from
                        the JD text ("$150,000–$180,000", "$120k"). Only
                        fires when a credible annual figure is found.
  max_years_required  — skip if the JD's stated years-of-experience
                        requirement exceeds this.
  text_blockers       — case-insensitive substrings that are instant skips.

Location/onsite gating was REMOVED (Aug 2026) — the search's own location
filter (config.json → search.locations) is the single source of truth, so
no redundant location/onsite gate runs here.

Usage (from run_scoring.py):
    from hard_constraints import check_hard_constraints
    skip, reasons = check_hard_constraints(job, description, salary_text, config)
"""

import re

# Annual-salary figure patterns for JD text scanning (structural format, not a
# tunable threshold — kept in code).
_SALARY_PATTERNS = [
    # $150,000 | $150,000–$180,000 | $150k - $180k
    r'\$\s?(\d{2,3}(?:,\d{3})?)\s*(?:[-–—]\s*\$?\s?(\d{2,3}(?:,\d{3})?))?',
    r'\$\s?(\d{2,3})\s?k\b\s*(?:[-–—]\s*\$?\s?(\d{2,3})\s?k)?',
]

# Fallback defaults — overridden by config.json → hard_constraints
_DEFAULT_SALARY_SANITY = {"min_annual": 50000, "max_annual": 2000000}


def _parse_number(s):
    """'150,000' -> 150000 ; '150k' -> 150000 (caller appends k)."""
    return int(str(s).replace(",", ""))


def _parse_salary_token(s, is_k, sanity):
    try:
        v = _parse_number(s)
    except (ValueError, AttributeError):
        return None
    if is_k:
        v *= 1000
    if v < sanity["min_annual"] or v > sanity["max_annual"]:
        return None
    return v


def _annual_figures_in(text, sanity):
    """Extract credible annual salary figures (USD) from text."""
    figures = []
    for pat in _SALARY_PATTERNS:
        for m in re.finditer(pat, text, re.I):
            lo = _parse_salary_token(m.group(1), 'k' in pat, sanity)
            hi = _parse_salary_token(m.group(2), 'k' in pat, sanity) if m.group(2) else None
            for v in (lo, hi):
                if v is not None:
                    figures.append(v)
    return figures


def extract_salary_range(text, sanity=None):
    """Extract a formatted annual salary range (e.g. '$150,000–$180,000') from
    JD text, or None if no credible range is found.

    Picks the highest credible range in the text (the most senior/representative
    figure). Returns a single value ('$150,000') when only one figure is found.
    """
    sanity = {**_DEFAULT_SALARY_SANITY, **(sanity or {})}
    best = None  # (lo, hi) tuple of the best range found
    for pat in _SALARY_PATTERNS:
        for m in re.finditer(pat, text, re.I):
            lo = _parse_salary_token(m.group(1), 'k' in pat, sanity)
            hi = _parse_salary_token(m.group(2), 'k' in pat, sanity) if m.group(2) else None
            if lo is None:
                continue
            # Prefer ranges over single figures; among ranges, the highest lo
            if best is None or (hi is not None and (best[1] is None or lo > best[0])):
                best = (lo, hi)
    if best is None:
        return None
    lo, hi = best
    if hi and hi > lo:
        return f"${lo:,}–${hi:,}"
    return f"${lo:,}"


def check_hard_constraints(job, description, salary_text="", config=None):
    """Evaluate all configured gates.

    Args:
        job: dict with 'title' and 'location'.
        description: full JD text (may be empty).
        salary_text: known salary string from the journal (e.g. "$135,624"),
                     empty if unknown.
        config: loaded config.json dict.

    Returns:
        (skip: bool, reasons: list[str]) — reasons is empty when no gate fires.
    """
    hc = (config or {}).get("hard_constraints") or {}
    reasons = []

    desc = str(description or "")
    desc_lower = desc.lower()

    sanity = {**_DEFAULT_SALARY_SANITY, **(hc.get("salary_sanity") or {})}

    # ── Compensation floor gate ──
    floor = hc.get("comp_floor")
    if floor:
        figures = _annual_figures_in(salary_text, sanity) + _annual_figures_in(desc, sanity)
        if figures:
            best = max(figures)
            if best < int(floor):
                reasons.append(f"Salary below floor (top figure ${best:,} < ${int(floor):,})")

    # ── Max years requirement gate ──
    max_years = hc.get("max_years_required")
    if max_years:
        m = re.search(r'(\d+)\+?\s*(?:\(\s*\w+\s*\)\s*)?years?(?:\s+of)?\s+(?:relevant\s+|professional\s+|related\s+)?experience', desc_lower) \
            or re.search(r'(\d+)\+?\s*years?', desc_lower)
        if m:
            try:
                years = int(m.group(1))
            except ValueError:
                years = 0
            if years > int(max_years):
                reasons.append(f"Requires {years}+ years experience (over limit {int(max_years)})")

    # ── Text blockers gate ──
    for blocker in hc.get("text_blockers") or []:
        b = str(blocker).lower()
        if b and b in desc_lower:
            reasons.append(f"Text blocker: \"{blocker}\"")

    return (len(reasons) > 0, reasons)