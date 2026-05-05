---
name: debate
description: Spawn a devil's advocate subagent to challenge the current branch's changes and debate until buy-in is reached. Use before pushing a PR — `/pr` should not run until `/debate` returns approval. Triggered by "debate this", "play devil's advocate", "stress-test this PR", or as a self-imposed gate before opening a PR.
---

Run an adversarial review of the current branch. You (the lead) defend the changes; a subagent attacks them. The branch is **not** pushed until the subagent explicitly signs off.

## Arguments

`$ARGUMENTS` is optional context (e.g. "focus on the auth changes", "be brutal about tests"). If empty, the subagent picks its own angles.

## Step 1: Gather the diff

Before spawning anything, collect the material the subagent needs:

1. `git rev-parse --abbrev-ref HEAD` — current branch.
2. `git log --oneline main..HEAD` — commits on the branch (substitute `main` with the default branch if different).
3. `git diff main..HEAD --stat` — files touched.
4. `git diff main..HEAD` — full diff.

If the branch is empty or identical to main, stop and tell the user there is nothing to debate.

## Step 2: Spawn the devil's advocate

Use the Agent tool (subagent_type: `general-purpose`, **not** worktree-isolated, run in the foreground — you need its responses to continue). The prompt must include:

- The branch name, commit list, and full diff (paste verbatim — do not summarize).
- Any extra context from `$ARGUMENTS`.
- Role instructions, verbatim:

  > You are a devil's advocate code reviewer. Your job is to **find reasons this change should not ship as-is**. Be skeptical, specific, and concrete. No hedging, no "looks good overall." Pick the strongest 3–5 objections you can defend.
  >
  > For each objection, give:
  > - **Claim** — one sentence stating the problem.
  > - **Evidence** — file/line reference or the exact code snippet.
  > - **Why it matters** — concrete failure mode, not vague concern.
  > - **What would satisfy you** — the specific change or argument that would resolve it.
  >
  > Cover at least: correctness/edge cases, tests, security, error handling, API/contract changes, and "is this the simplest thing that works." Skip nits.
  >
  > End your reply with one of:
  > - `VERDICT: BLOCK` — you have unresolved objections.
  > - `VERDICT: APPROVE` — all your objections are addressed and you'd ship this.
  >
  > Never approve on the first round unless the diff is genuinely trivial (≤10 lines, no logic). You must see the lead's responses to your objections before approving.

- A note that the lead will respond to each objection and the subagent should re-evaluate, not capitulate. If the lead's response is weak or hand-wavy, hold the line.

## Step 3: Debate loop

Repeat until the subagent returns `VERDICT: APPROVE` or you decide to escalate:

1. Read the subagent's objections.
2. For each one, decide honestly:
   - **Concede** — the objection is right. Fix the code (edit files, add tests, etc.) before responding.
   - **Push back** — the objection is wrong or out of scope. Explain why with evidence (existing code, the PRD, prior decisions).
3. Send a single reply to the subagent (use SendMessage with the agent's name) that addresses **every** objection. Structure it as one block per objection: `Objection N: <concede + what you changed>` or `Objection N: <push back + reasoning>`. Include any new diff hunks you produced.
4. Ask the subagent to re-evaluate and return a fresh verdict.

### Loop guardrails

- **Cap the loop at 4 rounds.** If the subagent still blocks after round 4, stop and surface the remaining disagreements to the user — do not push through and do not silently approve.
- **Never edit the subagent's verdict.** If you find yourself wanting to "interpret" a BLOCK as approval, that's the signal to escalate.
- **Concessions must land in the code before you reply.** Don't promise fixes; make them.
- If the subagent goes off the rails (objections about things not in the diff, repeated identical points), tell it once to refocus. If it persists, escalate to the user.

## Step 4: On approval

Once the subagent returns `VERDICT: APPROVE`:

1. Print a short summary to the user:
   - Number of debate rounds.
   - Objections conceded (with a 1-line description of each fix).
   - Objections pushed back on (with a 1-line description of the reasoning).
2. Tell the user: "Devil's advocate signed off. Ready to push — run `/pr` when you want the PR opened."
3. Do **not** push or open the PR yourself. The user (or a follow-up `/pr` invocation) does that.

## Step 5: On escalation

If the loop hits round 4 without approval, or the subagent misbehaves:

1. Print the unresolved objections verbatim.
2. Print your last response to each.
3. Ask the user: "Override and push anyway, keep debating, or drop the change?" Wait for an answer. Do not push without explicit user approval.

## Important

- The subagent is adversarial **by design**. Do not soften its prompt to make approval easier.
- Treat conceded objections as real work — fix them, run tests if applicable, then continue.
- Do not commit your fixes during the debate; let them accumulate as unstaged/staged changes so the user can review the full delta when it's done. (If a fix requires committing to test it — rare — note that in the summary.)
- This skill is a gate, not a substitute for `/cr` (which posts inline comments on an already-open PR). `/debate` runs **before** the PR exists.
