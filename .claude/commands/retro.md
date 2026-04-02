Analyze this conversation and extract actionable improvements to instructions, memories, and settings.

---

## Step 1: Scan the conversation

Review the entire conversation for:

1. **Corrections** — where the user said "no", "don't", "stop", "not that", or otherwise redirected you.
2. **Confirmations** — where the user approved a non-obvious approach ("yes exactly", "perfect", accepted without pushback).
3. **Repeated patterns** — things the user asked for more than once, or things you kept getting wrong.
4. **New preferences** — explicit or implicit signals about how the user wants to work.
5. **Tool/workflow friction** — places where a tool failed, a command was wrong, or the workflow was clunky.
6. **Missing context** — information you lacked that caused wrong assumptions or extra round-trips.

## Step 2: Categorize findings

Classify each finding by **scope** and **target**:

### Scope

- **Global** — applies across all projects (personal preferences, general coding style, tool behavior). These changes go in the **dotfiles repo** (`~/.claude/CLAUDE.md`, `~/.claude/settings.json`, memory files).
- **Repo-specific** — applies only to the current project (project conventions, architecture decisions, repo-specific commands). These changes go in the **current working directory** (`.claude/CLAUDE.md`, `.claude/settings.json`, `.claude/commands/`).

### Target

| Target | Global location | Repo-specific location |
|--------|----------------|----------------------|
| **Instruction** | `~/.claude/CLAUDE.md` | `.claude/CLAUDE.md` (cwd) |
| **Memory** | `~/.claude/projects/.../memory/` | — |
| **Setting** | `~/.claude/settings.json` | `.claude/settings.json` (cwd) |
| **Skill/Command** | `~/.claude/commands/` | `.claude/commands/` (cwd) |

For each finding, note:
- What happened (brief)
- Why it matters (what went wrong or could be better)
- Scope: global or repo-specific
- Proposed change (specific, actionable)

## Step 3: Present findings

Print all findings grouped by scope, then by target. For each:

```
[scope] [target] summary
  Context: what happened in the conversation
  Proposed: specific change to make
```

Skip findings that are conversation-specific and not generalizable.

If there are no findings, say so and stop.

## Step 4: Get approval

Ask: "Apply these changes? (all / pick / cancel)"

- **all**: apply every proposed change
- **pick**: user will specify which ones to apply
- **cancel**: abort

Do NOT make any changes until the user explicitly approves.

## Step 5: Apply changes

For each approved finding, apply to the correct location based on scope:

- **Global instruction**: Edit `~/.claude/CLAUDE.md`. Don't duplicate existing rules. If a rule already exists but needs strengthening, update it in place. Commit and push in the dotfiles repo.
- **Repo-specific instruction**: Edit `.claude/CLAUDE.md` in the current working directory. Create it if it doesn't exist.
- **Memory**: Write a memory file following the memory system format (frontmatter with name, description, type + content). Update MEMORY.md index.
- **Global setting**: Edit `~/.claude/settings.json`. Commit and push in the dotfiles repo.
- **Repo-specific setting**: Edit `.claude/settings.json` in the current working directory.
- **Global command**: Create/edit in `~/.claude/commands/`. Commit and push in the dotfiles repo.
- **Repo-specific command**: Create/edit in `.claude/commands/` in the current working directory.

After applying, print a summary of what was changed and where.

## Rules

- Be specific. "Be better at X" is not actionable. "Add rule: always run tests after editing py files" is.
- Don't propose changes that duplicate existing rules.
- Don't propose changes for one-off situations that won't recur.
- Prefer updating existing rules over adding new ones.
- When in doubt about whether something is generalizable, leave it out.
- Global changes in the dotfiles repo must be committed and pushed.
- Repo-specific changes are left uncommitted for the user to review.
