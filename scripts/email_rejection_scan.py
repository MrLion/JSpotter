#!/usr/bin/env python3
"""
iCloud email rejection scanner for a job search.

Scans the iCloud inbox via himalaya for employer rejection emails
(sent in the last N days) and prints them as JSON to stdout so a
downstream consumer (cron agent) can validate them against a job
journal and notify the user.

Output shape (one JSON object):
  {
    "found_ts": ...,
    "window_days": N,
    "total_scanned": M,
    "new_candidates": [
      {"id": 23084, "date": ..., "from": ..., "subject": ..., "snippet": "..."}
    ],
    "all_candidate_ids": [...]
  }

Dedupes across runs using a state file so the same email is only
reported once.

Configuration (env vars, all optional with defaults):
  EMJ_STATE        — path to the dedupe state file (default:
                     $XDG_STATE_HOME/email_rejection_seen.json, or
                     ~/.local/state/email_rejection_seen.json)
  EMJ_MAILBOX      — himalaya mailbox to scan (default: Inbox)
  EMJ_WINDOW_DAYS  — look back window in days (default: 3)
  HIMALAYA_CMD     — himalaya binary name/path (default: himalaya)

Requires the `himalaya` CLI configured for the target account.
Standard library only — no third-party dependencies.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

# --- Configuration (env-overridable, machine-independent defaults) ----------
def _default_state_file():
    """Pick a sensible default state-file path that any machine can use."""
    if os.environ.get("XDG_STATE_HOME"):
        base = os.environ["XDG_STATE_HOME"]
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "email_rejection_seen.json")


STATE_FILE = os.environ.get("EMJ_STATE", _default_state_file())
STATE_DIR = os.path.dirname(STATE_FILE)
MAILBOX = os.environ.get("EMJ_MAILBOX", "Inbox")
WINDOW_DAYS = int(os.environ.get("EMJ_WINDOW_DAYS", "3"))
HIMALAYA = os.environ.get("HIMALAYA_CMD", "himalaya")

# Rejection signals found in subject OR body text.
REJECT_PATTERNS = [
    r"not moving forward",
    r"no longer (?:recruiting|considering|being)",
    r"unable to offer",
    r"we won't be moving",
    r"will not be (?:moving|proceeding)",
    r"decided not to",
    r"another candidate",
    r"unfortunately",
    r"we regret to inform",
    r"position.*has been filled",
    r"do not match.*qualifications",
    r"no longer under consideration",
    r"is no longer available",
]

# Stronger signals = definite rejection; these override ambiguous ones.
STRONG_PATTERNS = [
    r"not moving forward",
    r"unable to offer",
    r"will not be moving forward",
    r"no longer recruiting",
    r"no longer under consideration",
    r"we regret to inform",
]

# Known non-employer senders to exclude (finance/news/notifications).
NON_EMPLOYER = [
    "a16z", "fidelity", "charles schwab", "colonial volkswagen",
    "santander", "amazon.jobs",  # amazon jobs application-confirmation (not rejection, handled by journal check)
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


def get_envelopes():
    """Fetch recent inbox envelopes as JSON via himalaya."""
    out = run(f'{HIMALAYA} envelope list --mailbox "{MAILBOX}" --json --page-size 200')
    try:
        data = json.loads(out)
        return data.get("envelopes", [])
    except Exception as e:
        print("ERR_PARSE_ENVELOPES", e, file=sys.stderr)
        print(out[:500], file=sys.stderr)
        return []


def get_message_body(mid):
    """Fetch message text (plain part) for a given envelope id."""
    out = run(f'{HIMALAYA} message read --mailbox "{MAILBOX}" {mid} 2>/dev/null')
    # Strip HTML tags and long whitespace to get searchable text.
    text = re.sub(r"<[^>]+>", " ", out)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def is_rejection(subject, body):
    """Decide whether a message is a rejection."""
    haystack = (subject + " " + body).lower()
    strong_hit = any(re.search(p, haystack) for p in STRONG_PATTERNS)
    any_hit = any(re.search(p, haystack) for p in REJECT_PATTERNS)
    # "unfortunately" alone is weak; require a stronger signal alongside.
    if any_hit and ("unfortunately" not in haystack or strong_hit):
        return True
    return False


def main():
    seen = load_seen()
    envelopes = get_envelopes()
    now = datetime.now(timezone.utc)
    candidates = []

    for env in envelopes:
        mid = env.get("id")
        if not mid or str(mid) in seen:
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

        body = get_message_body(mid)
        if is_rejection(subject, body):
            candidates.append({
                "id": str(mid),
                "date": date_raw,
                "from": frm,
                "subject": subject,
                "snippet": body[:200],
            })

    # Report only NEW candidates (not previously seen).
    new_candidates = [c for c in candidates if c["id"] not in seen]

    # Mark all detected candidate IDs as seen so each email is reported only once.
    seen.update(c["id"] for c in candidates)
    save_seen(seen)

    result = {
        "found_ts": now.isoformat(),
        "window_days": WINDOW_DAYS,
        "total_scanned": len(envelopes),
        "new_candidates": new_candidates,
        "all_candidate_ids": [c["id"] for c in candidates],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
