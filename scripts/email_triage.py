#!/usr/bin/env python3
"""
iCloud email triage scanner for a job search.

Scans the iCloud inbox via himalaya for employer emails and classifies
each into a type: rejection, interview, confirmation,
referral, or unknown (None). Prints classified candidates as JSON to
stdout so a downstream consumer (cron agent) can act on them.

Output shape (one JSON object):
  {
    "found_ts": ...,
    "window_days": N,
    "accounts": ["icloud", "gmail"],
    "total_scanned": M,
    "counts": {"rejection": n, "interview": n,
               "confirmation": n, "referral": n, "other": n},
    "new_candidates": [
      {"id": 23084, "date": ..., "from": ..., "subject": ...,
       "snippet": "...", "type": "rejection"}
    ],
    "all_candidate_ids": [...]
  }

Counts and new_candidates both reflect only NEW candidates (not seen in
prior runs); all_candidate_ids lists every candidate detected this run.

Dedupes across runs using a state file so the same email is only
reported once.

Configuration (env vars, all optional with defaults):
  EMJ_STATE        — path to the dedupe state file (default:
                     <project>/output/email_triage_seen.json)
  EMJ_ACCOUNTS     — comma-separated himalaya accounts to scan
                     (default: icloud,gmail)
  EMJ_MAILBOX      — himalaya mailbox to scan per account (default: Inbox)
  EMJ_WINDOW_DAYS  — look back window in days (default: 3)
  HIMALAYA_CMD     — himalaya binary name/path (default: himalaya)

Each candidate is tagged with its "account" (e.g. "icloud" or "gmail") so a
downstream consumer knows which himalaya account holds the message. Because
message IDs are per-account (iCloud and Gmail both number from 1), the dedupe
state is keyed by "account:id".

Requires the `himalaya` CLI configured for the target accounts.
Standard library only — no third-party dependencies.
"""

import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# --- Configuration (env-overridable, machine-independent defaults) ----------
def _default_state_file():
    """State file lives in the project's gitignored output/ dir (local-only),
    following the same BASE_DIR convention as the other pipeline scripts.
    """
    return str(BASE_DIR / "output" / "email_triage_seen.json")


STATE_FILE = os.environ.get("EMJ_STATE", _default_state_file())
STATE_DIR = os.path.dirname(STATE_FILE)
ACCOUNTS = [a.strip() for a in os.environ.get("EMJ_ACCOUNTS", "icloud,gmail").split(",") if a.strip()]
MAILBOX = os.environ.get("EMJ_MAILBOX", "Inbox")
WINDOW_DAYS = int(os.environ.get("EMJ_WINDOW_DAYS", "3"))
HIMALAYA = os.environ.get("HIMALAYA_CMD", "himalaya")

# --- Classification signals (matched against subject + body, lowercased) ----

# Definite rejection — checked first so a "thank you for applying" email
# that also says "unable to offer" is NOT miscounted as a confirmation.
REJECT_PATTERNS = [
    r"not moving forward",
    r"no longer (?:recruiting|considering|being)",
    r"unable to offer",
    r"we won't be moving",
    r"will not be (?:moving|proceeding)",
    r"decided not to",
    r"another candidate",
    r"we regret to inform",
    r"position.*has been filled",
    r"do not match.*qualifications",
    r"no longer under consideration",
    r"is no longer available",
    r"will not be advancing",
    r"not selected for",
]

# Stronger rejection signals; "unfortunately" alone is weak.
STRONG_PATTERNS = [
    r"not moving forward",
    r"unable to offer",
    r"will not be moving forward",
    r"no longer recruiting",
    r"no longer under consideration",
    r"we regret to inform",
]

# Interview requests / scheduling invites (ACTION REQUIRED).
# Match on the SUBJECT line — genuine interview emails almost always have
# "interview" (or screen/onsite) in the subject (e.g. "Interview Invitation",
# "Interview Reminder", "Phone Interview Request", "Onsite Interview").
# This is far more accurate than body heuristics, which over-match on
# newsletter boilerplate ("next steps", "availability", "interview resources").
INTERVIEW_PATTERNS = [
    r"interview",
    r"phone (?:screen|interview)",
    r"onsite interview",
    r"technical screen",
    r"interview.{0,12}(?:invitation|invite|request|availability|reminder|scheduled|rescheduled|update|confirm|hold)",
]

# Application received / under review (not a decision).
APPLICATION_CONFIRM_PATTERNS = [
    r"thank you for applying",
    r"thanks for applying",
    r"thank you for your interest",
    r"thank you for your application",
    r"application received",
    r"received your application",
    r"received your resume",
    r"we received your application",
    r"under review",
    r"currently reviewing",
    r"we are reviewing your application",
    r"application has been submitted",
    r"keep track of its status",
    r"you have applied",
    r"application was sent",
    r"your application was sent",
    r"application sent to",
]

# Referrals / recommendations.
REFERRAL_PATTERNS = [
    r"referred you to",
    r"has referred you",
    r"has recommended you",
    r"referred you for",
    r"referred you for a role",
    r"you were referred",
    r"recommended you for",
]

# Known non-employer / newsletter senders to exclude entirely.
# (amazon.jobs is intentionally NOT here — Amazon sends referral and
# application-confirmation emails that we now want to classify.)
NON_EMPLOYER = [
    "a16z", "fidelity", "charles schwab", "colonial volkswagen",
    "santander", "social security", "national grid", "redfin",
    "hbr executive", "hbr analytic", "the substack post", "nyc ferry",
    "fundstrat", "malibu invest", "one knight in product", "john cutler",
    "nick gerli", "rosco", "tom lee",
    "rsm - shrewsbury", "rsm shrewsbury", "capital one",
]


def run(cmd):
    """Run a shell command and return stdout."""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    return r.stdout


def load_seen():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_seen(ids):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(ids), f)


def get_envelopes(account):
    """Fetch recent inbox envelopes as JSON via himalaya for an account."""
    out = run(f'{HIMALAYA} -a {account} envelope list --mailbox "{MAILBOX}" --json --page-size 200')
    try:
        data = json.loads(out)
        return data.get("envelopes", [])
    except Exception as e:
        print(f"ERR_PARSE_ENVELOPES[{account}]", e, file=sys.stderr)
        print(out[:500], file=sys.stderr)
        return []


def get_message_body(account, mid):
    """Fetch message text (plain part) for a given envelope id in an account."""
    out = run(f'{HIMALAYA} -a {account} message read --mailbox "{MAILBOX}" {mid} 2>/dev/null')
    # Strip HTML tags and long whitespace to get searchable text.
    text = re.sub(r"<[^>]+>", " ", out)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def classify(subject, body):
    """Return a classification string, or None for unclassified.

    Priority: rejection > confirmation > referral > interview.

    Order matters: an application-confirmation email often contains
    boilerplate words like "interview resources" or "next steps" — so we
    must match the definitive confirmation FIRST. "Interview request" is
    matched on the SUBJECT line only (genuine interview emails carry
    "interview"/"onsite"/"screen" in the subject); body matching is too
    noisy because newsletters reuse the same words.
    """
    haystack = (subject + " " + body).lower()
    subject_l = subject.lower()

    # Rejection first (strong signal wins over a "thank you" confirmation).
    strong = any(re.search(p, haystack) for p in STRONG_PATTERNS)
    any_reject = any(re.search(p, haystack) for p in REJECT_PATTERNS)
    if any_reject and ("unfortunately" not in haystack or strong):
        return "rejection"

    # Definitive application confirmation / under-review — before interview,
    # because these emails routinely mention "interview" as generic advice.
    if any(re.search(p, haystack) for p in APPLICATION_CONFIRM_PATTERNS):
        return "confirmation"

    if any(re.search(p, haystack) for p in REFERRAL_PATTERNS):
        return "referral"

    # Interview requests: subject-only match.
    if any(re.search(p, subject_l) for p in INTERVIEW_PATTERNS):
        return "interview"

    return None


def main():
    seen = load_seen()
    now = datetime.now(timezone.utc)
    candidates = []
    total_scanned = 0

    for account in ACCOUNTS:
        envelopes = get_envelopes(account)
        total_scanned += len(envelopes)

        for env in envelopes:
            mid = env.get("id")
            if not mid:
                continue
            key = f"{account}:{mid}"
            if key in seen:
                continue
            date_raw = env.get("date", "")
            # Skip if outside window (best-effort parse)
            try:
                d = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
            except Exception:
                d = None
            if d and (now - d).days > WINDOW_DAYS:
                continue
            subject = env.get("subject", "") or ""
            frm = " ".join(a.get("name", "") or a.get("email", "") for a in env.get("from", []))
            frm_l = frm.lower()
            if any(x in frm_l for x in NON_EMPLOYER):
                continue

            body = get_message_body(account, mid)
            etype = classify(subject, body)
            if etype:
                candidates.append({
                    "account": account,
                    "id": str(mid),
                    "date": date_raw,
                    "from": frm,
                    "subject": subject,
                    "snippet": body[:200],
                    "type": etype,
                })

    # Report only NEW candidates (not previously seen).
    new_candidates = [c for c in candidates if f"{c['account']}:{c['id']}" not in seen]

    # Mark all detected candidate IDs as seen so each email is reported only once.
    seen.update(f"{c['account']}:{c['id']}" for c in candidates)
    save_seen(seen)

    # Counts reflect NEW candidates only, so consumers keyed on counts
    # don't re-report emails already delivered in a previous run.
    counts = Counter(c["type"] for c in new_candidates)
    result = {
        "found_ts": now.isoformat(),
        "window_days": WINDOW_DAYS,
        "accounts": ACCOUNTS,
        "total_scanned": total_scanned,
        "counts": dict(counts),
        "new_candidates": new_candidates,
        "all_candidate_ids": [f"{c['account']}:{c['id']}" for c in candidates],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
