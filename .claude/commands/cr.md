Review the code I've selected or the current file for:

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
