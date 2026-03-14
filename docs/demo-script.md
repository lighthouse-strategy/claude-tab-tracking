# Demo GIF Recording Script

Record a ~10-15 second GIF showing the plugin in action.

## Recording Tool

```bash
# Option A: asciinema + agg (terminal-native, small file)
brew install asciinema
brew install agg
asciinema rec demo.cast
agg demo.cast assets/demo.gif --cols 80 --rows 12 --font-size 16

# Option B: macOS screen recording (Cmd+Shift+5) → convert to GIF with ezgif.com
```

## Setup

- 2 terminal tabs, each with a Claude Code session in a different directory
- Use generic demo directories (e.g. `~/demo-project`, `~/sample-app`) — avoid showing real project content

## Script

### Step 1: Tab 1 — First task

Type:
```
help me write a hello world in python
```

Wait for Claude to respond. Statusline updates: `[---]` → `[WIP] Write hello world in Python`

### Step 2: Tab 2 — Different session

Type:
```
explain how git rebase works
```

Wait for response. Statusline shows: `[WIP] Explain git rebase`

This demonstrates each tab tracks independently.

### Step 3: Tab 1 — Task completes, start new task

After the hello world task finishes, type:
```
now add unit tests for it
```

Statusline shows the 3-line display (the money shot):
```
[WIP]  Add unit tests for hello world
[DONE] Write hello world in Python
       demo-project  |  ctx 8%  |  2min
```

### Step 4: Quick tab switch

Switch between Tab 1 and Tab 2 to show each one tracking its own task.

## Tips

- Keep it under 15 seconds — shorter is better for GitHub READMEs
- The 3-line statusline (WIP + DONE + info) is the key visual — make sure it's clearly visible
- If Claude takes too long to respond, you can use `/task` to manually set status for demo purposes

## Output

Save as `assets/demo.gif`, then uncomment the image line in README.md:
```
![demo](assets/demo.gif)
```
