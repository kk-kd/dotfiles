Fetch open PRs I need to review and present a summary with links.

## How it works

Read the review queue configuration from the current project's `.claude/CLAUDE.md` or `.claude/review-queue.json`. The config specifies repos and filter criteria (requested teams, requested reviewers, labels, etc.).

If no project-level config is found, check `~/.claude/review-queue.json` as a fallback.

### Config format (review-queue.json)

```json
{
  "repos": [
    {
      "repo": "org/repo-name",
      "teams": ["team-slug-1", "team-slug-2"],
      "reviewers": [],
      "exclude_drafts": true
    }
  ]
}
```

Alternatively, the config can be embedded in CLAUDE.md under a `## Review Queue` heading using the same JSON in a code block.

## Instructions

1. Load the config as described above. If no config is found, tell the user to create `.claude/review-queue.json` in their project and show the format.

2. Look up the current GitHub username:
   ```
   gh api user --jq .login
   ```

3. For each configured repo, fetch open PRs:
   ```
   gh api "repos/{owner}/{repo}/pulls?state=open&per_page=100" --jq '[.[] | select(.draft == false)]'
   ```

4. Filter PRs where any configured team appears in `.requested_teams[].slug` OR any configured reviewer appears in `.requested_reviewers[].login`.

5. For each matching PR, fetch reviews to detect re-review:
   ```
   gh api "repos/{owner}/{repo}/pulls/{number}/reviews" --jq '[.[] | select(.user.login == "{my_username}")]'
   ```
   If I have a previous review, mark as **⚠️ RE-REVIEW**.

6. Present results grouped by repo, oldest first:

   ```
   ## PRs to Review (N)

   ### org/repo
   - [#123 "PR title"](url) (author, 3d ago) — team-slug requested
   - [#456 "PR title"](url) (author, 1d ago) — ⚠️ RE-REVIEW — team-slug requested
   ```

7. If no PRs match: **No PRs to review right now.**

8. On macOS, send a notification:
   ```
   osascript -e 'display notification "N PRs waiting for review" with title "Review Queue"'
   ```

## Important

- Skip draft PRs unless config says otherwise.
- Do NOT use `$()` or backticks in shell commands — run each command separately and use literal values.
- Use `gh api` with `--jq` for filtering where possible.
