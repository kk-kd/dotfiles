Build an MVP prototype from an approved plan (typically from `/prd-plan`).

## Arguments

`$ARGUMENTS` is optional — a file path or pasted plan. If empty, use the plan from the current conversation context (assumes `/prd-plan` was run in this session).

## Process

### 1. Load and validate the plan

Read the plan. It should have a file list with descriptions and clear architecture. If the plan is missing or unclear, ask the user to provide one or run `/prd-plan` first.

### 2. Split work into assignments

Break the plan into 2 independent work packages, each owning a distinct set of files. Minimize cross-dependencies. Typical splits:
- By layer (frontend vs backend)
- By feature (feature A vs feature B)
- By concern (core logic vs API/UI surface)

If the project is too small to split meaningfully, use 1 subagent.

### 3. Spawn implementation agents

Launch subagents with `mode: "auto"` and `isolation: "worktree"`. Each agent prompt must include:
- The full plan for context
- Their specific assignment (which files, what to build)
- Interfaces they need to match (shared types, API contracts, function signatures)
- Instruction to ask the lead (you) if anything is unclear — do NOT guess
- Reminder: this is an MVP — working > perfect. Skip tests unless the plan specifies them.

### 4. Gather and integrate

As agents complete:
- Review each agent's output for correctness and adherence to the plan
- If an agent's work has issues, message them with specific feedback to revise
- Once all work passes review, integrate the changes:
  - Check for interface mismatches between the agents' work
  - Resolve any conflicts
  - Wire up any cross-cutting concerns (imports, config, routing)

### 5. Verify

After integration:
- Check that the code runs (build, lint, or a quick smoke test as appropriate)
- Fix any integration issues

### 6. Present the result

Show the user:
- List of files created/modified
- Brief description of what was built
- How to run/test it
- Known limitations or next steps

## Important

- Stick to the plan. Do NOT redesign or add scope.
- If you discover the plan has a gap that blocks implementation, ask the user rather than improvising.
- Each agent should own distinct files — no two agents editing the same file.
- Favor working code over clean code. This is a prototype.
