# logkit

A small library and CLI for making sense of plain-text log files
without dragging in a log aggregation stack for a one-off question
like "how many errors happened last night" or "show me everything
between these two timestamps".

Most ad-hoc log digging ends up as a pile of `grep`/`awk` one-liners
that don't understand timestamps or log levels as anything more than
text. logkit understands enough structure to filter by level and by
time range, and reads `.gz` files transparently, while staying small
enough to read in one sitting.

## Install

No dependencies beyond the Python standard library. Clone it and run
it in place, or install it with pip:

```
pip install -e .
```

## CLI usage

Count lines by level:

```
$ logkit tally app.log
ERROR     12
WARNING   47
INFO      930
total     989
```

Filter by level, time range, or a regex, in any combination:

```
$ logkit grep app.log --level ERROR
$ logkit grep app.log --since 2026-09-06T00:00:00 --until 2026-09-06T06:00:00
$ logkit grep app.log --match "connection (reset|refused)"
```

`.gz` files work the same way as plain text:

```
$ logkit tally app.log.2.gz
```

## Library usage

```python
from logkit import parse_line

entry = parse_line("2026-09-06 03:14:07,123 ERROR worker: connection refused")
entry.timestamp   # datetime(2026, 9, 6, 3, 14, 7, 123000)
entry.level       # "ERROR"
entry.raw         # the original line, newline stripped
```

`parse_line` recognizes ISO 8601 / Python-logging-style timestamps
and classic syslog timestamps (which have no year, so the current
year is assumed). If it can't find a timestamp or level, the
corresponding field is `None` rather than a guess.

## Status

Early. The timestamp and level detection covers the formats I run
into most often, not every format that exists. See the roadmap for
what's planned next.
