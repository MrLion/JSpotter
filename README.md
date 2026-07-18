# JSpotter

AI-powered job hunting automation pipeline — LinkedIn search, LLM scoring, resume tailoring, and application tracking.

## Pipeline Stages

1. **Daily Job Search** — LinkedIn browser extraction (Boston + Remote)
2. **AI Scoring** — Match score, ATS score, interview probability (defined algorithms)
3. **Prioritization** — High/Medium/Low priority based on match score
4. **Resume Tailoring** — LLM-generated tailored resumes with PDF output
5. **Application Tracking** — Journal-based tracking with status workflow

## Getting Started

1. Copy `templates/MASTER_PROFILE.template.md` and fill in your career details
2. Copy `templates/config.template.json` and configure your search parameters
3. Run the pipeline scripts in order

See [docs/SETUP.md](docs/SETUP.md) for detailed instructions.

## Project Structure

```
JSpotter/
├── scripts/          # Pipeline scripts (search, score, tailor, track)
├── templates/        # Templates for profile, config, resume layout
├── docs/             # Setup and usage documentation
└── README.md
```

## Requirements

- Python 3.10+
- openpyxl, reportlab, fpdf2
- Hermes Agent (for LLM scoring and resume tailoring)

## License

MIT