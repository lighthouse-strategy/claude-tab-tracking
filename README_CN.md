# claude-tab-tracking

[English](README.md)

> 一眼掌握每个 Claude Code 会话的工作状态。

![demo](assets/demo.svg)

为 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 提供实时任务追踪。自动显示每个会话正在做什么，并随对话进展实时更新。

同时运行多个 Claude Code 会话时，切换窗口即可一眼看到每个会话的当前任务。

## 效果展示

```
[WIP]  修复 api/routes.py 中的认证 bug
[DONE] 部署模型到生产服务器
       my-project  |  ctx 14%  |  23min
```

**状态标识：**
- `[---]` — 会话刚启动，显示目录和 git 分支
- `[WIP]` — 任务进行中，每轮对话自动更新
- `[DONE]` — 任务已完成（自动检测）
- `[SET]` — 通过 `/task` 手动设置的任务

当完成一个任务并开始新任务时，上一个任务会以暗色 `[DONE]` 保留在当前任务下方。

## 工作原理

四个 Claude Code hooks 协同工作：

| Hook | 功能 |
|------|------|
| `SessionStart` | 写入 `目录 [分支]` 作为初始标签 |
| `Stop` | 每次助手回复后：读取对话记录，更新任务描述，检测完成状态 |
| `TaskCompleted` | Claude 明确完成任务时标记为 `[DONE]` |
| `SessionEnd` | 清理会话状态文件 |

### 摘要生成后端

插件自动选择最佳可用后端：

| 优先级 | 后端 | 质量 | 速度 | 成本 |
|--------|------|------|------|------|
| 1 | Claude API（需设置 `ANTHROPIC_API_KEY`） | 最佳 | ~2 秒 | 约 $1/月 |
| 2 | Ollama（本地模型） | 良好 | ~2 秒 | 免费 |
| 3 | Claude Code CLI（Max 订阅） | 最佳 | ~10 秒（异步） | 包含在订阅内 |
| 4 | 关键词匹配 | 基础 | 即时 | 免费 |

无需额外设置，开箱即用。

#### 选择后端

设置 `CLAUDE_TAB_BACKEND` 环境变量来指定后端：

```bash
# 仅使用 Claude Code CLI（Max 订阅，无需 API key）
export CLAUDE_TAB_BACKEND=cli

# 仅使用 Anthropic API
export CLAUDE_TAB_BACKEND=api

# 仅使用本地 Ollama
export CLAUDE_TAB_BACKEND=ollama

# 仅使用关键词匹配（零网络请求）
export CLAUDE_TAB_BACKEND=keyword

# 自动检测最佳后端（默认）
export CLAUDE_TAB_BACKEND=auto
```

指定某个后端时，如果该后端失败则不会回退。设为 `auto`（或不设置）时，按优先级依次尝试所有后端。

## 安装

需要 [jq](https://jqlang.github.io/jq/)：
```bash
brew install jq  # macOS
apt install jq   # Debian/Ubuntu
```

然后：
```bash
git clone https://github.com/lighthouse-strategy/claude-tab-tracking.git
cd claude-tab-tracking && ./install.sh
```

打开新的 Claude Code 会话，状态栏立即生效。

## 对话记忆

插件会自动从每次对话中提取关键信息，保存为结构化备忘录。

### 工作原理

每次助手回复后（对话超过 3 轮时），插件自动提取带标签的内容：

- **决策** — 架构和设计选择
- **数据** — 事实、统计、发现
- **结论** — 原因分析、结果
- **待办** — 后续行动项

备忘录保存在 `~/.claude/memos/{项目名}/{YYYY-MM-DD}.md`，按项目和日期归类。

### 恢复上下文

使用 `/recall` 加载历史备忘录：

```
/recall              # 列出最近项目，交互选择
/recall my-project   # 直接跳到某个项目的日期选择
/recall 3-20         # 加载指定日期的所有备忘录
```

启动会话时，插件会提示是否有历史记录：
```
[memo] 最近项目: my-app (今天, 3条) | api-server (3-20, 5条)
输入 /recall 查看详情
```

### 查看备忘录

使用 `/memo` 浏览备忘录（不加载到上下文）：

```
/memo                # 查看今天的备忘录
/memo 3-20           # 查看指定日期的备忘录
/memo my-project     # 列出某项目最近的备忘录文件
/memo keyword        # 跨所有备忘录搜索关键词
```

## 手动设置任务

使用 `/task` 命令为当前会话设置自定义描述：

```
/task 审查 Q1 策略报告
```

这会写入 `MANUAL:` 前缀，锁定描述并停止自动更新。状态显示为 `[SET]`。

## 安装的文件

| 文件 | 用途 |
|------|------|
| `~/.claude/scripts/session_start.sh` | SessionStart hook |
| `~/.claude/scripts/dynamic_task_update.sh` | Stop hook（bash 封装） |
| `~/.claude/scripts/dynamic_task_update.py` | Stop hook（对话解析 + LLM 摘要） |
| `~/.claude/scripts/cli_background.py` | Claude Code CLI 后端的后台执行脚本 |
| `~/.claude/scripts/task_completed.sh` | TaskCompleted hook |
| `~/.claude/scripts/session_statusline.sh` | 状态栏渲染 |
| `~/.claude/scripts/session_end.sh` | SessionEnd 清理 |
| `~/.claude/commands/task.md` | `/task` 命令 |
| `~/.claude/commands/memo.md` | `/memo` 命令 |
| `~/.claude/commands/recall.md` | `/recall` 命令 |
| `~/.claude/session-tasks/` | 会话状态（7 天后自动清理） |
| `~/.claude/memos/` | 对话备忘录（按项目/日期归类） |

## 卸载

```bash
rm -f ~/.claude/scripts/session_start.sh \
      ~/.claude/scripts/dynamic_task_update.sh \
      ~/.claude/scripts/dynamic_task_update.py \
      ~/.claude/scripts/cli_background.py \
      ~/.claude/scripts/task_completed.sh \
      ~/.claude/scripts/session_statusline.sh \
      ~/.claude/scripts/session_end.sh \
      ~/.claude/commands/task.md \
      ~/.claude/commands/memo.md \
      ~/.claude/commands/recall.md
rm -rf ~/.claude/session-tasks/
rm -rf ~/.claude/memos/
```

然后从 `~/.claude/settings.json` 的 `hooks` 中删除 `SessionStart`、`Stop`、`TaskCompleted`、`SessionEnd` 条目，并删除 `statusLine` 键。

## 作者

由 [lh-strategy](https://github.com/lh-strategy) 构建

## 许可证

MIT
