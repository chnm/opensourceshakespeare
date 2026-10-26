"""Read rows out of a MySQL/phpMyAdmin SQL dump without a MySQL server.

Handles `INSERT INTO `T` (`a`, `b`) VALUES (...), (...);` statements with
quoted strings ('' and backslash escapes), numbers and NULL. Everything else in
the dump (CREATE TABLE, comments, SET) is skipped.
"""

import re

INSERT_RE = re.compile(r"INSERT INTO `(\w+)` \(([^)]*)\) VALUES\s*")
STRING_CHUNK_RE = re.compile(r"[^'\\]*")
BARE_RE = re.compile(r"[^,)\s]+")
WS_RE = re.compile(r"\s*")
ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "Z": "\x1a"}


def read_tables(path, tables, encoding="latin-1"):
    """Return {table: [row dict, ...]} for the named tables in the dump."""
    with open(path, encoding=encoding) as f:
        sql = f.read()
    result = {name: [] for name in tables}
    pos = 0
    while m := INSERT_RE.search(sql, pos):
        table = m.group(1)
        columns = [c.strip().strip("`") for c in m.group(2).split(",")]
        rows, pos = _parse_values(sql, m.end())
        if table in result:
            result[table].extend(dict(zip(columns, row, strict=True)) for row in rows)
    return result


def _parse_values(s, i):
    """Parse `(...), (...);` starting at s[i]. Return (rows, index after the `;`)."""
    rows = []
    while True:
        i = WS_RE.match(s, i).end()
        if s[i] != "(":
            raise ValueError(f"expected '(' at offset {i}: {s[i:i + 40]!r}")
        i += 1
        row = []
        while True:
            i = WS_RE.match(s, i).end()
            if s[i] == "'":
                value, i = _parse_string(s, i + 1)
            else:
                token = BARE_RE.match(s, i).group()
                i += len(token)
                value = None if token == "NULL" else (float(token) if "." in token else int(token))
            row.append(value)
            i = WS_RE.match(s, i).end()
            if s[i] == ",":
                i += 1
            elif s[i] == ")":
                i += 1
                break
            else:
                raise ValueError(f"unexpected {s[i]!r} at offset {i}")
        rows.append(row)
        i = WS_RE.match(s, i).end()
        if s[i] == ";":
            return rows, i + 1
        if s[i] != ",":
            raise ValueError(f"unexpected {s[i]!r} at offset {i}")
        i += 1


def _parse_string(s, i):
    """Parse a quoted string whose body starts at s[i]. Return (value, index after closing quote)."""
    parts = []
    while True:
        chunk = STRING_CHUNK_RE.match(s, i).group()
        parts.append(chunk)
        i += len(chunk)
        if s[i] == "\\":
            parts.append(ESCAPES.get(s[i + 1], s[i + 1]))
            i += 2
        elif s[i + 1 : i + 2] == "'":  # '' is an escaped quote
            parts.append("'")
            i += 2
        else:
            return "".join(parts), i + 1
