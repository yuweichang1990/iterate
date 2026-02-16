# Auto-Explorer: Scenarios & Use Cases

Turn Claude Code into an autonomous agent that works for hours — not minutes.
讓 Claude Code 變成自主工作數小時的 agent — 而不是幾分鐘。

---

## What is Auto-Explorer?

Most Claude Code sessions follow a pattern: you ask, Claude answers, you ask again. Auto-Explorer breaks this pattern. Give Claude a topic or task, and it keeps going — iteration after iteration — until the work is done or your budget runs out.

大多數 Claude Code 對話遵循一個模式：你問、Claude 答、你再問。Auto-Explorer 打破了這個模式。給 Claude 一個主題或任務，它會一輪接一輪地持續工作，直到完成或預算用盡。

One command. Zero babysitting.
一個指令，零看顧。

---

## Research Mode Scenarios / 研究模式情境

### Deep-dive into a new technology / 深入研究一項新技術

You want to learn Rust async programming but don't know where to start. Instead of reading scattered blog posts, ask Auto-Explorer.

```bash
/auto-explore Rust async programming
```

Claude will spend hours building a structured knowledge base: starting with an overview, then diving into async/await syntax, the Future trait, runtime internals (Tokio vs async-std), pinning, error handling, and real-world patterns. Each iteration goes deeper, and the `_index.md` file always has an up-to-date summary.

**Result**: A folder of well-organized Markdown reports — your personal textbook on the topic, written by an AI that understands context across iterations.

你想學 Rust 非同步程式設計但不知從何開始。與其閱讀零散的部落格文章，不如問 Auto-Explorer。Claude 會花數小時建立結構化的知識庫：從總覽開始，深入 async/await 語法、Future trait、runtime 內部機制、pin、錯誤處理和實務模式。每一輪都更深入，而 `_index.md` 始終有最新摘要。

### Explore a domain you're curious about / 探索你好奇的領域

```bash
/auto-explore distributed consensus algorithms
/auto-explore WebAssembly ecosystem and tooling
/auto-explore 量子計算基礎與最新進展
```

Whether it's distributed systems, ML fundamentals, or the latest in WebAssembly — Auto-Explorer researches it like a tireless analyst. You come back to find 10+ structured reports waiting for you.

不論是分散式系統、機器學習基礎，還是最新的 WebAssembly — Auto-Explorer 像不知疲倦的分析師一樣研究。回來時，10 多篇結構化報告已經等著你。

### Controlled exploration with budget / 有預算控制的探索

```bash
/auto-explore --budget conservative quantum computing
/auto-explore --budget aggressive distributed consensus
```

Don't want to use too much quota? `--budget conservative` stops at 40% usage. Want Claude to go deep? `--budget aggressive` pushes to 80%. The default `moderate` uses 60%.

不想用太多額度？`--budget conservative` 在 40% 用量時停止。想讓 Claude 深入？`--budget aggressive` 推到 80%。預設 `moderate` 使用 60%。

### Capped iteration count / 限制迭代次數

```bash
/auto-explore --max-iterations 5 Go generics
```

Just want a quick overview? Cap it at 5 iterations. Claude will write a summary on the final iteration.

只想要快速總覽？限制在 5 個迭代。Claude 會在最後一輪寫出摘要。

### No topic? Let Claude choose / 沒有主題？讓 Claude 選

```bash
/auto-explore
```

Auto-Explorer reads your interest profile (`~/.claude/user-interests.md`) and picks the first suggestion. Your interests are automatically updated every session — so the suggestions stay fresh.

Auto-Explorer 會讀取你的興趣檔案，選擇第一個建議。你的興趣每次對話都會自動更新 — 建議始終保持新鮮。

---

## Build Mode Scenarios / 建置模式情境

### Build a complete feature / 建置完整功能

```bash
/auto-explore build a REST API with authentication
```

Claude won't just write the code and stop. It will:

1. **Plan**: Write an architecture document with task breakdown
2. **Build**: Implement each sub-task across iterations, testing as it goes
3. **Enhance**: Review its own work — fix edge cases, add error handling, improve tests
4. **Polish**: Evaluate UX friction, improve onboarding, optimize defaults

Auto-detected from action verbs: `build`, `implement`, `create`, `fix`, `refactor`, `deploy`, `optimize`, `migrate`... and their CJK equivalents.

Claude 不會只寫程式碼就停下。它會：規劃、建置、增強，最後打磨產品體驗。從動作動詞自動偵測：`build`、`implement`、`建立`、`優化`...

### Fix and improve existing code / 修復和改善既有程式碼

```bash
/auto-explore fix the authentication bug in the login flow
/auto-explore refactor the database layer to use connection pooling
/auto-explore improve error handling across the API
```

Give Claude a problem, and it works until it's solved — then keeps going to make the solution robust.

給 Claude 一個問題，它會工作到解決為止 — 然後繼續讓方案更穩健。

### Self-evolve a project / 自我進化一個專案

```bash
/auto-explore 請自我進化此 project
```

Point Auto-Explorer at its own codebase (or any project), and Claude will find bugs to fix, tests to add, documentation to improve, and UX friction to smooth out. It's like having a tireless junior engineer doing code review and improvements.

將 Auto-Explorer 指向它自己的程式碼庫（或任何專案），Claude 會找到 bug 修復、需要新增的測試、需要改善的文檔和 UX 摩擦。就像有一個不知疲倦的初級工程師在做 code review 和改進。

### Auto-generated completion report / 自動產生完成報告

When build mode determines there's nothing left worth improving, it automatically generates a comprehensive `summary.md` before ending:

- What was built and why
- Architecture decisions
- List of all deliverables
- Test coverage results
- Known limitations
- How to use the result

No manual export needed — the summary is always there when the session ends.

當建置模式判定沒有值得改進的項目時，會在結束前自動產生完整的 `summary.md`：包含建置內容、架構決策、交付物清單、測試覆蓋率、已知限制和使用方式。不需要手動匯出。

---

## Bilingual & CJK Support / 雙語與 CJK 支援

Auto-Explorer works equally well in English and CJK languages. Topic detection, mode detection, and polite prefix handling all support both:

```bash
/auto-explore 建立一個 REST API 認證系統
/auto-explore 請幫我修復登入流程的 bug
/auto-explore 分散式共識演算法
```

Polite prefixes like "please", "can you", "請", "幫我" are automatically stripped for accurate mode detection — so natural language works naturally.

Auto-Explorer 在英文和 CJK 語言下同樣好用。主題偵測、模式偵測和禮貌前綴處理都支援雙語。禮貌前綴如 "please"、"請"、"幫我" 會自動去除，確保自然語言自然運作。

---

## Monitoring & Control / 監控與控制

### Real-time dashboard / 即時儀表板

```bash
/explore-status
```

See the current session's progress: topic, mode, iteration count, rate limit usage with ASCII progress bars, and session history.

查看當前 session 的進度：主題、模式、迭代次數、帶 ASCII 進度條的速率限制用量，以及 session 歷史。

### Cancel anytime / 隨時取消

```bash
/cancel-explore
```

Stop the current session gracefully. All findings written so far are preserved.

優雅地停止當前 session。已寫入的所有研究成果都會保留。

### Steer mid-session / 中途轉向

```bash
/explore-steer Focus more on practical examples, less theory
/explore-steer Skip performance section, go deeper into security
/explore-steer 請專注在效能比較
```

Redirect the active session without cancelling it. The direction change takes effect on the next iteration. It's a one-time directive — if you want persistent direction, modify the topic.

在不取消的情況下重新導向活躍的 session。方向變更在下一輪迭代生效。這是一次性指令 — 如果需要持久的方向，請修改主題。

### Exploration templates / 探索模板

```bash
/auto-explore --template deep-dive Kubernetes
/auto-explore --template quickstart FastAPI
/auto-explore --template architecture-review
/auto-explore --template security-audit
```

Pre-configured exploration strategies that shape how Claude structures its research. Each template defines a multi-phase plan optimized for a specific type of exploration:

- **deep-dive**: Exhaustive research covering theory, practice, ecosystem, and edge cases
- **quickstart**: Practical focus with working code examples — get productive fast
- **architecture-review**: Structural analysis of a codebase (dependencies, patterns, risks)
- **security-audit**: Security-focused analysis (vulnerabilities, attack surface, hardening)

Templates override the default mode and instructions while still using the same rate-limiting, steering, and resume infrastructure.

預設的探索策略，定義 Claude 如何結構化研究。每個模板定義了一個多階段計劃，針對特定類型的探索進行優化：deep-dive（詳盡）、quickstart（實務重點）、architecture-review（結構分析）、security-audit（安全審計）。

### Compare mode / 比較模式

```bash
/auto-explore --compare React vs Vue vs Svelte
/auto-explore --compare PostgreSQL vs MySQL vs SQLite
/auto-explore --template comparison Kubernetes vs Docker Swarm
```

Structured side-by-side comparison with evaluation criteria, scoring matrix, and a clear verdict. Claude first defines evaluation criteria, then analyzes each option individually with evidence, creates a head-to-head comparison table, and concludes with a recommendation for different use cases.

結構化的並排比較，包含評估標準、評分矩陣和明確結論。Claude 先定義評估標準，然後逐一分析每個選項並附上證據，建立對比表格，最後根據不同使用情境給出建議。

### Export HTML report / 匯出 HTML 報告

```bash
/explore-export                     # export active or most recent session
/explore-export rust-async          # export specific session
```

Generate a single-file HTML report from any session's Markdown findings. The report includes a sidebar navigation, dark/light mode, responsive layout, and is completely self-contained — no external CSS or JavaScript needed. HTML reports are also auto-generated when sessions complete.

從任何 session 的 Markdown 研究成果產生單一檔案 HTML 報告。報告包含側邊導航欄、暗色/亮色模式、響應式排版，完全自包含 — 不需要外部 CSS 或 JavaScript。HTML 報告在 session 完成時也會自動產生。

### Interest graph & smart suggestions / 興趣圖譜與智慧推薦

Auto-Explorer builds a structured graph of your interests over time (`~/.claude/interest-graph.json`). Each concept tracks how often you've explored it, when you last touched it, and how it relates to other concepts.

Auto-Explorer 隨時間建立你的結構化興趣圖譜。每個概念追蹤你探索的頻率、最後接觸的時間，以及它與其他概念的關聯。

```bash
# See what the graph suggests
# 查看圖譜推薦
python scripts/interest_graph.py suggest 5

# Output example:
#   Docker (strong interest, score: 0.891)
#   WebAssembly (revisit — not seen in a while, score: 0.734)
#   distributed-consensus (unexplored connection, score: 0.682)
```

How it works:
- **Auto-migration**: On first run, your existing `user-interests.md` keywords (~170+) are converted into graph concepts. No manual setup.
- **Thompson Sampling**: The algorithm learns which suggestions you actually explore (alpha++) vs. ignore (beta++), and adapts over time.
- **Half-life decay**: Old interests naturally fade (90-day half-life). Topics you haven't touched in months drift down in ranking.
- **Serendipity bonus**: Under-connected concepts get a novelty boost — so you don't only see the same topics.
- **Quality signals**: Each session records how it ended (natural / budget exhausted / rate limited), output density, and iteration efficiency.

運作方式：自動遷移（首次運行自動轉換既有關鍵字）、Thompson Sampling（學習你的偏好）、半衰期衰減（90天）、意外發現加分（新穎概念加權）、品質信號（記錄每次 session 的完成方式和效率）。

### Resume a previous session / 恢復之前的 Session

```bash
/auto-explore --resume                     # resume most recent
/auto-explore --resume rust-async          # resume specific session
/auto-explore --resume rust-async --budget aggressive  # resume with different budget
```

Pick up where you left off. When a session is interrupted by rate limits, max-iterations, or cancellation, use `--resume` to continue it. Auto-Explorer reads the previous `_index.md` for full context and continues writing to the same output directory.

從上次中斷的地方繼續。當 session 因速率限制、最大迭代次數或取消而中斷時，使用 `--resume` 繼續。Auto-Explorer 讀取之前的 `_index.md` 獲取完整脈絡，並繼續寫入同一個輸出目錄。

### Rate limit safety net / 速率限制安全網

Auto-Explorer monitors three time windows (4-hour, daily, weekly) and stops before you hit your plan's usage cap. The defaults are calibrated for typical usage, and you can customize them:

```json
// ~/.claude/auto-explorer-limits.json
{
  "threshold": 0.6,
  "rate_limits": {
    "4h":     { "tokens": 700000 },
    "daily":  { "tokens": 4100000 },
    "weekly": { "tokens": 29000000 }
  }
}
```

Auto-Explorer 監控三個時間窗口（4 小時、每日、每週），在你達到方案使用上限前停止。

---

## Who Is This For? / 目標用戶

### The Curious Learner / 好奇的學習者

You love learning new technologies but don't have time to curate learning paths. Set Auto-Explorer running before bed, wake up to a structured knowledge base.

你喜歡學習新技術但沒時間策劃學習路徑。睡前啟動 Auto-Explorer，醒來收穫結構化知識庫。

### The Solo Developer / 獨立開發者

You're building a side project and want to move faster. Let Auto-Explorer handle the scaffolding, testing, and polish while you focus on the high-level decisions.

你正在做一個 side project，想更快推進。讓 Auto-Explorer 處理腳手架、測試和打磨，你專注於高層決策。

### The Power User / 進階用戶

You already use Claude Code daily and want to maximize its potential. Auto-Explorer turns idle quota into structured output — research reports, code improvements, or project evolution.

你已經每天使用 Claude Code，想最大化它的潛力。Auto-Explorer 把閒置額度轉化為結構化產出。

### The Team Lead / 團隊負責人

You want to prototype ideas quickly or generate documentation for your team. Run Auto-Explorer on a topic, review the output, and share the findings.

你想快速原型化想法或為團隊產生文檔。對一個主題執行 Auto-Explorer，審查產出，分享研究成果。

---

## Comparison with Manual Exploration / 與手動探索的比較

| Aspect | Manual Q&A | Auto-Explorer |
|--------|-----------|---------------|
| **Effort** | Ask → wait → ask → wait | One command, walk away |
| **Depth** | Depends on your questions | Systematically covers the topic |
| **Output** | Chat history (hard to review) | Structured Markdown files |
| **Continuity** | Context lost between sessions | Each iteration builds on the previous |
| **Budget** | Easy to over-spend or under-use | Automatic rate limit management |
| **Summary** | You write it yourself | Auto-generated on completion |

---

## Future Directions / 未來方向

### v1.9.0: Improvement Engine / 改進引擎

The interest graph (v1.8.0) lays the foundation. The improvement engine builds on top of it:

興趣圖譜（v1.8.0）打下基礎，改進引擎在此之上建構：

- **Template bandits / 模板推薦**: Thompson Sampling to pick the best exploration template for a given topic. "Deep-dive works better for infrastructure topics, quickstart for frameworks."
  用 Thompson Sampling 為主題挑選最佳探索模板。
- **Budget adaptation / 預算適應**: Learn the right budget (conservative/moderate/aggressive) from session history. If your sessions always hit rate limits at 3 iterations, suggest a smaller budget.
  從歷史學習合適的預算。如果每次都在 3 輪觸及限制，建議更小的預算。
- **Repeat detection / 重複偵測**: Detect when a topic has been explored before and suggest deepening instead of re-covering. Uses the interest graph's co-occurrence edges.
  偵測重複主題，建議深入而非重新覆蓋。

### v1.10.0: Advanced Graph Intelligence / 進階圖譜智慧

- **Community detection / 社群偵測**: Label propagation to find natural clusters in your interest graph. "You have a Docker-CI-GitHub cluster and a FastAPI-Pydantic-testing cluster."
  標籤傳播演算法找出興趣圖譜中的自然叢集。
- **Gap-based serendipity / 結構缺口推薦**: Find concept pairs that share neighbors but aren't directly connected. "You know Docker and you know GitHub Actions, but you've never explored Docker + GitHub Actions together."
  找出共享鄰居但未直接連接的概念對。
- **Prompt evolution / 提示詞進化**: Bandit-based selection of prompt variations that produce better outcomes. Track which system messages lead to higher output density.
  基於 bandit 的提示詞變體選擇。追蹤哪些系統訊息產生更高的輸出密度。

### Fresh Context Mode / 全新上下文模式

For long sessions that approach context window limits, Auto-Explorer will start a new Claude session with a compressed summary of all previous work — getting fresh context while preserving continuity.

對於接近上下文視窗限制的長 session，Auto-Explorer 會啟動新的 Claude session，攜帶所有先前工作的壓縮摘要 — 獲得全新上下文的同時保持連續性。

### Build Mode Auto-Verification / 建置模式自動驗證

After each build iteration, automatically run the project's test suite and use the results to guide the next iteration. Failing tests become the next sub-task.

每次建置迭代後，自動運行專案的測試套件，用結果引導下一輪迭代。失敗的測試成為下一個子任務。

### Custom Stop Conditions / 自訂停止條件

```bash
/auto-explore --done-when "all tests pass" build the feature
/auto-explore --done-when "coverage > 80%" add tests
```

Define success criteria that Auto-Explorer checks each iteration. When the condition is met, it stops — not when budget runs out.

定義 Auto-Explorer 每輪檢查的成功標準。當條件滿足時停止 — 而不是預算用完才停。

---

## Getting Started / 開始使用

```bash
# Install (one time)
cd /path/to/parent-directory
claude plugin marketplace add ./auto-explorer
claude plugin install auto-explorer

# Start Claude Code in autonomous mode
claude --dangerously-skip-permissions

# Explore!
/auto-explore Rust async programming
```

That's it. Three commands to install, one command to explore. Everything else is automatic.

就這樣。三個指令安裝，一個指令探索。其他一切都是自動的。
