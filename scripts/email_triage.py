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
    "counts": {"rejection": n, "closed": n, "interview": n,
               "confirmation": n, "referral": n, "other": n},
    "unclassified": {"count": n, "ids": ["account:id", ...]},
    "new_candidates": [
      {"id": 23084, "date": ..., "from": ..., "subject": ...,
       "snippet": "...", "type": "rejection"}
    ],
    "all_candidate_ids": [...]
  }

Counts and new_candidates both reflect only NEW candidates (not seen in
prior runs); all_candidate_ids lists every candidate detected this run.

Dedupes across runs using a state file so the same email is only
reported once. Emails are marked as seen (acked) ONLY after they are
delivered — run with `EMJ_ACK="account:id,account:id"` to acknowledge
delivery. Without an ack, detected emails stay pending and are
re-reported next run, so a failed/silent run never drops an email.

Configuration (env vars, all optional with defaults):
  EMJ_STATE        — path to the dedupe state file (default:
                     <project>/output/email_triage_seen.json)
  EMJ_ACCOUNTS     — comma-separated himalaya accounts to scan
                     (default: icloud,gmail)
  EMJ_MAILBOX      — himalaya mailbox to scan per account (default: Inbox)
  EMJ_WINDOW_DAYS  — look back window in days (default: 7)
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
WINDOW_DAYS = int(os.environ.get("EMJ_WINDOW_DAYS", "7"))
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
# The rejection gate (classify) only accepts a REJECT match when the email
# also carries an "unfortunately" softener OR one of these STRONG signals.
# This list must therefore carry the explicit candidate-decision phrasings
# that recruiters use in matter-of-fact relayed rejections — those emails
# have no softener, and if they sit here as weak REJECT patterns only, they
# silently fall through to confirmation ("thank you for applying" line).
# Real case: MBTA "they will not be moving you forward in the process"
# classified as confirmation on 2026-09-16 and was never surfaced.
STRONG_PATTERNS = [
    r"not moving forward",
    r"unable to offer",
    r"will not be moving forward",
    r"not be moving you forward",
    r"decided to (?:go|move) in a different direction",
    r"decided to move forward with (?:other|different) candidates",
    r"passing on your (?:candidacy|application|profile)",
    r"no longer recruiting",
    r"no longer under consideration",
    r"we regret to inform",
    # Same-day ATS auto-rejection phrasing. Subject line is usually
    # "Thank you for your interest in <company>!" — i.e. it reads like a
    # confirmation — while the body is a rejection. Both phrases are
    # unambiguous candidate decisions, so they reject alone.
    r"identified candidates that are a (?:closer|better) match",
    r"a closer match to our needs",
    r"candidates that are a (?:closer|better) fit",
]

# Position-closed / withdrawn signals — the REQ was closed (filled or pulled)
# with no candidate-specific decision. Distinct from a candidate rejection:
# the journal keeps these two end states separate (Closed vs Rejected).
CLOSED_PATTERNS = [
    r"position.*(?:is|has been) (?:now )?closed",
    r"now closed",
    r"position has been filled",
    r"position is (?:no longer|now) available",
    r"this (?:position|role).*(?:closed|filled)",
    r"the position is closed",
    r"won't be moving forward with interviews because the position is now closed",
    r"position.*been withdrawn",
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

# Strong scheduling / recruiter-call signals. These indicate an actual
# request to meet (not generic "interview resources" boilerplate), so they
# override a "thank you for applying" confirmation line.
STRONG_INTERVIEW_PATTERNS = [
    r"recruiter call",
    r"recruiter screen",
    r"schedule.{0,15}(?:time|call|connect|meet|interview|screen)",
    r"let me know your availability",
    r"availability.{0,15}(?:call|interview|screen|meet)",
    r"set up.{0,15}(?:call|interview|screen|meet|time)",
    r"book.{0,15}(?:call|interview|screen|meet|time)",
    # Invites phrased without the word "interview" (Zeitview-style: a recruiter
    # offering "next steps" + a short call + a self-serve scheduling link).
    # These would otherwise fall through to the "received your application"
    # confirmation branch even though they are an explicit request to meet.
    # Negation-guarded: a rejection saying "not moving you forward" must never
    # match, and the rejection gate runs before this block anyway.
    r"(?<!not )(?<!unable to )move you forward to the next step",
    r"(?:love|happy|pleased|excited|glad) to (?:move|advance) you (?:forward )?to the next step",
    r"\b\d{1,3}[ -]minute (?:phone|video|virtual|introductory|screening) (?:call|conversation|screen|interview)",
    r"\b\d{1,3}[ -]min(?:ute)?s?[ -](?:phone|video|virtual|introductory) (?:call|conversation)",
    r"(?:pick|select|choose) a (?:time slot|slot|day and time|time that works)",
    r"select the day and time",
    r"receive a calendar invite",
    # A booked interview stated without the word "interview" in the subject,
    # and the bare calendar/video invites that follow it (Teams/Zoom/Meet links
    # carry no other scheduling language). Real case: a recruiter wrote
    # "Your interview with <client> is confirmed for Friday, 10/30 1:00 PM-1:30 PM"
    # in a reply thread whose subject was the original outreach line — it
    # classified as None and was never surfaced, while the client's Teams
    # invite also went undelivered.
    r"interview(?: with [^.]{0,60})? (?:is|has been) confirmed",
    r"confirmed for (?:mon|tues|wednes|thurs|fri|satur|sun)day",
    r"(?:sent|sending|send) you the (?:video|calendar|teams) invite",
    r"\bvideo invite\b",
    r"microsoft teams meeting",
    r"teams\.microsoft\.com/meet",
    r"zoom\.us/(?:j|my|s)/",
    r"meet\.google\.com/",
    r"meeting id:\s*[\d ]{9,}",
    r"dial in by phone",
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

# Unclassified-telemetry scope (commit 6459f9e follow-up): which
# unclassified emails are worth surfacing. Recruiter chatter, cold
# outreach, and marketing don't track — a rejection-shaped email does.
# An unacked, in-window email is counted ONLY if its subject reads
# application-ish OR its sender is a known ATS domain. Keeps the
# counter at "possible decisions", not "everything unclassified".
UNCLASSIFIED_SUBJECT_PATTERNS = [
    r"application",
    r"position",
    r"candidacy",
    r"\brole\b",
    r"opportunit",
    r"\bnext step",
]
UNCLASSIFIED_SENDER_PATTERNS = [
    r"myworkday", r"workdayjobs", r"greenhouse", r"ashbyhq", r"lever\.",
    r"rippling", r"icims", r"smartrecruiters", r"jobvite",
    r"successfactors", r"governmentjobs", r"\badp\b", r"ceipal",
    r"phenom", r"\bjobvite\b",
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

    Priority: rejection > closed > strong-interview > confirmation > referral > interview.

    Order matters: an application-confirmation email often contains
    boilerplate words like "interview resources" or "next steps" — so we
    must match the definitive confirmation FIRST. "Interview request" is
    matched on the SUBJECT line only (genuine interview emails carry
    "interview"/"onsite"/"screen" in the subject); body matching is too
    noisy because newsletters reuse the same words.
    """
    haystack = (subject + " " + body).lower()
    subject_l = subject.lower()

    # Position-closed / withdrawn — the req itself was closed, not the
    # candidate declined. Distinct terminal state (journal keeps Closed and
    # Rejected separate). Check BEFORE the rejection gate: Aledade-style
    # emails contain BOTH strong-reject phrasing ("will not be moving
    # forward with interviews") and closed phrasing ("position is now
    # closed") — the closed phrases must win.
    # "Thank you for your interest" + "position is now closed" → closed.
    if any(re.search(p, haystack) for p in CLOSED_PATTERNS):
        return "closed"

    # Rejection first (strong signal wins over a "thank you" confirmation).
    # Semantics: an explicit candidate-decision phrase (STRONG) rejects on
    # its own. Weak REJECT phrases (e.g. "is no longer available" — which
    # appears in benign contexts) need corroboration: an "unfortunately"
    # softener, a STRONG match, or a second weak phrase match. Do NOT gate
    # strong signals behind a weak match: MBTA's "will not be moving you
    # forward" (relayed by the recruiter, no "unfortunately") fell through
    # to confirmation on 2026-09-16 under the old gate.
    strong_matches = [p for p in STRONG_PATTERNS if re.search(p, haystack)]
    weak_matches = [p for p in REJECT_PATTERNS if re.search(p, haystack)]
    strong = bool(strong_matches)
    if strong or len(weak_matches) >= 2 or (weak_matches and "unfortunately" in haystack):
        return "rejection"

    # Strong scheduling / recruiter-call signal — an actual request to meet
    # overrides a generic "thank you for applying" confirmation line.
    if any(re.search(p, haystack) for p in STRONG_INTERVIEW_PATTERNS):
        return "interview"

    # Definitive application confirmation / under-review — before weak
    # interview signals, because these emails routinely mention "interview"
    # as generic advice.
    if any(re.search(p, haystack) for p in APPLICATION_CONFIRM_PATTERNS):
        return "confirmation"

    if any(re.search(p, haystack) for p in REFERRAL_PATTERNS):
        return "referral"

    # Interview requests: subject-only match (weak signal).
    if any(re.search(p, subject_l) for p in INTERVIEW_PATTERNS):
        return "interview"

    return None


def ack(ids):
    """Mark the given account:id keys as seen (acknowledged/delivered).

    Called by the cron agent AFTER it successfully produces and delivers
    the digest. Without an ack, an email stays pending and is re-reported
    on the next run — so a missed/failed run never silently drops an email.
    """
    seen = load_seen()
    seen.update(ids)
    save_seen(seen)
    print(json.dumps({"acked": sorted(ids)}))


def main():
    # --ack: mark IDs as delivered and exit (no scan).
    ack_raw = os.environ.get("EMJ_ACK", "").strip()
    if ack_raw:
        ids = [x.strip() for x in ack_raw.replace("|", ",").split(",") if x.strip()]
        if ids:
            ack(ids)
            return

    seen = load_seen()
    now = datetime.now(timezone.utc)
    candidates = []
    total_scanned = 0
    unclassified = []

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
            else:
                # In-window, unacked, employer-ish email that matched NO
                # pattern. Track it as telemetry ONLY when it looks like a
                # decision email (application-ish subject or known ATS
                # sender) — recruiter chatter and cold outreach are not
                # tracked, keeping the counter actionable.
                track = (
                    any(re.search(p, subject.lower()) for p in UNCLASSIFIED_SUBJECT_PATTERNS)
                    or any(re.search(p, frm_l) for p in UNCLASSIFIED_SENDER_PATTERNS)
                )
                if track:
                    unclassified.append(key)

    # Report all un-seen candidates as NEW (pending delivery). They are NOT
    # auto-marked as seen here — a run that detects them but fails to deliver
    # (e.g. returns [SILENT]) must not drop them. The cron agent acks them
    # via EMJ_ACK only after the digest is delivered.
    new_candidates = [c for c in candidates if f"{c['account']}:{c['id']}" not in seen]

    # Counts reflect NEW (pending delivery) candidates only.
    counts = Counter(c["type"] for c in new_candidates)
    result = {
        "found_ts": now.isoformat(),
        "window_days": WINDOW_DAYS,
        "accounts": ACCOUNTS,
        "total_scanned": total_scanned,
        "counts": dict(counts),
        "unclassified": {"count": len(unclassified), "ids": unclassified},
        "new_candidates": new_candidates,
        "all_candidate_ids": [f"{c['account']}:{c['id']}" for c in candidates],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
