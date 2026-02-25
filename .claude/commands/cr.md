Review the code I've selected or the current file.

If I provide a branch name, run this git workflow before reviewing:

1. `git fetch --all --prune`
2. `git checkout main && git pull --ff-only origin main`
3. `git checkout <branch> && git pull --ff-only origin <branch>`
4. `git diff main...<branch>` (optionally `git log --oneline --left-right main...<branch>`)

Do not compare until both `main` and `<branch>` have been updated.

---

## What to check

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

---

## Output format

```markdown
## Code Review: [Brief Summary]

### ✅ What's Working Well
- [Specific positive observations]

### 🔧 Suggested Improvements

#### Code Style
- [Specific issues with line references]

#### Structure/Organization
- [Architectural concerns]

#### Function Placement
- [Separation of concerns issues]

### 📋 Action Items
1. [ ] [Specific, actionable change]
2. [ ] [Another specific change]
```

For each issue: state the problem, show a diff fix, rate severity: 🔴 must-fix · 🟡 should-fix · 🟢 nit.

If the code looks good, say so briefly.
