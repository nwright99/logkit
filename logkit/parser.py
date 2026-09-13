"""Parsing loosely-structured log lines into a common shape.

Real logs don't agree on a format. This doesn't try to handle every
format that exists -- it recognizes the timestamp and level
conventions that show up most often (ISO 8601 / Python logging's
default format, classic syslog, and single-line JSON) and leaves the
fields as None when it can't find them, rather than guessing wrong.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

_LEVELS = ("CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "TRACE")
_LEVEL_RE = re.compile(r"\b(" + "|".join(_LEVELS) + r")\b")

# 2026-09-06T12:34:56 or 2026-09-06 12:34:56,123
_ISO_RE = re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(?:[.,](\d+))?")

# Sep  6 12:34:56 -- no year in the line, so we assume "this year"
_SYSLOG_RE = re.compile(r"([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})")
_SYSLOG_MONTHS = set("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())

# Field names seen in the wild across common JSON logging setups
# (Python's logging.Formatter with a json renderer, Bunyan, pino, ...).
_JSON_TIMESTAMP_KEYS = ("timestamp", "time", "ts", "@timestamp")
_JSON_LEVEL_KEYS = ("level", "levelname", "loglevel", "severity")


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


def _normalize_level(level: str) -> str:
    return "WARNING" if level == "WARN" else level


def _parse_level(text: str) -> Optional[str]:
    match = _LEVEL_RE.search(text.upper())
    if not match:
        return None
    return _normalize_level(match.group(1))


def _parse_json_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return _parse_timestamp(text)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    return None


def _parse_json_level(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    return _normalize_level(value.strip().upper())


def _parse_json_line(line: str) -> Optional[LogLine]:
    try:
        data = json.loads(line)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None

    timestamp = None
    for key in _JSON_TIMESTAMP_KEYS:
        if key in data:
            timestamp = _parse_json_timestamp(data[key])
            if timestamp is not None:
                break
    if timestamp is None:
        timestamp = _parse_timestamp(line)

    level = None
    for key in _JSON_LEVEL_KEYS:
        if key in data:
            level = _parse_json_level(data[key])
            if level is not None:
                break
    if level is None:
        level = _parse_level(line)

    return LogLine(raw=line, timestamp=timestamp, level=level)


def parse_line(raw: str) -> LogLine:
    line = raw.rstrip("\n")
    if line.lstrip().startswith("{"):
        entry = _parse_json_line(line)
        if entry is not None:
            return entry
    return LogLine(raw=line, timestamp=_parse_timestamp(line), level=_parse_level(line))
