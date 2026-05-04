---
name: sec-a
description: Perform a security audit on an agent skill. Use when the user asks to audit, review, or security-check a skill in `~/.claude/skills/` or any skill directory. Argument is the skill name or full path to the skill directory.
---

Perform a security audit on the agent skill at: $ARGUMENTS

Resolve the path: if it's a skill name, look under `skills/<name>/`. If it's a full path, use it directly. The skill directory must contain a SKILL.md file — if it doesn't, stop and tell the user this isn't a valid skill.

---

## Audit scope

Read **all files** in the skill directory — SKILL.md, scripts, configs, everything. Then evaluate against each category below.

### 1. Permission & privilege

- Does the skill follow least-privilege? Does it request only the permissions it needs?
- Are there any auto-escalation paths (gaining broader access without user confirmation)?
- Does it gate destructive actions (write, delete, mutation) behind explicit permission checks?
- Are file/directory access patterns scoped narrowly or overly broad?

### 2. Input validation & injection

- Are user inputs sanitized before being passed to shell commands, APIs, or file paths?
- Is there risk of **command injection** (unsanitized input in `subprocess`, `os.system`, backticks, `eval`)?
- Is there risk of **path traversal** (e.g., `../../etc/passwd` via user-controlled paths)?
- Are API responses validated before being used in subsequent operations?
- Are there any `eval()`, `exec()`, or dynamic code execution patterns?

### 3. Secrets & credentials

- Are any secrets, tokens, API keys, or credentials hardcoded?
- Are credential files stored with appropriate permissions (not world-readable)?
- Could the skill leak secrets through logs, error messages, or temp files?
- Are temp files created securely (using `tempfile` or equivalent, not predictable paths)?

### 4. Data flow & exfiltration

- Can the skill send data to external services? If so, is this scoped and documented?
- Could a malicious input cause the skill to exfiltrate local file contents?
- Are there any network calls that aren't strictly necessary for the skill's purpose?
- Is stdout/stderr output sanitized to avoid leaking sensitive context?

### 5. Error handling & failure modes

- Do errors fail safely (deny access, stop execution) rather than fail open?
- Are exceptions caught specifically, not with bare `except:`?
- Could error messages reveal internal paths, credentials, or system info?
- Are external CLI/API failures handled gracefully?

### 6. RULES.md compliance

- Check the skill against all principles in `skills/RULES.md`.
- Flag any violations with the specific principle violated.

### 7. Prompt injection & agent safety

- Could malicious content in external data (e.g., a fetched document) inject instructions into the agent's context?
- Does the skill process untrusted text that could be interpreted as agent commands?
- Are there adequate boundaries between data and instructions?

---

## Output format

```markdown
## Security Audit: [Skill Name]

**Audit date**: [date]
**Files reviewed**: [list all files examined]

### 🔴 Critical Issues
- [Issues that must be fixed before use — active vulnerabilities]

### 🟡 Warnings
- [Issues that should be fixed — potential vulnerabilities or bad practices]

### 🟢 Observations
- [Minor suggestions or hardening opportunities]

### ✅ What's Solid
- [Security measures already in place]

### 📋 Remediation
1. [ ] [Specific, actionable fix for each critical/warning issue]
```

For each issue: describe the vulnerability, reference the file and line, explain the attack scenario, and suggest a fix. Rate severity using 🔴 critical · 🟡 warning · 🟢 nit.

If the skill is clean, say so — don't invent issues.
