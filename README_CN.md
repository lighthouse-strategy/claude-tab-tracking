# claude-tab-tracking

[English](README.md)

为 [Claude Code](https://code.claude.com) 提供实时任务追踪。自动显示每个会话正在做什么，随对话进展实时更新。

如果你同时运行多个 Claude Code 会话，可以一目了然地看到每个会话的当前状态。

## 效果展示

```
[WIP] Fix data pipeline bug in core/fetcher.py
      my-project  |  ctx 14%  |  23min

[DONE] Deploy model to production server
       my-project  |  ctx 61%  |  1h12m

[---]  backend  [feature/auth]
       backend   |  ctx 2%   |  0min
```

**状态标记：**
- `[---]` — 会话刚启动，显示目录和 git 分支
- `[WIP]` — 任务进行中，每轮对话自动更新
- `[DONE]` — 任务已完成（自动检测）
- `[SET]` — 通过 `/task` 手动设置的任务

## 工作原理

四个 Claude Code 钩子协同工作：

| 钩子 | 功能 |
|------|------|
| `SessionStart` | 将 `目录 [分支]` 写入初始任务标签 |
| `Stop` | 每次助手回复后：读取对话记录，更新任务描述，检测是否完成 |
| `TaskCompleted` | 当 Claude 明确完成任务时，标记为 `[DONE]` |
| `SessionEnd` | 清理会话状态文件 |

状态栏脚本读取当前会话的任务文件，渲染两行内容：第一行是任务状态，第二行是目录 + 上下文使用率 + 会话时长。

### 摘要生成后端（自动检测，无需配置）

插件会自动选择最佳可用后端：

| 优先级 | 后端 | 质量 | 费用 |
|--------|------|------|------|
| 1 | Claude API（已设置 `ANTHROPIC_API_KEY`） | 最佳 | 约 $1/月 |
| 2 | Ollama（本地模型运行中） | 良好 | 免费 |
| 3 | 关键词启发式 | 基础 | 免费 |

无需额外设置，开箱即用。在环境变量中设置 `ANTHROPIC_API_KEY` 可获得最佳效果。

## 安装

需要 [jq](https://jqlang.github.io/jq/)：
```bash
brew install jq  # macOS
apt install jq   # Debian/Ubuntu
```

然后：
```bash
git clone https://github.com/lighthouse-strategy/claude-tab-tracking.git
cd claude-tab-tracking
chmod +x install.sh
./install.sh
```

打开一个新的 Claude Code 会话，状态栏会立即显示。

## 手动设置任务

使用 `/task` 斜杠命令为当前会话设置自定义描述：

```
/task Reviewing Q1 strategy report
```

这会写入 `MANUAL:` 前缀，固定描述内容并停止该会话的自动更新。状态标记显示为 `[SET]`。

## 安装的文件

| 文件 | 用途 |
|------|------|
| `~/.claude/scripts/session_start.sh` | SessionStart 钩子 |
| `~/.claude/scripts/dynamic_task_update.sh` | Stop 钩子（bash 包装器） |
| `~/.claude/scripts/dynamic_task_update.py` | Stop 钩子（对话解析 + LLM 摘要） |
| `~/.claude/scripts/task_completed.sh` | TaskCompleted 钩子 |
| `~/.claude/scripts/session_statusline.sh` | 状态栏渲染器 |
| `~/.claude/scripts/session_end.sh` | SessionEnd 清理 |
| `~/.claude/commands/task.md` | `/task` 斜杠命令 |
| `~/.claude/session-tasks/` | 会话状态（7 天后自动清理） |

## 卸载

```bash
rm -f ~/.claude/scripts/session_start.sh \
      ~/.claude/scripts/dynamic_task_update.sh \
      ~/.claude/scripts/dynamic_task_update.py \
      ~/.claude/scripts/task_completed.sh \
      ~/.claude/scripts/session_statusline.sh \
      ~/.claude/scripts/session_end.sh \
      ~/.claude/commands/task.md
rm -rf ~/.claude/session-tasks/
```

然后从 `~/.claude/settings.json` 的 `hooks` 部分删除 `SessionStart`、`Stop`、`TaskCompleted`、`SessionEnd` 条目，并删除 `statusLine` 键。

## 作者

由 [lh-strategy](https://github.com/lh-strategy) 构建

## 许可证

MIT
