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

### 2. Configure search parameters

```bash
cp templates/config.template.json config.json
```

Edit keywords, locations, scoring thresholds, and cron schedule.

### 3. Initialize the journal

```bash
python3 scripts/journal.py --init
```

This creates `journal.xlsx` with 4 sheets: Jobs, Applications, Resume Versions, Reference.

### 4. Run your first search

```bash
python3 scripts/search_linkedin.py
python3 scripts/journal.py --add output/linkedin_extract.json
python3 scripts/run_scoring.py
```

### 5. Generate tailored resumes

```bash
# Prepare tailoring input for high-priority jobs
python3 scripts/prepare_tailoring.py

# Dispatch LLM subagents using the prompt template
# (see templates/tailoring_prompt_template.md)

# Generate PDFs with quality gate
python3 scripts/generate_pdf.py output/tailoring_results.json
```

### 6. Set up daily automation (cron)

Using Hermes cron:
```
cronjob action=create schedule="0 9 * * *" name="Daily Job Scan"
```

## Pipeline Scripts

| Script | Purpose |
|--------|---------|
| `search_linkedin.py` | Browser-based LinkedIn job search |
| `journal.py` | Journal management (init, add, status) |
| `run_scoring.py` | Fetch descriptions + calculate all scores |
| `match_score.py` | Match score algorithm |
| `ats_score.py` | ATS keyword overlap algorithm |
| `interview_prob.py` | Interview probability algorithm |
| `generate_pdf.py` | PDF generation with quality gate |
| `quality_gate.py` | Technical quality scoring (Gate 1) |
| `validate_tailoring.py` | Structural validation + auto-fix |

## Quality Gates

### Gate 1: Technical (automated, instant)
- Formula compliance, conflation detection, structure rules
- Threshold: 75/100

### Gate 2: Human Review (LLM subagent, ~2 min)
- HR perspective + Hiring Manager perspective
- Threshold: Both scores ≥ 70

Only resumes passing both gates get PDFs generated.