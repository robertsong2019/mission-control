"""Characterization + contract tests for build_dashboard_data.py.

Fixtures mirror real `openclaw cron list` output (2026-09-09).
Run: python3 -m pytest tests/ -q  (or python3 -m unittest discover tests)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from build_dashboard_data import ago, parse_cron_jobs, parse_meminfo

HEADER = ("ID                                   Name                     "
          "Schedule                         Next       Last       "
          "Status    Target    Agent ID   Model               ")

# 7-col row: sched, next, last, status, target, agent, model
ROW_CRON = ("f7510f1f-9db8-46e7-8019-3c9a4858db2e project-testing-morning"
            "  cron 0 3 * * * (exact)           3m ago     1d ago"
            "     running   isolated  -          -")

# 6-col row: schedule truncated -> next glued with single space
ROW_GLUED = ("f0362050-d109-45ca-971b-6cc9cfad90eb essay-generation-morning"
             " cron 0 5 * * * @ Asia/Shangha... in 2h      22h ago"
             "    ok        isolated  -          glm-5.1")

# 7-col row with truncated tz suffix (ellipsis stripped, @ time dropped)
ROW_TZ = ("cccc4444-4444-4444-4444-444444444444 tz-job"
          "  cron 0 9 * * * @ Europe/Berli...  in 1h      2m ago"
          "     error     isolated  -          glm-5.1")

# every-type schedule: old parser dropped this row entirely (RED bug #1)
ROW_EVERY = ("aaaa1111-1111-1111-1111-111111111111 metrics-every-10m"
             " every 10m          in 5m      3m ago     ok"
             "        isolated  -          -")

# every-type with tz suffix truncated -> glued 6-col row
ROW_EVERY_GLUED = ("aaaa3333-3333-3333-3333-333333333333 sync-every-30m"
                   " every 30m @ Asia/Shangha... in 12m     9m ago"
                   "     ok        isolated  -          glm-5.1")

# at-type one-shot schedule
ROW_AT = ("aaaa2222-2222-2222-2222-222222222222 one-shot-task"
          "  at 2026-09-10T08:00  in 5h       1m ago     ok"
          "        isolated  -          -")

# well-formed id but unparseable columns -> skipped
ROW_JUNK = ("bbbb3333-3333-3333-3333-333333333333 weird-row"
            "  cron */5 * * *")


class TestParseCronJobs(unittest.TestCase):
    def test_seven_column_cron_row(self):
        jobs = parse_cron_jobs(HEADER + "\n" + ROW_CRON)
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j["id"], "f7510f1f")
        self.assertEqual(j["fullId"], "f7510f1f-9db8-46e7-8019-3c9a4858db2e")
        self.assertEqual(j["name"], "project-testing-morning")
        self.assertEqual(j["schedule"], "0 3 * * * (exact)")
        self.assertEqual(j["status"], "running")
        self.assertEqual(j["lastRun"], "1d ago")

    def test_glued_six_column_row(self):
        jobs = parse_cron_jobs(HEADER + "\n" + ROW_GLUED)
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j["schedule"], "0 5 * * *")
        self.assertEqual(j["status"], "ok")
        self.assertEqual(j["lastRun"], "22h ago")

    def test_tz_suffix_stripped(self):
        jobs = parse_cron_jobs(HEADER + "\n" + ROW_TZ)
        j = jobs[0]
        self.assertEqual(j["schedule"], "0 9 * * *")
        self.assertEqual(j["status"], "error")

    def test_every_schedule_row_kept(self):
        """RED bug #1: interval (every) schedules were silently dropped."""
        jobs = parse_cron_jobs(HEADER + "\n" + ROW_EVERY)
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j["name"], "metrics-every-10m")
        self.assertEqual(j["schedule"], "10m")
        self.assertEqual(j["status"], "ok")
        self.assertEqual(j["lastRun"], "3m ago")

    def test_every_glued_tz_row_kept(self):
        jobs = parse_cron_jobs(HEADER + "\n" + ROW_EVERY_GLUED)
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j["name"], "sync-every-30m")
        self.assertEqual(j["schedule"], "30m")
        self.assertEqual(j["lastRun"], "9m ago")

    def test_at_schedule_row_kept(self):
        """RED bug #1: one-shot (at) schedules were silently dropped."""
        jobs = parse_cron_jobs(HEADER + "\n" + ROW_AT)
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j["name"], "one-shot-task")
        self.assertEqual(j["schedule"], "2026-09-10T08:00")

    def test_known_id_mapping(self):
        row = ("2c714952-04af-4192-8e0a-95758dcbb3db github-trending-deep-..."
               "  cron 0 8 * * * @ Asia/Shangha... in 5h      19h ago"
               "    ok        isolated  -          -")
        jobs = parse_cron_jobs(HEADER + "\n" + row)
        self.assertEqual(jobs[0]["name"], "github-trending-deep-analysis")

    def test_unknown_id_keeps_raw_name(self):
        jobs = parse_cron_jobs(HEADER + "\n" + ROW_CRON)
        self.assertEqual(jobs[0]["name"], "project-testing-morning")

    def test_non_job_lines_skipped(self):
        out = "\n".join([HEADER, "garbage line without id", ROW_JUNK, ROW_CRON])
        jobs = parse_cron_jobs(out)
        self.assertEqual([j["id"] for j in jobs], ["f7510f1f"])

    def test_short_column_row_skipped(self):
        jobs = parse_cron_jobs(HEADER + "\n" + ROW_JUNK + "\n" + ROW_CRON)
        self.assertEqual(len(jobs), 1)

    def test_status_counts_derivable(self):
        out = "\n".join([ROW_CRON, ROW_GLUED, ROW_TZ, ROW_EVERY])
        jobs = parse_cron_jobs(out)
        self.assertEqual(
            {j["status"] for j in jobs}, {"running", "ok", "error"})


class TestAgo(unittest.TestCase):
    NOW = 1_000_000_000_000  # ms

    def check(self, delta_ms, expected):
        self.assertEqual(ago(self.NOW - delta_ms, now_ms=self.NOW), expected)

    def test_zero(self):
        self.check(0, "0s ago")

    def test_seconds_below_minute(self):
        self.check(59_500, "59s ago")

    def test_one_minute_boundary(self):
        self.check(60_000, "1m ago")

    def test_minutes_below_hour(self):
        self.check(3_599_000, "59m ago")

    def test_one_hour_boundary(self):
        self.check(3_600_000, "1h ago")

    def test_hours_below_day(self):
        self.check(86_399_000, "23h ago")

    def test_one_day_boundary(self):
        self.check(86_400_000, "1d ago")

    def test_days(self):
        self.check(5 * 86_400_000, "5d ago")

    def test_future_timestamp_clamps_to_zero(self):
        """RED bug #2: future ts produced negative strings like '-5s ago'."""
        self.assertEqual(ago(self.NOW + 5_000, now_ms=self.NOW), "0s ago")

    def test_default_now_used_when_omitted(self):
        self.assertIsInstance(ago(0), str)  # huge delta, just needs to not crash


class TestParseMeminfo(unittest.TestCase):
    FIXTURE = (
        "MemTotal:       16384 kB\n"
        "MemFree:         2048 kB\n"
        "MemAvailable:    8192 kB\n"
        "SwapTotal:       4096 kB\n"
        "SwapFree:       1024 kB\n"
        "HugePages_Total:       0\n"
    )

    def test_values_in_kb(self):
        mem = parse_meminfo(self.FIXTURE)
        self.assertEqual(mem["MemTotal"], 16384)
        self.assertEqual(mem["MemAvailable"], 8192)
        self.assertEqual(mem["SwapFree"], 1024)

    def test_zero_value_line(self):
        self.assertEqual(parse_meminfo(self.FIXTURE)["HugePages_Total"], 0)

    def test_mb_math_contract(self):
        """main() derives usedMB = (MemTotal - MemAvailable) // 1024."""
        mem = parse_meminfo(self.FIXTURE)
        self.assertEqual((mem["MemTotal"] - mem["MemAvailable"]) // 1024, 8)


if __name__ == "__main__":
    unittest.main()
