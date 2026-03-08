Set or update the session task description shown in the statusline.

When this command is invoked:

1. Determine the task description:
   - If the user typed something after `/task` (e.g. `/task Fix the Model-A bug`), use that text as the description.
   - If no text was provided, ask: "What task are you working on in this session?"

2. Find the current session's task file using the cwd-indexed lookup:
   - Run: `CWD_HASH=$(echo "$PWD" | md5 | cut -c1-8) && cat ~/.claude/session-tasks/current_${CWD_HASH}.txt 2>/dev/null`
   - This gives you the SESSION_ID for the current session.
   - If no session ID is found, say "Session task file not found — the SessionStart hook may not have run yet. Try restarting Claude Code."

3. Write the task description to the task file:
   - Format: `MANUAL:<description>` (MANUAL prefix prevents the Stop hook from auto-updating it)
   - Run: `echo "MANUAL:<description>" > ~/.claude/session-tasks/<SESSION_ID>.txt`
   - Replace `<description>` with the actual task text and `<SESSION_ID>` with the value from step 2.

4. Confirm to the user:
   - Say: "Task set: <description>"
   - Add: "It will appear in the statusline as [SET] after your next interaction."

Note on prefixes:
- `WIP:` = auto-tracked by Stop hook (updates each turn)
- `DONE:` = task completed (set by Stop hook or TaskCompleted hook)
- `MANUAL:` = user-set description (Stop hook will NOT auto-update this)
