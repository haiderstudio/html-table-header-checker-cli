# html-table-header-checker-cli

Check every `<table>` in HTML files has header cells — fail CI when one does not.

[![CI](https://github.com/haiderstudio/html-table-header-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/html-table-header-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`html_table_header_checker` reads each HTML file,
finds every `<table>`, and reports each one with no
header cells — no `<th>` anywhere inside it, and no
first row inside a `<thead>` — with the file and the
line number. It exits 1 when any table lacks headers,
so it can fail a CI run. A file whose tables all
carry headers exits 0.

- A table with no `<th>` is unreadable to a screen
  reader — the reader cannot say which column a cell
  belongs to — and it looks unlabelled to every
  sighted reader too. This names the exact line, and
  the fix is a few tags per table.
- A table counts as headed when a `<th>` cell appears
  anywhere inside it, or when the first row of a
  `<thead>` exists — a row in `<thead>` is a header
  row even if it is written with `<td>` cells, as
  some authors do. An empty first row in `<thead>`
  does not count, and a later row does not replace
  it.
- A `<th>` inside a nested table counts for the
  nested table only, never for the outer one, and a
  `<th>` after the table closes does not count
  either.
- A file given directly on the command line is always
  checked, whatever its name. A folder is walked for
  files ending in `.html` or `.htm` only, recursively
  by default (`--no-recursive` stops at the top
  level). `.git` folders are never walked, and
  directory links are never followed.
- `--json` prints the result as JSON, and `--stdin`
  checks one HTML document read from standard input.
- Tables inside HTML comments are not tables — the
  parser skips them. Markup inside `<script>` and
  `<style>` blocks is not parsed as HTML either, so
  a `"<table>"` written in a JavaScript string or a
  stylesheet is left alone. Tag and attribute names
  are matched without regard to case, as HTML
  requires — `<TABLE>` and `<TH>` are checked
  exactly like `<table>` and `<th>`.

## Who it is for

Every site owner with a data table — a price list, a
schedule, a comparison table, a results table. One
table with no headers and a screen reader user
cannot tell which column a cell belongs to, and the
fix is a few tags once the table is found. This is
the gate that stops it at the pull request.

## What it does NOT do

- It does not check Markdown tables. That is repo
  #68, markdown-table-checker-cli — Markdown tables
  are different files.
- It does not check the page title. That is repo
  #50, html-title-checker-cli — the title is a
  different check on the same pages.
- It does not check whether the header text is
  meaningful — a `<th>` that says "Column 1" passes.
  Meaningful wording is a human judgement, not a
  check this tool can run.
- It never rewrites a file, and it never touches the
  network.

## How this differs

- A fresh search of GitHub on Nov 15, 2026 found 0
  results for `"html-table-header-checker-cli"` and 2
  results for `html table header checker` —
  prantho-kumer/HTML-CSS-JS, 1 star, a coursework
  page that merely contains a table, and
  ManojKumarPatnaik/Major-project-list, 262 stars, a
  list of practice projects for students, not a
  checker of any kind.
- No rival checks table headers in local files.

## Install

```sh
git clone https://github.com/haiderstudio/html-table-header-checker-cli.git
cd html-table-header-checker-cli
```

There is nothing else to install: Python 3.10 or newer,
standard library only, no dependencies.

## Usage

Check one HTML file:

```sh
python3 src/html_table_header_checker.py page.html
```

A file whose tables all carry headers passes:

```sh
$ python3 src/html_table_header_checker.py examples/clean.html
OK — 1 file(s) checked, every table carries headers.
```

A file with tables missing headers fails, with the
file and line for each one:

```sh
$ python3 src/html_table_header_checker.py examples/flagged.html
FAIL examples/flagged.html: <table> line 5 has no header cells
FAIL examples/flagged.html: <table> line 9 has no header cells
FAIL examples/flagged.html: <table> line 12 has no header cells
Checked 1 file(s), 3 table(s) without headers in 1 file(s).
```

Check a whole folder (`.html` / `.htm` files only):

```sh
$ python3 src/html_table_header_checker.py examples/
FAIL examples/flagged.html: <table> line 5 has no header cells
FAIL examples/flagged.html: <table> line 9 has no header cells
FAIL examples/flagged.html: <table> line 12 has no header cells
Checked 3 file(s), 3 table(s) without headers in 1 file(s).
```

Check one document from standard input:

```sh
$ printf '<table><tr><td>x</td></tr></table>\n' | python3 src/html_table_header_checker.py --stdin
FAIL <stdin>: <table> line 1 has no header cells
Checked 1 file(s), 1 table(s) without headers in 1 file(s).
```

Machine-readable output:

```sh
$ python3 src/html_table_header_checker.py --json examples/flagged.html
{
  "files": [
    {
      "path": "examples/flagged.html",
      "findings": [
        {
          "line": 5,
          "reason": "has no header cells"
        },
        {
          "line": 9,
          "reason": "has no header cells"
        },
        {
          "line": 12,
          "reason": "has no header cells"
        }
      ],
      "error": null
    }
  ],
  "checked": 1,
  "findings": 3
}
```

Exit codes: 0 when every table carries headers, 1
when any table lacks them or a file cannot be read, 2
for a usage error (a missing path, a bad flag, or no
HTML files found).

## Examples

A table in a comment and a table written inside a
script string are not tables, and `examples/clean.html`
holds both — it passes:

```sh
$ python3 src/html_table_header_checker.py examples/clean.html
OK — 1 file(s) checked, every table carries headers.
```

Uppercase tags, a `<th>` split across lines, and a
`<thead>` first row written with `<td>` are all
handled — `examples/edge.html` has all of them, and
it passes:

```sh
$ python3 src/html_table_header_checker.py examples/edge.html
OK — 1 file(s) checked, every table carries headers.
```

A table whose `<thead>` is empty still fails — an
empty header section is not a header:

```sh
$ printf '<table><thead></thead><tbody><tr><td>x</td></tr></tbody></table>\n' | python3 src/html_table_header_checker.py --stdin
FAIL <stdin>: <table> line 1 has no header cells
Checked 1 file(s), 1 table(s) without headers in 1 file(s).
```

Run every bundled example at once with `sh
examples/run-example.sh` — the output is saved in
[examples/sample-output.md](examples/sample-output.md).

## How it is tested

```sh
python3 tests/test_html_table_header_checker.py
```

The tests cover table detection (a table with a
`<th>` passes, a table with no headers fails, a
`<th>` in `<thead>` passes, a `<thead>` first row
written with `<td>` passes, an empty `<thead>` fails,
a `<thead>` with no rows fails, an empty first
`<thead>` row fails even when the second row has
cells, a second `<thead>` row does not count, a
`<th>` in `<tbody>` passes, a `<th>` after the table
closes does not count, several tables in one file in
document order, an uppercase `<TABLE>` and `<TH>`, a
`<th>` with a scope attribute, a table on the same
line as other markup, a table split across lines
reports the line the tag starts on, a file with no
tables passes, an empty document passes, an unclosed
table still checked, an unclosed table with a
`<th>` passes, a nested table whose inner `<th>`
does not count for the outer table, nested tables
both headed pass, a nested table without headers
fails), skipping (a table in a comment, a table in
a script string, a table in a style block, a real
table after a script checked, unclosed tags
elsewhere in the file), the CLI (exit 0/1/2, folder
walking for several HTML files including `.htm`,
nested folders, `--no-recursive`, `--exclude`,
`.git` skipped, a direct file checked whatever its
name, duplicate paths checked once, `--json`
output, `--stdin`, bad flags, missing paths, empty
folders, `--version`, a non-UTF-8 file reported,
input files left unchanged, the tool run from
another folder and under a changed HOME), the
bundled examples (sample output compared byte-for-byte
against a fresh run, and the README-quoted outputs
checked against it), and hygiene checks (no
placeholder text, no absolute paths, no real secrets
outside the tests and examples, stdlib imports only,
no network use in the source, `.env` first in
`.gitignore`, CI file runs the test file, README
names the neighbouring repos).

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The
idea of checking table headers is not new, and the
parsing follows Python's own standard-library HTML
parser — but no existing tool does this one job,
checking that every table in local HTML files carries
header cells, as a tested command-line gate with a CI
exit code, as the search above shows — and every
line of code here is original, built on nothing but
Python's standard library.
