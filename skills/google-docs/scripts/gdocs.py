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
DOC_URL_PATTERN = re.compile(
    r"https?://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)"
)
SAFE_SOURCE_DIRS = (Path("/tmp"), Path(tempfile.gettempdir()))
MAX_STDERR_LEN = 2000

HEADING_MAP = {
    "HEADING_1": "# ",
    "HEADING_2": "## ",
    "HEADING_3": "### ",
    "HEADING_4": "#### ",
    "HEADING_5": "##### ",
    "HEADING_6": "###### ",
}

log = logging.getLogger("gdocs")
logging.basicConfig(level=logging.INFO, format="%(message)s")


# --- Validation ---


def extract_doc_id(doc_id_or_url: str) -> str:
    """Extract a doc ID from a URL or return as-is if already an ID."""
    url_match = DOC_URL_PATTERN.search(doc_id_or_url)
    if url_match:
        return url_match.group(1)
    return doc_id_or_url


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
        stdout = result.stdout.strip()[:MAX_STDERR_LEN]
        print(f"gws error (stderr): {stderr}", file=sys.stderr)
        if stdout:
            print(f"gws error (stdout): {stdout}", file=sys.stderr)
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


def build_batch_update(doc: ParsedDocument, insert_at: int = 1) -> dict:
    """Build a Google Docs batchUpdate request from parsed markdown.

    Strategy: insert all text first, then apply styles in reverse order
    to avoid index shifting.

    Args:
        doc: Parsed markdown document.
        insert_at: 1-based Google Docs body index to insert at.
    """
    # Build the full plain text and track ranges
    full_text = ""
    ranges: list[tuple[int, int, TextSegment]] = []

    for segment in doc.segments:
        start = len(full_text) + insert_at
        full_text += segment.text
        end = len(full_text) + insert_at
        ranges.append((start, end, segment))

    requests: list[dict] = []

    # Insert all text at the specified index
    if full_text:
        requests.append(
            {
                "insertText": {
                    "location": {"index": insert_at},
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


def gdoc_json_to_markdown(data: dict) -> str:
    """Convert Google Docs API JSON response to readable markdown."""
    lines: list[str] = []
    title = data.get("title", "")
    if title:
        lines.append(f"# {title}")
        lines.append("")

    body = data.get("body", {}).get("content", [])
    list_state: dict[str, int] = {}  # nestingLevel -> counter for numbered lists

    for element in body:
        if "paragraph" in element:
            para = element["paragraph"]
            style = para.get("paragraphStyle", {})
            named_style = style.get("namedStyleType", "")
            bullet = para.get("bullet", {})

            # Extract text with inline formatting
            text_parts: list[str] = []
            for elem in para.get("elements", []):
                text_run = elem.get("textRun", {})
                content = text_run.get("content", "")
                ts = text_run.get("textStyle", {})

                # Strip trailing newline (we add our own)
                content = content.rstrip("\n")
                if not content:
                    continue

                # Apply inline formatting
                is_bold = ts.get("bold", False)
                is_italic = ts.get("italic", False)
                font = ts.get("weightedFontFamily", {}).get("fontFamily", "")
                is_code = font in ("Courier New", "Consolas", "Source Code Pro")

                if is_code:
                    content = f"`{content}`"
                if is_bold:
                    content = f"**{content}**"
                if is_italic:
                    content = f"*{content}*"

                text_parts.append(content)

            text = "".join(text_parts).strip()
            if not text:
                lines.append("")
                continue

            # Heading prefix
            heading_prefix = HEADING_MAP.get(named_style, "")
            if heading_prefix:
                lines.append(f"{heading_prefix}{text}")
                lines.append("")
                continue

            # List items
            if bullet:
                nesting = bullet.get("nestingLevel", 0)
                indent = "  " * nesting
                list_id = bullet.get("listId", "")
                # Check if numbered list from the lists metadata
                is_numbered = False
                lists = data.get("lists", {})
                if list_id in lists:
                    list_props = lists[list_id].get("listProperties", {})
                    nesting_levels = list_props.get("nestingLevel", [])
                    if nesting_levels and len(nesting_levels) > nesting:
                        glyph_type = nesting_levels[nesting].get("glyphType", "")
                        if glyph_type and glyph_type != "GLYPH_TYPE_UNSPECIFIED":
                            is_numbered = True

                if is_numbered:
                    key = f"{list_id}:{nesting}"
                    list_state[key] = list_state.get(key, 0) + 1
                    lines.append(f"{indent}{list_state[key]}. {text}")
                else:
                    lines.append(f"{indent}- {text}")
                continue

            # Reset numbered list counters on non-list paragraphs
            list_state.clear()
            lines.append(text)

        elif "table" in element:
            table = element["table"]
            rows_data: list[list[str]] = []
            for row in table.get("tableRows", []):
                cells: list[str] = []
                for cell in row.get("tableCells", []):
                    cell_text = ""
                    for content in cell.get("content", []):
                        if "paragraph" in content:
                            for elem in content["paragraph"].get("elements", []):
                                cell_text += elem.get("textRun", {}).get(
                                    "content", ""
                                )
                    cells.append(cell_text.strip())
                rows_data.append(cells)

            if rows_data:
                # Calculate column widths
                col_count = max(len(r) for r in rows_data)
                col_widths = [0] * col_count
                for row in rows_data:
                    for i, cell in enumerate(row):
                        col_widths[i] = max(col_widths[i], len(cell))

                # Header row
                header = rows_data[0]
                header_line = "| " + " | ".join(
                    cell.ljust(col_widths[i]) for i, cell in enumerate(header)
                ) + " |"
                sep_line = "| " + " | ".join(
                    "-" * col_widths[i] for i in range(col_count)
                ) + " |"
                lines.append(header_line)
                lines.append(sep_line)

                # Data rows
                for row in rows_data[1:]:
                    padded = [
                        (row[i] if i < len(row) else "").ljust(col_widths[i])
                        for i in range(col_count)
                    ]
                    lines.append("| " + " | ".join(padded) + " |")
                lines.append("")

    # Clean up excessive blank lines
    result_lines: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = line.strip() == ""
        if is_blank and prev_blank:
            continue
        result_lines.append(line)
        prev_blank = is_blank

    return "\n".join(result_lines).strip() + "\n"


def cmd_read(doc_id: str) -> None:
    """Read a Google Doc and output as markdown."""
    params = json.dumps({"documentId": doc_id})
    result = run_gws(["docs", "documents", "get", "--params", params])
    raw = result.stdout.strip()

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, KeyError):
        print("Error: failed to parse document response from gws", file=sys.stderr)
        sys.exit(1)

    markdown = gdoc_json_to_markdown(data)
    print("--- BEGIN DOCUMENT CONTENT ---")
    print(markdown, end="")
    print("--- END DOCUMENT CONTENT ---")


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


def _get_doc_json(doc_id: str) -> dict:
    """Fetch the raw Google Docs JSON for a document."""
    params = json.dumps({"documentId": doc_id})
    result = run_gws(["docs", "documents", "get", "--params", params])
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        print("Error: failed to parse document response from gws", file=sys.stderr)
        sys.exit(1)


def _get_doc_end_index(data: dict) -> int:
    """Get the insertion index at the end of the document body."""
    body_content = data.get("body", {}).get("content", [])
    if not body_content:
        return 1
    # Last element's endIndex minus 1 (before the trailing newline)
    return body_content[-1].get("endIndex", 2) - 1


def _find_heading_end_index(data: dict, heading_text: str) -> int | None:
    """Find the end index of the section under a given heading.

    Returns the start index of the next same-or-higher-level heading,
    or the end of the document if the heading is the last section.
    """
    body_content = data.get("body", {}).get("content", [])
    found_level: int | None = None
    heading_text_lower = heading_text.strip().lower()

    for element in body_content:
        para = element.get("paragraph", {})
        style = para.get("paragraphStyle", {})
        named_style = style.get("namedStyleType", "")

        # Extract paragraph text
        para_text = ""
        for elem in para.get("elements", []):
            para_text += elem.get("textRun", {}).get("content", "")
        para_text = para_text.strip().lower()

        # Check if this is a heading
        if named_style.startswith("HEADING_"):
            level = int(named_style.split("_")[1])

            if found_level is not None and level <= found_level:
                # Found the next same-or-higher-level heading — insert before it
                return element.get("startIndex", 1)

            if para_text == heading_text_lower:
                found_level = level

    if found_level is not None:
        # Heading was the last section — append at end of doc
        return _get_doc_end_index(data)

    return None


def cmd_append(
    doc_id: str,
    markdown_source: str | None = None,
    after_heading: str | None = None,
) -> None:
    """Append markdown content to a Google Doc without replacing existing content."""
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
        print("Error: no content to append", file=sys.stderr)
        sys.exit(1)

    # Fetch current document to determine insertion point
    data = _get_doc_json(doc_id)

    if after_heading:
        insert_at = _find_heading_end_index(data, after_heading)
        if insert_at is None:
            print(
                f"Error: heading '{after_heading}' not found in document",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        insert_at = _get_doc_end_index(data)

    # Ensure content starts with a newline for separation
    if not content.startswith("\n"):
        content = "\n" + content

    source_label = str(markdown_source) if markdown_source else "stdin"
    print(
        f"About to append to doc {doc_id}\n"
        f"  Source: {source_label}\n"
        f"  Insert at index: {insert_at}\n"
        f"  Content length: {len(content)} chars",
        file=sys.stderr,
    )
    if sys.stdin.isatty():
        answer = input("Proceed? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.", file=sys.stderr)
            sys.exit(1)

    doc = parse_markdown(content)
    batch = build_batch_update(doc, insert_at=insert_at)
    batch["documentId"] = doc_id

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
  create <title>                                  Create a new Google Doc
  read <doc_id>                                   Read a Google Doc
  write <doc_id> [markdown_file]                  Write markdown to a Google Doc (or stdin)
  append <doc_id> [markdown_file]                 Append markdown to a Google Doc (preserves existing content)
  append <doc_id> [markdown_file] --after "heading"  Append after a specific heading
  allow <doc_id>                                  Allow editing a doc you didn't create\
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
            print("Usage: gdocs.sh read <doc_id_or_url>", file=sys.stderr)
            sys.exit(1)
        doc_id = extract_doc_id(sys.argv[2])
        validate_doc_id(doc_id)
        cmd_read(doc_id)

    elif command == "write":
        if len(sys.argv) < 3:
            print("Usage: gdocs.sh write <doc_id_or_url> [markdown_file]", file=sys.stderr)
            sys.exit(1)
        doc_id = extract_doc_id(sys.argv[2])
        validate_doc_id(doc_id)
        source = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_write(doc_id, source)

    elif command == "append":
        if len(sys.argv) < 3:
            print(
                "Usage: gdocs.sh append <doc_id_or_url> [markdown_file] [--after 'heading']",
                file=sys.stderr,
            )
            sys.exit(1)
        doc_id = extract_doc_id(sys.argv[2])
        validate_doc_id(doc_id)

        # Parse optional --after flag and markdown source
        source = None
        after_heading = None
        idx = 3
        while idx < len(sys.argv):
            if sys.argv[idx] == "--after" and idx + 1 < len(sys.argv):
                after_heading = sys.argv[idx + 1]
                idx += 2
            elif source is None:
                source = sys.argv[idx]
                idx += 1
            else:
                print(f"Warning: unknown argument ignored: {sys.argv[idx]}", file=sys.stderr)
                idx += 1

        cmd_append(doc_id, source, after_heading=after_heading)

    elif command == "allow":
        if len(sys.argv) < 3:
            print("Usage: gdocs.sh allow <doc_id_or_url>", file=sys.stderr)
            sys.exit(1)
        doc_id = extract_doc_id(sys.argv[2])
        validate_doc_id(doc_id)
        cmd_allow(doc_id)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
