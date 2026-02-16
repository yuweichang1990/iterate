# Changelog

All notable changes to Auto-Explorer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.0] - 2026-02-16

### Added
- **Exploration templates** (`--template <name>`): Pre-configured exploration strategies that shape how Claude structures research. 5 built-in templates:
  - `deep-dive` — Exhaustive research covering theory, practice, ecosystem, and edge cases (6-phase structure)
  - `quickstart` — Practical focus with working code examples, get productive fast (6-phase structure)
  - `architecture-review` — Structural analysis of a codebase: dependencies, patterns, testing, security, performance (10-phase structure)
  - `security-audit` — Security-focused analysis: attack surface, input validation, auth, secrets, CVEs, configuration (10-phase structure)
  - `comparison` — Structured side-by-side evaluation with criteria, scoring matrix, and verdict (4-phase structure)
- **Compare mode** (`--compare`): Convenience flag for `--template comparison`. Produces structured technology comparisons with evaluation framework, individual analysis per option, head-to-head scoring matrix, and recommendation
- **HTML export** (`/explore-export [slug]`): Generate navigable single-file HTML reports from session findings. Zero external dependencies. Features: sidebar navigation, dark/light mode (`prefers-color-scheme`), responsive layout, print-friendly, CJK support. Auto-generated on session completion
- `scripts/export-html.py`: Zero-dependency Markdown→HTML converter with `convert_inline()`, `render_table()`, `md_to_html()`, `generate_report()` functions. Supports headers (h1-h6 with anchors), fenced code blocks, tables, ordered/unordered lists, horizontal rules, bold/italic/code/links
- `scripts/helpers.py`: `load_template()`, `list_templates()` functions and `load-template`, `list-templates` CLI commands for template loading with frontmatter parsing and `{{TOPIC}}`/`{{OUTPUT_DIR}}` placeholder substitution
- `.claude/skills/explore-export/SKILL.md`: New slash command skill for on-demand HTML report generation
- `templates/` directory: 5 built-in template files with YAML frontmatter (name, description, mode) and body with placeholder support
- `tests/test_export.py`: 33 tests for HTML export (inline conversion, Markdown→HTML, table rendering, report generation, dark mode, responsive CSS, CJK content)
- `tests/test_templates.py`: 22 tests for template loading, listing, built-in template content validation, documentation checks
- `tests/test_compare.py`: 15 tests for comparison template, --compare flag, documentation consistency

### Changed
- `hooks/stop-hook.sh`: Auto-generates HTML report (`report.html`) on session completion alongside summary; completion message shows HTML report path
- `scripts/setup-auto-explorer.sh`: Added `--template`, `--compare` flags; template body injection replaces default state file body; template mode overrides auto-detection (but `--mode` flag overrides template); `--template` and `--compare` cannot combine with `--resume`
- `.claude-plugin/plugin.json`: Version 2.0.0; updated description with new features; registered `explore-export` skill
- `.claude-plugin/marketplace.json`: Version 2.0.0 (3 locations); updated descriptions
- `.claude/skills/explore-help/SKILL.md`: Documented `--template`, `--compare`, `/explore-export` with descriptions and examples
- `SCENARIOS.md`: Moved Exploration Templates, HTML Export, Compare Mode, and Audit Mode from "Future Directions" to current features sections
- Total test count: 155 → 225 (+70 new tests)

## [1.6.0] - 2026-02-16

### Added
- **Interactive steering** (`/explore-steer`): Redirect an active session mid-flight without cancelling it. Write a direction change that takes effect on the next iteration. Supports both build and research modes with "STEERED by user" indicator in system messages
- **Session resume** (`--resume [slug]`): Continue a previous session that was rate-limited, max-iterations, cancelled, or errored. Full context injection via `_index.md`, iteration counter continues from where it left off. New "resumed" `[->]` status in history
- **Token usage reporting**: Session end messages and dashboard now show estimated output tokens, files written, and total output KB. New lifetime stats section in dashboard (total sessions, iterations, tokens, files, output size)
- `scripts/helpers.py`: `get_session_stats()` function and `session-stats` CLI command for extracting token counts from transcript JSONL and output directory stats
- `scripts/history.py`: `cmd_resume()` for finding and marking resumable sessions; `RESUMABLE_STATUSES` constant; extended `cmd_end()` with `estimated_tokens`, `files_written`, `total_output_kb` fields
- `.claude/skills/explore-steer/SKILL.md`: New slash command skill that writes a steer file consumed by the stop hook
- `tests/test_steer.py`: 13 tests for interactive steering (gitignore, stop hook logic, skill config, help docs)
- `tests/test_resume.py`: 15 tests for session resume (history resume, status icons, resumable statuses, docs)

### Changed
- `hooks/stop-hook.sh`: Reads/consumes steer file for direction changes; transcript extraction moved earlier for session stats; all 3 end paths pass token stats to history; end messages show token count and `--resume` hint
- `scripts/history.py`: Dashboard shows per-session token estimate and lifetime stats section; "resumed" `[->]` status icon added to legend; helpers import moved to top of `cmd_show()` for broader access
- `.claude/skills/explore-help/SKILL.md`: Documented `/explore-steer` and `--resume` with examples
- `.gitignore`: Added `.claude/auto-explorer-steer.md`
- Total test count: 129 → 155

## [1.5.0] - 2026-02-16

### Added
- **Top-3 topic suggestions**: When running `/auto-explore` without a topic, shows up to 3 suggestions from your interest profile (not just auto-selecting the first one)
- `scripts/helpers.py`: `get_active_info()`, `validate_limits_config()`, `abbreviate_number()`, `suggest_topics()` functions with corresponding CLI commands (`active-info`, `validate-limits`, `suggest-topics`)
- `.topic` file created in output directory for CJK slug readability (maps hash-based slugs back to the original topic)
- Rate limits config validation on startup with warning for malformed JSON
- Dashboard threshold `|` markers on progress bars showing where the stop threshold is
- Abbreviated numbers in dashboard (281k, 4.1M instead of raw numbers)
- `tests/test_helpers.py`: 22 new tests for active-info, validate-limits, abbreviate-number, suggest-topics

### Changed
- Plugin descriptions optimized in `plugin.json` and `marketplace.json` for better marketplace discovery
- "Session already active" error now shows topic, mode, iteration, and duration (not just a generic message)
- Dashboard rate limits header changed to "Rate Limits (| = stop threshold)"
- History entry labels changed from `>> reason` / `>> output_dir/` to `Result: reason` / `Output: output_dir/`
- "Resume later" text in stop hook changed to "Continue later: /auto-explore $TOPIC (starts new session)"
- `.claude/skills/explore-help/SKILL.md`: Added link to SCENARIOS.md
- Total test count: 94 → 129

## [1.4.0] - 2026-02-16

### Added
- **Auto-export summary on session completion**: When `<explore-done>` is detected, Auto-Explorer automatically injects one more prompt asking Claude to generate a comprehensive `summary.md` before ending the session — mode-aware prompts for both build and research modes
- `tests/test_auto_export.py`: 9 tests validating auto-export flag file consistency, prompt content, and cleanup across stop-hook.sh, cancel-explore, and .gitignore
- `SCENARIOS.md`: Comprehensive bilingual (EN/ZH) scenarios and introduction document covering all existing features and future directions — research mode, build mode, CJK support, monitoring, target audiences, and planned features (compare mode, audit mode, session resume, fresh context, templates, HTML export, custom stop conditions)

### Changed
- `stop-hook.sh`: `<explore-done>` handler now creates a `.claude/auto-explorer-summary-pending` flag file and injects a summary generation prompt instead of immediately ending — the next stop-hook invocation detects the flag and ends the session with the summary path in the completion message
- `cancel-explore/SKILL.md`: Now cleans up the summary-pending flag file alongside the state file
- `.gitignore`: Added `.claude/auto-explorer-summary-pending` to ignored files
- Total test count: 85 → 94

## [1.3.0] - 2026-02-16

### Added
- `LICENSE` file (MIT) for open-source discoverability and trust
- Stale session detection: sessions >24h old are auto-cleaned instead of permanently blocking new sessions
- `scripts/helpers.py`: shared utility module extracted from inline Python in bash scripts — single source of truth for frontmatter parsing, slug generation, mode detection, tag extraction, stale detection, topic suggestion, duration formatting, and rate summary formatting
- `tests/test_helpers.py`: 27 tests covering all helpers.py functions (frontmatter, slug, stale, suggestion, duration, rate summary)
- `tests/test_bash_syntax.py`: validates both `.sh` scripts pass `bash -n` syntax check (Windows-aware: finds Git Bash explicitly to avoid WSL)
- `tests/test_version_consistency.py`: validates version numbers are consistent across `plugin.json`, `marketplace.json`, and `CHANGELOG.md`
- `tests/conftest.py`: shared test configuration with `import_script()` helper for importing hyphenated script filenames
- Polite prefix stripping for mode detection: "please build", "can you fix", "請進化", "請自我進化", "幫我建立" etc. now correctly detect build mode (8 English + 11 CJK prefixes)
- `.github/workflows/test.yml`: CI/CD with GitHub Actions — runs on push/PR, tests on Python 3.9 + 3.12 (ubuntu) and 3.12 (windows)

### Fixed
- **Critical**: `stop-hook.sh` used `$SCRIPT_DIR` before it was defined (regression from helpers.py extraction) — moved `SCRIPT_DIR` definition before first `helpers.py` call

### Changed
- `stop-hook.sh`: all 6 inline Python blocks replaced with `helpers.py` calls (frontmatter parsing, duration formatting, JSON field extraction, rate summary, tag extraction, JSON output)
- `setup-auto-explorer.sh`: all 5 inline Python blocks replaced with `helpers.py` calls (topic suggestion, stale check, stale info, slug+mode detection); 4 separate Python calls for stale session info consolidated into 1
- `test_tag_extraction.py` and `test_mode_detection.py` now import from `helpers.py` instead of duplicating logic
- Total test count: 48 → 85

## [1.2.0] - 2026-02-16

### Added
- **Phase 3: Product & Strategy** in build mode — after engineering enhancements, Claude now evaluates product/UX improvements: friction reduction, better defaults, onboarding, competitive positioning, and delight moments
- Auto-create `~/.claude/auto-explorer-limits.json` with sensible defaults on first use — eliminates silent no-guardrails first-run
- First-use welcome message with quick tips when no session history exists
- Richer session completion messages showing topic, mode, iterations, duration, file count, and next-step suggestions (for all end conditions: completed, rate-limited, max-iterations)
- Expanded build mode auto-detection: 17 new English verbs (`improve`, `optimize`, `update`, `configure`, `install`, `redesign`, `integrate`, `automate`, `extract`, `remove`, `delete`, `replace`, `move`, `rename`, `split`, `merge`, `clean up`, `debug`, `patch`, `scaffold`, `generate`, `wire up`) and 18 new CJK verbs
- `tests/test_mode_detection.py`: 9 test cases with 76 subtests covering all English and CJK patterns

### Fixed
- Stop hook `get_session_duration()` no longer re-parses state file — uses `started_at` from single frontmatter parse
- Stop hook duration calculation now passes timestamp via `sys.argv` instead of bash string interpolation (prevents injection)
- `count_output_files()` trims whitespace from `wc -l` output with `tr -d ' '`

### Changed
- Build mode Phase 2 renamed to "Engineering Enhancement" (was "Autonomous Enhancement") for clarity alongside new Phase 3
- Session end messages now include structured summary with duration and file count instead of terse one-liners
- Setup output simplified: removed implementation details (stop hook mechanism, config file paths), now shows only topic/mode/output/budget + action commands
- Stop hook prompt now explicitly reminds Claude to update `_index.md` every iteration (prevents lost progress on unexpected stop)
- Stop hook prompt uses `<descriptive-name>` instead of `<task-slug>` placeholder for clarity
- Dashboard shows "Start one: /auto-explore <topic>" when no active session (call-to-action instead of dead end)
- History entries now display output directory path so users can find results after session ends
- Total test count: 39 → 48

## [1.1.0] - 2026-02-16

### Added
- `--mode` flag: Force `research` or `build` mode, overriding auto-detection
- `.gitignore`: Prevents runtime artifacts from being tracked by git
- Test suite: 39 tests covering rate limits, history manager, tag extraction, and stale sessions
- Python 3.6+ version check in setup script and stop hook
- Rate limit usage display in `/explore-status` dashboard with ASCII progress bars
- Stale session auto-fix at startup (previously only ran on `/explore-status`)
- `CHANGELOG.md` following Keep a Changelog format
- Developer guide sections: `--mode` flag usage, test running instructions, new design lessons

### Fixed
- **Critical**: `setup-auto-explorer.sh` used `IFS=$'\t'` for Python→bash data passing — the same tab-stripping bug documented in `developer_guide.md` Problem 4 (already fixed in `stop-hook.sh` but missed in setup script). Now uses `$'\x1f'` (Unit Separator)
- Stop hook no longer kills session when transcript is temporarily unavailable — continues with fallback prompt instead
- `rm` → `rm -f` in all stop hook error paths (prevents failure if file already removed)
- State file update protected against sed failure (cleans up temp file on error)

## [1.0.0] - 2026-02-15

### Added
- Initial release
- Research mode: autonomous multi-iteration topic exploration
- Build mode: code implementation with autonomous enhancement phase
- Stop hook engine with rate limit checking (4h/daily/weekly windows)
- Budget levels: conservative (40%), moderate (60%), aggressive (80%)
- Auto-detect mode from topic wording (action verbs → build, otherwise → research)
- Session history tracking and dashboard (`/explore-status`)
- Windows compatibility: Node.js entry point for Git Bash resolution
- CJK encoding fix (UTF-8 forced for Windows CP950/Big5 environments)
- Unit Separator delimiter fix for bash `read` IFS whitespace stripping
- User interest tracking integration (`~/.claude/user-interests.md`)
- Four slash commands: `/auto-explore`, `/cancel-explore`, `/explore-status`, `/explore-help`
