---
name: ctx-relay
description: Continue repo work across rotating small models (opencode + freellmapi) using state in <repo>/.ctx/. Use at the start of every task in a repo with .ctx/. Planners (Claude, Codex) use it to write tasks.
---

# ctx-relay

You may be a different model than last turn. You remember nothing. `.ctx/` in the repo root is the only truth.

A big model (Claude, Codex) plans and writes TASKS. A small model executes. **Planner: read [references/planner.md](references/planner.md) instead of the loop below.**

## Files

| File | Written by | Read |
|---|---|---|
| `.ctx/STATE.md` | executor, after every step | always |
| `.ctx/TASKS.md` | planner; executor only flips markers | always |
| `.ctx/LOG.md` | executor appends one line per task | only when asked |
| `.ctx/ctx.py` | nobody (copied by init) | run it |

## Executor loop

1. Run `python .ctx/ctx.py check` (`python3` if `python` is missing). FAIL -> fix that line, rerun. Cannot fix -> report and stop.
2. Read `.ctx/STATE.md` and `.ctx/TASKS.md`.
3. `status: blocked` -> report the `blocked:` line. Stop. Do no work.
   `status: idle` -> take the first `- [ ]` task. Set `task: T<n>`, `status: active`, `did: -`, `next: <first step>`, `fails: 0`. No `- [ ]` left -> report "all tasks done" and stop.
4. Read any file. Edit or create only paths in the task's `files:`. `do:` unclear, or another file needed -> go to blocked (step 6). Do not guess.
5. After every edit or command: rewrite `did`, `next`, `updated` in STATE, run check. Always before ending a reply.
6. Run the task's `verify:` command exactly as written.
   - Exit 0 -> TASKS `- [ ]` to `- [x]`. Append a LOG line. STATE `task: -`, `status: idle`, `did: -`, `next: -`, `fails: 0`. Commit. Back to step 3.
   - Non-zero -> `fails` +1. Error gist in `did`, fix plan in `next`. Fix and rerun.
   - `fails` reaches 2, or blocked in step 4 -> TASKS `- [!]`. STATE `status: blocked`, `blocked: <cause and what the planner must decide>`. Append a LOG line. Stop.

## Formats

STATE keys are fixed. `-` means none. Each value is one line, max 300 chars.

```md
# STATE
goal: Email login with validation
updated: 2026-09-23 14:10

## now
task: T3
status: active
did: added validateEmail; 2/3 tests pass
next: handle empty string case
fails: 1
blocked: -

## notes
- API responses use snake_case
```

`## notes`: max 5 bullets, 200 chars each. Planner owns them.

LOG line: `2026-09-23 14:10 | T3 | done | verify exit 0 | model: <your model id or ?> | <short note>`

Commit after each done task: `git add <task files> .ctx` then `git commit -m "T3: <task title>"`.

## Never

- Mark `[x]` without exit 0 from `verify:` in this session.
- Edit `do:`, `files:`, `verify:`, or add or remove tasks. That is the planner's job.
- Edit test files that are not in `files:` to make `verify:` pass.
- Add STATE sections or keys.
- `git push`, `git reset --hard`, `git stash`, or delete files not in `files:`.
