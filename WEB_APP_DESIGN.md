# JSpotter Web App — Design Brainstorm

## Architecture

**Backend: FastAPI (Python)**
- Reuses all existing scripts as service layers — no rewrite needed
- `match_score.py`, `ats_score.py`, `quality_gate.py` become API endpoints
- `generate_pdf.py` becomes a download endpoint
- SQLite instead of xlsx — same data, queryable

**Frontend: React + Tailwind**
- Single-page app, dashboard layout
- No framework overhead — Vite + React is enough

**Data: SQLite + file storage**
- Journal moves from xlsx to SQLite (same columns, queryable)
- PDFs/cover letters served as downloads
- config.json/theme.json editable in UI

## Pages

| Page | What it does |
|------|-------------|
| **Dashboard** | Stats: jobs found, applied, interviews, rejection rate. Priority breakdown chart. Recent activity feed. |
| **Job Journal** | Sortable/filterable table (like current xlsx but interactive). Color-coded status. Bulk actions. Click row → job detail with description, scores, match breakdown. |
| **Pipeline Runner** | Pick a job → click "Run Pipeline" → see live progress: Generating → Validating → Quality Gate → Review → PDF. Download resume + cover letter when done. |
| **Resume Preview** | View generated PDF inline. Side-by-side: resume vs review notes. Cover letter preview. |
| **Config** | Edit config.json (keywords, locations, thresholds) and theme.json (fonts, colors, margins) in a form UI. Live preview of resume header. |
| **Master Profile** | Edit MASTER_PROFILE.md in a rich text editor. See bullet formula validation in real-time. |

## Key Features

**1. One-click pipeline**
Instead of running delegate_task → validate → quality_gate → review → PDF manually, click "Run" and watch progress. Backend orchestrates the same subagent calls.

**2. Journal as a real database**
- Filter by priority, status, company, date
- Click any job → full detail (description, scores, missing skills, resume link)
- Color coding built in (no Apple Numbers limitations)
- Export to xlsx anytime for backup

**3. Resume gallery**
- All generated resumes in one view
- Filter by company, status, score
- Download PDF + cover letter individually or in bulk
- Review notes shown inline

**4. Daily scan automation**
- Cron job runs in background (already works)
- Results appear in dashboard activity feed
- Telegram delivery stays as-is

**5. Config editor**
- Change search keywords without editing JSON
- Adjust quality gate threshold with a slider
- Edit theme colors with a color picker
- Live preview of resume header

## Tech Stack

```
Backend:  FastAPI + SQLite + existing Python scripts
Frontend: React + Vite + TailwindCSS + shadcn/ui
Charts:   Recharts (priority breakdown, status funnel)
PDF:      ReportLab (existing) → served as downloads
Auth:     Simple token (single user, not public)
Deploy:   Docker → local or VPS
```

## Migration Path

Instead of rebuilding everything:

1. **Phase 1: API wrapper** — Wrap existing scripts as FastAPI endpoints. Journal stays as xlsx. Frontend is a simple table + run button.
2. **Phase 2: SQLite migration** — Move journal from xlsx to SQLite. Add filtering, sorting, stats dashboard.
3. **Phase 3: Pipeline orchestration** — Backend manages subagent dispatches. Live progress in UI.
4. **Phase 4: Config editor + resume preview** — Form-based config editing, inline PDF preview.

Each phase is independently useful. Phase 1 alone would give you a web UI for the journal without changing any backend logic.

## What stays the same
- All scoring algorithms (match_score, ats_score, interview_prob)
- Quality gate logic
- PDF generation (ReportLab)
- Subagent dispatching for tailoring + review
- Cron job for daily scans
- Telegram delivery

## What changes
- xlsx → SQLite (queryable, no Apple Numbers issues)
- Manual terminal commands → web UI buttons
- config.json/theme.json editing → form UI
- Reading review notes from files → inline display

## Deployment Options

**Local (your Mac)**
- ✅ No hosting cost, no deployment
- ✅ Already has all scripts, Python, PDFs, journal
- ❌ Only works when your Mac is on
- ❌ Can't access from phone or other devices
- ❌ Same machine doing everything (browser + server + subagents)

**VPS (cloud)**
- ✅ Always on, accessible from anywhere
- ✅ Separate from your Mac
- ❌ Monthly cost (~$5-20)
- ❌ Need to migrate scripts, config, journal
- ❌ Subagent calls need API keys on the server
- ❌ Browser automation (LinkedIn search) harder on headless server

**Hybrid (recommended)**
- Keep the heavy lifting on your Mac (LinkedIn search, subagent dispatching, PDF generation)
- Serve the web UI from your Mac too
- Use Tailscale to access it from your phone/other devices securely
- No cloud cost, accessible everywhere, nothing to migrate

The hybrid approach makes the most sense because the pipeline already runs on the Mac — the cron job, the browser, the Python environment. Moving it to a server would break the LinkedIn browser search and require setting up all the API keys again.

Tailscale gives a private URL like `http://mintmrlion-mac.tail-scale.net:3000` that works from your phone, only for you.

## Brainstorm Date
July 22, 2026