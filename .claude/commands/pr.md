Create a pull request for the current branch.

Steps:
1. Run `git log --oneline main..HEAD` (or the default branch) to see commits.
2. Run `git diff main..HEAD --stat` to see changed files.
3. Determine a clear, concise PR title using conventional commit style.
4. Write a PR description with:
   - **What**: 1-2 sentence summary of what changed.
   - **Why**: Motivation or linked issue.
   - **How**: Brief description of approach (only if non-obvious).
   - **Testing**: What was tested and how.
5. Push the branch: `git push -u origin HEAD`.
6. Create the PR using `gh pr create --title "<title>" --body "<body>"`.

If `gh` CLI is not installed, output the title + body and provide the GitHub URL to create it manually.
