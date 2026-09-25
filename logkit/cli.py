"""Command-line interface for logkit.

    logkit tally access.log
    logkit grep access.log --level ERROR
    logkit grep access.log --since 2026-09-06T00:00:00 --match timeout
    logkit histogram access.log --interval 1h
    tail -f access.log | logkit grep - --level ERROR
"""
from __future__ import annotations

import argparse
import gzip
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from typing import Iterator, Optional

from .parser import LogLine, parse_line

_INTERVAL_RE = re.compile(r"^(\d+)([smhd])$")
_INTERVAL_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_EPOCH = datetime(1970, 1, 1)


def iter_lines(path: str) -> Iterator[str]:
    if path == "-":
        for line in sys.stdin:
            yield line
        return
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", errors="replace") as handle:
        for line in handle:
            yield line


def iter_log_lines(path: str) -> Iterator[LogLine]:
    for raw in iter_lines(path):
        yield parse_line(raw)


def cmd_tally(args: argparse.Namespace) -> int:
    counts: Counter = Counter()
    total = 0
    unclassified = 0
    for entry in iter_log_lines(args.path):
        total += 1
        if entry.level:
            counts[entry.level] += 1
        else:
            unclassified += 1
    for level in ("CRITICAL", "FATAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"):
        if counts[level]:
            print(f"{level:<9} {counts[level]}")
    if unclassified:
        print(f"{'(none)':<9} {unclassified}")
    print(f"{'total':<9} {total}")
    return 0


def parse_interval(text: str) -> timedelta:
    match = _INTERVAL_RE.match(text.strip())
    if not match:
        raise argparse.ArgumentTypeError(
            f"invalid interval {text!r}, expected e.g. 30s, 15m, 1h, 1d"
        )
    count, unit = match.groups()
    return timedelta(seconds=int(count) * _INTERVAL_UNIT_SECONDS[unit])


def bucket_start(timestamp: datetime, interval: timedelta) -> datetime:
    # Floor against a fixed epoch (not local calendar fields) so buckets
    # line up consistently regardless of interval size.
    elapsed = (timestamp - _EPOCH).total_seconds()
    step = interval.total_seconds()
    return _EPOCH + timedelta(seconds=(elapsed // step) * step)


def _bucket_label_format(interval: timedelta) -> str:
    if interval >= timedelta(days=1):
        return "%Y-%m-%d"
    if interval >= timedelta(hours=1):
        return "%Y-%m-%d %H:00"
    if interval >= timedelta(minutes=1):
        return "%Y-%m-%d %H:%M"
    return "%Y-%m-%d %H:%M:%S"


def cmd_histogram(args: argparse.Namespace) -> int:
    interval = args.interval
    counts: Counter = Counter()
    unclassified = 0
    for entry in iter_log_lines(args.path):
        if entry.timestamp is None:
            unclassified += 1
            continue
        counts[bucket_start(entry.timestamp, interval)] += 1

    label_fmt = _bucket_label_format(interval)
    for start in sorted(counts):
        print(f"{start.strftime(label_fmt)}  {counts[start]}")
    if unclassified:
        print(f"(no timestamp)  {unclassified}")
    return 0


def cmd_grep(args: argparse.Namespace) -> int:
    since = datetime.fromisoformat(args.since) if args.since else None
    until = datetime.fromisoformat(args.until) if args.until else None
    pattern = re.compile(args.match, re.IGNORECASE) if args.match else None

    for entry in iter_log_lines(args.path):
        if args.level and entry.level != args.level.upper():
            continue
        if since and (entry.timestamp is None or entry.timestamp < since):
            continue
        if until and (entry.timestamp is None or entry.timestamp > until):
            continue
        if pattern and not pattern.search(entry.raw):
            continue
        print(entry.raw)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="logkit", description="Inspect and filter log files.")
    sub = parser.add_subparsers(dest="command", required=True)

    tally = sub.add_parser("tally", help="count log lines by level")
    tally.add_argument("path", help="log file to read (.gz is handled transparently)")
    tally.set_defaults(func=cmd_tally)

    grep = sub.add_parser("grep", help="filter log lines")
    grep.add_argument(
        "path", help="log file to read (.gz is handled transparently), or - for stdin"
    )
    grep.add_argument("--level", help="only show this level, e.g. ERROR")
    grep.add_argument("--match", help="only show lines matching this regex")
    grep.add_argument("--since", help="only show lines at or after this ISO timestamp")
    grep.add_argument("--until", help="only show lines at or before this ISO timestamp")
    grep.set_defaults(func=cmd_grep)

    histogram = sub.add_parser("histogram", help="count log lines per time bucket")
    histogram.add_argument("path", help="log file to read (.gz is handled transparently)")
    histogram.add_argument(
        "--interval",
        type=parse_interval,
        default=timedelta(hours=1),
        help="bucket width, e.g. 30s, 15m, 1h, 1d (default: 1h)",
    )
    histogram.set_defaults(func=cmd_histogram)

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"logkit: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
