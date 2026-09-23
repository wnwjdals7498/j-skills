# ctx-relay planner guide

You are the planner (Claude, Codex, or another big model). Small executor models rotate every request, have no memory and reason poorly. Everything they need must be in `.ctx/TASKS.md`.

## Setup

From the target repo root:

```text
python <skill-dir>/scripts/ctx.py init --goal "<one-line end goal>"
```

This creates `.ctx/STATE.md`, `TASKS.md` and `LOG.md` (keeps existing ones), copies `ctx.py` into `.ctx/`, and adds or refreshes the ctx-relay block in `AGENTS.md`. opencode injects `AGENTS.md` into every request, so executors see the loop even when they never load this skill. Rerun `init` after updating the skill. Commit `.ctx/` and `AGENTS.md`.

## Writing tasks

```md
- [ ] T4 Add email validator
  files: src/auth/validate.ts
  do: Export `validateEmail(s: string): boolean` from src/auth/validate.ts.
    Return true only for one "@" with non-empty local part and a domain containing ".".
    Trim whitespace first. Empty string returns false. No regex libraries.
  verify: npm test -- validate
```

- One task = one small change: 1 to 3 files, one behavior.
- `do:` is self-contained. Name exact paths, functions, signatures, inputs, outputs and edge cases. No "as discussed", no "see T2". Continuation lines stay indented.
- `files:` lists every path the executor may edit or create. Nothing else gets touched.
- `verify:` is one shell command. Exit 0 means done. It must run in the executor's shell (PowerShell or bash). Prefer a targeted test over the full suite.
- Write tests yourself, or in an earlier task, and keep test files out of later `files:`. Weak models edit tests to make them pass.
- Order is execution order. The executor takes the first `- [ ]` from the top.
- IDs are unique and never reused. Next ID = highest ID ever used + 1 (check `LOG.md`).
- Put repo-wide conventions in STATE `## notes`: max 5 bullets, 200 chars each.
- Keep `TASKS.md` under 12,000 chars. Delete `[x]` tasks when starting a new batch; `LOG.md` keeps the history.
- Set STATE `goal:` and TASKS `plan:` to the current batch.
- Run `python .ctx/ctx.py check` before handing off. It must print `OK`.

## Unblocking

The executor stops at `status: blocked`. Then:

1. Read STATE `blocked:`, the task, the tail of `LOG.md`, and `git diff`.
2. Fix the cause: rewrite `do:`, widen `files:`, split the task, or fix the code yourself.
3. Change `- [!]` back to `- [ ]` (or delete it if you replaced it). Set STATE `task: -`, `status: idle`, `fails: 0`, `blocked: -`.
4. Run check, then commit.

## Review

After a batch, read `git log --oneline` and `LOG.md`, then run each `verify:` yourself. Check that `git diff` stays inside each task's `files:`.

## Install

The script needs Python 3.6+ and the stdlib only. Link this folder instead of copying it:

| Tool | Skill location |
|---|---|
| opencode | `~/.config/opencode/skills/ctx-relay` (also reads `~/.claude/skills/`) |
| Claude Code | `~/.claude/skills/ctx-relay` |
| Codex | `~/.codex/skills/ctx-relay` |

On Windows, use a directory junction (from PowerShell): `cmd /c mklink /J "%USERPROFILE%\.claude\skills\ctx-relay" "<j-skills>\ctx-relay"`.
