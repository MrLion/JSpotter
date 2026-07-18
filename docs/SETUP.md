# JSpotter Setup Guide

## Prerequisites

1. **Python 3.10+**
   ```bash
   python3 --version
   ```

2. **Required packages**
   ```bash
   pip install openpyxl reportlab fpdf2 Pillow
   ```

3. **Hermes Agent** (for LLM scoring and resume tailoring)
   ```bash
   curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
   ```

4. **GitHub CLI** (optional, for version control)
   ```bash
   gh auth login
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
| `resume_tailoring.bullet_max_words` | Max words per bullet | `25` |
| `resume_tailoring.quality_gate_threshold` | Technical gate minimum score | `75` |
| `resume_tailoring.human_review_threshold` | LLM review minimum score | `70` |
| `journal.path` | Path to journal file | `"journal.xlsx"` |
| `resume_dir` | Where tailored resumes go | `"resume/tailored"` |

All settings have defaults — you can start with just keywords and locations.

### 3. Initialize the journal

```bash
python3 scripts/journal.py --init
```

Creates `journal.xlsx` with 4 sheets: Jobs, Applications, Resume Versions, Reference.

### 4. Run your first search

```bash
# Browser-based LinkedIn search (reads keywords + locations from config.json)
python3 scripts/search_linkedin.py

# Add results to journal
python3 scripts/journal.py --add output/linkedin_extract_today.json

# Fetch descriptions and score all new jobs
python3 scripts/run_scoring.py
```

### 5. Generate tailored resumes

```bash
# Prepare tailoring input for high-priority jobs
# Then dispatch LLM subagents using templates/tailoring_prompt_template.md

# Generate PDFs with quality gate (reads threshold from config.json)
python3 scripts/generate_pdf.py output/tailoring_results.json
```

### 6. Set up daily automation (cron)

Using Hermes cron:
```
cronjob action=create schedule="0 9 * * *" name="Daily Job Scan"
```

The cron job reads `config.json` for keywords and locations automatically.

## Pipeline Scripts

| Script | Purpose | Reads config.json |
|--------|---------|-------------------|
| `search_linkedin.py` | Browser-based LinkedIn job search | ✅ keywords, locations |
| `journal.py` | Journal management (init, add, status) | ✅ journal path |
| `run_scoring.py` | Fetch descriptions + calculate all scores | ✅ priority thresholds |
| `match_score.py` | Match score algorithm | ✅ location, thresholds |
| `ats_score.py` | ATS keyword overlap algorithm | — |
| `interview_prob.py` | Interview probability algorithm | ✅ preferred location |
| `generate_pdf.py` | PDF generation with quality gate | ✅ output dir |
| `quality_gate.py` | Technical quality scoring (Gate 1) | ✅ quality threshold |
| `validate_tailoring.py` | Structural validation + auto-fix | — |

## Quality Gates

### Gate 1: Technical (automated, instant)
- Formula compliance, conflation detection, structure rules
- Threshold: configurable via `config.json → resume_tailoring.quality_gate_threshold` (default 75)

### Gate 2: Human Review (LLM subagent, ~2 min)
- HR perspective + Hiring Manager perspective
- Threshold: configurable via `config.json → resume_tailoring.human_review_threshold` (default 70)

Only resumes passing both gates get PDFs generated.

## Configuration Reference

See `templates/config.template.json` for all available settings with comments.