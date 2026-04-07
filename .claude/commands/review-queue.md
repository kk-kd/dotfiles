Fetch open PRs I need to review and present a summary with links.

## Configuration

Check the current project's `.claude/review-queue.json` for repo-specific config. If none exists, use this default:

```json
{
  "repos": [
    {
      "repo": "plenful/plenful",
      "teams": ["ml-eng", "automations-review"],
      "reviewers": ["cady-plenful"],
      "exclude_drafts": true
    }
  ]
}
```

Projects can override by placing their own `.claude/review-queue.json` with the same format.

## Instructions

1. Look up the current GitHub username:
   ```
   gh api user --jq .login
   ```

2. For each configured repo, fetch open non-draft PRs:
   ```
   gh api "repos/{owner}/{repo}/pulls?state=open&per_page=100" --jq '[.[] | select(.draft == false)]'
   ```

3. Filter PRs based on the repo config:
   - If `teams` is set: match PRs where any configured team appears in `.requested_teams[].slug`.
   - If `reviewers` is set: match PRs where any configured reviewer appears in `.requested_reviewers[].login`.
   - If `title_contains` is set: match PRs where the title contains the given string (case-insensitive).
   - All filters are OR'd within a single repo entry (a PR matching any filter is included).
   - Filters can coexist on different repo entries (even for the same repo). Deduplicate PRs by number across all entries.

4. For each matching PR, fetch reviews to detect re-review:
   ```
   gh api "repos/{owner}/{repo}/pulls/{number}/reviews" --jq '[.[] | select(.user.login == "{my_username}")]'
   ```
   If I have a previous review, mark as **⚠️ RE-REVIEW**.

5. Present results grouped by repo (and label if set), oldest first:

   ```
   ## PRs to Review (N)

   ### org/repo
   - [#123 "PR title"](url) (author, 3d ago) — team-slug requested
   - [#234 "PR title"](url) (author, 2d ago) — reviewer requested
   - [#456 "PR title"](url) (author, 1d ago) — ⚠️ RE-REVIEW — team-slug requested

   ### org/repo (PDM)
   - [#789 "PDM: some feature"](url) (author, 2d ago) — title match
   ```

6. **My PRs needing attention**: For each configured repo, fetch my open PRs:
   ```
   gh api "repos/{owner}/{repo}/pulls?state=open&per_page=100" --jq '[.[] | select(.draft == false and .user.login == "{my_username}")]'
   ```
   For each of my PRs, fetch reviews:
   ```
   gh api "repos/{owner}/{repo}/pulls/{number}/reviews" --jq '[.[] | select(.user.login != "{my_username}")]'
   ```
   A PR needs attention if it has any review with `state` of `CHANGES_REQUESTED` or `COMMENTED` (and no subsequent `APPROVED` from the same reviewer). Show these in a separate section:

   ```
   ## My PRs Needing Attention (N)

   ### org/repo
   - [#101 "My PR title"](url) (2d ago) — 🔴 changes requested by reviewer1
   - [#102 "Another PR"](url) (5d ago) — 💬 commented by reviewer2
   ```

7. If no PRs match either section: **No PRs to review right now.**

8. On macOS, send a notification:
   ```
   terminal-notifier -title "Review Queue" -message "N PRs waiting for review, M of mine need attention"
   ```

## Important

- Skip draft PRs.
- Do NOT use `$()` or backticks in shell commands — run each command separately and use literal values.
- Use `gh api` with `--jq` for filtering where possible.
