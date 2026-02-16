# Changelog

All notable changes to Auto-Explorer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
