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
- **Always use f-strings** — never `.format()`, `%`, or `%s`-style logging. This includes `logger.error(f"...: {exc}")`, not `logger.error("...%s", exc)`.
- Prefer `pathlib.Path` over `os.path`.
- Use `loguru` or stdlib `logging` — never bare `print()` for diagnostics.

## Coding Style (General)

- Favor readability over cleverness.
- Small functions that do one thing.
- Meaningful variable names — no single-letter names outside of comprehensions or lambdas.
- Handle errors explicitly. No bare `except:`.
- Prefer early returns to reduce nesting.
- **Don't make formatting-only changes** (reordering imports, rewrapping lines, adjusting whitespace) unless the linter flags them. Unnecessary formatting diffs make code review harder.
- **Never run `ruff format` on files where you only added a few lines.** Only format files you created from scratch. Running the formatter on existing files creates massive style-only diffs that obscure the real changes.

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

## Dotfiles

- When adding new config files or directories to this repo, **always add a corresponding symlink to `setup.sh`**.

## Shell Commands (CRITICAL)

These rules are **non-negotiable** — violating them causes unskippable confirmation prompts:

1. **NEVER use `$()`, backticks, or `${}` variable expansion in commands.** They all trigger confirmation prompts. Instead:
   - Run `printenv VAR_NAME` in a separate Bash call to read env vars
   - Run `date +%s` etc. in a separate Bash call to get computed values
   - Then use the literal values in the next command
2. **NEVER use `cd` or `source` in compound commands.** Not `cd /foo && cmd`, not `source ~/.zshrc && cmd`. Instead:
   - Use absolute paths: `git -C /path/to/repo diff`
   - Pass full paths to commands: `grep -E '"test"' /full/path/package.json`
   - Read env vars with `printenv` instead of sourcing shell configs

## Working Rules

- After editing files, check for errors before considering the task done.
- When creating files, only create what's necessary. Don't scaffold junk.
- Use `ruff check` and `ruff format` before committing Python.
- Never commit secrets, tokens, or credentials.

## Task Tracking

- For non-trivial tasks, write a `.todo.md` file in the working directory to track progress.
- Use checkbox format: `- [ ] task` / `- [x] done`.
- Update it as you go — check off items when complete, add new ones as they come up.
- Delete the file when all tasks are done.
- This applies to both the lead agent and subagents — each should maintain awareness of the todo list.

## Subagents

Proactively spin off a subagent for any self-contained piece of work that is **independent of the main task** and can run in parallel. Examples:

- Fixing a skill or config file while working on a feature branch.
- Committing or creating a PR while still working on the current task.
- Writing tests while implementing a feature (once the interface is stable).
- Updating docs or CLAUDE.md while doing unrelated code changes.
- Running a security audit or lint fix on a different directory.

**When to subagent vs. do inline**: If the work touches different files/directories and doesn't depend on the main task's output, subagent it. If it's tightly coupled (e.g., needs to see the code you're actively writing), do it inline. Don't spawn agents for single-command tasks (e.g., `gh pr edit`, `git push`) — just run the command inline.

**Always run subagents in the background** (`run_in_background: true`) so the main conversation stays responsive. Only use foreground agents when you absolutely need their result before proceeding.

## Agent Teams

When a task benefits from parallel work (e.g., multi-module features, research from multiple angles, cross-layer changes), create an agent team.

### Team structure

- The **lead** owns coordination: break the work into tasks, assign each task to a specific teammate, and track progress. Do not let teammates self-claim.
- Spawn 3–5 teammates unless the task clearly needs fewer or more.
- Each teammate should own a distinct set of files to avoid merge conflicts.

### Plan approval

- For complicated or risky tasks, **require plan approval** before teammates begin implementation. Include this in the spawn prompt, e.g.: _"Require plan approval before making any changes."_
- Reject plans that lack test coverage, touch files outside their scope, or skip error handling. Provide concrete feedback on rejection so the teammate can revise.
- For straightforward, low-risk tasks (single-file changes, simple tests), skip plan approval to avoid unnecessary overhead.

### Code review

- When a teammate finishes a task, the **lead must review their changes** before marking the task complete.
- Review criteria: correctness, adherence to the coding style in this file, test coverage, no leftover debug code, and no unintended side effects.
- If changes need revision, message the teammate with specific feedback. Do not mark the task complete until the revision lands.

### Worktrees

- **Never spawn subagents with `isolation: "worktree"`.** Worktrees do not work reliably in this environment (venvs/tools disappear, pre-commit hooks fail, leftover worktrees accumulate). Subagents should work in the main repo or on a branch instead.

### Tracking & interjections

- **User interjections are additive, not replacements.** When the user reviews progress mid-task and gives new feedback or prompts, all prior instructions and tasks still apply unless the user explicitly corrects or cancels them.
- At the start of any non-trivial task, use `TaskCreate` to track every commitment from the conversation.
- When the user interjects with new guidance, add it as a new task — do not drop or deprioritize existing tasks.
- Before marking work as done, review the full task list to ensure **all** prior instructions were addressed, not just the most recent ones.
- If unsure whether new guidance replaces or supplements an earlier instruction, ask.

### Workflow

1. Analyze the request and break it into independent, well-scoped tasks.
2. Spawn teammates with detailed prompts that include relevant context (file paths, dependencies, constraints).
3. Assign tasks explicitly — do not rely on self-claiming.
4. For complex tasks, require plan approval and review plans before greenlighting.
5. As teammates finish, review their work and request fixes if needed.
6. After all tasks pass review, synthesize results and clean up branches.
7. Wait for all teammates to finish before proceeding — do not start implementing tasks yourself.
