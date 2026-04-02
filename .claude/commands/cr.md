Review a PR and post findings as **pending inline comments** on GitHub.

ARGUMENTS: branch name OR PR number

---

## Step 1: Resolve the PR

- If the argument looks like a number, treat it as a PR number.
- If it looks like a branch name, find the PR: `gh pr view <branch> --json number,headRefName,baseRefName`
- If no argument is given, use the current branch: `gh pr view --json number,headRefName,baseRefName`
- Extract the PR number and base branch from the result.

## Step 2: Get the diff

1. `git fetch --all --prune`
2. `git checkout <base> && git pull --ff-only origin <base>`
3. `git checkout <head> && git pull --ff-only origin <head>`
4. `git diff <base>...<head>`

Do not compare until both branches have been updated.

## Step 3: Analyze the diff

Check for:

1. **Bugs & logic errors** — anything that would break at runtime or produce wrong results.
2. **Security issues** — injection, hardcoded secrets, unsafe deserialization, etc.
3. **Performance** — unnecessary allocations, N+1 queries, blocking calls in async code.
4. **Readability** — unclear naming, overly clever code, missing type hints or docstrings.
5. **Design** — violations of SRP, tight coupling, missing abstractions.

### Code style
- Imports at top; never mid-file
- Functions under ~50 lines
- Type hints on all public functions
- No excessive comments — prefer self-documenting code
- No heavyweight ASCII separators (`# =====...`); use `# ---` or a blank line

### Structure & organization
- Each file has one clear purpose
- No duplicated information across docs
- No circular dependencies

### Function placement
| Problem | Solution |
|---------|----------|
| DB ops in router/controller | Move to repository/model layer |
| Business logic in API endpoint | Extract to service layer |
| File I/O in transform functions | Extract to dedicated file handler |
| Config parsing scattered | Centralize in config module |
| Validation logic duplicated | Create shared validators |

### Architecture questions
- Does this follow existing patterns?
- Are there existing utilities that could be reused?
- Can this be unit tested in isolation? Are side effects isolated?
- Will a new team member understand this in 6 months?
- Are there magic strings/numbers that should be constants?

## Step 4: Show comments for approval

Before posting anything, print all proposed comments in the conversation for the user to review. Format each comment as:

```
[severity] file/path.py:L123
comment body
```

Then ask: "Post these comments? (yes/edit/cancel)"

- **yes**: proceed to post
- **edit**: user will tell you which comments to drop or modify, then re-confirm
- **cancel**: abort without posting

Do NOT post to GitHub until the user explicitly approves.

## Step 5: Post pending review comments

For each finding, determine the **exact file path** and **diff line number** to comment on.

### Computing the correct line position

CRITICAL: The `line` field in the GitHub review comment API refers to the **line number in the file** (after the change), NOT the position in the diff hunk. Use the line number from the new version of the file as shown in the diff `+` side or unchanged context lines.

For lines that exist only in the old version (deleted lines), use `side: "LEFT"` with the old file line number.

### Posting the review

Use a SINGLE `gh api` call to create a pending review with all comments at once:

```
gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  --method POST \
  -f event="PENDING" \
  -f 'comments=[...]'
```

Build the JSON body with all comments in one array. Each comment object:
```json
{
  "path": "relative/file/path.py",
  "line": <line_number_in_new_file>,
  "body": "**severity** comment body with explanation and suggested fix"
}
```

Severity prefixes for comment bodies:
- `**must-fix:**` for bugs, security issues, correctness problems
- `**should-fix:**` for performance, design, or maintainability issues
- `**nit:**` for style, naming, or minor improvements

Include a diff suggestion block in the comment body when a concrete fix is possible:

````
**should-fix:** Description of the issue.

```suggestion
replacement code here
```
````

### Important rules

- Do NOT use `--input` with a temp file. Build the JSON inline.
- The `path` must be relative to the repo root (e.g. `py/plenish/store.py`, not `/full/path/...`).
- Only comment on lines that are part of the diff (added or modified lines). Do not comment on unchanged code.
- If the code looks good overall, still create the review but add a single top-level comment: "LGTM - code looks good."
- Skip nits if there are fewer than 2 real issues — don't leave noise.
- After posting, print a summary: number of comments posted, severity breakdown, and a link to the PR.
- If posting fails, fall back to printing the review in conversation format.

## Output

After posting, print a short summary to the conversation:

```
Posted N pending review comments on PR #X (Y must-fix, Z should-fix, W nit).
Review: <pr_url>
```
