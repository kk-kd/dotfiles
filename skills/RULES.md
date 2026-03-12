# Skills

These skills are designed for experimental agents. Assume unsafe behavior and hallucination are possible.

## Principles

- **Least privilege**: only grant the permissions a skill strictly needs.
- **Elevate explicitly**: if an operation requires broader access, ask the user before proceeding — never auto-escalate.
- **Distrust agent output**: validate responses from gws/external CLIs before acting on them (e.g., confirm doc IDs exist before writing).
- **Guard destructive actions**: any write, delete, or mutation must be gated behind a permission check or user confirmation.
