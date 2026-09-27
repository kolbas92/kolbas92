import io
import os
import tempfile
import unittest
import urllib.error
from datetime import date, timedelta
from unittest import mock
from xml.dom import minidom

from stats import Day, main, parse_calendar, render, summarize
from theme import DARK

START = date(2026, 1, 4)  # a Sunday


def days_from(counts: list[int]) -> list[Day]:
    return [Day(START + timedelta(days=i), c, min(c, 4)) for i, c in enumerate(counts)]


class SummarizeTest(unittest.TestCase):
    def test_longest_streak_picks_the_longest_run(self):
        s = summarize(days_from([1, 1, 1, 1, 0, 2, 2, 0]))
        self.assertEqual(s.longest_streak, 4)

    def test_streak_running_to_the_last_day_counts(self):
        s = summarize(days_from([0, 1, 1, 0, 2, 3, 1]))
        self.assertEqual(s.longest_streak, 3)

    def test_totals(self):
        s = summarize(days_from([0, 5, 0, 2]))
        self.assertEqual((s.total, s.active_days), (7, 2))

    def test_busiest_day(self):
        s = summarize(days_from([1, 7, 0, 7]))
        self.assertEqual((s.busiest.count, s.busiest.day), (7, START + timedelta(days=1)))

    def test_no_activity(self):
        s = summarize(days_from([0, 0, 0]))
        self.assertEqual((s.total, s.active_days, s.longest_streak), (0, 0, 0))
        self.assertIsNone(s.busiest)


class ParseCalendarTest(unittest.TestCase):
    def test_flattens_weeks_and_maps_levels(self):
        payload = {"data": {"user": {"contributionsCollection": {"contributionCalendar": {"weeks": [
            {"contributionDays": [
                {"date": "2026-01-05", "contributionCount": 4, "contributionLevel": "THIRD_QUARTILE"},
                {"date": "2026-01-04", "contributionCount": 0, "contributionLevel": "NONE"},
            ]},
        ]}}}}}
        days = parse_calendar(payload)
        self.assertEqual([d.day.day for d in days], [4, 5])
        self.assertEqual([d.level for d in days], [0, 3])

    def test_error_payload_is_reported(self):
        with self.assertRaisesRegex(ValueError, "Bad credentials"):
            parse_calendar({"errors": [{"message": "Bad credentials"}]})


class RenderTest(unittest.TestCase):
    def test_renders_well_formed_svg_with_a_cell_per_day(self):
        days = days_from([i % 5 for i in range(371)])
        svg = render(days, summarize(days), DARK, days[-1].day)
        doc = minidom.parseString(svg)
        cells = [r for r in doc.getElementsByTagName("rect") if r.getElementsByTagName("title")]
        self.assertEqual(len(cells), 371)


class MainErrorsTest(unittest.TestCase):
    def run_main(self, failure: Exception) -> tuple[int, str]:
        stderr = io.StringIO()
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "t"}), \
                mock.patch("stats.urllib.request.urlopen", side_effect=failure), \
                mock.patch("sys.stderr", stderr), tempfile.TemporaryDirectory() as out:
            code = main(["--out", out])
        return code, stderr.getvalue()

    def test_http_error_is_reported_without_a_traceback(self):
        failure = urllib.error.HTTPError(
            "https://api.github.com/graphql", 401, "Unauthorized", {},
            io.BytesIO(b'{"message":"Bad credentials"}'))
        code, err = self.run_main(failure)
        self.assertEqual(code, 1)
        self.assertIn("HTTP 401", err)
        self.assertIn("Bad credentials", err)

    def test_network_error_is_reported(self):
        code, err = self.run_main(urllib.error.URLError("timed out"))
        self.assertEqual(code, 1)
        self.assertIn("unreachable", err)


if __name__ == "__main__":
    unittest.main()
