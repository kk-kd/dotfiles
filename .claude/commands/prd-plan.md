Generate a prototype plan from a PRD or requirements description using multiple perspectives.

## Arguments

`$ARGUMENTS` is the PRD — a file path, pasted requirements, a Jira ticket, or a verbal description. If empty, ask the user what they want to prototype.

## Process

### 1. Parse the requirements

Read and understand the input. If it's a file path, read it. If it's a Jira ticket ID, fetch it. Distill the core requirements into a clear problem statement.

### 2. Spawn 2 planning agents in parallel

Launch 2 subagents (Agent tool), each tasked with proposing a **different** approach to implementing the requirements. Use `mode: "plan"` so they require plan approval.

Each agent prompt must include:
- The full requirements text
- Instruction to propose a concrete implementation plan (file structure, key components, tech choices, trade-offs)
- Instruction to explain the **why** behind their approach and what trade-offs they're making
- Instruction to ask the lead (you) if anything is unclear — do NOT guess
- A note that this is for a **prototype/MVP**, not production — favor speed and simplicity
- Agent A: bias toward the simplest possible solution
- Agent B: bias toward a more structured/extensible solution

### 3. Gather and critique

Once both agents return their plans:
- Summarize each approach in 3-5 bullets
- Compare them: strengths, weaknesses, trade-offs
- Identify areas of agreement (these are likely correct)
- Identify areas of disagreement (these need a decision)

### 4. Synthesize a final plan

Combine the best ideas from both approaches into a single cohesive plan. The final plan should include:
- **Architecture**: high-level structure and key components
- **File list**: specific files to create/modify with a 1-line description each
- **Tech choices**: libraries, patterns, frameworks with brief justification
- **Scope cuts**: what's explicitly NOT included in the MVP
- **Open questions**: anything that needs user input before building

### 5. Present for approval

Show the user:
1. A brief summary of both agent approaches (2-3 bullets each)
2. The synthesized final plan
3. Any open questions

Tell the user: "Review the plan and let me know if you want changes. When ready, run `/prd-build` to start implementation."

## Important

- Do NOT start writing code. This command is planning only.
- If a subagent asks a question you can't answer from the requirements, escalate to the user.
- Keep the final plan concrete and actionable — no vague "we could do X or Y" hedging. Make decisions.
- The plan should be copy-pasteable as input to `/prd-build`.
