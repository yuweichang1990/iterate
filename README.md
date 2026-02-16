# Auto-Explorer

Autonomous exploration and interest tracking system for Claude Code.
Claude Code 自主探索與興趣追蹤系統。

Tell Claude what you want to explore or build — it will keep going on its own, iteration after iteration, until done.
告訴 Claude 你想探索或建造什麼 — 它會自己一輪接一輪地持續下去，直到完成。

---

## Installation / 安裝

```bash
# 1. Navigate to the parent directory containing auto-explorer/
# 1. 切換到包含 auto-explorer/ 的父目錄
cd /path/to/parent-directory

# 2. Register auto-explorer as a local marketplace
# 2. 將 auto-explorer 註冊為本地 marketplace
claude plugin marketplace add ./auto-explorer

# 3. Install the plugin (globally available across all projects)
# 3. 安裝插件（全域可用，任何專案目錄都能使用）
claude plugin install auto-explorer

# 4. Verify installation
# 4. 驗證安裝
claude plugin list
# Should show: auto-explorer@auto-explorer-marketplace  Status: ✔ enabled
```

> **Note / 注意**: The slash commands (`/auto-explore`, `/cancel-explore`, etc.) will be available in **all new Claude Code sessions**, regardless of which directory you open Claude in.
> 斜線指令在**所有新的 Claude Code session** 中都能使用，不論在哪個目錄開啟 Claude。

---

## Quick Start / 快速開始

```bash
# Recommended: start Claude Code in autonomous mode
# 建議：以自主模式啟動 Claude Code
claude --dangerously-skip-permissions

# Then just pick a topic — Claude handles the rest
# 然後選一個主題就好 — Claude 會處理剩下的
/auto-explore Rust async programming
```

That's it. Claude will research the topic across multiple rounds, writing structured Markdown reports to `auto-explore-findings/rust-async-programming/`. It stops automatically when your account usage reaches the budget threshold.
就這樣。Claude 會跨多輪研究主題，將結構化的 Markdown 報告寫入 `auto-explore-findings/rust-async-programming/`。當帳戶用量達到預算閾值時會自動停止。

### More examples / 更多範例

```bash
# Build mode — auto-detected from action verbs
# 建置模式 — 從動作動詞自動偵測
/auto-explore build a REST API with authentication

# Force a specific mode (overrides auto-detection)
# 強制指定模式（覆蓋自動偵測）
/auto-explore --mode research build system internals
/auto-explore --mode build improve error handling

# Control how much quota to use
# 控制使用多少額度
/auto-explore --budget conservative WebAssembly
/auto-explore --budget aggressive distributed consensus

# Cap the number of iterations
# 限制迭代次數
/auto-explore --max-iterations 30 Go generics

# No topic? Claude picks from your interest profile
# 沒有主題？Claude 會從你的興趣檔案中挑選
/auto-explore
```

---

## Commands / 指令

| Command / 指令 | Description / 說明 |
|---------|-------------|
| `/auto-explore [TOPIC] [OPTIONS]` | Start autonomous exploration / 開始自主探索 |
| `/cancel-explore` | Cancel current exploration / 取消目前的探索 |
| `/explore-status` | Show session dashboard / 顯示 session 儀表板 |
| `/explore-help` | Show detailed help / 顯示詳細說明 |

---

## Two Modes / 雙模式

Auto-Explorer auto-detects which mode to use from your topic wording (override with `--mode`):
Auto-Explorer 會從你的主題用語自動偵測要用哪種模式（可用 `--mode` 覆蓋）：

| Mode / 模式 | When / 何時 | What happens / 行為 |
|------|---------|----------|
| **Research** | Concepts, subjects, questions | Writes Markdown research reports 撰寫 Markdown 研究報告 |
| **Build** | Action verbs (build, fix, implement...) | Writes working code, then autonomously enhances it 撰寫可運行的程式碼，然後自主增強 |

**Build mode** has three phases / 建置模式有三個階段:
1. **Core Implementation** — Complete the requested task / 完成要求的任務
2. **Engineering Enhancement** — Fix bugs, improve robustness, add tests / 修復 bug、提升穩健性、新增測試
3. **Product & Strategy** — Evaluate UX friction, onboarding, and competitive positioning / 評估使用者體驗摩擦、入門體驗與競爭定位

---

## Budget / 預算

Budget controls how much of your account quota to use — not the number of iterations.
預算控制的是帳戶額度的使用比例 — 而非迭代次數。

| Level / 等級 | Threshold / 閾值 | Meaning / 意義 |
|-------|-----------|----------|
| `conservative` | 40% | Stop early, preserve most quota / 提早停止，保留大部分額度 |
| `moderate` | 60% | Balanced (default) / 均衡（預設） |
| `aggressive` | 80% | Use most quota for exploration / 用大部分額度來探索 |

Exploration runs **unlimited iterations** until account usage hits the threshold. `--max-iterations N` is available as an optional hard cap on top of this.
探索會**不限輪次**地持續運行，直到帳戶用量達到閾值。`--max-iterations N` 可作為額外的硬性上限。

---

## Output Structure / 輸出結構

**Research mode / 研究模式:**
```
auto-explore-findings/<topic-slug>/
  00-overview.md          # Broad topic overview / 主題總覽
  01-<subtopic>.md        # First sub-topic deep dive / 第一個子主題
  02-<subtopic>.md        # Second sub-topic / 第二個子主題
  ...
  _index.md               # Running summary, updated each round / 每輪更新的索引摘要
  summary.md              # Final summary (if --max-iterations set) / 最終總結
```

**Build mode / 建置模式:**
```
<working directory>/      # Actual code lives here / 實際程式碼在此
auto-explore-findings/<topic-slug>/
  00-plan.md              # Architecture plan and task breakdown / 架構計畫與任務拆解
  01-<task>.md             # Progress log per sub-task / 子任務進度日誌
  ...
  _index.md               # Running progress overview / 每輪更新的進度總覽
```

---

## How It Works / 運作原理

```
  /auto-explore "topic"
         │
         ▼
  ┌─────────────┐     auto-detect mode
  │ Setup script │───► (research or build)
  └──────┬──────┘     + create state file
         │
         ▼
  ┌─────────────────────────────────┐
  │  Exploration Loop               │
  │                                 │
  │  1. Claude works on sub-topic   │
  │  2. Writes output (MD / code)   │
  │  3. Emits <explore-next> tag    │
  │         │                       │
  │         ▼                       │
  │  ┌─────────────┐               │
  │  │  Stop Hook   │               │
  │  │  • check rate limits         │
  │  │  • extract <explore-next>    │
  │  │  • feed next prompt          │
  │  └──────┬──────┘               │
  │         │                       │
  │    over budget? ──yes──► STOP   │
  │         │no                     │
  │         └── loop back ──────────┘
  └─────────────────────────────────┘
```

Step by step / 逐步說明:

1. **Setup / 初始化**: `/auto-explore` parses your arguments, auto-detects mode from topic wording, creates a state file (`.claude/auto-explorer.local.md`) and output directory.
   解析參數、從主題用語偵測模式、建立狀態檔與輸出目錄。

2. **Exploration loop / 探索迴圈**: Each round, Claude works on a sub-topic/sub-task, writes output, and emits `<explore-next>` to declare what to do next.
   每輪處理子主題/子任務、寫入產出，並用 `<explore-next>` 宣告下一步。

3. **Stop hook / 停止鉤子**: After each response, the stop hook checks rate limits, extracts the `<explore-next>` tag, and feeds it as the next prompt. If budget is exceeded, exploration stops.
   每次回應後，停止鉤子檢查速率限制、提取標籤、餵入下一輪提示詞。超出預算則停止。

4. **Dynamic steering / 動態導向**: Each round's direction is determined by Claude's analysis — not a static repeated prompt.
   每輪方向由 Claude 分析決定，而非重複同一提示詞。

5. **Completion signal / 完成信號**: In build mode, Claude emits `<explore-done>` when the task is genuinely done and no more enhancements are worthwhile.
   建置模式下，Claude 在任務完成且無值得的增強後發出 `<explore-done>`。

---

## Rate Limits / 速率限制

Auto-Explorer checks three time windows to prevent exceeding your Claude plan's usage caps:
Auto-Explorer 檢查三個時間窗口，防止超出 Claude 方案的使用額度：

| Window / 窗口 | Source / 來源 | Default limit / 預設上限 |
|--------|--------|-----------|
| **4h** | Current session transcript / 當前 session | 700,000 tokens |
| **daily** | `~/.claude/stats-cache.json` | 4,100,000 tokens |
| **weekly** | `~/.claude/stats-cache.json` | 29,000,000 tokens |

When any window's usage reaches the budget threshold (e.g. 60% by default), exploration stops.
任一窗口用量達到預算閾值（預設 60%）時，探索即停止。

### Configuration / 設定

Edit `~/.claude/auto-explorer-limits.json`:
編輯 `~/.claude/auto-explorer-limits.json`：

```json
{
  "threshold": 0.6,
  "rate_limits": {
    "4h":     { "tokens": 700000 },
    "daily":  { "tokens": 4100000 },
    "weekly": { "tokens": 29000000 }
  }
}
```

### How the defaults were calculated / 預設值的計算方式

Calibrated by reverse-calculating from actual usage: ~578k local tokens ≈ 2% of weekly cap → 100% ≈ 29M tokens.
依據實際用量反推校準：~578k 本地 tokens ≈ 每週額度的 2% → 100% ≈ 29M tokens。

| Window / 窗口 | Limit (100%) / 上限 | Stops at (60%) / 停止線 | Rationale / 理由 |
|--------|-------|-----------|-----------|
| **4h** | 700,000 | 420,000 | 29M / 42 four-hour windows per week |
| **daily** | 4,100,000 | 2,460,000 | 29M / 7 days |
| **weekly** | 29,000,000 | 17,400,000 | Reverse-calculated from 578k ≈ 2% |

> **Note / 注意**: These are conservative lower-bound estimates. If `stats-cache.json` was reset mid-week, the actual cap may be higher — limits will trigger slightly early, which is safe by design. Adjust as needed.
> 這些是保守的下限估計。如果 `stats-cache.json` 週間被重置過，實際額度可能更高 — 限制會提早觸發，設計上偏安全。可依需求調整。

### Calibration tips / 校準建議

1. Note your current usage % on [Claude's website](https://claude.ai) / 記下 Claude 網站上的用量百分比
2. Check `stats-cache.json` for the same period / 查看同期的 stats-cache 數據
3. Reverse-calculate: `weekly_limit = local_tokens / (website_pct / 100)` / 反推計算
4. Update `~/.claude/auto-explorer-limits.json` / 更新設定檔

---

## Architecture / 架構

```
auto-explorer/
  .claude-plugin/marketplace.json     # Marketplace manifest / Marketplace 清單
  .claude-plugin/plugin.json          # Plugin metadata / 插件元資料
  .claude/skills/
    auto-explore/
      SKILL.md                        # Main skill dispatcher / 主技能調度器
      research-mode.md                # Research mode behavior / 研究模式行為
      build-mode.md                   # Build mode behavior + Phase 2 / 建置模式行為
      rules.md                        # Common rules + completion signal / 共通規則
    cancel-explore/SKILL.md           # /cancel-explore / 取消技能
    explore-status/SKILL.md           # /explore-status / 儀表板技能
    explore-help/SKILL.md             # /explore-help / 說明技能
  hooks/
    hooks.json                        # Stop hook config / 停止鉤子設定
    stop-hook-entry.js                # Windows-compatible entry point / Windows 相容入口
    stop-hook.sh                      # Core engine / 核心引擎
  scripts/
    setup-auto-explorer.sh            # Initialization / 初始化腳本
    check-rate-limits.py              # Rate limit checker / 速率限制檢查
    history.py                        # Session history manager / 歷史管理器
    helpers.py                        # Shared utilities (frontmatter, slug, tags) / 共用工具
  tests/
    test_check_rate_limits.py         # Rate limit tests / 速率限制測試
    test_history.py                   # History manager tests / 歷史管理器測試
    test_tag_extraction.py            # Tag extraction tests / 標籤提取測試
    test_mode_detection.py            # Build/research mode detection tests / 模式偵測測試
    test_helpers.py                   # Shared helpers tests / 共用工具測試
    test_bash_syntax.py               # Bash script syntax validation / Bash 腳本語法驗證
    test_version_consistency.py       # Version consistency checks / 版本一致性檢查
    conftest.py                       # Shared test config / 共用測試設定
  LICENSE                             # MIT License / MIT 授權
  .gitignore                          # Git ignore rules / Git 忽略規則
  CHANGELOG.md                        # Version history / 版本歷史
  developer_guide.md                  # Developer guide / 開發者指南
  README.md                           # This file / 本文件
```

### Companion files / 搭配檔案

| File / 檔案 | Purpose / 用途 |
|------|--------|
| `~/.claude/CLAUDE.md` | Global rules: auto-update interests every session / 全域規則：每次對話自動更新興趣 |
| `~/.claude/user-interests.md` | Persistent interest profile / 持久化興趣檔案 |
| `~/.claude/auto-explorer-limits.json` | Rate limit config / 速率限制設定 |
| `.claude/auto-explorer.local.md` | Runtime state file (per-project) / 執行時狀態檔（每個專案各自） |
| `auto-explore-findings/.history.json` | Session history log / Session 歷史紀錄 |

---

## Coexistence with Ralph Loop / 與 Ralph Loop 共存

Auto-Explorer and Ralph Loop use separate state files and do not interfere with each other. However, running both simultaneously is **not supported** — the setup script will warn if Ralph Loop is active.

Auto-Explorer 與 Ralph Loop 使用不同的狀態檔，資料互不干擾。但**不支援同時運行** — 初始化腳本會警告 Ralph Loop 是否正在運行。

---

## Development / 開發

### Running tests / 執行測試

```bash
# Run all tests (85 tests)
# 執行全部測試（85 個）
python -m pytest tests/ -v

# Run a specific test file
# 執行單一測試檔
python -m pytest tests/test_tag_extraction.py -v
```

### Bash syntax check / Bash 語法檢查

```bash
bash -n scripts/setup-auto-explorer.sh
bash -n hooks/stop-hook.sh
```

For more details, see `developer_guide.md`.
詳細資訊請參閱 `developer_guide.md`。

---

## Dependencies / 相依套件

- **Python 3.6+** — for JSON parsing and rate limit checking (f-strings, `datetime.timezone`)
  用於 JSON 解析與速率限制檢查
- **Bash** — shell scripts run in Git Bash on Windows
  Shell 腳本在 Windows 上透過 Git Bash 執行
- **Node.js** — Windows entry point for stop hook (resolves Git Bash vs WSL)
  Windows 上 stop hook 的入口點（解決 Git Bash 與 WSL 衝突）
- **Claude Code** — with plugin support
  需要支援插件的 Claude Code
