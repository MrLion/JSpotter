# Changelog

All notable changes to this project are documented here.

## [0.14.1] - 2026-08-27

### Removed
- **`interview_prob.py` and the Interview Probability column** — the 6-factor interview-probability estimate was redundant with the match score and added no actionable signal. The column is deleted from the journal (data migrated; backup at `/tmp/journal_backup_pre_interview_removal.xlsx`), the module is removed, and `run_scoring.py` no longer computes or writes it. The Telegram report drops the `Prob:` field. `JOBS_COL_INDEX` re-derives all column positions automatically; the Recommendation column shifts from col 19 to col 18.

## [0.14.0] - 2026-08-27

### Added
- **Hard-constraint gates (deal-breakers before scoring)** — new `scripts/hard_constraints.py` module + a pre-scoring gate check in `run_scoring.py`. Gates: allowed locations (Boston/Remote), fully on-site demands outside allowed locations (including on-site cities named inside the JD text), compensation floor ($140,000 — from Adzuna non-predicted salaries or JD text, hourly-rate immune, inclusive at the floor, fail-open when salary is undisclosed), max years-of-experience requirement (20), and text blockers (security clearance, citizenship requirements). A job failing any gate is never scored or prioritized: it gets match=0, `Recommendation: SKIP: <reason>`, and surfaces in the new 🚫 Gated section of the daily Telegram report instead of the high-priority list. All thresholds live in `config.json → hard_constraints` (unset/null = gate inactive; both configs updated).
- **`Recommendation` column in the journal (Jobs sheet, col 19)** — `APPLY` / `MAYBE` / `LOW FIT` from score bands, or `SKIP: <reason>` from gates. Appended only (no existing column indexes shift); header is added idempotently to existing journals by both `journal.py --add` and `run_scoring.py`.
- **`scripts/extract_requirements.py` — JD requirement extraction** — classifies every requirement in a JD as `required` / `preferred` / `bonus` with category and confidence, stored in `output/requirements_cache.json`. Primary engine: ollama-cloud (`glm-5.3-flash`, OpenAI-compatible endpoint, 5 parallel workers, ~4s/JD); automatic fallback to a pure-Python heuristic classifier when the LLM is unavailable. Every extracted requirement is quote-verified against the source JD (hallucination guard); markdown-fenced and token-truncated model output is salvaged; LLM errors are recorded in the cache and surfaced in `--report` instead of failing silently. Config via env (`EMR_ENDPOINT`/`EMR_MODEL`/`EMR_TIMEOUT`/`EMR_MAX_TOKENS`/`EMR_WORKERS`/`OLLAMA_API_KEY`, falling back to `~/.hermes/.env`).
- **`run_daily.sh` step 4** — the daily cron now runs requirement extraction after scoring (cap 40/run, cache-backed, no-op for already-extracted JDs). Both the local and template copies updated.
- **Salary Estimate autofill** — `journal.py --add` now fills the Salary Estimate column from `output/adzuna_extract.json` real (non-predicted) salaries, with annual-range sanity bounds.

### Changed
- **`run_scoring.py` JD fetch preserves line structure** — block-level tags now convert to newlines instead of flattening everything to one line, so requirement/section parsing has real boundaries going forward (the existing cache remains flattened; new fetches accumulate structured). JSON-LD fallback also preserves `\n`.
- **Priority-threshold config load hoisted out of the per-job loop** in `run_scoring.py` (was re-reading config.json once per row).
- **Docs** — SETUP.md project structure and pipeline table cover the two new scripts; run_daily.sh steps documented.

### Fixed
- **Hardcoded values removed across the pipeline** — all gate thresholds now read from `config.json → hard_constraints` (location tokens, remote tokens, onsite phrases, salary sanity bounds, states, generic words); all journal column numbers now derive from a single `journal.JOBS_COL_INDEX` map instead of hardcoded indexes scattered across `run_scoring.py`, `ats_score.py`, `match_score.py`, `interview_prob.py`, and `journal.py`; extraction thresholds and heuristic cue vocabularies are env-overridable (`EMR_*`). Only structural regexes and fallback defaults remain in code.

## [0.13.4] - 2026-08-27

### Fixed
- **`run_scoring.py` NameError in the description-fetch loop** — the loop referenced an undefined variable, so every description fetched by the thread pool was silently discarded and the retry loop re-fetched everything serially with a 2s delay per job. Descriptions now cache on first fetch and the progress counter reports correctly.
- **`search_linkedin.py` jobs missing `search_mode`** — jobs fetched via the guest API are now tagged with the search mode of the config location they came from (`remote` for remote-only locations, otherwise the lowercased location name). Fixes empty Source column entries in the journal (171 rows and counting) and empty per-mode sections in the daily Markdown report.
- **`email_triage.py` counts** — `counts` now reflects only NEW candidates; previously it counted all candidates including already-seen ones, so consumers keyed on counts could re-report old mail every run.
- **`journal.py` empty status** — an empty `status` value in source JSON now writes "Not Applied" instead of an empty cell (which openpyxl round-trips to None, losing the status color coding).
- **`run_batch_review.py --save`** — now accepts an optional batch-file path (`--save [path]`) instead of ignoring it, filters the flag out of resume paths, and creates `resume/tailored/` if missing.

### Changed
- **`journal.py` Source normalization** — Source values are lowercased on write, ending the `LinkedIn`/`Dice`/`dice` casing drift in the journal.
- **`interview_prob.py` stricter missing-domain keywords** — broad single words (`security`, `compliance`, `consumer`, `brand`, `monitoring`, `device`, …) fired on generic JD text and wrongly penalized regulated-fintech/B2C postings −6 to −24 interview-probability points. Matching now uses the same multi-word standard as the config-driven match score.
- **`match_score.py` docs corrected** — domain match is 40 pts (docstrings said 35); matches SETUP.md and the actual code.
- **`generate_pdf.py`** — cover-letter name stripping now relies solely on the configured candidate name.
- **Docs** — removed the Pillow requirement (no script uses it); corrected SETUP.md file-organization (no `resume/tailored/reviews/` dir exists; documented that `update_status()` moves PDFs/TXTs only and stray `*_review.json` files must be moved by hand).

### Removed
- **Dead browser-flow code in `search_linkedin.py`** — no-op browser-orchestration function, sign-in/scroll/extract JS constants, AppleScript helper, unused `build_search_urls`, and the `--boston`/`--remote`/`--input` flags the guest-API flow ignored.
- **Phantom `--mode` option in `journal.py`** — documented in the docstring but never wired to argparse; the unused parameter dropped from `add_jobs()`.
- **Unused imports and locals** across `ats_score.py`, `match_score.py`, `interview_prob.py`, `run_scoring.py`, `journal.py`, `search_adzuna.py`, `search_dice.py`, `generate_pdf.py`, and `run_review.py` (stale `descriptions_2026-07-14.json` standalone entry points untouched).

## [0.13.3] - 2026-08-27

### Added
- **`journal.py --remove` command** — remove jobs from the journal via the standard pipeline (no custom scripts). Supports `--company`/`--title` match, `--url` substring match (e.g. a LinkedIn job ID), and `--remove-all-medlow` to delete all Medium/Low priority, Not Applied jobs at once. Tested against a temp copy; the real journal is untouched.

## [0.13.2] - 2026-08-26

### Added
- **`scripts/search_adzuna.py` — Adzuna job search via REST API** — fetches product-management roles from the Adzuna API (no browser/login needed) and writes them to `output/adzuna_extract.json` in the same shape the journal/scoring expects. Reads keywords/location from `config.json` and credentials from `config.json → credentials.adzuna`. Paginates up to 500 results, dedupes by URL, and filters by `search.title_filter_terms`. Adzuna credentials stay in the gitignored `config.json` (template includes generic placeholders).
- **`credentials.adzuna` in `config.json`** — `app_id`/`app_key` for the Adzuna API, kept local (never pushed).

## [0.13.1] - 2026-08-26

### Added
- **`scripts/email_triage.py` — email inbox triage scanner** — scans iCloud and Gmail inboxes via `himalaya` for employer emails and classifies each into a type: `rejection`, `interview`, `confirmation`, `referral`, or unclassified. Outputs JSON to stdout for the daily cron to process. Genericized for the repo (env-overridable config via `EMJ_STATE`/`EMJ_ACCOUNTS`/`EMJ_MAILBOX`/`EMJ_WINDOW_DAYS`/`HIMALAYA_CMD`, machine-independent defaults, standard library only — no hardcoded credentials).
- **Multi-account scanning** — the scanner now reads from both `icloud` and `gmail` himalaya accounts (configurable via `EMJ_ACCOUNTS`). Each candidate is tagged with its `account`; the dedupe state is keyed `account:id` so message IDs that collide across accounts don't clobber each other.

### Changed
- **`email_rejection_scan.py` renamed to `email_triage.py`** — the script triages multiple signal types (interviews, confirmations, referrals) rather than only rejections, so it was renamed to match its expanded role. Classification priority: rejection > confirmation > referral > interview (confirmations are matched before interviews because they contain boilerplate like "interview resources"/"next steps"). JSON output adds a `type` field per candidate plus type `counts`; the existing `found_ts`/`window_days`/`total_scanned`/`new_candidates`/`all_candidate_ids` fields are preserved. Type labels use plain words (`interview`, `confirmation`) rather than underscored code names.
- **Interview detection simplified to subject-line matching** — interview requests are now matched on the subject line (genuine emails carry "interview"/"onsite"/"screen" there), not body heuristics. Body matching over-fires on newsletter boilerplate ("next steps", "availability", "interview resources"); subject matching returns exactly the real interview threads with no exclusion lists needed.
- **`amazon.jobs` removed from the non-employer exclusion list** — Amazon now sends referral and application-confirmation emails that should be classified.
- **Dedupe state moved to the project** — the state file now lives at `output/email_triage_seen.json` (gitignored, alongside `journal.db` and `descriptions_cache.json`), following the project's `BASE_DIR` convention, instead of a scattered `~/.local/state/` path.

### Removed
- **Redundant cron wrapper/symlink** — the cron job previously ran the script through a thin wrapper (and later a symlink) under the profile scripts dir. Removed both: the cron prompt now runs `scripts/email_triage.py` directly via the terminal tool. There is one source of truth (the committed repo script) and no indirection.

## [0.13.0] - 2026-08-26

### Added
- **`search_linkedin.py` self-fetching via LinkedIn guest API** — the script now fetches fresh job listings directly via curl (`jobs-guest/jobs/api/seeMoreJobPostings/search`), no browser or manual extraction needed. Running `python3 scripts/search_linkedin.py` fetches, dedups, filters, and writes `output/linkedin_extract.json` in one step. Fixes the daily cron silently re-processing stale extracts and reporting "0 new jobs".

### Changed
- **Scripts moved to `scripts/` folder** — all pipeline scripts relocated from the repo root into `scripts/`, with `BASE_DIR` updated to `Path(__file__).parent.parent` so they resolve `config.json`, `journal.xlsx`, `resume/`, and `output/` from the project root. `run_daily.sh` and docs updated to reference `scripts/`.
- **`run_review.py` moved into `scripts/`** — relocated from repo root to match the structure documented in `docs/SETUP.md`; its `OUTPUT_DIR` now resolves from the project root.
- **`templates/run_daily.sh` added** — generic daily pipeline runner for the repo; the local copy with absolute paths stays gitignored (matches the `config.template.json` / `config.json` pattern).

### Fixed
- **`templates/config.template.json` rebuilt to match the scripts** — added missing `candidate` keys (`full_name`, `bad_keywords`, `pandering_phrases`, `client_names_in_profile`, `client_employment_regex`, `include_name_in_filename`), added the full `scoring.domains` definitions, expanded `domain_weights` from 8 to all 12 domains (corrected stale names like `Enterprise` → `Enterprise/B2B`), set the single-USA search location, and corrected `results_file` to `output/linkedin_extract.json`. A fresh copy now works with the scripts.
- **Doc inconsistencies** — removed pinned cron model/provider (no longer indicated); updated `linkedin_extract_today.json` → `linkedin_extract.json` in `docs/SETUP.md`; added `TELEGRAM_TEMPLATE.md` and `run_daily.sh` to the project-structure tree; corrected LinkedIn search to guest API (not browser); added `adapt_resume.py`, `run_batch_review.py`, and `run_review.py` to the Pipeline Scripts table; clarified that browser configuration is only needed for the Dice search, not the daily LinkedIn scan.

## [0.12.1] - 2026-08-22

### Fixed
- **`update_status()` Applied archiving in journal.py** — previously only archived files for Rejected/Closed/Withdrawn, so Applied roles' PDFs stayed in `tailored/` root instead of moving to `applied/`. Added an `Applied` branch that moves PDFs/TXTs into `applied/`.
- **Company filename matching** — replaced substring match with normalized matching (strips punctuation/spaces/case) so names like "Qventus, Inc" match filenames like "Qventus Inc".
- **Review notes moved with resumes for Rejected/Closed/Withdrawn** — previously only PDFs were archived from the root for these statuses, leaving `*_review_notes.txt` behind in `tailored/`. Now TXT review notes are moved to `archived/` alongside resumes/cover letters.

### Changed
- **`include_name_in_filename` config flag in generate_pdf.py** — candidate name prepended to generated PDF filenames is now optional. Set `candidate.include_name_in_filename: false` to omit it (default `true`, backwards compatible).

## [0.12.0] - 2026-08-15

### Added
- **Capital Markets domain** — split from Finance; weight 12, `has_in_profile: false`. Keywords: trading, capital markets, investment, portfolio management, Charles River, Aladdin, Simcorp, fixed income, buy-side, sell-side, asset manager, hedge fund, investment bank, trading lifecycle, order management
- **Life Sciences/Bioprocessing domain** — weight 12, `has_in_profile: false`. Keywords: bioprocessing, chromatography, affinity ligands, resin, protein purification, downstream processing, biologics, biopharmaceutical, fermentation, cell culture, purification, GMP, upstream processing, drug substance, drug product
- **`update_status()` function in journal.py** — single function for status changes; updates Status + Last Updated columns, sets Date Applied, color-codes company cell, auto-archives PDFs/TXTs to `archived/` for Rejected/Closed/Withdrawn
- **Last Updated column** in journal (col 18) — tracks date of last status change
- **Candidate name in PDF filenames** — e.g., `Candidate_Name_Company_Title_v1.pdf`
- **Tailoring prompt rule 14 updated** — cover letter must NOT include date/company/Re: header (PDF generator adds them)
- **Job hunting pipeline skill** — saved as reusable skill with full pipeline steps, file organization, and common pitfalls

### Fixed
- **Domain scoring: word boundary matching** — keywords now use `re.search(r'\b...\b')` instead of `kw in desc_lower`; fixes "iot" matching inside "biotechnology", "equity" matching in compensation text
- **Removed "equity" from Capital Markets keywords** — too ambiguous (stock compensation vs equity markets)
- **Cache overwrite guard in run_scoring.py** — `fetch_job_description()` no longer overwrites existing cached JDs
- **Domain definitions moved from match_score.py to config.json** — all domain keywords, weights, and has_in_profile flags are now config-driven
- **Removed hardcoded candidate name from scripts** — quality_gate.py and validate_tailoring.py now read `full_name` from config.json instead of hardcoding "Georgii"
- **Full sweep: all personal data moved to config.json** — client names, conflation metrics, client keywords, bad keywords, pandering phrases, client employment regex, career order all config-driven; zero hardcoded company names or candidate data in quality_gate.py or validate_tailoring.py
- **Multi-word domain keywords** — replaced generic single-word keywords ("security", "compliance", "investment", "equity") with multi-word variants to eliminate false positive domain matches across unrelated JDs
- **Cybersecurity keywords overhauled** — "security" replaced with "cybersecurity", "security operations", "threat detection", "zero trust", etc.
- **Capital Markets keywords refined** — removed "equity" and "investment", added "investment bank", "investment banking", "equity trading", "derivatives", "securities"
- **Finance keywords refined** — "compliance" replaced with "financial compliance", "regulatory" with "regulatory reporting", "payment" with "payment processing"
- **Tailoring prompt rule 16 added** — no cross-domain analogies; if JD doesn't mention AI/ML, don't include AI/ML in summary or strength labels
- **Tailoring prompt rule 15 added to file** — surface leadership bullets when JD requires senior experience
- **update_status() function** — single function for status changes with auto-archiving, timestamping, color coding
- **Last Updated column** added to journal (col 18)
- **Project structure moved from README.md to SETUP.md**
- **Review JSON/TXT file organization** — review JSONs in `tailored/reviews/`, review notes TXT in `tailored/` or `tailored/applied/`, rejected job files in `tailored/archived/`
- **Cover letter duplicate header** — removed date/company/Re: block from cover letter text (PDF generator handles it)

### Changed
- **Bioprocessing role** match score: 84 (High) → 60 (Low) — Life Sciences/Bioprocessing domain correctly flagged as missing
- **Capital markets role 1** match score: 87 (High) → 72 (Medium) — Capital Markets domain correctly flagged as missing
- **Capital markets role 2** match score: 98 (High) → 78 (Medium) — Capital Markets domain correctly flagged as missing
- **LinkedIn search locations** — removed metro-specific filter, now USA only (remote + hybrid + on-site)
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