#!/usr/bin/env python3
"""Reduce a CTPB competition HTML fixture to what the parser tests assert.

The page saved from CTPB is a whole season's results: 5.5 MB, 155 408 lines,
9 000 rows. The parser tests read that file, and re-parsing it costs about 53
seconds each time — the suite took ten minutes because of it.

The tests need a fraction of it: the page head and its metadata (season, page
title), the first game of the file, every phase letter, at least two series, and
at least one incomplete game. So this keeps:

  - the head, verbatim, up to the first game row;
  - one game row per (series, phase letter) pair;
  - the first game row, and one incomplete row;
  - for each kept row, the context row that gives it its championship
    (<td colspan="7">, then the column header).

Everything else — the other 7 500 game rows and the spacers between them — goes.

Run it against the saved page to rebuild the fixture:

    python3 scripts/reduce_html_fixture.py <saved.html> <fixture.html>

The output is deterministic: running it on the same page twice gives the same
file, which is what lets the fixture live in the repository instead of being
regenerated on every clone.
"""
import re
import sys
from pathlib import Path

CONTEXT_KEYS = ("Trinquet", "Place Libre", "Main Nue", "Groupe")
SERIES = ("1ère Série", "2ème Série", "3ème Série", "4ème série",
          "1.Maila", "2.Maila", "3.Maila", "4.Maila")
PHASE_RE = re.compile(r"\b([PBHQDF])\s+(\d+)\b")
INCOMPLETE_RE = re.compile(r"class=\"[^\"]*forfait|>\s*(FG|P)\s*/|/\s*(FG|P)\s*<")

HEADER_COMMENT = """<!--
  Reduced CTPB results page, kept for the parser tests.

  The page saved from the site holds a whole season: 5.5 MB and 7 592 game rows,
  and each test re-parsing it cost about 53 seconds. This file carries what the
  tests assert — the head and its metadata, the first game, every phase letter,
  two series and an incomplete game — and nothing else.

  Regenerate it with backend/scripts/reduce_html_fixture.py.
-->
"""


def text_of(block: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", block).split())


def series_of(context: str) -> str:
    for series in SERIES:
        if series in context:
            return series
    return ""


def reduce_html(html: str) -> str:
    parts = re.split(r"(<tr>.*?</tr>)", html, flags=re.S)

    keys = set()
    first_row_seen = False
    incomplete = False
    in_head = True
    context_block = None
    column_block = None
    kept = [HEADER_COMMENT]

    for part in parts:
        is_row = part.startswith("<tr>")

        if not is_row or 'class="L0"' not in part:
            if in_head:
                kept.append(part)
                continue
            if is_row and 'colspan="7"' in part and any(k in text_of(part) for k in CONTEXT_KEYS):
                context_block, column_block = part, None
            elif is_row and context_block is not None and column_block is None:
                column_block = part
            continue

        in_head = False
        match = PHASE_RE.search(text_of(part))
        key = (series_of(text_of(context_block or "")), match.group(1) if match else "?")

        keep = not first_row_seen or key not in keys
        first_row_seen = True
        keys.add(key)
        if not incomplete and INCOMPLETE_RE.search(part):
            incomplete = True
            keep = True

        if keep:
            kept.extend(x for x in (context_block, column_block, part) if x)

    return "".join(kept)


def main() -> int:
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    reduced = reduce_html(source.read_text(encoding="utf-8"))
    target.write_text(reduced, encoding="utf-8")
    print(f"{source.name}: {source.stat().st_size / 1e6:.2f} Mo -> "
          f"{target.name}: {target.stat().st_size / 1024:.1f} Ko")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
