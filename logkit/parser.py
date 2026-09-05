"""Parsing loosely-structured log lines into a common shape.

Real logs don't agree on a format. This doesn't try to handle every
format that exists -- it recognizes the timestamp and level
conventions that show up most often (ISO 8601 / Python logging's
default format, and classic syslog) and leaves the fields as None
when it can't find them, rather than guessing wrong.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

_LEVELS = ("CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "TRACE")
_LEVEL_RE = re.compile(r"\b(" + "|".join(_LEVELS) + r")\b")

# 2026-09-06T12:34:56 or 2026-09-06 12:34:56,123
_ISO_RE = re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(?:[.,](\d+))?")

# Sep  6 12:34:56 -- no year in the line, so we assume "this year"
_SYSLOG_RE = re.compile(r"([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})")
_SYSLOG_MONTHS = set("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())


@dataclass
class LogLine:
    raw: str
    timestamp: Optional[datetime]
    level: Optional[str]


def _parse_timestamp(text: str) -> Optional[datetime]:
    match = _ISO_RE.search(text)
    if match:
        stamp, fraction = match.groups()
        stamp = stamp.replace("T", " ")
        try:
            dt = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
        if fraction:
            dt = dt.replace(microsecond=int(fraction[:6].ljust(6, "0")))
        return dt

    match = _SYSLOG_RE.search(text)
    if match and match.group(1)[:3] in _SYSLOG_MONTHS:
        try:
            dt = datetime.strptime(match.group(1), "%b %d %H:%M:%S")
        except ValueError:
            return None
        return dt.replace(year=datetime.now().year)

    return None


def _parse_level(text: str) -> Optional[str]:
    match = _LEVEL_RE.search(text.upper())
    if not match:
        return None
    level = match.group(1)
    return "WARNING" if level == "WARN" else level


def parse_line(raw: str) -> LogLine:
    line = raw.rstrip("\n")
    return LogLine(raw=line, timestamp=_parse_timestamp(line), level=_parse_level(line))
