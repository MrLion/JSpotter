#!/usr/bin/env python3
"""
Hard-constraint gates — deal-breaker checks run BEFORE job scoring.

A job that fails any gate is never scored or prioritized; it gets
Recommendation = "SKIP: <reason>" in the journal instead. This prevents a
high skills match from papering over a fundamental constraint (location,
work authorization, compensation floor, excessive experience requirement).

ALL thresholds come from config.json → hard_constraints. A missing key or
null value disables that gate, so old configs keep working unchanged.
Configurable keys:
  comp_floor, allowed_locations, location_tokens, remote_tokens,
  onsite_tolerance, onsite_phrases, max_years_required, text_blockers,
  salary_sanity.{min_annual,max_annual}, specific_location_states,
  generic_onsite_words

The only literals in this module are fallback defaults (used when a config
key is absent) and structural parsing patterns (salary/state formats) — every
behavioral threshold is overridable via config.

Gates:
  comp_floor          — minimum acceptable annual salary (USD). Salary is
                        taken from the journal Salary Estimate column (filled
                        from Adzuna non-predicted salaries) or parsed from
                        the JD text ("$150,000–$180,000", "$120k"). Only
                        fires when a credible annual figure is found.
  allowed_locations   — acceptable locations. A job whose location names a
                        specific OTHER city/state and shows no remote signal
                        anywhere in title/location/description fails the gate.
  onsite_tolerance    — "hybrid" (default) | "onsite" | "remote". Fires when
                        the JD demands fully on-site work AND the location is
                        not explicitly allowed AND there is no remote signal.
  max_years_required  — skip if the JD's stated years-of-experience
                        requirement exceeds this.
  text_blockers       — case-insensitive substrings that are instant skips.

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
_DEFAULT_REMOTE_TOKENS = ("remote", "work from home", "wfh", "distributed",
                          "anywhere in the us", "us remote", "remote-first")
_DEFAULT_ONSITE_PHRASES = (
    "on-site 5 days", "onsite 5 days", "in-office 5 days", "in office 5 days",
    "100% onsite", "100% on-site", "fully onsite", "fully on-site",
    "five days a week on-site", "5 days/week on-site", "on-site, 5",
)
_DEFAULT_GENERIC_ONSITE_WORDS = {"downtown", "headquarters", "office", "campus", "hq",
                                 "the", "our", "a", "an", "one", "person", "hybrid"}
_DEFAULT_SPECIFIC_STATES = [
    "ma", "ny", "ca", "tx", "fl", "il", "pa", "oh", "ga", "nc", "va", "wa",
    "az", "co", "ut", "ct", "ri",
    "massachusetts", "new york", "california", "texas", "florida", "illinois",
    "pennsylvania", "ohio", "georgia", "north carolina", "virginia", "washington",
    "arizona", "colorado", "utah", "connecticut", "rhode island",
]
_DEFAULT_NATIONWIDE_RE = r'\bunited states\b|\busa\b|\b(us|u\.s\.)\b'


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


def _has_remote_signal(text_lower, remote_tokens):
    return any(t in text_lower for t in remote_tokens)


def _build_location_tokens(allowed_locations, location_tokens):
    """Flatten allowed locations into a token list. Uses the location_tokens
    map when present, else derives tokens from the location names themselves."""
    tokens = []
    for loc in allowed_locations or []:
        loc_lower = str(loc).lower()
        if location_tokens and loc in location_tokens:
            tokens.extend(location_tokens[loc])
        else:
            tokens.append(loc_lower)
    return tokens


def _build_specific_re(states):
    states = states or _DEFAULT_SPECIFIC_STATES
    return re.compile(r',\s*(?:' + '|'.join(re.escape(s) for s in states) + r')\b', re.I)


def _location_allowed(location_lower, location_tokens, nationwide_re):
    if any(t in location_lower for t in location_tokens):
        return True
    if re.search(nationwide_re, location_lower):
        return True
    return False


def _onsite_city(desc_lower, generic_words):
    """Extract a city name from an on-site demand phrase, or None.
    'fully on-site 5 days a week in our nyc headquarters' -> 'nyc'
    'on-site 5 days a week in our downtown office'        -> None (no city)
    """
    m = re.search(
        r'on-?site[^.]{0,80}?\bin (?:our |the )?([a-z][a-z ]{1,25}?)'
        r'(?:,|\.| headquarters| office| campus| hq\b|$)',
        desc_lower)
    if not m:
        return None
    words = [w for w in m.group(1).split() if w not in generic_words]
    return " ".join(words) if words else None


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

    location = str(job.get("location", "") or "")
    location_lower = location.lower()
    desc = str(description or "")
    desc_lower = desc.lower()

    # Config-driven token sets (fall back to defaults when absent)
    allowed = hc.get("allowed_locations")
    location_tokens = _build_location_tokens(allowed, hc.get("location_tokens"))
    remote_tokens = hc.get("remote_tokens") or _DEFAULT_REMOTE_TOKENS
    onsite_phrases = hc.get("onsite_phrases") or _DEFAULT_ONSITE_PHRASES
    generic_words = set(hc.get("generic_onsite_words") or _DEFAULT_GENERIC_ONSITE_WORDS)
    sanity = {**_DEFAULT_SALARY_SANITY, **(hc.get("salary_sanity") or {})}
    specific_re = _build_specific_re(hc.get("specific_location_states"))
    nationwide_re = re.compile(_DEFAULT_NATIONWIDE_RE, re.I)

    # ── Location gate ──
    if allowed and location.strip():
        if not _location_allowed(location_lower, location_tokens, nationwide_re) \
                and not _has_remote_signal(desc_lower, remote_tokens):
            if specific_re.search(location_lower):
                reasons.append(f"Location: {location} (not in {', '.join(allowed)}, no remote signal)")

    # ── Onsite tolerance gate ──
    tolerance = (hc.get("onsite_tolerance") or "").lower()
    if tolerance in ("hybrid", "remote") and desc_lower:
        demands_onsite = any(p in desc_lower for p in onsite_phrases) or \
            (re.search(r'\bon-?site\b', desc_lower) and re.search(r'\b5\s*days\b|\bfive days\b', desc_lower))
        if demands_onsite and not _has_remote_signal(desc_lower, remote_tokens):
            onsite_city = _onsite_city(desc_lower, generic_words)
            if onsite_city:
                # City named in the JD itself governs, even if the posting
                # location is generic ("United States").
                if not _location_allowed(onsite_city, location_tokens, nationwide_re):
                    reasons.append(f"Requires fully on-site work in {onsite_city}")
            elif not _location_allowed(location_lower, location_tokens, nationwide_re):
                reasons.append("Requires fully on-site work outside allowed locations")

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