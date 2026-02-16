# Auto-Explorer 架構總覽

本文件用流程圖說明 Auto-Explorer 的運作方式。如果你是第一次接觸這個專案，建議從**術語表**開始閱讀。

> 本文件中的圖表使用 [Mermaid](https://mermaid.js.org/) 語法。在 GitHub 上可以直接渲染，在 VS Code 中需安裝 Mermaid 擴充套件才能看到圖形。

---

## 術語表

以下是本文件和整個專案中會用到的術語。先讀過一遍，之後遇到不懂的詞可以回來查。

### 基礎概念

| 術語 | 說明 |
|------|------|
| **Plugin（插件）** | 一段可以「裝進」Claude Code 的擴充功能，讓 Claude Code 學會新技能。Auto-Explorer 就是一個 Plugin。 |
| **Skill（技能）** | Plugin 提供給使用者的「指令」。在 Claude Code 聊天中輸入 `/auto-explore` 就是在使用一個 Skill。每個 Skill 對應一個 `SKILL.md` 檔案，裡面寫著 Claude 該怎麼執行這個指令。 |
| **Slash Command（斜線指令）** | 以 `/` 開頭的指令，例如 `/auto-explore`、`/cancel-explore`。這是使用者跟 Plugin 互動的方式，也就是上面說的 Skill。 |
| **Hook（鉤子）** | 一段在「特定事件發生時」自動執行的程式。Auto-Explorer 使用 **Stop Hook**：每當 Claude 回應完一段話後，系統會自動執行這段程式，用來決定「要不要讓 Claude 繼續下一輪」。 |
| **State File（狀態檔）** | 位於 `.claude/auto-explorer.local.md` 的檔案。它記錄了目前探索 session 的所有資訊（主題、模式、進行到第幾輪等）。Stop Hook 每次執行時都會讀取和更新這個檔案。探索結束時會被刪除。 |
| **Session（工作階段）** | 一次完整的探索過程。從你輸入 `/auto-explore` 開始，到探索結束為止。一個 Session 可能包含多個 Iteration（輪次）。 |
| **Iteration（輪次/迭代）** | 探索的一「輪」。每一輪中 Claude 會：研究一個子主題 → 寫出報告 → 告訴 Hook 下一步要做什麼。一個 Session 通常有 5~30 輪。 |

### 資料格式

| 術語 | 說明 |
|------|------|
| **JSON** | 一種常見的資料格式，用大括號 `{}` 和中括號 `[]` 來組織資料，例如 `{"name": "Alice", "age": 25}`。本專案的設定檔和歷史紀錄都是 JSON 格式。 |
| **JSONL** | JSON Lines 的縮寫。每一行是一筆獨立的 JSON 資料。用在遙測紀錄（telemetry），方便逐行追加，不需要重寫整個檔案。 |
| **Markdown（.md）** | 一種輕量的文字格式語法。用 `#` 表示標題、`**粗體**`、`- 列表` 等。Auto-Explorer 的研究報告都用 Markdown 撰寫。 |
| **Frontmatter（前言區塊）** | Markdown 檔案開頭以 `---` 包圍的區域，用來放「關於這個檔案的資料」。例如狀態檔的 frontmatter 記錄了主題、模式、當前輪次等。像這樣：<br>`---`<br>`topic: "Rust"`<br>`iteration: 3`<br>`---` |
| **Slug（短網址標識）** | 把主題名稱轉換成適合當檔案名稱的格式。例如 `"Rust async programming"` → `"rust-async-programming"`。去掉空格、特殊字元，全部小寫。 |

### 程式語言與工具

| 術語 | 說明 |
|------|------|
| **Bash（Shell 腳本）** | 一種命令列腳本語言，常用於 Linux/macOS。Auto-Explorer 的核心邏輯（`stop-hook.sh`、`setup-auto-explorer.sh`）是用 Bash 寫的。 |
| **Node.js** | 讓 JavaScript 可以在命令列執行的環境。Auto-Explorer 用 Node.js 寫了一個小程式（`stop-hook-entry.js`）來解決 Windows 上的相容性問題。 |
| **Python** | 程式語言。Auto-Explorer 的工具程式（速率檢查、歷史管理、興趣圖譜等）都是用 Python 寫的。 |
| **Git Bash** | Windows 上安裝 Git 時附帶的 Bash 環境。Auto-Explorer 在 Windows 上透過 Git Bash 來執行 Shell 腳本。 |
| **WSL（Windows Subsystem for Linux）** | Windows 的 Linux 子系統。它也有一個 `bash.exe`，但跟 Git Bash 的路徑系統不同，Auto-Explorer 必須避開它（詳見 [Windows 相容性](#7-windows-相容性層)）。 |

### AI 與用量相關

| 術語 | 說明 |
|------|------|
| **Token（權杖）** | AI 模型處理文字的最小單位。中文大約 1~2 個字 = 1 個 token，英文大約 1 個單字 = 1~2 個 token。使用 Claude 時會消耗 token，token 用量就是你的「帳戶額度消耗量」。 |
| **Rate Limit（速率限制）** | Claude 帳戶在一段時間內可使用的 token 上限。例如每天最多用 410 萬 token。Auto-Explorer 會檢查這些限制，在接近上限時自動停止，避免把帳戶額度用光。 |
| **Threshold（閾值）** | 觸發停止的百分比門檻。例如 threshold = 0.6 表示「當任何一個時間窗口的用量達到限制的 60% 時停止」。 |
| **Budget（預算）** | 使用者設定的用量等級，對應不同的 threshold：`conservative`（40%）、`moderate`（60%，預設）、`aggressive`（80%）。 |

### 興趣圖譜相關

| 術語 | 說明 |
|------|------|
| **Interest Graph（興趣圖譜）** | 一種用「節點」和「連線」表示你興趣的資料結構。每個節點是一個概念（如 "Docker"），連線表示兩個概念之間的關係（如 "Docker" 和 "Kubernetes" 是相關的）。存在 `~/.claude/interest-graph.json`。 |
| **Concept（概念）** | 興趣圖譜中的一個節點。例如 "Python"、"Docker"、"Rust" 都是概念。每個概念有權重（你有多關心它）、類別、最後看到的日期等。 |
| **Co-occurrence（共現）** | 兩個概念在同一次探索 session 中同時出現。例如你在同一次探索中研究了 "Docker" 和 "CI/CD"，這兩者就有了一條共現連線。共現越多，表示這兩個概念越常一起被研究。 |
| **Decay（衰減）** | 概念的權重會隨時間降低。90 天半衰期的意思是：一個概念如果你 90 天沒碰它，權重會降為原來的一半。這讓最近的興趣比較重要，很久以前的興趣會漸漸淡出。 |
| **Thompson Sampling（湯普森取樣）** | 一種用來決定「推薦哪些主題」的演算法。它會兼顧兩件事：(1) 推薦你以前喜歡的主題、(2) 偶爾推薦你沒試過的主題。使用越多次，推薦就越準確。 |
| **Community Detection（社群偵測）** | 在圖譜中找出「彼此緊密連結的概念群」。例如 {Docker, Kubernetes, CI/CD} 可能形成一個社群，{Python, Flask, API} 形成另一個社群。 |
| **Structural Gap（結構缺口）** | 兩個概念群之間缺少連線的地方。例如你研究了 "Docker" 和 "Python"，但從沒同時研究過它們的交集 — 這就是一個缺口，也是一個潛在的有趣方向。 |

### 其他

| 術語 | 說明 |
|------|------|
| **Telemetry（遙測）** | 每輪探索結束時自動記錄的資料（輪次、耗時、token 數等）。寫在 `.session-outcomes.jsonl` 裡，用來分析歷史表現。 |
| **Template（模板）** | 預先寫好的探索「說明書」。例如 `deep-dive.md` 模板會引導 Claude 深入研究一個主題。使用者可以選擇不同模板來控制探索的風格。 |
| **HTML Export（HTML 匯出）** | 把 Markdown 報告轉換成一個可以在瀏覽器打開的漂亮 HTML 網頁，方便分享給別人。 |
| **UTF-8** | 一種文字編碼方式，能正確顯示中文、日文、韓文等各國文字。Windows 預設不是 UTF-8（繁體中文 Windows 預設是 Big5/CP950），所以需要特別設定。 |
| **Unit Separator（`\x1f`）** | ASCII 控制字元之一，用來分隔資料欄位。Auto-Explorer 用它取代 Tab（`\t`）來在 Python 和 Bash 之間傳遞資料，避免 Bash 的特殊行為導致資料錯位（詳見 `developer_guide.md`）。 |

---

## 1. 元件總覽

這張圖展示 Auto-Explorer 的所有檔案，以及它們之間的關係。

**怎麼看這張圖**：方框是檔案或元件，箭頭表示「誰呼叫或依賴誰」。顏色標示了不同角色：橘色 = 核心 Shell 腳本，藍色 = Python 工具，黃色 = 執行時狀態檔。

```mermaid
graph TB
    subgraph "Claude Code Plugin 系統"
        PC["plugin.json<br/>（插件註冊檔）"] --> SK[Skills]
        PC --> HK[Hooks]
    end

    subgraph SK["斜線指令（Skills）"]
        S1["/auto-explore<br/>開始探索"]
        S2["/cancel-explore<br/>取消探索"]
        S3["/explore-status<br/>查看儀表板"]
        S4["/explore-help<br/>查看說明"]
        S5["/explore-steer<br/>調整方向"]
        S6["/explore-export<br/>匯出報告"]
    end

    subgraph HK["Stop Hook 鏈"]
        HJ["hooks.json<br/>（定義何時觸發哪支程式）"] --> ENTRY["stop-hook-entry.js<br/>（Node.js 入口，處理 Windows 相容）"]
        ENTRY --> SH["stop-hook.sh<br/>（核心決策引擎）"]
    end

    subgraph PY["Python 工具程式"]
        HP["helpers.py<br/>（共用工具：解析、Slug 生成等）"]
        CRL["check-rate-limits.py<br/>（檢查是否快超出用量限制）"]
        HIS["history.py<br/>（管理探索歷史紀錄）"]
        IG["interest_graph.py<br/>（興趣圖譜與主題推薦）"]
        IE["improvement_engine.py<br/>（根據歷史自動建議模板和預算）"]
        EXP["export-html.py<br/>（將報告轉成 HTML 網頁）"]
    end

    subgraph DATA["資料檔案"]
        STATE[".claude/auto-explorer.local.md<br/>（執行時狀態：目前探索的所有資訊）"]
        HIST["auto-explore-findings/.history.json<br/>（所有 session 的歷史紀錄）"]
        GRAPH["~/.claude/interest-graph.json<br/>（你的興趣圖譜）"]
        LIMITS["~/.claude/auto-explorer-limits.json<br/>（用量限制設定）"]
        STATS["~/.claude/stats-cache.json<br/>（Claude Code 的使用統計）"]
    end

    subgraph TPL["模板"]
        T1["deep-dive.md<br/>（深度研究）"]
        T2["quickstart.md<br/>（快速入門）"]
        T3["architecture-review.md<br/>（架構評審）"]
        T4["security-audit.md<br/>（安全審查）"]
        T5["comparison.md<br/>（比較分析）"]
        T6["dual-lens.md<br/>（雙透鏡：結合興趣圖譜）"]
    end

    S1 --> |"執行"| SETUP["setup-auto-explorer.sh<br/>（初始化腳本）"]
    SETUP --> STATE
    SETUP --> HIS
    SETUP --> IE
    SETUP --> HP

    SH --> HP
    SH --> CRL
    SH --> HIS
    SH --> IG
    SH --> EXP

    CRL --> LIMITS
    CRL --> STATS
    HIS --> HIST
    IG --> GRAPH

    S3 --> HIS
    S6 --> EXP

    SETUP -.-> TPL

    style STATE fill:#ff9,stroke:#333
    style SH fill:#f96,stroke:#333
    style SETUP fill:#f96,stroke:#333
    style HP fill:#69f,stroke:#333
```

**重點摘要**：
- **使用者透過斜線指令與 Auto-Explorer 互動**（左上角），例如 `/auto-explore` 開始、`/cancel-explore` 取消。
- **`setup-auto-explorer.sh`** 是啟動入口（橘色），負責解析參數、建立狀態檔、初始化一切。
- **`stop-hook.sh`** 是核心引擎（橘色），每當 Claude 回應完畢時自動執行，負責決定要不要繼續下一輪。
- **Python 工具程式**（藍色）各司其職，被 Shell 腳本呼叫。
- **資料檔案**分為兩類：專案內的（狀態檔、歷史檔）和全域的（興趣圖譜、用量設定，放在 `~/.claude/` 使用者目錄下）。

---

## 2. 探索迴圈的生命週期

這是 Auto-Explorer 最核心的機制。整個流程可以用一句話概括：

> **Claude 回應 → Stop Hook 決定要不要繼續 → 如果繼續，就餵入下一個問題讓 Claude 繼續回答 → 重複。**

以下是完整流程圖。菱形 `{}` 是「判斷點」（是/否的岔路），方框是「動作」，圓角框是「起點/終點」。

```mermaid
flowchart TD
    START(["/auto-explore 主題名稱"]) --> SETUP["setup-auto-explorer.sh<br/>解析參數、偵測模式、建立狀態檔"]
    SETUP --> |"建立 .claude/auto-explorer.local.md"| FIRST["Claude 開始第一輪<br/>（讀取狀態檔中的提示詞）"]

    FIRST --> RESPOND["Claude 產生回應<br/>回應末尾帶有特殊標籤"]
    RESPOND --> HOOK{"Stop Hook<br/>自動觸發"}

    HOOK --> CHK_STATE{"狀態檔<br/>存在嗎？"}
    CHK_STATE --> |"不存在"| ALLOW_EXIT["允許 Claude 停止<br/>（不是探索 session）"]
    CHK_STATE --> |"存在"| PARSE["解析 frontmatter<br/>（讀取目前的輪次、閾值、主題等）"]

    PARSE --> CHK_SUMMARY{"正在等待<br/>產生摘要？"}
    CHK_SUMMARY --> |"是"| FINALIZE["結束 session<br/>+ 匯出 HTML 報告<br/>+ 刪除狀態檔"]
    FINALIZE --> DONE([探索完成])

    CHK_SUMMARY --> |"否"| CHK_MAX{"已達到<br/>最大輪次？"}
    CHK_MAX --> |"是"| END_MAX["結束 session<br/>原因：達到輪次上限"]
    END_MAX --> DONE

    CHK_MAX --> |"否"| CHK_RATE{"用量是否<br/>超過限制？"}
    CHK_RATE --> |"是"| END_RATE["結束 session<br/>原因：接近用量限制"]
    END_RATE --> DONE

    CHK_RATE --> |"否"| EXTRACT["從 Claude 的回應中<br/>提取特殊標籤"]
    EXTRACT --> CHK_DONE{"找到<br/>explore-done<br/>標籤？"}

    CHK_DONE --> |"是"| INJECT_SUMMARY["設定「等待摘要」旗標<br/>注入提示詞：請寫一份完整摘要<br/>（再多跑一輪來產生 summary.md）"]
    INJECT_SUMMARY --> SUMMARY_ITER["Claude 撰寫 summary.md"]
    SUMMARY_ITER --> HOOK

    CHK_DONE --> |"否"| CHK_STEER{"使用者有<br/>新指示嗎？"}
    CHK_STEER --> |"有（steer 檔案存在）"| READ_STEER["讀取使用者指示<br/>加入下一輪的提示詞"]
    CHK_STEER --> |"沒有"| BUILD_PROMPT["用 explore-next 標籤的內容<br/>組成下一輪的提示詞"]
    READ_STEER --> BUILD_PROMPT

    BUILD_PROMPT --> INCREMENT["更新狀態檔<br/>輪次 +1"]
    INCREMENT --> TELEMETRY["記錄遙測資料<br/>（寫入 JSONL 檔案）"]
    TELEMETRY --> BLOCK_STOP["輸出 JSON 給 Claude Code：<br/>阻止停止 + 注入新提示詞"]
    BLOCK_STOP --> NEXT_ITER["Claude 開始下一輪"]
    NEXT_ITER --> RESPOND

    style HOOK fill:#f96,stroke:#333
    style DONE fill:#6c6,stroke:#333
    style BLOCK_STOP fill:#69f,stroke:#333
```

**關鍵概念 — 兩個特殊標籤**：

Claude 每次回應結束時，會在結尾加上一個特殊標籤，告訴 Stop Hook 接下來要做什麼：

| 標籤 | 含義 | Stop Hook 的反應 |
|------|------|-----------------|
| `<explore-next>下一個子主題</explore-next>` | 「我這輪做完了，下一輪請讓我研究這個」 | 阻止 Claude 停止，把標籤裡的內容當作下一輪的提示詞 |
| `<explore-done>原因</explore-done>` | 「整個任務完成了」 | 先注入一輪讓 Claude 寫摘要，然後結束 session |

---

## 3. Stop Hook 決策樹（簡化版）

上面的流程圖比較複雜，這裡是精簡版，只展示 Stop Hook 的 5 種結果：

```mermaid
flowchart LR
    IN(["Stop Hook 被觸發"]) --> A{"狀態檔存在嗎？"}
    A -->|"不存在"| EXIT0["直接放行<br/>（不是探索 session）"]
    A -->|"存在"| B{"正在等待摘要？"}

    B -->|"是"| EXIT_DONE["Session 完成<br/>匯出 HTML 報告"]
    B -->|"否"| C{"達到最大輪次？"}

    C -->|"是"| EXIT_MAX["輪次到達上限，停止"]
    C -->|"否"| D{"用量超過限制？"}

    D -->|"是"| EXIT_RATE["接近用量限制，停止"]
    D -->|"否"| E{"找到 explore-done？"}

    E -->|"是"| INJECT["注入「請寫摘要」的提示詞<br/>（最後再跑一輪）"]
    E -->|"否"| CONTINUE["繼續下一輪<br/>阻止停止 + 注入新提示詞"]

    style EXIT0 fill:#ddd,stroke:#333
    style EXIT_DONE fill:#6c6,stroke:#333
    style EXIT_MAX fill:#fc6,stroke:#333
    style EXIT_RATE fill:#fc6,stroke:#333
    style INJECT fill:#69f,stroke:#333
    style CONTINUE fill:#69f,stroke:#333
```

**5 種結果一覽**：

| 結果 | 何時發生 | 意思 |
|------|---------|------|
| 灰色：直接放行 | 狀態檔不存在 | 這不是探索 session，不干涉 |
| 綠色：Session 完成 | 摘要已寫完 | 正常結束，匯出報告 |
| 黃色：輪次上限 | 超過 `--max-iterations` | 強制停止 |
| 黃色：用量限制 | 接近帳戶額度上限 | 安全停止，保護帳戶額度 |
| 藍色：繼續 / 注入摘要 | 還有工作要做 | 繼續探索下一輪 |

---

## 4. 啟動流程

使用者輸入 `/auto-explore` 後，背後發生了什麼事？

```mermaid
flowchart TD
    CMD(["/auto-explore [主題] [選項]"]) --> PARSE_ARGS["解析選項<br/>--budget, --mode, --template,<br/>--resume, --max-iterations, --compare"]

    PARSE_ARGS --> CHK_RESUME{"有 --resume 嗎？"}
    CHK_RESUME --> |"有"| RESUME_FLOW
    CHK_RESUME --> |"沒有"| CHK_TOPIC{"有提供主題嗎？"}

    subgraph RESUME_FLOW["恢復之前的 Session"]
        RF1["從歷史紀錄中找到<br/>上次的 session 資料"] --> RF2["讀取 _index.md<br/>取得之前的進度"]
        RF2 --> RF3["建立狀態檔<br/>帶入之前的上下文"]
    end

    CHK_TOPIC --> |"沒有"| SUGGEST["從興趣圖譜中<br/>推薦一個主題"]
    SUGGEST --> |"找到推薦"| USE_TOPIC["使用該主題"]
    SUGGEST --> |"沒有資料"| ERROR(["錯誤：沒有主題"])
    CHK_TOPIC --> |"有"| USE_TOPIC

    USE_TOPIC --> LIMITS{"用量限制<br/>設定檔存在嗎？"}
    LIMITS --> |"不存在"| CREATE_LIMITS["建立預設的<br/>用量限制設定檔"]
    LIMITS --> |"存在"| VALIDATE["驗證設定檔格式正確"]
    CREATE_LIMITS --> VALIDATE

    VALIDATE --> CHK_CONFLICT{"有其他迴圈<br/>正在運行嗎？"}
    CHK_CONFLICT --> |"有"| ERROR2(["錯誤：衝突"])
    CHK_CONFLICT --> |"沒有"| CHK_EXISTING{"已有探索<br/>session 嗎？"}

    CHK_EXISTING --> |"有，但超過 24 小時"| CLEANUP["自動清理過期 session"]
    CHK_EXISTING --> |"有，還很新"| ERROR3(["錯誤：已有進行中的 session"])
    CHK_EXISTING --> |"沒有"| DETECT["產生 Slug<br/>+ 自動偵測模式"]
    CLEANUP --> DETECT

    DETECT --> IMPROVE["改進引擎建議<br/>適合的模板和預算"]
    IMPROVE --> CHK_TPL{"有指定模板嗎？"}

    CHK_TPL --> |"有"| LOAD_TPL["載入模板<br/>替換佔位符"]
    CHK_TPL --> |"沒有"| DEFAULT_BODY["使用預設內容<br/>（依模式而異）"]
    LOAD_TPL --> WRITE_STATE
    DEFAULT_BODY --> WRITE_STATE

    WRITE_STATE["寫入狀態檔<br/>+ 新增歷史紀錄<br/>+ 建立輸出目錄"]
    WRITE_STATE --> READY(["Session 啟動完成<br/>Claude 讀取狀態檔開始工作"])

    RESUME_FLOW --> READY

    style READY fill:#6c6,stroke:#333
    style CMD fill:#69f,stroke:#333
```

**重點**：
- 如果沒提供主題，Auto-Explorer 會從你的興趣圖譜中用 Thompson Sampling 推薦一個。
- 啟動前會做多項安全檢查：有沒有衝突的 session、用量設定是否正確等。
- 超過 24 小時的舊 session 會被自動清理（可能是上次異常結束的殘留）。

---

## 5. 資料流向

這張圖展示各元件之間「資料怎麼流動」。箭頭上的文字說明了操作類型（讀取、寫入、呼叫等）。

```mermaid
flowchart LR
    subgraph "使用者輸入"
        TOPIC["主題 + 選項"]
    end

    subgraph "啟動階段"
        SETUP["setup-auto-explorer.sh"]
    end

    subgraph "執行時狀態（探索進行中才存在）"
        SF[".claude/auto-explorer.local.md<br/>（狀態檔）"]
        STEER[".claude/auto-explorer-steer.md<br/>（使用者的方向調整指示）"]
        SUMFLAG[".claude/auto-explorer-summary-pending<br/>（「等待摘要」旗標檔）"]
    end

    subgraph "Stop Hook"
        SH["stop-hook.sh"]
    end

    subgraph "Python 工具"
        HP["helpers.py"]
        CRL["check-rate-limits.py"]
        HIST["history.py"]
        IG["interest_graph.py"]
        IE["improvement_engine.py"]
        EXP["export-html.py"]
    end

    subgraph "持久化儲存（長期保存）"
        LIMITS["auto-explorer-limits.json"]
        STATS["stats-cache.json"]
        IGRAPH["interest-graph.json"]
        HFILE[".history.json"]
    end

    subgraph "輸出成果"
        FINDINGS["auto-explore-findings/主題名/"]
        HTML["report.html"]
        JSONL[".session-outcomes.jsonl"]
    end

    TOPIC --> SETUP
    SETUP -->|"寫入"| SF
    SETUP -->|"新增紀錄"| HIST
    HIST -->|"讀寫"| HFILE

    SH -->|"讀取"| SF
    SH -->|"讀取後刪除"| STEER
    SH -->|"讀寫刪"| SUMFLAG
    SH -->|"呼叫"| HP
    SH -->|"呼叫"| CRL
    SH -->|"呼叫"| HIST
    SH -->|"呼叫"| IG
    SH -->|"呼叫"| EXP

    CRL -->|"讀取"| LIMITS
    CRL -->|"讀取"| STATS
    CRL -->|"讀取"| SF

    IG -->|"讀寫"| IGRAPH
    IE -->|"讀取"| HFILE

    HP -->|"追加寫入"| JSONL
    EXP -->|"讀取 MD 寫入"| HTML
    EXP -->|"讀取"| FINDINGS

    SH -->|"更新"| SF
    SH -.->|"Session 結束時刪除"| SF
```

**兩類資料的差別**：
- **執行時狀態**（中間的框）：只在探索進行中才存在。Session 結束後，狀態檔和旗標檔都會被刪除。
- **持久化儲存**（右下的框）：永久保存。歷史紀錄、興趣圖譜、用量設定都會保留到下次使用。

---

## 6. Build 模式的三個階段

Build 模式（建置模式）把一個開發任務分成三個遞進的階段。Claude 會自己判斷什麼時候從一個階段進入下一個。

```mermaid
stateDiagram-v2
    [*] --> 階段一: Session 開始

    state 階段一 {
        [*] --> 規劃: 第 1 輪
        規劃 --> 實作: 寫好 00-plan.md
        實作 --> 實作: 每輪完成一個子任務
        實作 --> [*]: 核心任務完成
    }

    階段一 --> 階段二: Claude 認為核心功能已完成

    state 階段二 {
        [*] --> 評估: 檢視程式碼
        評估 --> 修復: Bug 修復、邊界情況
        修復 --> 強化: 錯誤處理、效能
        強化 --> 測試: 補充測試
        測試 --> 評估: 還有值得改進的地方？
        評估 --> [*]: 沒有了
    }

    階段二 --> 階段三: 工程品質已夠好

    state 階段三 {
        [*] --> 使用體驗: 使用者體驗有摩擦嗎？
        使用體驗 --> 預設值: 更好的預設值
        預設值 --> 回饋: 更清楚的回饋訊息
        回饋 --> 打磨: 細節打磨
        打磨 --> [*]: 沒有值得加的了
    }

    階段三 --> 摘要: Claude 發出 explore-done
    摘要 --> [*]: 產生 summary.md + HTML 報告

    note right of 階段一: 核心實作\n完成使用者要求的任務
    note right of 階段二: 工程強化\n修 Bug、提升穩健性、補測試
    note right of 階段三: 產品打磨\n使用體驗、入門體驗、細節
```

**簡單比喻**：
- **階段一**：蓋房子（完成使用者要求的功能）
- **階段二**：驗收（檢查門窗有沒有裝好、水管有沒有漏水）
- **階段三**：裝潢（讓住起來更舒適）

---

## 7. Windows 相容性層

Auto-Explorer 的腳本是用 Bash 寫的，但在 Windows 上執行 Bash 有三個問題。`stop-hook-entry.js` 這個 Node.js 小程式負責在執行 Bash 之前解決它們。

> 如果你只在 macOS 或 Linux 上使用，這個部分可以跳過。

```mermaid
flowchart TD
    CC["Claude Code<br/>（每次回應完畢觸發 Stop Hook）"] --> HJ["hooks.json<br/>指定執行：node stop-hook-entry.js"]

    HJ --> ENTRY["stop-hook-entry.js"]

    ENTRY --> IS_WIN{"作業系統<br/>是 Windows 嗎？"}

    IS_WIN --> |"不是（macOS/Linux）"| DIRECT["直接執行 bash stop-hook.sh"]

    IS_WIN --> |"是（Windows）"| FIX1["問題 1：找到正確的 Bash<br/>Windows 有兩個 bash：<br/>Git Bash（能用）vs WSL bash（不能用）<br/>→ 明確找到 Git Bash 的路徑"]
    FIX1 --> FIX2["問題 2：確保工具指令可用<br/>cat、grep、sed 等工具在 Git 的子目錄中<br/>→ 把這些路徑加入 PATH"]
    FIX2 --> FIX3["問題 3：解決中文亂碼<br/>Windows 預設用 Big5 編碼<br/>→ 強制所有程式使用 UTF-8"]
    FIX3 --> EXEC["用正確的 Git Bash<br/>執行 stop-hook.sh"]

    DIRECT --> SH["stop-hook.sh<br/>（核心決策引擎）"]
    EXEC --> SH

    SH --> PY["Python 工具程式"]

    style FIX1 fill:#fc6,stroke:#333
    style FIX2 fill:#fc6,stroke:#333
    style FIX3 fill:#fc6,stroke:#333
```

**三個問題的摘要**：

| # | 問題 | 症狀 | 解法 |
|---|------|------|------|
| 1 | Git Bash vs WSL Bash 路徑衝突 | `No such file or directory` | 明確找到 Git Bash 的完整路徑，不依賴系統 PATH |
| 2 | 工具指令找不到 | `cat: command not found` | 把 Git 安裝目錄下的工具路徑加入 PATH |
| 3 | 中文變成亂碼 | `½Ч¹¦¨` | 設定環境變數強制使用 UTF-8 編碼 |

> 詳細的技術說明請參閱 `developer_guide.md`。

---

## 8. 興趣圖譜與主題推薦流程

Auto-Explorer 會記住你過去探索了什麼，並用這些資料來推薦新主題。這個系統叫做「興趣圖譜」。

```mermaid
flowchart TD
    subgraph "資料來源"
        MD["user-interests.md<br/>（舊格式的興趣清單）"]
        SESSIONS["每次探索結束時<br/>提取的關鍵字"]
    end

    subgraph "興趣圖譜引擎"
        MIGRATE["migrate_from_markdown()<br/>把舊格式轉成新格式<br/>（只在第一次執行）"] --> GRAPH["interest-graph.json<br/>（你的興趣圖譜）"]
        ADD["add_concepts()<br/>新增概念到圖譜"] --> GRAPH
        COOC["record_cooccurrences()<br/>記錄哪些概念常一起出現"] --> GRAPH
        DECAY["apply_decay()<br/>讓舊的興趣漸漸淡出<br/>（90 天權重減半）"] --> GRAPH
    end

    subgraph "分析功能"
        GRAPH --> TS["suggest_topics()<br/>用 Thompson Sampling 推薦主題<br/>（兼顧你的喜好和新鮮感）"]
        GRAPH --> COMM["detect_communities()<br/>找出緊密相關的概念群<br/>（例如：Docker + K8s + CI/CD）"]
        GRAPH --> GAPS["find_gaps()<br/>找出你還沒探索過的交叉領域<br/>（例如：Python × Docker）"]
        GRAPH --> BRIEF["generate_brief()<br/>產生圖譜摘要<br/>（注入到模板中給 Claude 參考）"]
    end

    subgraph "使用場景"
        TS --> SETUP["setup-auto-explorer.sh<br/>（自動推薦主題給使用者）"]
        TS --> GENMD["generate_markdown()<br/>（更新 user-interests.md）"]
        COMM --> BRIEF
        GAPS --> BRIEF
        BRIEF --> DUALLENS["dual-lens 模板<br/>（讓 Claude 看到你的興趣全貌）"]
    end

    MD --> |"第一次執行時自動轉換"| MIGRATE
    SESSIONS --> ADD
    SESSIONS --> COOC

    style GRAPH fill:#ff9,stroke:#333
    style TS fill:#69f,stroke:#333
```

**運作方式簡述**：
1. **資料收集**：每次探索結束後，Stop Hook 自動把這次用到的關鍵字加入圖譜。
2. **關係建立**：同一次探索中出現的關鍵字會建立「共現」連線。
3. **時間衰減**：90 天沒碰的概念權重減半，讓圖譜反映你「現在」的興趣。
4. **智慧推薦**：Thompson Sampling 不只推薦你最常用的主題（那樣會很無聊），也會偶爾推薦你沒試過的主題（帶來驚喜）。
5. **缺口分析**：找出你的知識盲區 — 兩個你分別熟悉但從沒交叉研究的領域。

---

## 9. 用量限制架構

Auto-Explorer 會自動檢查你的 Claude 帳戶用量，在接近上限時停止探索，避免把額度用光。

它同時檢查三個時間窗口，任何一個超標就停止：

```mermaid
flowchart LR
    subgraph "資料來源"
        TRANSCRIPT["Session 對話紀錄<br/>（記錄這次用了多少 token）"]
        STATSCACHE["~/.claude/stats-cache.json<br/>（Claude Code 記錄的每日用量）"]
        CONFIG["auto-explorer-limits.json<br/>（你的用量上限設定）"]
    end

    subgraph "check-rate-limits.py 的檢查邏輯"
        direction TB
        S4H["4 小時窗口<br/>這次 session 用了多少？"]
        SDAILY["每日窗口<br/>今天總共用了多少？"]
        SWEEKLY["每週窗口<br/>這 7 天總共用了多少？"]

        S4H --> COMPARE
        SDAILY --> COMPARE
        SWEEKLY --> COMPARE

        COMPARE{"任何一個窗口<br/>超過閾值？"}
    end

    TRANSCRIPT --> |"這次的 token 數"| S4H
    TRANSCRIPT --> |"這次的 token 數"| SDAILY
    TRANSCRIPT --> |"這次的 token 數"| SWEEKLY
    STATSCACHE --> |"每日 token 統計"| SDAILY
    STATSCACHE --> |"每日 token 統計"| SWEEKLY
    CONFIG --> |"閾值 + 上限數值"| COMPARE

    COMPARE --> |"都沒超過"| CONTINUE["繼續探索"]
    COMPARE --> |"有超過"| STOP["停止探索"]

    style STOP fill:#f66,stroke:#333
    style CONTINUE fill:#6c6,stroke:#333
```

**三個時間窗口**：

| 窗口 | 檢查什麼 | 預設上限（100%） | 預設停止線（60%） |
|------|---------|-----------------|-----------------|
| **4 小時** | 這次 session 的 token 用量 | 70 萬 | 42 萬 |
| **每日** | 今天所有 session 的 token 用量 | 410 萬 | 246 萬 |
| **每週** | 過去 7 天的 token 用量 | 2,900 萬 | 1,740 萬 |

**為什麼需要三個窗口？** 只看 4 小時的話，可能一天跑很多次就超出每日限制。只看每日的話，可能一次跑太久就超出 4 小時限制。三個窗口互相補充，確保安全。

> 這些數值可以在 `~/.claude/auto-explorer-limits.json` 中自行調整。詳見 `README.md` 的 Rate Limits 段落。
