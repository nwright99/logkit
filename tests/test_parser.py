from datetime import datetime
import unittest

from logkit.parser import parse_line


class TimestampTests(unittest.TestCase):
    def test_iso_with_t_separator(self):
        entry = parse_line("2026-09-06T12:34:56 worker started")
        self.assertEqual(entry.timestamp, datetime(2026, 9, 6, 12, 34, 56))

    def test_iso_with_space_separator_and_comma_millis(self):
        entry = parse_line("2026-09-06 03:14:07,123 ERROR worker: connection refused")
        self.assertEqual(entry.timestamp, datetime(2026, 9, 6, 3, 14, 7, 123000))

    def test_iso_with_dot_micros(self):
        entry = parse_line("2026-09-06 03:14:07.5 debug tick")
        self.assertEqual(entry.timestamp, datetime(2026, 9, 6, 3, 14, 7, 500000))

    def test_syslog_format_assumes_current_year(self):
        entry = parse_line("Sep  6 12:34:56 host sshd[1]: session opened")
        self.assertEqual(
            entry.timestamp,
            datetime(datetime.now().year, 9, 6, 12, 34, 56),
        )

    def test_syslog_rejects_non_month_prefix(self):
        # "Xxx 6 12:34:56" looks syslog-shaped but isn't a real month.
        entry = parse_line("Xxx  6 12:34:56 host sshd[1]: nope")
        self.assertIsNone(entry.timestamp)

    def test_no_timestamp_present(self):
        entry = parse_line("just a plain line with no time in it")
        self.assertIsNone(entry.timestamp)

    def test_iso_takes_priority_over_syslog_looking_text(self):
        entry = parse_line("2026-09-06T12:34:56 Sep 1 00:00:00 noise")
        self.assertEqual(entry.timestamp, datetime(2026, 9, 6, 12, 34, 56))


class LevelTests(unittest.TestCase):
    def test_detects_error(self):
        self.assertEqual(parse_line("2026-09-06T12:34:56 ERROR boom").level, "ERROR")

    def test_detects_lowercase_level(self):
        self.assertEqual(parse_line("something debug happened").level, "DEBUG")

    def test_warn_is_normalized_to_warning(self):
        self.assertEqual(parse_line("WARN disk almost full").level, "WARNING")

    def test_no_level_present(self):
        self.assertIsNone(parse_line("2026-09-06T12:34:56 worker started").level)

    def test_level_must_be_a_whole_word(self):
        # ERRORCODE should not be mistaken for ERROR.
        self.assertIsNone(parse_line("status=ERRORCODE").level)

    def test_first_matching_level_wins(self):
        entry = parse_line("INFO retrying after ERROR")
        self.assertEqual(entry.level, "INFO")


class RawFieldTests(unittest.TestCase):
    def test_trailing_newline_is_stripped(self):
        entry = parse_line("2026-09-06T12:34:56 INFO ok\n")
        self.assertEqual(entry.raw, "2026-09-06T12:34:56 INFO ok")


if __name__ == "__main__":
    unittest.main()
