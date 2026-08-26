# Cron Template — Daily Job Scan

Use this template when creating or updating the daily job scan cron job.

## Cron Job Configuration

```
Name: Daily Job Scan
Schedule: 0 9 * * * (daily at 9 AM local time)
Model: glm-5.2
Provider: zai
Deliver: telegram:<chat_id>
Toolsets: browser, terminal, file
Workdir: <project path>
```

## Prompt

```
Run the daily job search pipeline. Work in <PROJECT_PATH>.

Step 1: Run: bash run_daily.sh
This runs search, journal add, and scoring. Read the output for job counts.

Step 2: Read <PROJECT_PATH>/TELEGRAM_TEMPLATE.md for the report format.

Step 3: Format the report using ONLY the template. Your final response IS the Telegram message — it must contain ONLY the report.

Keep your response SHORT. Do not include more than 10 high-priority jobs with details. Do not narrate what you did. Just output the report.
```

## Shell Script (run_daily.sh)

```bash
#!/bin/bash
# Daily pipeline runner — called by cron job
# Uses explicit Python path to avoid venv conflicts

PYBIN="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
cd "<PROJECT_PATH>" || exit 1

echo "=== Step 1: LinkedIn Search ==="
PYTHONPATH="" "$PYBIN" scripts/search_linkedin.py 2>&1

echo "=== Step 2: Add to Journal ==="
PYTHONPATH="" "$PYBIN" scripts/journal.py --add output/linkedin_extract.json 2>&1

echo "=== Step 3: Score New Jobs ==="
PYTHONPATH="" "$PYBIN" scripts/run_scoring.py 2>&1

echo "=== DONE ==="
```

## Key Design Decisions

1. **Shell wrapper (run_daily.sh)** — cron agent calls `bash run_daily.sh` instead of individual Python commands. Prevents the agent from invoking the wrong Python or writing custom scripts.

2. **Allowlist** — `bash run_daily.sh` must be added to `command_allowlist` in Hermes config to avoid approval prompts blocking the cron job:
   ```yaml
   command_allowlist:
     - "bash run_daily.sh"
   ```

3. **No direct Python in prompt** — the prompt tells the agent NOT to run python3 directly. All Python execution happens inside the shell script.

4. **Response = Telegram message** — the agent's final response is delivered to Telegram. It must contain ONLY the formatted report. No narration, no pipeline summaries.

5. **Provider matters** — `zai` provider handles the output length. `ollama-cloud` may truncate the response.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Approval prompt blocks cron | Add command to `command_allowlist` in config.yaml |
| Response truncated | Switch provider from `ollama-cloud` to `zai` |
| Python 3.11 App Management entry | Expected — Hermes runtime uses its own venv. Approve it in macOS System Settings |
| `journal.py: error: unrecognized arguments` | Use `--add` not `add` |
| Agent narrates work in Telegram | Reinforce "ABSOLUTE RULE" in prompt |