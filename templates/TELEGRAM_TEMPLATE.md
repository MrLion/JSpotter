# Daily Telegram Report Template

Use this format when the cron job delivers the daily job scan results to Telegram.

## Template

```
📋 JSpotter Daily Scan — {DATE}

📊 Summary
• New jobs found: {COUNT}
• High priority: {HIGH_COUNT}
• Medium priority: {MED_COUNT}
• Low priority: {LOW_COUNT}
• Total in journal: {TOTAL}

🔥 High Priority (New)
{COMPANY} — {TITLE}
Match: {SCORE} | ATS: {ATS}
{LOCATION}
{URL}

{repeat for each high-priority job}

🚫 Gated (SKIP): {SKIP_COUNT}
{repeat for each newly gated job: COMPANY — TITLE: reason, max 3 lines}

🟡 Medium/Low Priority: {MED_COUNT} medium, {LOW_COUNT} low

---
Previously applied: {APPLIED_COUNT} | Interviews: {INTERVIEW_COUNT} | Rejected: {REJECTED_COUNT} | Closed: {CLOSED_COUNT}
```

## Rules

1. **Always include the date** in the header
2. **Always include the summary stats** — even if zero new jobs
3. **High priority jobs get full detail** — company, title, match/ATS/prob, location, URL
4. **Medium/Low priority: count only** — no company names or details, just the number
5. **Low priority jobs are not listed** — just the count
6. **If no new jobs, say so** — don't skip the message
7. **Bottom line shows pipeline status** — read these counts from the **Jobs sheet** (column O = `Status`), NOT the Applications sheet. Count rows by status value: `Applied`, `Interview`, `Rejected`, `Closed`, `Withdrawn`. The Applications sheet is unused for automated reporting.
8. **Keep it compact** — Telegram messages should be scannable, not walls of text
9. **Use emoji sparingly** — only for section headers (📋📊🔥🟡📭)
10. **No markdown bold** — renders inconsistently in Telegram