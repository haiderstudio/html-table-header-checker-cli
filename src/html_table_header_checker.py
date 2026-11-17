#!/usr/bin/env python3
"""Check every <table> in HTML files has header cells.

Run: python3 src/html_table_header_checker.py page.html
     python3 src/html_table_header_checker.py site/
     python3 src/html_table_header_checker.py --stdin < page.html

A table with no <th> is unreadable to a screen reader —
the reader cannot say which column a cell belongs to —
and it looks unlabelled to every sighted reader too.
This tool reads each HTML file, finds every <table>,
and reports each one with no header cells — no <th>
anywhere inside it, and no first row inside a <thead> —
with the file and the line number. It exits 1 when any
table lacks headers, so it can fail a CI run. A file
whose tables all carry headers exits 0.

A table counts as headed when any of these is true:
a <th> cell appears anywhere inside the table, or the
first row of a <thead> exists (a row in <thead> is a
header row even if it is written with <td> cells, as
some authors do). A <th> inside a nested table counts
for the nested table only, never for the outer one.
A <th> after the table closes does not count either.

A file given directly on the command line is always
checked, whatever its name. A folder is walked for
files ending in .html or .htm only, recursively by
default (--no-recursive stops at the top level).
.git folders are never walked, and directory links
are never followed.

Tables inside HTML comments are not tables — the
parser skips them. Markup inside <script> and
<style> blocks is not parsed as HTML either, so a
"<table>" written in a JavaScript string is left
alone. Tag and attribute names are matched without
regard to case, as HTML requires.

It never rewrites a file, never touches the network,
and reads only the files and folders you point it at.
"""

import argparse
import fnmatch
import json
import os
import sys
from html.parser import HTMLParser
from pathlib import Path

__version__ = "1.0.0"

HTML_SUFFIXES = (".html", ".htm")


class TableHeaderParser(HTMLParser):
    """Collect every <table> with no header cells.

    HTMLParser already treats <script> and <style>
    content as character data, so markup written
    inside those blocks never reaches handle_starttag.
    Comments never reach it either.

    A stack holds one frame per open table. A frame
    tracks whether the table has seen a <th>, whether
    it is inside a <thead>, whether it has seen the
    first row of that <thead>, and whether that first
    row held any cell at all. A nested table gets its
    own frame, so its <th> never counts for the outer
    table. An unclosed table is judged when the
    document ends.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.findings = []
        self.stack = []

    def _finish(self, frame):
        if not frame["has_th"] and not frame["thead_first_row"]:
            self.findings.append({
                "line": frame["line"],
                "reason": "has no header cells",
            })

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            line, _offset = self.getpos()
            self.stack.append({
                "line": line,
                "has_th": False,
                "in_thead": False,
                "thead_row_seen": False,
                "thead_first_row": False,
                "in_thead_row": False,
                "thead_row_has_cell": False,
            })
        elif not self.stack:
            return
        elif tag == "thead":
            self.stack[-1]["in_thead"] = True
        elif tag == "tr":
            frame = self.stack[-1]
            if frame["in_thead"] and not frame["thead_row_seen"]:
                frame["in_thead_row"] = True
                frame["thead_row_has_cell"] = False
        elif tag in ("th", "td"):
            frame = self.stack[-1]
            if tag == "th":
                frame["has_th"] = True
            if frame["in_thead_row"]:
                frame["thead_row_has_cell"] = True

    def handle_endtag(self, tag):
        if not self.stack:
            return
        if tag == "table":
            self._finish(self.stack.pop())
        elif tag == "thead":
            self.stack[-1]["in_thead"] = False
        elif tag == "tr":
            frame = self.stack[-1]
            if frame["in_thead_row"]:
                frame["in_thead_row"] = False
                if not frame["thead_row_seen"]:
                    frame["thead_row_seen"] = True
                    frame["thead_first_row"] = frame["thead_row_has_cell"]

    def close(self):
        super().close()
        while self.stack:
            self._finish(self.stack.pop())
        self.findings.sort(key=lambda item: item["line"])


def check_text(text):
    """Check one document's text.

    Returns a list of findings, each {"line": int,
    "reason": str}, in document order.
    """
    parser = TableHeaderParser()
    parser.feed(text)
    parser.close()
    return parser.findings


def check_file(path):
    """Check one file. Returns (findings, error)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], "not valid UTF-8"
    except OSError as exc:
        return [], str(exc)
    try:
        return check_text(text), None
    except Exception as exc:  # malformed markup the parser rejects
        return [], "could not be parsed: %s" % exc


def _is_html_file(path):
    return Path(path).name.lower().endswith(HTML_SUFFIXES)


def collect_files(paths, recursive=True, exclude=None):
    """Expand CLI paths into a sorted list of HTML files.

    A file given directly is always checked, whatever its
    name. A folder is walked for files ending in .html
    or .htm only. .git folders are never walked, and
    directory links are never followed.
    """
    exclude = exclude or []
    found = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            found.append(str(path))
        elif path.is_dir():
            for dirpath, dirs, files in os.walk(path, followlinks=False):
                dirs[:] = [
                    d for d in dirs
                    if d != ".git"
                    and not any(fnmatch.fnmatch(d, pat) for pat in exclude)
                ]
                for name in files:
                    candidate = Path(dirpath) / name
                    if not _is_html_file(candidate):
                        continue
                    if any(
                        fnmatch.fnmatch(str(candidate), pat)
                        or fnmatch.fnmatch(name, pat)
                        for pat in exclude
                    ):
                        continue
                    found.append(str(candidate))
                if not recursive:
                    break
        else:
            raise FileNotFoundError("no such file or folder: %s" % raw)
    seen = set()
    unique = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return sorted(unique)


def format_finding(path, finding):
    """One human-readable line for one table without headers."""
    return ("FAIL %s: <table> line %d %s"
            % (path, finding["line"], finding["reason"]))


def run(paths, recursive=True, exclude=None, as_json=False):
    """Check paths, print the report, return the exit code."""
    try:
        files = collect_files(paths, recursive=recursive, exclude=exclude)
    except FileNotFoundError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if not files:
        print("error: no HTML files found", file=sys.stderr)
        return 2
    results = []
    findings = 0
    files_with_findings = 0
    for path in files:
        bad, error = check_file(path)
        count = len(bad) + (1 if error else 0)
        if count:
            findings += count
            files_with_findings += 1
        results.append({"path": path, "findings": bad, "error": error})
    if as_json:
        print(json.dumps(
            {"files": results, "checked": len(files),
             "findings": findings},
            indent=2))
    else:
        for result in results:
            if result["error"]:
                print("FAIL %s: %s" % (result["path"], result["error"]))
            for finding in result["findings"]:
                print(format_finding(result["path"], finding))
        if findings:
            print("Checked %d file(s), %d table(s) without headers "
                  "in %d file(s)." % (len(files), findings,
                                      files_with_findings))
        else:
            print("OK — %d file(s) checked, every table carries "
                  "headers." % len(files))
    return 1 if findings else 0


def run_stdin(as_json=False):
    """Check one HTML document read from standard input."""
    text = sys.stdin.read()
    bad = check_text(text)
    findings = len(bad)
    if as_json:
        print(json.dumps(
            {"files": [{"path": "<stdin>", "findings": bad,
                        "error": None}],
             "checked": 1, "findings": findings},
            indent=2))
    else:
        for finding in bad:
            print(format_finding("<stdin>", finding))
        if findings:
            print("Checked 1 file(s), %d table(s) without headers "
                  "in 1 file(s)." % findings)
        else:
            print("OK — 1 file(s) checked, every table carries "
                  "headers.")
    return 1 if findings else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="html_table_header_checker",
        description="Check every <table> in HTML files has "
                    "header cells, fail CI when one does not.")
    parser.add_argument("paths", nargs="*",
                        help="HTML files or folders to walk")
    parser.add_argument("--no-recursive", action="store_true",
                        help="do not walk into subfolders")
    parser.add_argument("--exclude", action="append", default=[],
                        help="skip files or folders matching this pattern "
                             "(repeatable)")
    parser.add_argument("--json", action="store_true",
                        help="print the result as JSON")
    parser.add_argument("--stdin", action="store_true",
                        help="check one HTML document from standard input")
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__)
    args = parser.parse_args(argv)
    if args.stdin:
        if args.paths:
            parser.error("--stdin takes no file or folder arguments")
        return run_stdin(as_json=args.json)
    if not args.paths:
        parser.error("give at least one HTML file or folder")
    return run(args.paths, recursive=not args.no_recursive,
               exclude=args.exclude, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
