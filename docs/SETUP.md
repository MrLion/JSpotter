# JSpotter Setup Guide

## Prerequisites

1. **Python 3.10+**
   ```bash
   python3 --version
   ```

2. **Required packages**
   ```bash
   pip install openpyxl reportlab Pillow
   ```

3. **Hermes Agent** (for LLM scoring and resume tailoring)
   ```bash
   curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
   ```

4. **GitHub CLI** (optional, for version control)
   ```bash
   gh auth login
   ```

## Project Structure

```
JSpotter/
├── scripts/                    # Pipeline scripts
│   ├── search_linkedin.py      # LinkedIn browser extraction
│   ├── search_dice.py          # Dice.com browser extraction (requires login)
│   ├── journal.py              # Journal management (add, init, status, validation)
│   ├── run_scoring.py          # Full scoring pipeline (match, ATS, interview prob)
│   ├── match_score.py          # Match score algorithm (config-driven domains)
│   ├── ats_score.py            # ATS keyword overlap score
│   ├── interview_prob.py       # Interview probability algorithm
│   ├── generate_pdf.py         # PDF + cover letter generator (ReportLab)
│   ├── quality_gate.py         # Technical quality gate (6 checks, 100pts)
│   ├── validate_tailoring.py   # Structural validation + auto-fix
│   ├── run_batch_review.py     # Batch LLM review (multiple resumes in one call)
│   ├── adapt_resume.py         # Same-company resume adapter
│   └── run_review.py           # Single resume LLM review
├── templates/                  # All templates (generic, no personal data)
│   ├── MASTER_PROFILE.template.md
│   ├── config.template.json
│   ├── theme.template.json
│   ├── tailoring_prompt_template.md
│   ├── review_prompt_template.md
│   └── cron_template.md
├── docs/                       # Setup and usage documentation
│   ├── SETUP.md                # Installation and configuration
│   └── CRON.md                 # Cron job setup and troubleshooting
├── CHANGELOG.md                # Release history
└── README.md
```

## Setup Steps

### 1. Create your master profile

```bash
cp templates/MASTER_PROFILE.template.md resume/MASTER_PROFILE.md
```

Fill in your career details following the bullet formula:
> verb + product/workflow/platform + scope + measurable result + by/through method

### 2. Configure your job search

```bash
cp templates/config.template.json config.json
```

Edit `config.json` to customize:

| Setting | Description | Example |
|---------|-------------|---------|
| `search.keywords` | Job search keywords | `"product manager AI"` |
| `search.locations` | Locations to search | Boston + Remote USA |
| `search.max_results_per_search` | Max results per location | `70` |
| `scoring.priority_thresholds.high` | Match score for High priority | `80` |
| `scoring.priority_thresholds.medium` | Match score for Medium priority | `65` |
| `scoring.preferred_location` | Your preferred location | `"Boston"` |
| `scoring.candidate_domains` | Your strongest domains | `["AI/ML", "Healthcare"]` |
| `scoring.domain_weights` | Weight per domain | See config |
| `resume_tailoring.bullet_max_words` | Max words per bullet | `35` |
| `resume_tailoring.quality_gate_threshold` | Technical gate minimum score | `75` |
| `resume_tailoring.human_review_threshold` | LLM review minimum score | `70` |
| `journal.path` | Path to journal file | `"journal.xlsx"` |
| `resume_dir` | Where tailored resumes go | `"resume/tailored"` |

All settings are required — scripts raise ValueError if config keys are missing. Start from the template and fill in all values.

### 3. Configure resume design

```bash
cp templates/theme.template.json theme.json
```

Edit `theme.json` to customize the resume appearance:

| Setting | Description | Example |
|---------|-------------|---------|
| `fonts.name` | Name font family and size | `{"family": "Helvetica-Bold", "size": 16}` |
| `fonts.section_header` | Section header font | `{"family": "Helvetica-Bold", "size": 11}` |
| `fonts.body` | Body text font | `{"family": "Helvetica", "size": 10.5}` |
| `colors.name` | Name text color (hex) | `"#2c3e50"` |
| `colors.rule_primary` | Header horizontal rule color | `"#2c3e50"` |
| `colors.rule_section` | Section divider color | `"#bdc3c7"` |
| `layout.margin_left` | Left margin (inches) | `0.75` |
| `layout.margin_top` | Top margin (inches) | `1.05` |
| `layout.header_name_y` | Name Y position on page | `10.55` |
| `layout.spacer_between_sections` | Space between sections (pts) | `3` |
| `layout.spacer_between_jobs` | Space between jobs (pts) | `4` |
| `strengths.columns` | Number of columns for strengths | `2` |
| `strengths.bullet_char` | Bullet character for strengths | `"•"` |
| `bullets.char` | Bullet character for highlights | `"–"` |
| `bullets.indent` | Bullet indent (pts) | `14` |
| `bullets.max_words` | Max words per bullet | `35` |
| `contact_info.line1` | First line of contact info | `"City, State · (xxx) xxx-xxxx · email"` |
| `contact_info.line2` | Second line (optional) | `"linkedin.com/in/profile"` |

All design settings are required — start from `theme.template.json` and fill in all values.

### 4. Initialize the journal

```bash
python3 scripts/journal.py --init
```

Creates `journal.xlsx` with 4 sheets: Jobs, Applications, Resume Versions, Reference.

### 5. Run your first search

```bash
# Browser-based LinkedIn search (reads keywords + locations from config.json)
python3 scripts/search_linkedin.py

# Browser-based Dice search (requires login, extracts company ATS URLs)
python3 scripts/search_dice.py

# Add results to journal (dedup by App URL, then source URL, then company+title+location)
python3 scripts/journal.py --add output/linkedin_extract_today.json

# Fetch descriptions and score all new jobs
python3 scripts/run_scoring.py
```

**Cross-source dedup:** Jobs are deduplicated across LinkedIn and Dice using three layers:
1. **App URL** — company ATS URL (highest priority, available from Dice)
2. **Source URL** — LinkedIn or Dice job URL
3. **Company + title + location** — fallback for jobs without App URL (LinkedIn)

### 6. Generate tailored resumes

```bash
# Prepare tailoring input for high-priority jobs
# Extract JD text from descriptions_cache.json and pass it directly in the
# subagent context — do NOT have subagents read descriptions_cache.json
# (the cache file can exceed read_file truncation limits as it grows)

# Dispatch LLM subagents using templates/tailoring_prompt_template.md
# The parent agent inserts the JD text into the goal block before dispatching

# Generate PDFs with quality gate (reads threshold from config.json)
python3 scripts/generate_pdf.py output/tailoring_results.json
```

PDFs are styled according to `theme.json` — fonts, colors, margins, spacing, bullet styles.

### 7. Set up daily automation (cron)

See **[docs/CRON.md](CRON.md)** for the full cron setup guide, including:
- Creating `run_daily.sh` shell wrapper
- Adding commands to the allowlist
- Configuring the cron job (schedule, model, provider, delivery)
- Troubleshooting common issues (truncation, approval prompts, Python conflicts)

## Pipeline Scripts

| Script | Purpose | Reads config.json | Reads theme.json |
|--------|---------|-------------------|-------------------|
| `search_linkedin.py` | Browser-based LinkedIn job search | ✅ keywords, locations | — |
| `search_dice.py` | Browser-based Dice job search (login required) | ✅ keywords, locations | — |
| `journal.py` | Journal management (init, add, status) | ✅ journal path | — |
| `run_scoring.py` | Fetch descriptions + calculate all scores | ✅ priority thresholds | — |
| `match_score.py` | Match score algorithm | ✅ location, thresholds | — |
| `ats_score.py` | ATS keyword overlap algorithm | — | — |
| `interview_prob.py` | Interview probability algorithm | ✅ preferred location | — |
| `generate_pdf.py` | PDF generation with quality gate | ✅ output dir | ✅ all design |
| `quality_gate.py` | Technical quality scoring (Gate 1) | ✅ quality threshold | — |
| `validate_tailoring.py` | Structural validation + auto-fix | — | — |
| `journal.py` (validate) | Journal row integrity validation | — | — |

## Scoring

### Match Score (0-100)
| Component | Max Pts | Description |
|-----------|---------|-------------|
| Domain match | 35 | Weighted domain keyword overlap (AI/ML, Healthcare, Finance, etc.) |
| Skill match | 20 | Skill category overlap (PM, AI/ML, Methodology, Technical, etc.) |
| Seniority | 15 | Title-based seniority fit |
| Years requirement | 10 | Years of experience match |
| Location | 10 | Preferred location match |
| Entrepreneurship | 5 | Founder/entrepreneur experience |
| Certification gap | -15 | Deducts 5pts per cert in JD but missing from profile (capped at -15). Checks: CFA, PMP, AIPMM, SAFe, POPM, CPA, CISSP, AWS/Azure/GCP Certified, PHR, SHRM, Six Sigma, ITIL |

### Priority Thresholds (configurable)
- **High:** ≥80
- **Medium:** 65-79
- **Low:** <65

## Quality Gates

### Gate 1: Technical (automated, instant)
- Formula compliance, conflation detection, structure rules
- Threshold: configurable via `config.json → resume_tailoring.quality_gate_threshold` (default 75)

### Gate 2: Human Review (LLM subagent, ~2 min)
- HR perspective + Hiring Manager perspective
- Threshold: configurable via `config.json → resume_tailoring.human_review_threshold` (default 70)

Only resumes passing both gates get PDFs generated.

## Configuration Reference

| File | Purpose |
|------|---------|
| `config.json` | Search keywords, locations, scoring thresholds, quality gate settings |
| `theme.json` | Resume fonts, colors, margins, spacing, bullet styles, contact info |
| `templates/MASTER_PROFILE.template.md` | Template for your career profile |
| `templates/tailoring_prompt_template.md` | Prompt template for LLM resume tailoring |
| `templates/review_prompt_template.md` | Prompt template for LLM human review |
| `templates/config.template.json` | Config file with all settings documented |
| `templates/theme.template.json` | Theme file with all design options documented |