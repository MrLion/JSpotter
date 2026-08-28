# JSpotter Setup Guide

## Prerequisites

1. **Python 3.10+**
   ```bash
   python3 --version
   ```

2. **Required packages**
   ```bash
   pip install openpyxl reportlab
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
│   ├── search_linkedin.py      # LinkedIn search via guest API (no browser/login)
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
│   ├── run_review.py           # Single resume LLM review
│   ├── email_triage.py         # Email inbox triage (rejections/interviews/confirmations/referrals)
│   ├── search_adzuna.py        # Adzuna job search (REST API, no browser/login)
│   ├── hard_constraints.py     # Hard-constraint gates (location, comp floor, deal-breakers)
│   └── extract_requirements.py # JD requirement extraction (required/preferred, LLM + fallback)
├── templates/                  # All templates (generic, no personal data)
│   ├── MASTER_PROFILE.template.md
│   ├── config.template.json
│   ├── theme.template.json
│   ├── tailoring_prompt_template.md
│   ├── review_prompt_template.md
│   ├── TELEGRAM_TEMPLATE.md
│   ├── cron_template.md
│   └── run_daily.sh
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
| `search.locations` | Locations to search (LinkedIn filters) | USA |
| `search.max_results_per_search` | Max results per location | `70` |
| `scoring.priority_thresholds.high` | Match score for High priority | `80` |
| `scoring.priority_thresholds.medium` | Match score for Medium priority | `65` |
| `scoring.preferred_location` | Your preferred location | `"Boston"` |
| `scoring.candidate_domains` | Your strongest domains | `["AI/ML", "Healthcare", "Finance", "Enterprise/B2B"]` |
| `scoring.domains` | Domain definitions (keywords, weights, has_in_profile) | See config |
| `scoring.domain_weights` | Weight per domain | See config |
| `candidate.full_name` | Full legal name (checked against preferred name) | See config |
| `candidate.bad_keywords` | Banned terms in highlights | See config |
| `candidate.pandering_phrases` | Banned phrases in summary/cover letter | See config |
| `candidate.conflation_metrics` | Metric-to-engagement mappings | See config |
| `candidate.client_keywords` | Client identification keywords | See config |
| `candidate.client_names_in_profile` | Client display names | See config |
| `candidate.client_employment_regex` | Regex for direct employment detection | See config |
| `candidate.career_order` | Career history order for validation | See config |
| `credentials.adzuna` | Adzuna API credentials (`app_id`, `app_key`) — get a free key from the Adzuna developer portal | See config |
| `resume_tailoring.bullet_max_words` | Max words per bullet | `35` |
| `resume_tailoring.quality_gate_threshold` | Technical gate minimum score | `75` |
| `resume_tailoring.human_review_threshold` | LLM review minimum score | `70` |
| `journal.path` | Path to journal file | `"journal.xlsx"` |
| `resume_dir` | Where tailored resumes go | `"resume/tailored"` |
| `hard_constraints.comp_floor` | Minimum acceptable annual salary (USD); fail-open when undisclosed | `140000` |
| `hard_constraints.allowed_locations` | Acceptable locations; jobs naming other cities with no remote signal are skipped | `["Boston", "Remote"]` |
| `hard_constraints.location_tokens` | Per-location token lists for the location gate | See config |
| `hard_constraints.remote_tokens` | Phrases that signal a remote role | See config |
| `hard_constraints.onsite_tolerance` | `hybrid` / `onsite` / `remote`; fires on fully on-site demands outside allowed locations | `"hybrid"` |
| `hard_constraints.onsite_phrases` | JD phrases that signal fully on-site work | See config |
| `hard_constraints.salary_sanity` | Annual salary bounds (`min_annual`/`max_annual`) for parsing | `{"min_annual": 50000, "max_annual": 2000000}` |
| `hard_constraints.max_years_required` | Skip roles requiring more experience than this | `20` |
| `hard_constraints.text_blockers` | Case-insensitive instant-skip substrings | `["security clearance", ...]` |

All settings are required — scripts raise ValueError if config keys are missing. Start from the template and fill in all values. Hard-constraint gates are disabled when their key is unset/null.

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

Creates `journal.xlsx` with sheets: Jobs, Applications, Resume Versions, Reference. Each row in the Jobs sheet includes a Last Updated column tracking the date of last status change.

### 5. Run your first search

```bash
# LinkedIn search — fetches fresh jobs via LinkedIn's guest API (no browser/login needed)
python3 scripts/search_linkedin.py

# Dice search (requires login, extracts company ATS URLs)
python3 scripts/search_dice.py

# Adzuna search (REST API, no browser/login — reads keywords + credentials from config.json)
python3 scripts/search_adzuna.py

# Add results to journal (dedup by App URL, then source URL, then company+title+location)
python3 scripts/journal.py --add output/linkedin_extract.json

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
| `search_linkedin.py` | LinkedIn job search via guest API (no browser/login) | ✅ keywords, locations | — |
| `search_dice.py` | Dice job search (browser, login required) | ✅ keywords, locations | — |
| `search_adzuna.py` | Adzuna job search via REST API (no browser/login) | ✅ keywords, locations, credentials | — |
| `journal.py` | Journal management (init, add, status, validation, update_status) | ✅ journal path | — |
| `run_scoring.py` | Fetch descriptions + calculate all scores | ✅ priority thresholds | — |
| `match_score.py` | Match score algorithm (config-driven domains) | ✅ domains, location, thresholds | — |
| `ats_score.py` | ATS keyword overlap algorithm | — | — |
| `interview_prob.py` | Interview probability algorithm | ✅ preferred location | — |
| `generate_pdf.py` | PDF generation with quality gate | ✅ output dir | ✅ all design |
| `quality_gate.py` | Technical quality scoring (Gate 1, config-driven) | ✅ quality threshold, candidate config | — |
| `validate_tailoring.py` | Structural validation + auto-fix (config-driven) | ✅ candidate config | — |
| `adapt_resume.py` | Same-company resume adapter | ✅ candidate config | — |
| `run_batch_review.py` | Batch LLM review (multiple resumes in one call) | — | — |
| `run_review.py` | Single-resume LLM review dispatcher | — | — |
| `email_triage.py` | Email inbox triage (rejections/interviews/confirmations/referrals) | — | — |
| `hard_constraints.py` | Hard-constraint gates checked before scoring (SKIP + reason) | ✅ hard_constraints | — |
| `extract_requirements.py` | JD requirement extraction into required/preferred/bonus (LLM with heuristic fallback, quote-verified) | — | — |

## Scoring

### Match Score (0-100)
| Component | Max Pts | Description |
|-----------|---------|-------------|
| Domain match | 40 | Weighted domain keyword overlap with word boundary matching. Domains defined in `config.json → scoring.domains`. Current domains: AI/ML, Healthcare, Finance, Capital Markets, Enterprise/B2B, Cybersecurity, E-commerce/Consumer, Infrastructure/DevOps, Mobile/Hardware, Life Sciences/Bioprocessing, Semiconductor/Materials R&D, Public Sector/Transportation |
| Skill match | 20 | Skill category overlap (PM, AI/ML, Methodology, Technical, etc.) |
| Seniority | 15 | Title-based seniority fit |
| Years requirement | 10 | Years of experience match |
| Location | 10 | Preferred location match |
| Entrepreneurship | 5 | Founder/entrepreneur experience |
| Certification gap | -15 | Deducts 5pts per cert in JD but missing from profile (capped at -15). Checks: CFA, PMP, AIPMM, SAFe, POPM, CPA, CISSP, AWS/Azure/GCP Certified, PHR, SHRM, Six Sigma, ITIL |

Domain keywords use multi-word matching (e.g., "cybersecurity" not "security", "investment bank" not "investment") to avoid false positive domain matches across unrelated JDs.

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

Only resumes passing both gates get clean PDFs. Resumes below Gate 2 threshold still get PDFs but with review notes appended.

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

## Browser Configuration

The daily LinkedIn scan uses the guest API directly (no browser/login), so it runs unattended without browser access. A browser is only needed if you use the **Dice search** (`search_dice.py`), which requires login. If you automate Dice or other browser-based tasks, set the browser engine to Playwright to avoid Chrome remote debugging approval popups:

```bash
hermes config set browser.engine playwright
hermes gateway restart
```

## File Organization

Tailored resume files are organized by application status:

```
resume/tailored/           — PDFs + review notes TXT (not yet applied)
resume/tailored/applied/    — PDFs + review notes TXT (applied jobs)
resume/tailored/archived/   — PDFs + TXTs (rejected/closed/withdrawn)
```

Use `update_status()` from `journal.py` to move files automatically when status changes. Note that `update_status()` moves PDFs/TXTs only — any stray `*_review.json` files must be moved by hand.

## Descriptions Cache

Job descriptions are cached in `output/descriptions_cache.json`. To keep the cache clean:

- Orphan entries (JDs for jobs no longer in the journal) should be purged periodically
- Compare cache URLs against journal URLs and delete orphans
- Zero-score jobs (match=0) typically have no cached JD — `fetch_job_description()` failed to extract text from LinkedIn