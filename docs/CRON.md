# Cron Jobs

JSpotter uses Hermes cron jobs for automated daily tasks. This guide covers setup, configuration, and troubleshooting.

## Daily Job Scan

Runs the full search → add → score pipeline every morning and delivers a summary to Telegram.

### Setup

1. **Create `run_daily.sh`** in your project root:

```bash
#!/bin/bash
PYBIN="/path/to/python3"
cd "/path/to/Job hunting" || exit 1

echo "=== Step 1: LinkedIn Search ==="
PYTHONPATH="" "$PYBIN" search_linkedin.py 2>&1

echo "=== Step 2: Add to Journal ==="
PYTHONPATH="" "$PYBIN" journal.py --add output/linkedin_extract.json 2>&1

echo "=== Step 3: Score New Jobs ==="
PYTHONPATH="" "$PYBIN" run_scoring.py 2>&1

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
- Model: `glm-5.2`
- Provider: `zai`
- Deliver: `telegram:<chat_id>`
- Toolsets: `browser`, `terminal`, `file`
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

## LinkedIn Post Ideas

Generates 5 post ideas every Friday based on trending PM/AI topics.

- Schedule: `30 8 * * 5` (Friday 8:30 AM)
- Sources: Lenny's Newsletter, a16z, Hugging Face, OpenAI, Anthropic
- Output: saved to `linkedin/ideas_{DATE}.md` and delivered to Telegram

See `LINKEDIN_IDEAS_TEMPLATE.md` for the format.

## Troubleshooting

### Cron job fails with "Response remained truncated"

The model output exceeded the token limit. Switch provider:
- `ollama-cloud` has lower output limits
- `zai` handles longer responses

### Approval prompt blocks execution

Cron jobs run unattended — they can't approve commands. Fix:
1. Add the command to `command_allowlist` in `~/.hermes/config.yaml`
2. Restart Hermes

### Python version conflicts

Hermes runs on its own venv Python (e.g., 3.11). Pipeline scripts may need a different version. Fix:
- Use `run_daily.sh` with explicit `PYBIN` path
- Set `PYTHONPATH=""` to avoid venv module conflicts
- The Hermes Python 3.11 App Management entry is expected — approve it in macOS

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