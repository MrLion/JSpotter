# JSpotter

![JSpotter](JSpotter.png)

AI-powered job hunting automation pipeline — LinkedIn search, LLM scoring, resume tailoring, and application tracking.

## Pipeline Stages

1. **Daily Job Search** — LinkedIn browser extraction (config-driven locations)
2. **AI Scoring** — Match score, ATS score, interview probability (defined algorithms)
3. **Prioritization** — High/Medium/Low priority based on match score
4. **Resume Tailoring** — LLM-generated tailored resumes with PDF output
5. **Quality Gates** — Technical scoring (formula compliance, anti-conflation, ATS keywords) + human review (HR/HM perspectives)
6. **Application Tracking** — Journal-based tracking with status workflow and color coding

## Getting Started

1. Copy `templates/MASTER_PROFILE.template.md` and fill in your career details
2. Copy `templates/config.template.json` and configure your search parameters
3. Run the pipeline scripts in order

See [docs/SETUP.md](docs/SETUP.md) for detailed instructions and project structure.

## Automation

Daily job search runs automatically via Hermes cron. See [docs/CRON.md](docs/CRON.md) for setup and troubleshooting.

## Key Files (not in repo — create locally)

| File | Purpose |
|------|---------|
| `tailoring_prompt_local.md` | Working tailoring prompt with personal data |
| `config.json` | Search keywords, locations, scoring thresholds, career order |
| `theme.json` | Resume design (fonts, colors, margins, education, contact info) |
| `journal.xlsx` | Job tracking (4 sheets, color-coded statuses) |
| `resume/MASTER_PROFILE.md` | Your career profile |
| `output/descriptions_cache.json` | Cached job descriptions for scoring |

## Requirements

- Python 3.10+
- openpyxl, reportlab, Pillow
- Hermes Agent (for LLM scoring and resume tailoring)

## License

MIT