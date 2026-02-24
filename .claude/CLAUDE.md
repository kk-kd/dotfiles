# Personal Instructions

## Communication

- Be direct and terse. No fluff, no filler — just answers and code.
- Skip introductions, conclusions, and "here's what I did" summaries unless asked.
- When something is wrong, fix it.
- If you need to explain, keep it to 1-2 sentences max.

## Python

- Type hints on all function signatures and return types. No `Any` unless truly unavoidable.
- Prefer `dataclasses` or `pydantic` models over raw dicts.
- Use `pytest` for all testing. Prefer fixtures and parametrize over repetitive test functions.
- Format with `ruff` (Black-compatible). Line length 88.
- Google-style docstrings on public functions and classes.
- Prefer f-strings over `.format()` or `%`.
- Prefer `pathlib.Path` over `os.path`.
- Use `loguru` or stdlib `logging` — never bare `print()` for diagnostics.

## Coding Style (General)

- Favor readability over cleverness.
- Small functions that do one thing.
- Meaningful variable names — no single-letter names outside of comprehensions or lambdas.
- Handle errors explicitly. No bare `except:`.
- Prefer early returns to reduce nesting.

## Git & Workflow

- **Conventional commits**: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:`.
- Commit messages are short imperative phrases: `feat: add user auth endpoint`.
- Always squash-merge PRs.
- **Never `git push --force`** unless you are absolutely certain it's safe (e.g., you just rebased your own branch with no one else on it). If unsure, ask me first.
- When working in this dotfiles repo, **always push after making changes**.

## Editor & Environment

- Primary editors: VS Code / Cursor.
- Heavy terminal usage — prefer CLI solutions when appropriate.
- When suggesting shell commands, target macOS / zsh.

## Working Rules

- After editing files, check for errors before considering the task done.
- When creating files, only create what's necessary. Don't scaffold junk.
- Use `ruff check` and `ruff format` before committing Python.
- Never commit secrets, tokens, or credentials.
