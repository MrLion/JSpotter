# JSpotter

![JSpotter](JSpotter.png)

Automate your job search — find relevant roles, score them against your profile, generate tailored resumes, and track every application in one place.

## What It Does

- **Finds jobs** — searches LinkedIn daily for roles matching your keywords and locations
- **Scores them** — ranks each job by how well it matches your experience (0-100)
- **Tailors your resume** — generates a custom resume and cover letter for each role
- **Quality checks** — validates every resume for accuracy, keyword coverage, and readability
- **Tracks everything** — logs every job, application, interview, and rejection in a spreadsheet

## Quick Start

1. **Set up your profile** — copy `templates/MASTER_PROFILE.template.md`, fill in your career history
2. **Configure your search** — copy `templates/config.template.json`, set your keywords, locations, and scoring preferences
3. **Run the pipeline** — search, score, tailor, apply

Full setup guide: [docs/SETUP.md](docs/SETUP.md)

## How It Works

1. **Search** — scans LinkedIn for jobs matching your criteria
2. **Score** — each job gets a match score (domain fit, skills, seniority, location, certifications)
3. **Prioritize** — jobs sorted into High / Medium / Low priority
4. **Tailor** — generates a resume and cover letter tailored to each job description
5. **Review** — automated quality checks + AI review from recruiter and hiring manager perspectives
6. **Track** — job status (Not Applied → Applied → Interview → Rejected) with color coding

## Daily Automation

Runs automatically every morning via Hermes cron. Results delivered to your Telegram.

Setup guide: [docs/CRON.md](docs/CRON.md)

## Key Files (not in repo — create locally)

| File | Purpose |
|------|---------|
| `config.json` | Your search keywords, locations, scoring settings, career details |
| `theme.json` | Resume design — fonts, colors, margins, contact info |
| `journal.xlsx` | Job tracking spreadsheet (4 sheets, color-coded statuses) |
| `resume/MASTER_PROFILE.md` | Your career profile |
| `tailoring_prompt_local.md` | Resume tailoring instructions (with your personal data) |
| `output/descriptions_cache.json` | Cached job descriptions for scoring |

## Requirements

- Python 3.10+
- Packages: openpyxl, reportlab, Pillow
- [Hermes Agent](https://hermes-agent.nousresearch.com/) (for resume tailoring and job scoring)

## License

MIT