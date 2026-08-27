# Cron Jobs

JSpotter uses Hermes cron jobs for automated daily tasks. This guide covers setup, configuration, and troubleshooting.

## Browser Configuration

The daily LinkedIn scan uses the guest API directly (no browser/login), so the cron runs unattended without browser access. A browser is only needed if you also automate the **Dice search** (`search_dice.py`), which requires login. If you do, set the browser engine to Playwright to avoid Chrome remote debugging approval popups:

```bash
hermes config set browser.engine playwright
hermes gateway restart
```

Chrome requires per-connection "Allow remote debugging?" approval which blocks unattended cron runs. Playwright uses its own Chromium instance — no popup needed.

## Daily Job Scan

Runs the full search → add → score pipeline every morning and delivers a summary to Telegram.

### Setup

1. **Create `run_daily.sh`** in your project root:

```bash
#!/bin/bash
PYBIN="/path/to/python3"
cd "/path/to/Job hunting" || exit 1

echo "=== Step 1: LinkedIn Search ==="
PYTHONPATH="" "$PYBIN" scripts/search_linkedin.py 2>&1

echo "=== Step 2: Add to Journal ==="
PYTHONPATH="" "$PYBIN" scripts/journal.py --add output/linkedin_extract.json 2>&1

echo "=== Step 3: Score New Jobs ==="
PYTHONPATH="" "$PYBIN" scripts/run_scoring.py 2>&1

echo "=== DONE ==="
```

2. **Make it executable:**
```bash
chmod +x run_daily.sh
```

3. **Add to allowlist** in `~/.hermes/config.yaml`:
```yaml
command_allowlist:
  - "bash run_daily.sh"
```

4. **Create the cron job** (via Hermes):
```bash
hermes cron create "0 9 * * *"
```

Or use the `cronjob` tool:
- Schedule: `0 9 * * *`
- Deliver: `telegram:<chat_id>`
- Toolsets: `terminal`, `file`
- Workdir: your project path

5. **Restart Hermes** for config changes to take effect.

### Cron Prompt Rules

The prompt must enforce:

1. **Run `bash run_daily.sh` only** — no direct Python calls
2. **Read TELEGRAM_TEMPLATE.md** for report format
3. **Final response = the Telegram message** — nothing else
4. **No narration** — no "here is the report," no pipeline summaries
5. **Keep response short** — max 10 high-priority jobs with details

### Report Template

See `TELEGRAM_TEMPLATE.md` for the daily report format. Key rules:
- High priority jobs: full detail (company, title, scores, location, URL)
- Medium/Low priority: counts only
- Bottom line: applied, interviews, rejected, closed counts

### Search Configuration

Search locations and keywords are configured in `config.json`:
- `search.locations` — list of LinkedIn location filters (e.g., USA with `linkedin_filter: "United States"`)
- `search.keywords` — search query string (e.g., "product manager AI")
- `search.title_filter_terms` — title words to include (manager, director, vp, head, lead, owner)
- `search.max_results_per_search` — max results per location

To add Dice.com as a second source, run `search_dice.py` (requires login — cookies persist between runs).

### Journal Data Integrity

The journal automatically validates rows on every `add_jobs()` call via `validate_journal_rows()`:
- Job ID must not contain URLs
- Status must be in {Not Applied, Applied, Interview, Rejected, Closed, Withdrawn}
- Priority must be in {High, Medium, Low}
- Date Applied must not contain URLs
- App URL must not contain status words

### Status Updates

Use `update_status()` from `journal.py` for all status changes:
```python
from journal import update_status
update_status("Company", "Applied")           # all roles for company
update_status("Company", "Rejected", title="Specific Title")  # one role only
```

This automatically:
- Updates Status + Last Updated columns
- Sets Date Applied if Applied
- Color-codes the company cell
- Archives PDFs/TXTs to `tailored/archived/` for Rejected/Closed/Withdrawn

### Duplicate Handling

Journal dedup is URL-based. Cross-source duplicates (LinkedIn + Dice) may have different URLs for the same job — manual dedup may be needed when same company + title appears from both sources.

## LinkedIn Post Ideas

Generates 5 post ideas every Wednesday based on trending PM/AI topics.

- Schedule: `30 8 * * 3` (Wednesday 8:30 AM)
- Toolsets: `browser`, `file` (no terminal — runs autonomously, no approval prompts)
- Sources: Lenny's Newsletter, a16z, Hugging Face, OpenAI, Anthropic
- Output: saved to `linkedin/ideas_{DATE}.md` and delivered to Telegram

Rules:
- Every idea MUST include a source URL — agent must visit the source site, not invent topics from memory
- The topic leads — posts are community commentary, not personal case studies
- Pitches must NOT start with "I" or center on the user's experience
- See `LINKEDIN_IDEAS_TEMPLATE.md` for the format

## Daily Email Triage Check

Runs every morning to scan the **iCloud and Gmail** inboxes (via `himalaya`) for employer emails and classify them as rejection / interview / confirmation / referral.

- Schedule: `0 9 * * *` (daily 9 AM)
- Script: `scripts/email_triage.py` — reads both inboxes via `himalaya` (`-a icloud` / `-a gmail`), dedupes across runs with a state file (`output/email_triage_seen.json`), and outputs classified candidates as JSON
- Delivers to Telegram + Bot Chat
- The bot validates each flagged email against the job journal before reporting it, so rejections/interviews are only surfaced for applications that were actually made (avoids misattributing an email to a company never applied to). Rejections get flagged for status updates, interviews are surfaced as action required.
- Both **rejections and application confirmations** are handed off to @job-hunter for journal updates: rejections → mark status `Rejected`; confirmations → mark status `Applied` (where not already recorded/Applied). @job-hunter cross-checks each against the journal before changing anything.
- Type labels are plain words: `rejection`, `interview`, `confirmation`, `referral`. Interview detection matches the subject line (genuine interview emails carry "interview"/"onsite"/"screen" there) — body heuristics over-match on newsletter boilerplate.

## Troubleshooting

### Chrome "Allow remote debugging?" popup blocks cron

Chrome requires per-connection remote debugging approval which cron jobs can't provide. This only affects browser-based automation (e.g., the Dice search). Fix:
```bash
hermes config set browser.engine playwright
hermes gateway restart
```

### Cron job fails with "Response remained truncated"

The model output exceeded the token limit. Switch to a model/provider with a higher output limit.

### Approval prompt blocks execution

Cron jobs run unattended — they can't approve commands. Fix:
1. Add the command to `command_allowlist` in `~/.hermes/config.yaml`
2. Restart Hermes

### Python version conflicts

Hermes runs on its own venv Python (e.g., 3.11). Pipeline scripts may need a different version. Fix:
- Use `run_daily.sh` with explicit `PYBIN` path
- Set `PYTHONPATH=""` to avoid venv module conflicts

### Telegram delivery fails

Check gateway logs:
```bash
grep "telegram.*fail\|delivery" ~/.hermes/logs/gateway.log | tail -10
```

Common causes:
- Network connectivity to `api.telegram.org`
- Telegram bot token expired
- Chat ID incorrect

### Source column shows location_1/location_2

The cron agent wrote custom search code instead of using `search_linkedin.py`. Fix:
- Ensure the prompt says `bash run_daily.sh` (not individual Python commands)
- The prompt must say "Do NOT write custom search code"

### Jobs scored at 0 (no JD fetched)

`fetch_job_description()` failed to extract the JD from LinkedIn. These jobs get match=0. Fix:
- Delete zero-score jobs from journal
- Manually add JD text to `descriptions_cache.json` and re-score
- Or use `open_preview` + `read_preview` to extract JD text and cache manually

### Stale cache entries

Cache may contain JDs for jobs deleted from the journal. To clean:
- Compare `descriptions_cache.json` URLs against journal URLs
- Delete orphan entries (in cache but not in journal)