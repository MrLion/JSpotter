# Changelog

All notable changes to this project are documented here.

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