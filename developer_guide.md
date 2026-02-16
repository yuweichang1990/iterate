# Developer Guide

## Stop Hook — Windows 相容性

### 問題背景

在 Windows 上使用 Claude Code Plugin 的 Stop Hook 時，bash shell script 會因為環境差異而無法正常執行。此問題涉及三個層次的故障。

---

### 問題 1：WSL bash 與 Git Bash 路徑衝突

**現象**

```
Stop hook error: bash: C:/Users/.../hooks/stop-hook.sh: No such file or directory
```

檔案確實存在，但 bash 報告找不到。

**根因**

Windows 系統上存在多個 `bash.exe`：

| 路徑 | 來源 | 說明 |
|------|------|------|
| `C:\Program Files\Git\usr\bin\bash.exe` | Git for Windows | MSYS2 bash，能存取 `C:/` 路徑 |
| `C:\Windows\System32\bash.exe` | WSL | Linux 子系統，僅能存取 `/mnt/c/` 路徑 |

當 Claude Code 執行 hook command 時，PATH 解析可能優先找到 WSL bash。WSL bash 無法識別 Windows 原生路徑格式（`C:/Users/...`），因此回報 `No such file or directory`。

**原始 hooks.json（有問題的寫法）**

```json
{
  "command": "bash -c 'exec bash \"${0//\\\\/\\/}/hooks/stop-hook.sh\"' '${CLAUDE_PLUGIN_ROOT}'"
}
```

此寫法的問題：
1. `bash -c` 呼叫的 `bash` 可能是 WSL bash
2. 內層 `exec bash` 再次解析 PATH，同樣可能找到 WSL bash
3. `cmd.exe` 與 `bash` 的引號處理規則不同，複雜的 single/double quote 嵌套在 Windows 上容易出錯

---

### 問題 2：MSYS 工具不在 PATH 中

**現象**

```
stop-hook.sh: line 11: cat: command not found
```

路徑問題修復後，腳本能被找到並執行，但腳本中使用的 `cat`、`grep`、`sed` 等指令全部找不到。

**根因**

Claude Code 執行 hook 時可能清理或限縮 PATH 環境變數，導致 MSYS/Git 工具目錄（`Git\usr\bin`、`Git\mingw64\bin`）不在 PATH 中。即使使用正確的 Git Bash，缺少這些路徑就無法使用 Unix 基礎工具。

---

### 問題 3：CJK 字元亂碼（CP950 / Big5 編碼衝突）

**現象**

Stop hook 輸出中的中文變成亂碼：

```
½Ч¹¦¨ change-event-hub ªº³]­p
```

原文應為「完成 change-event-hub 的設計」。

**根因**

Windows 繁體中文系統預設的 console code page 是 950（Big5）。當 bash/python 子程序輸出 UTF-8 位元組時，被系統以 CP950 解讀，造成 mojibake。

```cmd
chcp
> 使用中的字碼頁: 950
```

**修復**

在 entry script 中設定 UTF-8 環境變數，強制所有子程序使用 UTF-8：

```javascript
env.LANG = "C.UTF-8";
env.LC_ALL = "C.UTF-8";
env.PYTHONIOENCODING = "utf-8";
```

- `LANG` / `LC_ALL`：影響 bash 和 MSYS 工具的字元編碼
- `PYTHONIOENCODING`：影響 Python 的 stdin/stdout 編碼（stop-hook.sh 中多次呼叫 python）

---

### 解決方案：Node.js Entry Point 模式

使用 Node.js 作為跨平台入口點，在呼叫 bash 前解決路徑和環境問題。

**hooks.json**

```json
{
  "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-hook-entry.js\" \"${CLAUDE_PLUGIN_ROOT}\""
}
```

**stop-hook-entry.js**（見 `hooks/stop-hook-entry.js`）

核心邏輯：

```javascript
// 1. 反斜線轉正斜線
const pluginRoot = (process.argv[2] || "").replace(/\\/g, "/");

// 2. 明確找到 Git Bash（避免 WSL bash）
function findGitBash() {
  const candidates = [
    path.join(process.env.PROGRAMFILES, "Git", "usr", "bin", "bash.exe"),
    path.join(process.env.PROGRAMFILES, "Git", "bin", "bash.exe"),
    // ...
  ];
  // ...
}

// 3. 確保 MSYS 工具在 PATH 中
const msysPaths = [
  path.join(gitDir, "usr", "bin"),    // cat, grep, sed, awk
  path.join(gitDir, "mingw64", "bin"), // git, etc.
];

// 4. 強制 UTF-8 編碼（避免 CJK 亂碼）
env.LANG = "C.UTF-8";
env.LC_ALL = "C.UTF-8";
env.PYTHONIOENCODING = "utf-8";

// 5. 以 --login 啟動，確保 bash profile 被載入
execFileSync(bashPath, ["--login", scriptPath], { stdio: "inherit", env });
```

---

### 設計考量

| 面向 | 說明 |
|------|------|
| **為何用 Node.js** | `node` 在 Claude Code 環境中一定存在；原生處理 Windows 路徑；`execFileSync` 不經過 `cmd.exe`，避免引號問題 |
| **為何用 `execFileSync`** | 直接呼叫可執行檔，不經過 shell 層，避免 `cmd.exe` 的引號解析問題 |
| **為何注入 PATH** | Claude Code 可能在 hook 執行環境中清理 PATH，需手動確保 MSYS 工具可用 |
| **為何強制 UTF-8** | Windows 預設 CP950/Big5，bash/python 輸出的 UTF-8 中文會被誤讀成亂碼 |
| **為何用 `--login`** | 讓 bash 載入 profile，初始化完整的 MSYS 環境 |
| **跨平台相容** | 非 Windows 時直接使用 `bash`，不做任何路徑轉換 |

---

### 診斷技巧

**查看 debug log**

```bash
ls -lt ~/.claude/debug/ | head -5
grep -E "hook.*error|stop-hook|No such file|command not found" ~/.claude/debug/<session-id>.txt
```

**確認系統上的 bash 版本**

```bash
where bash    # Windows cmd
which -a bash # Git Bash
```

如果 `C:\Windows\System32\bash.exe`（WSL）排在 Git Bash 前面，hook 就會出問題。

**模擬 Claude Code 的 hook 執行環境**

```cmd
@echo off
REM 模擬 Claude Code 的精簡 PATH
set "PATH=C:\Windows\system32;C:\Program Files\nodejs"
echo {"transcript_path":""} | node "<plugin-root>\hooks\stop-hook-entry.js" "<plugin-root>"
echo EXIT_CODE:%errorlevel%
```

---

### 注意事項

- Plugin cache（`~/.claude/plugins/cache/`）中的檔案會在 plugin 更新時被覆蓋，修復需同步到源碼 repo
- 修改 hooks.json 後需要**重啟 Claude Code** 才會生效（hooks 在啟動時載入）
- Windows 環境下的 PATH 有 `PATH` 和 `Path` 兩種大小寫，Node.js 中需同時處理

---

### 問題 4：Bash `IFS` + `read` 的 whitespace 陷阱（Tab 分隔符 Bug）

**現象**

Stop hook 在第一次 iteration 後就結束 session，將 `<explore-next>` 的內容誤判為 `<explore-done>`。

例如 Claude 輸出 `<explore-next>Add per-node timing</explore-next>` 後，hook 報告：

```
Auto-Explorer: Task completed!
   Reason: Add per-node timing
```

**根因**

Python 輸出使用 tab (`\t`) 作為分隔符：

```python
# done 為空字串, next_t 為 "Add per-node timing"
print(done + '\t' + next_t)   # 輸出: "\tAdd per-node timing"
```

Bash 使用 `IFS=$'\t' read -r` 接收：

```bash
IFS=$'\t' read -r EXPLORE_DONE NEXT_SUBTOPIC <<< "$TAGS"
```

**問題在於 Bash `read` 對 whitespace 類 IFS 的特殊處理**：當 IFS 是空白字元（space、tab、newline）時，`read` 會自動 **strip 開頭和結尾的 IFS 字元**。這導致：

| 輸入 | IFS | 預期結果 | 實際結果 |
|------|-----|----------|----------|
| `\tworld` | `$'\t'` (tab) | A=`""`, B=`"world"` | A=`"world"`, B=`""` |
| `\|world` | `\|` (pipe) | A=`""`, B=`"world"` | A=`""`, B=`"world"` |

Tab 是 whitespace → 開頭 tab 被 strip → `"world"` 成為第一個 field → 指派給 `EXPLORE_DONE` → hook 誤判為 session 完成。

**這個 bug 影響 stop-hook.sh 中所有三處 `IFS=$'\t' read`**：

1. `IFS=$'\t' read -r ITERATION MAX_ITERATIONS ...` — frontmatter 解析（若某欄位為空，後續欄位全部偏移）
2. `IFS=$'\t' read -r RATE_ALLOWED RATE_DETAIL RATE_SUMMARY` — rate limit 解析
3. `IFS=$'\t' read -r EXPLORE_DONE NEXT_SUBTOPIC` — tag 解析（直接觸發誤判 bug）

**修復**

將分隔符從 tab (`\t`) 換成 **Unit Separator** (`\x1f`)。Unit Separator 是 ASCII 控制字元，不是 whitespace，因此 `read` 不會 strip 它：

```bash
# 定義 non-whitespace 分隔符
SEP=$'\x1f'

# Python 端使用 sep 變數
TAGS=$(... | python -c "
...
print(done + sep + next_t)
" "$SEP" ...)

# Bash 端使用同一分隔符
IFS="$SEP" read -r EXPLORE_DONE NEXT_SUBTOPIC <<< "$TAGS"
```

驗證：

```bash
$ IFS=$'\x1f' read -r A B <<< $'\x1fworld'
$ echo "A=[$A] B=[$B]"
A=[] B=[world]    # 正確！
```

**另外新增 `stop_hook_active` 防護**

Claude Code 的 Stop hook 在每次 assistant 回應結束時都會觸發。若 hook 已經在上一輪 block 了 stop 並注入新 prompt，Claude Code 會在新回應結束後再次觸發 hook，此時 `stop_hook_active: true`。

原 hook 未檢查此欄位，可能導致無限循環或不預期行為。修復後在 hook 開頭加入檢查：

```bash
IS_ACTIVE=$(echo "$HOOK_INPUT" | python -c "
import json, sys
data = json.load(sys.stdin)
print('yes' if data.get('stop_hook_active', False) else 'no')
" 2>/dev/null || echo "no")

if [[ "$IS_ACTIVE" == "yes" ]]; then
  exit 0  # 允許 Claude 正常停止
fi
```

---

### 設計經驗總結

| 教訓 | 說明 |
|------|------|
| **永遠不要用 tab 作為 bash `read` 的 IFS** | Tab 是 whitespace，`read` 會 strip 開頭的 tab，導致欄位偏移。使用 `\x1f` (Unit Separator) 或 `\x1e` (Record Separator) |
| **Python→Bash 的資料傳遞要用 non-whitespace 分隔符** | 或改用 JSON + `jq`/`python` 逐欄位提取 |
| **必須檢查 `stop_hook_active`** | 否則 stop hook 會在每次 iteration 都嘗試 block，造成無限循環 |
| **測試 stop hook 時要覆蓋「空欄位」情境** | `<explore-next>` 有值但 `<explore-done>` 為空 = 第一個欄位為空 = 最容易觸發此 bug |
| **Stop hook 不應因 transcript 缺失而終止 session** | Transcript 可能暫時不可用，應以 fallback prompt 繼續迴圈，下次再檢查 rate limit |
| **用 `rm -f` 而非 `rm`** | 避免併發刪除或檔案已不存在時出錯 |

---

## `--mode` 強制模式旗標

### 用法

```bash
/auto-explore --mode build Rust async patterns
/auto-explore --mode research build system internals
```

自動偵測有時會判斷錯誤（例如主題含有「build」但其實是研究目的）。`--mode` 旗標讓使用者直接覆蓋。

實作位於 `setup-auto-explorer.sh`：
- 解析 `--mode` 參數，驗證值為 `research` 或 `build`
- 在 Python 自動偵測之後套用覆蓋

---

## 測試 / Testing

### 執行測試

```bash
# 在專案根目錄執行所有測試
python -m pytest tests/ -v

# 執行特定測試檔
python -m pytest tests/test_tag_extraction.py -v
python -m pytest tests/test_check_rate_limits.py -v
python -m pytest tests/test_history.py -v
```

### 測試結構

| 檔案 | 涵蓋範圍 | 測試數 |
|------|----------|--------|
| `tests/test_tag_extraction.py` | `<explore-next>`/`<explore-done>` regex、Unit Separator 協定、Tab bug 迴歸、JSONL 解析 | 14 |
| `tests/test_check_rate_limits.py` | Session token 計算、每日 token 提取、閾值檢查、override 機制 | 12 |
| `tests/test_history.py` | Session 新增/結束、過期 session 清理、duration 格式化、狀態圖示、品質信號 | 13 |
| `tests/test_interest_graph.py` | 興趣圖譜 load/save、add concepts、co-occurrence、decay、Thompson Sampling、bandit feedback、Markdown 生成、migration、community detection、gap finding、CLI | 52 |
| `tests/test_improvement_engine.py` | 改進引擎 template stats、suggest template、suggest budget、mode correction、frequent keywords、session similarity、detect repeat、extract keywords、CLI | 27 |
| `tests/test_mode_detection.py` | 英文/中文動作動詞 build 偵測、research 主題排除、大小寫不敏感、空格變體 | 9 (76 subtests) |
| `tests/test_helpers.py` | frontmatter 解析、slug 生成、過期偵測、主題建議、duration 格式化、rate summary、budget-iterations | 27 |
| `tests/test_auto_export.py` | 自動匯出 flag file 一致性、summary prompt 內容、清理機制 | 9 |
| `tests/test_bash_syntax.py` | `bash -n` 語法檢查（Windows 自動尋找 Git Bash，避免 WSL） | 2 |
| `tests/test_version_consistency.py` | plugin.json、marketplace.json、CHANGELOG.md 版本一致性 | 4 |

### Bash 語法檢查

```bash
bash -n scripts/setup-auto-explorer.sh
bash -n hooks/stop-hook.sh
```

上述語法檢查也包含在 `test_bash_syntax.py` 中，CI 環境可直接用 pytest 執行。
