---
name: session-skill-review
description: Review which skills fired in a pi session log, and why one did not. Use for "which skills did I use in that session", "why did my skill not fire", "analyze this session log", "optimize this skill".
---

Ask which session log to review, find which skills fired in it, then analyze one skill against what actually happened: where it fired, where it should have, and which actions the agent took that it never mentions. The output is a small edit to that skill, not a report.

Extraction is mechanical: `skills-used.py` beside this file (see its docstring for what counts as a fire).

## 1. Pick the session

Run `python3 skills-used.py --list 5`. Paste the numbered list as-is (numbers, date, first user message — drop the long paths) and ask which number.

Logs live in `~/.pi/agent/sessions/<cwd-slug>/*.jsonl`, where the slug is the working directory with `/` replaced by `-` (`--home-rus-tmp-pi--`). If the user names a project, filter that folder instead of listing everything.

**Done when** the user has answered a number and you have the path it maps to. Re-run the identical `--list` command to resolve it — changing the limit renumbers the list, and the user answered the old numbers.

## 2. Find the skills that fired

Run `python3 skills-used.py <path>`. It prints `Nx name` with the transcript line of each read.

**Done when** you hold a skill list with counts and line numbers, or the script said none fired.

## 3. Branch on the count

- **None fired** — say so and stop. If the user expected one to fire, that is a description problem: name the user message that should have triggered it and move to step 5.
- **One fired** — go to step 4.
- **Several fired** — show `Nx name` for each and ask which one to analyze. **Done when** one skill name is chosen.

## 4. Analyze the chosen skill

Read its `SKILL.md` first, then check four things against the transcript:

- **Trigger** — find the user message just before the read (`line N`) and quote it. Did it match one of the description's trigger branches, or did the agent reach the skill by luck?
- **Near miss** — scan the other user messages in the session for a moment the skill should have fired and did not.
- **Body** — did the actions after the read follow the procedure? Name the step that was skipped or misread.
- **Coverage** — did the agent do work the skill never mentions? Inventoried below.

**Done when** each of the four has a verdict with a transcript anchor: a `line N` or a quoted user phrase. A claim with no anchor is not a finding.

### Coverage: uncovered actions

Run `python3 skills-used.py --actions <path> --from <line of the read>` for every tool call after the skill loaded, in order.

Cross out each action a step already prescribes. Label each leftover:

- **Missing step** — it recurs, and the job cannot be done without it: the skill should own it.
- **Incidental** — one-off and specific to this repo or this day: leave it out.
- **Wrong** — the skill should have prevented it: sharpen the line that failed to.

Info-gathering commands are the usual missing step: `ls` to find the layout, `git log` to date a change, `grep` for a path, `--help` on a tool the skill assumes. The test is whether the reader must invent the same command every run. If yes, the skill owes it, verbatim.

**Done when** every action after the read is either traced to a step or labelled, and each missing step carries the exact command from the transcript.

## 5. Propose the smallest edit

- **Trigger missed** — edit the `description` only. It is the one field Pi indexes; the body never reaches a decision to load. Reuse the user's own words from the log.
- **Body ignored** — sharpen the single line that was read past. Keep the surrounding text.
- **Uncovered action** — add one step: the command verbatim, then what done looks like. Adding it to an existing step beats a new heading.

**Done when** you have a ≤3-line diff and can say which branch it fixes. Label it a hypothesis: one session is not a rate.

## Pitfalls

- The skill index sits in every session's system prompt, so `grep` for a skill name matches all sessions. Count reads, not mentions. But a `<skill name="...">` block **injected into a user message** is a real fire (the platform's "use this skill" mechanism) — not an index mention; the script now counts these as `line N: <skill> injection`, and the body may run bundled scripts without ever reading `SKILL.md`.
- A `bash cat` of a skill is not counted by the script. If the transcript shows one, add it by hand.
- A read is not automatically a fire — the user may have said "read the brainstorming skill". Check the trigger message before believing the count.
- A step the skill gets right makes the same command look "covered" while every run also depends on an undocumented one beside it. Read the inventory for what is absent, not only for what is wrong.
- A dozen local sessions cannot support a rate. Look for the qualitative miss, not a percentage.
- Logs carry whole prompts and may carry secrets. Quote only what the finding needs.

## Verify

- `python3 skills-used.py --list 3` prints paths that exist.
- Usage mode on a session with no skill reads prints `no skills invoked in this session`.
- `--actions` prints one line per tool call and a `# Nx tool` summary; line numbers match the `read` line from usage mode.
- Every claim in the analysis cites a `line N` or a quoted user message.
