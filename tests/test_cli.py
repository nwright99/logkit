from datetime import datetime, timedelta
import unittest

from logkit.cli import bucket_start, parse_interval


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


if __name__ == "__main__":
    unittest.main()
