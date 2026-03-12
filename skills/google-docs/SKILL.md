---
name: google-docs
description: Create, read, and write Google Docs via gws CLI
---

# Google Docs Skill

All Google Docs operations go through the `gdocs.sh` wrapper script. **Never call `gws` directly.**

## Rules

- You can always **create** and **read** docs.
- You can only **write** to docs that you created (tracked in `~/.claude/google-docs-created.txt`).
- To edit a doc you didn't create, **ask the user for permission first**, then run `allow <doc_id>` before writing.
- Pass markdown content to the `write` command via a temp file or stdin.

## Commands

### Create a new doc
```bash
bash ~/.claude/skills/google-docs/scripts/gdocs.sh create "My Document Title"
```

### Read a doc
```bash
bash ~/.claude/skills/google-docs/scripts/gdocs.sh read <doc_id>
```

### Write markdown content to a doc
```bash
# From a file:
bash ~/.claude/skills/google-docs/scripts/gdocs.sh write <doc_id> /path/to/content.md

# From stdin:
echo "# Hello" | bash ~/.claude/skills/google-docs/scripts/gdocs.sh write <doc_id>
```

### Allow editing a doc you didn't create
```bash
bash ~/.claude/skills/google-docs/scripts/gdocs.sh allow <doc_id>
```

## Supported Markdown

- `# H1` through `###### H6` (heading styles)
- `**bold**` and `*italic*`
- `- item` / `* item` (bullet lists)
- `1. item` (numbered lists)
- `` `code` `` (monospace / Courier New)
- Regular paragraphs
