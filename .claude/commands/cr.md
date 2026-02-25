Review the code I've selected or the current file for:

If I provide a branch name, run this git workflow before doing the review/comparison:

1. Update remote refs:
   - `git fetch --all --prune`
2. Ensure `main` is up to date with `origin/main`:
   - `git checkout main`
   - `git pull --ff-only origin main`
3. Ensure the provided branch is up to date with its remote:
   - `git checkout <branch>`
   - `git pull --ff-only origin <branch>`
4. Compare against updated `main` (from branch or main):
   - `git diff main...<branch>`
   - optionally: `git log --oneline --left-right main...<branch>`

Do not compare until both `main` and `<branch>` have been updated.

1. **Bugs & logic errors** — anything that would break at runtime or produce wrong results.
2. **Security issues** — injection, hardcoded secrets, unsafe deserialization, etc.
3. **Performance** — unnecessary allocations, N+1 queries, blocking calls in async code.
4. **Readability** — unclear naming, overly clever code, missing type hints or docstrings.
5. **Design** — violations of SRP, tight coupling, missing abstractions.

For each issue found:

- State the problem in one line.
- Show the fix as a code diff.
- Rate severity: 🔴 must-fix, 🟡 should-fix, 🟢 nit.

If the code looks good, say so briefly and move on.
