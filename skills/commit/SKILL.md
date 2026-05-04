---
name: commit
description: Create a git commit for the work just done. Use when the user asks to commit, says "commit this", or finishes a logical chunk of work and wants it recorded. Stages only files related to the current task — never `git add -A`.
---

Create a commit for the work you just did.

**Critical: Only commit files relevant to your task.** The user may be working on other things in parallel. Never blindly `git add -A`.

Steps:
1. Run `git status` to see all modified/untracked files.
2. Review the list and identify ONLY the files related to the task you were working on. Ignore files that:
   - You didn't create or edit during this task.
   - Belong to a different feature or unrelated change.
   - Are editor artifacts, OS files, or unrelated config changes.
3. Stage only the relevant files: `git add <file1> <file2> ...`
   - If files are already staged, verify they're all relevant. Unstage anything that isn't.
4. Run `git diff --cached` to read the actual changes and confirm they're coherent.
5. Write a **conventional commit** message based on the diff:
   - Format: `type: short imperative description`
   - Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`
   - Keep the subject line under 72 chars.
   - Add a body only if the change is non-obvious (blank line, then wrap at 72 chars).
6. Run `git commit -m "<message>"`.
7. If this is the dotfiles repo, also `git push`.

Do NOT ask for confirmation — just commit.
