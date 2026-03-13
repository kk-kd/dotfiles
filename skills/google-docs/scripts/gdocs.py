#!/usr/bin/env python3
"""Google Docs CLI wrapper around gws with permission enforcement."""

import json
import logging
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

TRACKING_FILE = Path.home() / ".claude" / "google-docs-created.txt"
DOC_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
SAFE_SOURCE_DIRS = (Path("/tmp"), Path(tempfile.gettempdir()))
MAX_STDERR_LEN = 200

log = logging.getLogger("gdocs")
logging.basicConfig(level=logging.INFO, format="%(message)s")


# --- Validation ---


def validate_doc_id(doc_id: str) -> None:
    """Validate a doc ID matches the expected format."""
    if not DOC_ID_PATTERN.match(doc_id):
        print(f"Error: invalid doc ID format: {doc_id!r}", file=sys.stderr)
        sys.exit(1)


def validate_source_path(path: str) -> Path:
    """Validate that a markdown source path is safe to read.

    Rejects absolute paths outside safe dirs and path traversal.
    """
    source = Path(path).resolve()

    if ".." in Path(path).parts:
        print(f"Error: path traversal not allowed: {path}", file=sys.stderr)
        sys.exit(1)

    in_safe_dir = any(
        source == safe_dir or safe_dir in source.parents
        for safe_dir in SAFE_SOURCE_DIRS
    )
    cwd = Path.cwd().resolve()
    in_cwd = source == cwd or cwd in source.parents

    if not (in_safe_dir or in_cwd):
        print(
            f"Error: source path must be under cwd or temp dir: {path}",
            file=sys.stderr,
        )
        sys.exit(1)

    return source


# --- Tracking ---


def load_allowed_ids() -> set[str]:
    """Load the set of doc IDs we're allowed to edit."""
    if not TRACKING_FILE.exists():
        return set()
    return {
        line.strip()
        for line in TRACKING_FILE.read_text().splitlines()
        if line.strip()
    }


def append_doc_id(doc_id: str) -> None:
    """Append a doc ID to the tracking file."""
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TRACKING_FILE.open("a") as fh:
        fh.write(f"{doc_id}\n")
    TRACKING_FILE.chmod(0o600)


def is_allowed(doc_id: str) -> bool:
    """Check if a doc ID is in the tracking file."""
    return doc_id in load_allowed_ids()


# --- gws helpers ---


def _gws_env() -> dict[str, str]:
    """Build env for gws, removing service account creds that block OAuth."""
    import os

    env = os.environ.copy()
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    return env


def run_gws(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a gws command and return the result."""
    result = subprocess.run(
        ["gws", *args],
        capture_output=True,
        text=True,
        env=_gws_env(),
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()[:MAX_STDERR_LEN]
        print(f"gws error: {stderr}", file=sys.stderr)
        sys.exit(result.returncode)
    return result


# --- Markdown parsing ---


@dataclass
class TextSegment:
    """A segment of text with formatting metadata."""

    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    heading_level: int = 0  # 0 = not a heading, 1-6 = H1-H6
    list_type: str = ""  # "", "BULLET", "NUMBERED"


@dataclass
class ParsedDocument:
    """A parsed markdown document ready for Google Docs conversion."""

    segments: list[TextSegment] = field(default_factory=list)


def parse_inline(text: str) -> list[TextSegment]:
    """Parse inline markdown formatting (bold, italic, code)."""
    segments: list[TextSegment] = []
    pattern = re.compile(
        r"(`[^`]+`)"  # inline code
        r"|(\*\*[^*]+\*\*)"  # bold
        r"|(\*[^*]+\*)"  # italic
    )
    last_end = 0

    for match in pattern.finditer(text):
        # Plain text before this match
        if match.start() > last_end:
            plain = text[last_end : match.start()]
            if plain:
                segments.append(TextSegment(text=plain))

        if match.group(1):  # code
            segments.append(TextSegment(text=match.group(1)[1:-1], code=True))
        elif match.group(2):  # bold
            segments.append(TextSegment(text=match.group(2)[2:-2], bold=True))
        elif match.group(3):  # italic
            segments.append(TextSegment(text=match.group(3)[1:-1], italic=True))

        last_end = match.end()

    # Trailing plain text
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            segments.append(TextSegment(text=remaining))

    if not segments and text:
        segments.append(TextSegment(text=text))

    return segments


def parse_markdown(content: str) -> ParsedDocument:
    """Parse markdown content into segments."""
    doc = ParsedDocument()
    lines = content.split("\n")
    idx = 0

    while idx < len(lines):
        line = lines[idx]

        # Skip empty lines
        if not line.strip():
            idx += 1
            continue

        # Headings
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            for seg in parse_inline(text):
                seg.heading_level = level
                doc.segments.append(seg)
            doc.segments.append(TextSegment(text="\n"))
            idx += 1
            continue

        # Bullet lists
        bullet_match = re.match(r"^[\-\*]\s+(.+)$", line)
        if bullet_match:
            text = bullet_match.group(1)
            for seg in parse_inline(text):
                seg.list_type = "BULLET"
                doc.segments.append(seg)
            doc.segments.append(TextSegment(text="\n"))
            idx += 1
            continue

        # Numbered lists
        numbered_match = re.match(r"^\d+\.\s+(.+)$", line)
        if numbered_match:
            text = numbered_match.group(1)
            for seg in parse_inline(text):
                seg.list_type = "NUMBERED"
                doc.segments.append(seg)
            doc.segments.append(TextSegment(text="\n"))
            idx += 1
            continue

        # Code blocks
        if line.strip().startswith("```"):
            idx += 1
            code_lines: list[str] = []
            while idx < len(lines) and not lines[idx].strip().startswith("```"):
                code_lines.append(lines[idx])
                idx += 1
            idx += 1  # skip closing ```
            code_text = "\n".join(code_lines)
            if code_text:
                doc.segments.append(TextSegment(text=code_text, code=True))
                doc.segments.append(TextSegment(text="\n"))
            continue

        # Regular paragraph
        for seg in parse_inline(line):
            doc.segments.append(seg)
        doc.segments.append(TextSegment(text="\n"))
        idx += 1

    return doc


# --- Google Docs batch update builder ---


def build_batch_update(doc: ParsedDocument) -> dict:
    """Build a Google Docs batchUpdate request from parsed markdown.

    Strategy: insert all text first, then apply styles in reverse order
    to avoid index shifting.
    """
    # Build the full plain text and track ranges
    full_text = ""
    ranges: list[tuple[int, int, TextSegment]] = []

    for segment in doc.segments:
        start = len(full_text) + 1  # +1 for 1-based Google Docs index
        full_text += segment.text
        end = len(full_text) + 1
        ranges.append((start, end, segment))

    requests: list[dict] = []

    # Insert all text at index 1 (start of document body)
    if full_text:
        requests.append(
            {
                "insertText": {
                    "location": {"index": 1},
                    "text": full_text,
                }
            }
        )

    # Apply formatting in reverse order to preserve indices
    for start, end, segment in reversed(ranges):
        if segment.text == "\n":
            continue

        # Find the newline that ends this segment's paragraph
        para_end = end
        # Look ahead for the newline
        for next_start, next_end, next_seg in ranges:
            if next_start == end and next_seg.text == "\n":
                para_end = next_end
                break

        # Heading styles
        if segment.heading_level > 0:
            style_name = f"HEADING_{segment.heading_level}"
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": {
                            "startIndex": start,
                            "endIndex": para_end,
                        },
                        "paragraphStyle": {"namedStyleType": style_name},
                        "fields": "namedStyleType",
                    }
                }
            )

        # List styles
        if segment.list_type:
            requests.append(
                {
                    "createParagraphBullets": {
                        "range": {
                            "startIndex": start,
                            "endIndex": para_end,
                        },
                        "bulletPreset": (
                            "NUMBERED_DECIMAL_ALPHA_ROMAN"
                            if segment.list_type == "NUMBERED"
                            else "BULLET_DISC_CIRCLE_SQUARE"
                        ),
                    }
                }
            )

        # Text styles
        text_style: dict = {}
        if segment.bold:
            text_style["bold"] = True
        if segment.italic:
            text_style["italic"] = True
        if segment.code:
            text_style["weightedFontFamily"] = {
                "fontFamily": "Courier New",
                "weight": 400,
            }

        if text_style:
            field_names = []
            if segment.bold:
                field_names.append("bold")
            if segment.italic:
                field_names.append("italic")
            if segment.code:
                field_names.append("weightedFontFamily")

            requests.append(
                {
                    "updateTextStyle": {
                        "range": {
                            "startIndex": start,
                            "endIndex": end,
                        },
                        "textStyle": text_style,
                        "fields": ",".join(field_names),
                    }
                }
            )

    return {"requests": requests}


# --- Subcommands ---


def cmd_create(title: str) -> None:
    """Create a new Google Doc."""
    body = json.dumps({"title": title})
    result = run_gws(["docs", "documents", "create", "--json", body])
    output = result.stdout.strip()
    print(output)

    # Parse doc ID from JSON response
    try:
        data = json.loads(output)
        doc_id = data.get("documentId", "")
        if doc_id:
            append_doc_id(doc_id)
            print(f"Tracked doc ID: {doc_id}", file=sys.stderr)
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"Warning: could not parse doc ID from response: {exc}", file=sys.stderr)


def cmd_read(doc_id: str) -> None:
    """Read a Google Doc."""
    params = json.dumps({"documentId": doc_id})
    result = run_gws(["docs", "documents", "get", "--params", params])
    print(result.stdout.strip())


def cmd_write(doc_id: str, markdown_source: str | None = None) -> None:
    """Write markdown content to a Google Doc."""
    if not is_allowed(doc_id):
        print(
            f"Error: doc {doc_id} is not in the allowed list.\n"
            "Use 'allow <doc_id>' after getting user permission.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Read markdown from file or stdin
    if markdown_source and markdown_source != "-":
        source_path = validate_source_path(markdown_source)
        content = source_path.read_text()
    else:
        content = sys.stdin.read()

    if not content.strip():
        print("Error: no content to write", file=sys.stderr)
        sys.exit(1)

    # Confirmation step
    source_label = str(markdown_source) if markdown_source else "stdin"
    print(
        f"About to write to doc {doc_id}\n"
        f"  Source: {source_label}\n"
        f"  Content length: {len(content)} chars",
        file=sys.stderr,
    )
    if sys.stdin.isatty():
        answer = input("Proceed? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.", file=sys.stderr)
            sys.exit(1)

    doc = parse_markdown(content)
    batch = build_batch_update(doc)
    batch["documentId"] = doc_id

    # Write batch update JSON to a temp file and pass to gws
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmp:
        json.dump(batch, tmp)
        tmp_path = tmp.name

    try:
        params = json.dumps({"documentId": doc_id})
        result = run_gws([
            "docs",
            "documents",
            "batchUpdate",
            "--params",
            params,
            "--json",
            f"@{tmp_path}",
        ])
        print(result.stdout.strip())
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def cmd_allow(doc_id: str) -> None:
    """Allow editing a doc by adding its ID to the tracking file."""
    if is_allowed(doc_id):
        print(f"Doc {doc_id} is already allowed.")
        return
    append_doc_id(doc_id)
    timestamp = datetime.now(timezone.utc).isoformat()
    log.info(f"[{timestamp}] Allowed doc: {doc_id}")
    print(f"Doc {doc_id} added to allowed list.")


# --- Main ---

USAGE = """\
Usage: gdocs.sh <command> [args]

Commands:
  create <title>                   Create a new Google Doc
  read <doc_id>                    Read a Google Doc
  write <doc_id> [markdown_file]   Write markdown to a Google Doc (or stdin)
  allow <doc_id>                   Allow editing a doc you didn't create\
"""


def main() -> None:
    """Entry point."""
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < 3:
            print("Usage: gdocs.sh create <title>", file=sys.stderr)
            sys.exit(1)
        cmd_create(sys.argv[2])

    elif command == "read":
        if len(sys.argv) < 3:
            print("Usage: gdocs.sh read <doc_id>", file=sys.stderr)
            sys.exit(1)
        validate_doc_id(sys.argv[2])
        cmd_read(sys.argv[2])

    elif command == "write":
        if len(sys.argv) < 3:
            print("Usage: gdocs.sh write <doc_id> [markdown_file]", file=sys.stderr)
            sys.exit(1)
        doc_id = sys.argv[2]
        validate_doc_id(doc_id)
        source = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_write(doc_id, source)

    elif command == "allow":
        if len(sys.argv) < 3:
            print("Usage: gdocs.sh allow <doc_id>", file=sys.stderr)
            sys.exit(1)
        validate_doc_id(sys.argv[2])
        cmd_allow(sys.argv[2])

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
