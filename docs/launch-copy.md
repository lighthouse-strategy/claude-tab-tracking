# claude-tab-tracking Launch Copy

**Launch:** 2026-03-15 (Sunday)
**Repo:** https://github.com/lighthouse-strategy/claude-tab-tracking

---

## 1. Twitter/X

"Which tab was fixing the bug again?"

If you run multiple Claude Code sessions, you know the pain. Built a tiny plugin that shows what each session is doing — right in the statusline.

Zero config. Auto-detects tasks. Just install and forget.

[demo GIF]

github.com/lighthouse-strategy/claude-tab-tracking

#ClaudeCode #OpenSource

---

## 2. Reddit r/ClaudeAI

**Title:** "Which tab was doing what?" — built a plugin to fix this

I keep 3-4 Claude Code sessions running at once. The problem: I constantly forget which tab is working on what.

So I built a statusline plugin that auto-detects what each session is doing:

```
[WIP]  Add unit tests for hello.py
[DONE] Add greet function
       my-project  |  ctx 8%  |  3min
```

No manual input. It reads the conversation, figures out the task, and updates every turn. When a task completes and you start a new one, it keeps the previous task visible.

Two lines to install:
```
git clone https://github.com/lighthouse-strategy/claude-tab-tracking.git
cd claude-tab-tracking && ./install.sh
```

[demo GIF]

MIT licensed. Feedback welcome.

---

## 3. Reddit r/commandline

**Title:** Statusline plugin for Claude Code — auto-tracks what each session is doing

Multiple Claude Code tabs open. Can't tell them apart.

Built a fix: shell hooks + a Python transcript parser that auto-summarizes the current task into the statusline. No daemon, no config.

```
[WIP]  Add unit tests for hello.py
[DONE] Add greet function
       my-project  |  ctx 8%  |  3min
```

Three summarization backends (auto-selected): Claude API > Ollama > keyword heuristics.

https://github.com/lighthouse-strategy/claude-tab-tracking

---

## 4. Hacker News (Show HN)

**Title:** Show HN: Auto-track what each Claude Code session is doing

**URL:** https://github.com/lighthouse-strategy/claude-tab-tracking

**Comment:**

Problem: multiple Claude Code tabs, can't tell them apart.

This hooks into Claude Code's lifecycle events and auto-generates a task summary in the statusline. Summarization uses Claude API, Ollama, or keyword heuristics — auto-selects the best available. No config. `git clone && ./install.sh`.

---

## 5. Discord

"Which Claude tab was doing the refactor?" — sound familiar?

Built a small plugin that shows each session's current task in the statusline. Auto-detected, zero config.

```
[WIP]  Add unit tests
[DONE] Fix auth bug
       my-project  |  ctx 8%  |  3min
```

Install: `git clone ... && ./install.sh`

[demo GIF]

https://github.com/lighthouse-strategy/claude-tab-tracking

---

## 6. V2EX

**Title:** 开了 4 个 Claude Code 窗口，完全不记得哪个在干嘛——所以写了个插件

同时用多个 Claude Code session 的痛：切 tab 之前根本不知道哪个在写测试、哪个在修 bug。

做了个插件，自动从对话里提取任务显示在 statusline 上：

```
[WIP]  给 hello.py 写单元测试
[DONE] 添加 greet 函数
       my-project  |  ctx 8%  |  3min
```

不用手动输入，每轮对话自动更新。三种摘要后端自动切换（Claude API > Ollama > 关键词）。

两行安装，零配置。MIT 开源。

GitHub: lighthouse-strategy/claude-tab-tracking

---

## 7. 即刻

开了一堆 Claude Code 窗口，切过去之前："这个在干嘛来着？"

写了个插件，自动识别每个会话的任务，贴在 statusline 上。不用手动打标签，它自己从对话里读。

完成一个任务开始下一个时，上一个任务还会留着：
[WIP] 当前任务
[DONE] 刚做完的

两行命令装好，零配置。

GitHub: lighthouse-strategy/claude-tab-tracking

#ClaudeCode #开源 #开发工具

---

## 8. 小红书

**标题：** 同时开好几个 Claude Code？这个插件让你一眼看清每个在干嘛

**正文：**

用 Claude Code 的朋友们有没有这个痛点：

同时开了 3、4 个终端窗口让 Claude 干活，切来切去根本不记得哪个在做什么。

做了个小插件，装上之后每个窗口的状态栏会自动显示当前任务：

- 正在做什么 [WIP]
- 刚做完什么 [DONE]
- 上下文用了多少、跑了多久

最关键的是——完全自动！不用手动打标签，它自己从对话里提取任务。

两行命令安装，零配置，开源免费。

GitHub 搜：claude-tab-tracking

#ClaudeCode #AI编程 #效率工具 #开源 #程序员

---

## Launch Checklist

- [ ] Make repo public (Sunday morning)
- [ ] Post Twitter/X with demo GIF
- [ ] Post Reddit r/ClaudeAI
- [ ] Post Reddit r/commandline
- [ ] Submit Hacker News (Show HN)
- [ ] Post Discord
- [ ] Post V2EX
- [ ] Post 即刻
- [ ] Post 小红书 with screenshots
- [ ] Monitor and reply to comments within 2h
