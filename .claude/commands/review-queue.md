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

3. Filter PRs where any configured team appears in `.requested_teams[].slug`.

4. For each matching PR, fetch reviews to detect re-review:
   ```
   gh api "repos/{owner}/{repo}/pulls/{number}/reviews" --jq '[.[] | select(.user.login == "{my_username}")]'
   ```
   If I have a previous review, mark as **⚠️ RE-REVIEW**.

5. Present results grouped by repo, oldest first:

   ```
   ## PRs to Review (N)

   ### org/repo
   - [#123 "PR title"](url) (author, 3d ago) — team-slug requested
   - [#456 "PR title"](url) (author, 1d ago) — ⚠️ RE-REVIEW — team-slug requested
   ```

6. If no PRs match: **No PRs to review right now.**

7. On macOS, send a notification:
   ```
   osascript -e 'display notification "N PRs waiting for review" with title "Review Queue"'
   ```

## Important

- Skip draft PRs.
- Do NOT use `$()` or backticks in shell commands — run each command separately and use literal values.
- Use `gh api` with `--jq` for filtering where possible.
