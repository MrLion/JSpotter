# Changelog

All notable changes to this project are documented here.

## [0.12.0] - 2026-08-15

### Added
- **Capital Markets domain** — split from Finance; weight 12, `has_in_profile: false`. Keywords: trading, capital markets, investment, portfolio management, Charles River, Aladdin, Simcorp, fixed income, buy-side, sell-side, asset manager, hedge fund, investment bank, trading lifecycle, order management
- **Life Sciences/Bioprocessing domain** — weight 12, `has_in_profile: false`. Keywords: bioprocessing, chromatography, affinity ligands, resin, protein purification, downstream processing, biologics, biopharmaceutical, fermentation, cell culture, purification, GMP, upstream processing, drug substance, drug product
- **`update_status()` function in journal.py** — single function for status changes; updates Status + Last Updated columns, sets Date Applied, color-codes company cell, auto-archives PDFs/TXTs to `archived/` for Rejected/Closed/Withdrawn
- **Last Updated column** in journal (col 18) — tracks date of last status change
- **Candidate name in PDF filenames** — e.g., `George Mishchenko_Company_Title_v1.pdf`
- **Tailoring prompt rule 14 updated** — cover letter must NOT include date/company/Re: header (PDF generator adds them)
- **Job hunting pipeline skill** — saved as reusable skill with full pipeline steps, file organization, and common pitfalls

### Fixed
- **Domain scoring: word boundary matching** — keywords now use `re.search(r'\b...\b')` instead of `kw in desc_lower`; fixes "iot" matching inside "biotechnology", "equity" matching in compensation text
- **Removed "equity" from Capital Markets keywords** — too ambiguous (stock compensation vs equity markets)
- **Cache overwrite guard in run_scoring.py** — `fetch_job_description()` no longer overwrites existing cached JDs
- **Domain definitions moved from match_score.py to config.json** — all domain keywords, weights, and has_in_profile flags are now config-driven
- **Review JSON/TXT file organization** — review JSONs in `tailored/reviews/`, review notes TXT in `tailored/` or `tailored/applied/`, rejected job files in `tailored/archived/`
- **Cover letter duplicate header** — removed date/company/Re: block from cover letter text (PDF generator handles it)

### Changed
- **Repligen Corporation** match score: 84 (High) → 60 (Low) — Life Sciences/Bioprocessing domain correctly flagged as missing
- **Publicis Sapient** match score: 87 (High) → 72 (Medium) — Capital Markets domain correctly flagged as missing
- **Koyfin** match score: 98 (High) → 78 (Medium) — Capital Markets domain correctly flagged as missing
- **LinkedIn search locations** — removed Greater Boston, now USA only (remote + hybrid + on-site)
- **config.json domain_weights** — updated to include Capital Markets and Life Sciences/Bioprocessing with correct names

## [0.11.0] - 2026-08-08

### Added
- **Certification gap scoring** — deducts 5pts per cert in JD but missing from profile (capped at -15). Checks CFA, PMP, AIPMM, SAFe, POPM, CPA, CISSP, AWS/Azure/GCP Certified, PHR, SHRM, Six Sigma, ITIL
- **Journal validation** — `validate_journal_rows()` checks Job ID, Status, Priority, Date Applied, App URL integrity after every `add_jobs()` call
- **Scoring breakdown table** in SETUP.md

### Fixed
- **Job ID extraction bug** — was splitting URLs by "-" producing generic words like "Manager"; now splits by "/" and only extracts segments with digits
- **11 journal rows with wrong Job IDs** — LinkedIn URLs as Job IDs (8 rows) and Dice column shifts (3 rows) corrected
- **27 broken Dice staffing firm rows** — scored at near-zero with no JD cached, deleted

### Changed
- **Match score now clamped to 0-100** (was 1-100) — certification penalties can reduce below previous floor
- **State Street** match score: 93→88 (CFA gap)
- **TJX** match score: 93→83 (SAFe + POPM gaps)

## [0.10.2] - 2026-08-02

### Changed
- **Tailoring prompt: JD-in-context approach** — parent agent extracts JD text and passes it directly in subagent context; subagent never reads descriptions_cache.json (1.9MB, 322 entries, exceeds read_file truncation limit)
- **Rule 13 strengthened** — explicitly bans `execute_code`, `python3 -c`, .py files, temp scripts; allows `search_files` alongside `read_file`/`write_file`
- **Quality gate: action verbs expanded** — added operated, managed, maintained
- **LinkedIn ideas template: topic leads, not resume** — posts are community commentary, not personal case studies; pitches must not start with "I"
- **LinkedIn ideas: source URLs required** — every idea must include a URL to the specific article/paper visited
- **LinkedIn Post Ideas cron: removed terminal toolset** — only browser + file needed, prevents approval prompts in autonomous runs

### Fixed
- **Job ID extraction bug in journal.py** — was splitting URLs by "-" and taking last segment; generic words like "Manager" matched across different jobs. Now splits by "/" and only extracts if segment contains digits
- **Subagents attempting execute_code** — root cause: descriptions_cache.json grew too large for read_file; fixed by passing JD text in context

## [0.10.1] - 2026-08-01

### Added
- **TELEGRAM_TEMPLATE.md** added to repo templates

### Changed
- **Cron prompt rewritten** — explicit browser step instructions (navigate, dismiss dialog, extract JS, save) so agent actually browses LinkedIn
- **IEC 62304 / ISO 13485** added to master profile (GE Healthcare engagement)

### Fixed
- Cron job reporting "no new jobs" — root cause: relevance sort returned same 112 jobs daily; `sortBy=DD` resolves this

## [0.10.0] - 2026-07-29

### Changed
- **LinkedIn search now sorts by date posted** (`sortBy=DD`) — surfaces newest jobs first instead of relevance-ranked results that never changed
- **Cron prompt updated** — explicit browser step instructions (navigate, dismiss dialog, extract JS, save) so the agent actually browses LinkedIn instead of only running the Python script

### Added
- **Action verbs expanded** in quality gate — added incorporated, embedded, integrated, sourced, curated
- **IEC 62304 / ISO 13485** added to master profile (GE Healthcare engagement) — surfaces for medical device roles

### Fixed
- Cron job reporting "no new jobs" — root cause was relevance sort returning same 112 jobs daily; date sort resolves this

## [0.9.0] - 2026-07-28

### Changed
- **Title filter broadened** — now includes Director, VP, Head of Product, Lead, Owner roles (was Manager-only)
- **title_filter_terms moved to config.json** (`search.title_filter_terms`) — no hardcoded fallback, raises ValueError if missing
- Both `search_linkedin.py` and `search_dice.py` updated

### Added
- **Quality gate check for project tenure dates** on bullets (-2 pts per occurrence)
- **Rule 12 updated** in tailoring prompt: "NEVER append project tenure dates to individual bullets"

### Fixed
- Removed hardcoded `["manager"]` fallback from title filter in both search scripts

## [0.8.0] - 2026-07-27

### Added
- **Cross-source dedup** via App URL — Dice apply URL extraction identifies company ATS URLs, enabling dedup across LinkedIn and Dice
- **`search_dice.py`** — Dice.com job search with login, ATS URL extraction, and job board filtering
- **3-layer dedup** in `journal.py`: App URL → source URL → company+title+location fallback
- **Job board filter** — Dice postings redirecting to other job boards (efinancialcareers, indeed, etc.) are automatically skipped

### Changed
- Journal column "LinkedIn URL" renamed to "Job URL" (supports multiple sources)
- Added `app_url`, `status`, `date_applied` columns to `JOBS_COLUMNS` definition
- `bullet_max_words` updated from 25 to 35 in docs
- Removed `fpdf2` from prerequisites (replaced by ReportLab)
- `search_linkedin.py` and `match_score.py` — removed hardcoded values, now config-driven

### Known Limitations
- LinkedIn login blocked by bot detection — apply URL not available, falls back to company+title+location dedup
- Dice apply URL extraction requires visiting each job detail page while logged in

## [0.7.0] - 2026-07-25

### Added
- **Telegram report template** (`TELEGRAM_TEMPLATE.md`): standardized daily scan format — high priority jobs with full detail, medium/low as counts only, pipeline status at bottom
- **LinkedIn ideas template** (`LINKEDIN_IDEAS_TEMPLATE.md`): weekly post idea generator scanning 5 sources (Lenny's, a16z, Hugging Face, OpenAI, Anthropic)
- **LinkedIn ideas cron job**: every Friday 8:30 AM EST, generates 5 post ideas grounded in real experience, saves to file, delivers to Telegram
- **Web app design doc** (`WEB_APP_DESIGN.md`): brainstorm for future FastAPI + React dashboard
- **Color coding in run_scoring.py**: company cells auto-colored by status (green=Applied, blue=Interview, red=Rejected, grey=Closed, yellow=Not Applied)
- **Business letter format** for cover letter PDFs: date, recipient block, salutation, body, standard closing, enclosure notation
- **Legal status** in resume header: "U.S. Permanent Resident"
- **Custom JD pipeline**: supports .docx files as job description source

### Changed
- Bullet word limit increased from 25 to 35 across all scripts
- Cron prompt rewritten: final response must be ONLY the report — no narration, no explanations
- EPAM dates locked to "May 2026" — template rule prevents changing to "Present" (background check integrity)
- Job titles locked to master profile — template rule prevents inflation
- Cover letter template rule: no closing/signature — generator adds standard business closing
- Page margins reduced from 0.75" to 0.6"

### Fixed
- Quality gate false positives: per-sentence conflation check, expanded verb list (55+)
- Cover letter duplicate signature: generator strips agent closings, always renders standard business closing
- Source column bug: cron agent was setting location_1/location_2 instead of boston/remote
- Job ID assignment for manually added jobs
- run_scoring.py auto-applies color coding after scoring

### Pipeline Stats (to date)
- 324 jobs tracked, 12 applied, 2 interviews, 1 rejected, 6 closed
- Quality gate scores: 87-100 across all generated resumes
- Scripts: 12 active (8 obsolete removed)

## [0.6.0] - 2026-07-20

### Added
- **Batch review pipeline validated**: `run_batch_review.py` tested end-to-end on Veeva dual-role scenario — 1 subagent reviews both resumes in ~150s, catches cross-resume consistency issues
- **Same-company adapter tested**: `adapt_resume.py` tested and reverted — full generation produces better quality when roles have different domain focus (PromoMats vs Development Cloud)

### Changed
- Pipeline standardizes on: **full generation per resume + batch review for multiple resumes**
- Adapter (`adapt_resume.py`) kept for very similar roles only (e.g., Senior vs Lead same product line)

### Tested
- Veeva Senior PM + Technical PM pipeline: 2 full generations + 1 batch review = 3 subagents (vs 4 previously)

## [0.5.0] - 2026-07-20

### Added
- **Batch review** (`run_batch_review.py`): reviews up to 4 resumes in one subagent call (~70% review token savings)
- **Same-company adapter** (`adapt_resume.py`): adapts base resume for second role at same company (~50% generation token savings)
- **Cover letter PDF generation**: business letter format with date, recipient block, salutation, body, closing, enclosure notation
- **Legal status** in resume header (U.S. Permanent Resident)
- **Insulet Corporation** job added to journal with full scoring

### Changed
- Page margins reduced from 0.75" to 0.6" for more content space
- Page 2+ header simplified to name only (no contact info — ATS-friendly)
- Company cells color-coded in journal (green=Applied, red=Rejected, grey=Closed, yellow=Not Applied)
- EPAM end date changed to "Present" across all resumes

### Removed
- 8 obsolete scripts: `score_jobs.py`, `tailor_resume.py`, `tailor_resume_v2.py`, `update_scores.py`, `prepare_scoring.py`, `archive_applied.py`, `report_helper.py`, `report_today.py`

### Fixed
- Quality gate false positives: summary conflation now checks per-sentence, verb list expanded to 55+
- Review JSON cleanup: handles both flat and nested structures, special characters in company names
- Cover letter PDF: business letter format with all 6 standard elements

## [0.4.0] - 2026-07-20

### Fixed
- **Quality gate false positives**: Summary conflation now checks per-sentence instead of whole paragraph — legitimate multi-engagement summaries no longer falsely flagged
- **Action verb list**: Expanded from ~35 to 55+ verbs (added completed, won, generated, secured, unlocked, etc.)
- **Review file naming**: Handles special characters in company names (e.g., Advisor360°)
- **Nested review JSON**: Supports both flat (`hr_score`) and nested (`hr_recruiter_review.total_score`) JSON structures
- **Career order validation**: Fixed `infinity_idx` typo crash in `validate_tailoring.py`
- **Validator reorder**: Now reads career order from config instead of hardcoded company names

### Changed
- **Quality gate is informational, not blocking**: PDFs generate regardless of Gate 2 scores; review notes attached as separate txt file
- **JSON review files deleted after extraction**: Only txt notes kept
- **Page 2+ header simplified**: Name only, no contact info (saves space, avoids ATS parsing issues)

### Added
- Clark University MSc IT support in career order and validation
- Dates validation on highlight headers
- Tools format validation (dict vs list, markdown asterisks check)
- `config.json → candidate` section: name, career_order, conflation_metrics, client_keywords

## [0.3.0] - 2026-07-19

### Added
- **Resume design system**: `theme.json` controls fonts, colors, margins, spacing, bullet styles, education entries, contact info
- **Config-driven scoring**: Priority thresholds, preferred location, domain weights read from `config.json`
- **Human review (Gate 2)**: LLM-based HR + Hiring Manager review with scoring rubric, interview questions, and regenerate feedback
- **Quality gate integration**: `generate_pdf.py` runs both gates before generating PDFs

### Changed
- All hardcoded personal data removed from scripts (name, dates, contact info, education, career order)
- Scripts now fully generic for public repo — all personal config in `config.json` and `theme.json`
- Bullet formula enforced: verb + product + scope + measurable result + method (15-25 words)
- EPAM entry requires cohesive intro line (italic) framing the role

### Fixed
- Tools section: handles both dict and list formats from subagents; strips markdown asterisks
- Career order: validator auto-reorders highlights to match config

## [0.2.0] - 2026-07-17

### Added
- **Tailoring prompt template**: Standardized prompt for LLM resume generation with 12 structural rules
- **Review prompt template**: HR and hiring manager review rubrics
- **Configurable keywords and locations**: `config.json` drives search parameters
- **Daily automation**: Cron job searches LinkedIn, scores new jobs, delivers to Telegram
- **Application tracking**: Status, App URL, Date Applied columns in journal

### Changed
- Scoring algorithms replace LLM subjective scoring:
  - `match_score.py`: 6-component weighted formula (domain, skills, seniority, years, location, entrepreneurship)
  - `ats_score.py`: Keyword overlap across 7 categories
  - `interview_prob.py`: 6-factor probability model
- Priority thresholds: High ≥80, Medium 65-79, Low <65
- Resume output format: PDF (ReportLab) replaces DOCX

## [0.1.0] - 2026-07-14

### Added
- Initial pipeline: LinkedIn search → journal → scoring → resume tailoring
- `search_linkedin.py`: Browser-based LinkedIn job extraction
- `journal.py`: XLSX journal with 4 sheets (Jobs, Applications, Resume Versions, Reference)
- `generate_pdf.py`: ReportLab PDF generator with professional formatting
- `validate_tailoring.py`: 13 structural checks + auto-fix
- `quality_gate.py`: 6-category technical quality scoring (Gate 1)
- Master profile template
- GitHub repo created: https://github.com/MrLion/JSpotter