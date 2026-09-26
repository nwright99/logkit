import argparse
import json
import tempfile
from datetime import datetime, timedelta
from io import StringIO
from unittest import mock
import unittest

from logkit.cli import bucket_start, cmd_tally, iter_lines, parse_interval


class ParseIntervalTests(unittest.TestCase):
    def test_seconds(self):
        self.assertEqual(parse_interval("30s"), timedelta(seconds=30))

    def test_minutes(self):
        self.assertEqual(parse_interval("15m"), timedelta(minutes=15))

    def test_hours(self):
        self.assertEqual(parse_interval("2h"), timedelta(hours=2))

    def test_days(self):
        self.assertEqual(parse_interval("1d"), timedelta(days=1))

    def test_rejects_missing_unit(self):
        with self.assertRaises(Exception):
            parse_interval("15")

    def test_rejects_unknown_unit(self):
        with self.assertRaises(Exception):
            parse_interval("15w")

    def test_rejects_garbage(self):
        with self.assertRaises(Exception):
            parse_interval("soon")


class BucketStartTests(unittest.TestCase):
    def test_floors_to_hour_boundary(self):
        ts = datetime(2026, 9, 6, 14, 37, 12)
        self.assertEqual(bucket_start(ts, timedelta(hours=1)), datetime(2026, 9, 6, 14, 0, 0))

    def test_floors_to_fifteen_minute_boundary(self):
        ts = datetime(2026, 9, 6, 14, 37, 12)
        self.assertEqual(bucket_start(ts, timedelta(minutes=15)), datetime(2026, 9, 6, 14, 30, 0))

    def test_floors_to_day_boundary(self):
        ts = datetime(2026, 9, 6, 23, 59, 59)
        self.assertEqual(bucket_start(ts, timedelta(days=1)), datetime(2026, 9, 6, 0, 0, 0))

    def test_already_on_boundary_is_unchanged(self):
        ts = datetime(2026, 9, 6, 14, 0, 0)
        self.assertEqual(bucket_start(ts, timedelta(hours=1)), ts)

    def test_sub_minute_interval(self):
        ts = datetime(2026, 9, 6, 14, 37, 12)
        self.assertEqual(bucket_start(ts, timedelta(seconds=30)), datetime(2026, 9, 6, 14, 37, 0))


class TallyFormatTests(unittest.TestCase):
    def _run(self, lines, fmt):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as handle:
            handle.write("\n".join(lines) + "\n")
            path = handle.name
        args = argparse.Namespace(path=path, format=fmt)
        with mock.patch("sys.stdout", new_callable=StringIO) as out:
            cmd_tally(args)
        return out.getvalue()

    def test_table_is_default_output(self):
        output = self._run(
            ["2026-09-06 03:14:07 ERROR boom", "2026-09-06 03:14:08 INFO ok"], "table"
        )
        self.assertIn("ERROR     1", output)
        self.assertIn("total     2", output)

    def test_json_output_is_valid_and_matches_counts(self):
        output = self._run(
            ["2026-09-06 03:14:07 ERROR boom", "2026-09-06 03:14:08 ERROR boom again"], "json"
        )
        payload = json.loads(output)
        self.assertEqual(payload["ERROR"], 2)
        self.assertEqual(payload["total"], 2)

    def test_json_output_includes_unclassified(self):
        output = self._run(["no level or timestamp here"], "json")
        payload = json.loads(output)
        self.assertEqual(payload["(none)"], 1)
        self.assertEqual(payload["total"], 1)


class IterLinesStdinTests(unittest.TestCase):
    def test_dash_reads_from_stdin(self):
        fake_stdin = StringIO("one\ntwo\n")
        with mock.patch("logkit.cli.sys.stdin", fake_stdin):
            self.assertEqual(list(iter_lines("-")), ["one\n", "two\n"])


if __name__ == "__main__":
    unittest.main()
