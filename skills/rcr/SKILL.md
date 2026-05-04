---
name: rcr
description: Respond to code review comments and CI failures on the current PR. Use when the user asks to address review feedback, reply to PR comments, or fix CI failures on their PR.
---

Respond to code review comments on the current PR.

Steps:
1. Run `gh pr view --json reviews,comments` to fetch review feedback.
2. Run `gh pr checks` to fetch CI status. For each failing check:
   - Fetch the failed job log via `gh api repos/OWNER/REPO/actions/jobs/JOB_ID/logs` and grep for `error|FAIL|assert` (skip warnings, codecov, deprecation notices).
   - Classify: **code failure** (test/type/lint/format error, real assertion) vs **infra flake** (network 5xx, runner timeout, image pull failure, codecov upload error).
   - For code failures, fix directly alongside review feedback. Check whether a later commit on the branch already fixed it before doing anything.
   - For infra flakes, run `gh run rerun RUN_ID --failed` and note it in the summary.
3. Skip threads where `isResolved` is true (fetch via `gh api graphql … reviewThreads`). Also skip threads where the PR author already replied — don't reopen settled debates. Only triage **unresolved, un-replied** threads.
4. Triage remaining comments before making any edits. For each comment, classify as:
   - **Accept** — describe the proposed fix in 1-2 sentences (file:line + what will change). Do NOT edit yet.
   - **Push back** — draft the reply (1-2 sentences) explaining why.
   - **Clarify** — needs user input before deciding.
5. Present the full triage to the user as a list (accepts with proposed edits, pushbacks with draft replies). Wait for user approval or course correction before touching any files.
6. After approval, apply the accepted edits.
7. After making all fixes:
   - Run linters/tests to confirm nothing broke.
   - Stage and commit with `fix: address review feedback` (or more specific if warranted).
   - Push the changes.
8. Check for merge conflicts with the base branch:
   - Run `git fetch origin <base>` and `git merge-base --is-ancestor origin/<base> HEAD` (or check `gh pr view --json mergeable`).
   - If the branch is behind the base or marked unmergeable, attempt `git rebase origin/<base>`.
   - If the rebase has more than ~2 conflicting files or spans many commits, **abort and surface to the user** — do not silently churn through deep rebases. Report the conflicting files and ask whether to merge, rebase, or take a different approach.
   - If conflicts are small and mechanical, resolve them, run linters/tests again, and force-push (ask first per memory).
9. Resolve addressed review threads:
   - List the comment threads you fixed or replied to.
   - Ask the user for permission before resolving any threads.
   - If approved, resolve them using the GraphQL API:
     - First fetch thread IDs: `gh api graphql -f query='{ repository(owner:"OWNER",name:"REPO") { pullRequest(number:NUM) { reviewThreads(first:100) { nodes { id isResolved comments(first:1) { nodes { body } } } } } } }'`
     - Then resolve each: `gh api graphql -f query='mutation { resolveReviewThread(input:{threadId:"THREAD_ID"}) { thread { id } } }'`
   - Only resolve threads where the feedback was accepted and the fix was pushed. Do NOT resolve threads where you pushed back.
10. Summarize what was addressed, what was pushed back on, and which threads were resolved.

Bias toward accepting feedback. Only push back when the reviewer is factually wrong or the suggestion would degrade the code.
