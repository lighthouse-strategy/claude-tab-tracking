# Demo GIF Recording Script

Record a ~15-20 second GIF showing the plugin in action.

## Setup

- 3 terminal tabs, each with a Claude Code session in a different project
- Recommended tool: [asciinema](https://asciinema.org/) + [agg](https://github.com/asciinema/agg) for high-quality terminal GIF

## Script

1. **Tab 1** — Start a task. Statusline shows `[---]` → `[WIP] Fix data pipeline bug`
2. **Tab 2** — Different project, different task. `[WIP] Add user authentication`
3. **Tab 1** — Task completes. `[DONE] Fix data pipeline bug`
4. **Tab 1** — Start new task. Shows:
   ```
   [WIP]  Refactor API endpoints
   [DONE] Fix data pipeline bug
          my-project  |  ctx 23%  |  12min
   ```
5. Quick cut between tabs to show each one tracking independently

## Output

Save as `assets/demo.gif`, then uncomment the image line in README.md:
```
![demo](assets/demo.gif)
```
