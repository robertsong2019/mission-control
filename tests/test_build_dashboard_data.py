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

# 7-col row with non-standard status (paused) -> must land in `other` bucket
ROW_PAUSED = ("dddd5555-5555-5555-5555-555555555555 paused-job"
              "  cron 0 12 * * *                 in 3h       2d ago"
              "     paused    isolated  -          -")

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

    def test_extra_column_row_best_effort_kept(self):
        """8-col row (future schema growth) must not be silently dropped:
        best-effort parse with the stable 7-col positions (silent row drop
        family, cf. every-type row fix)."""
        row = ROW_CRON + "  bonus-col"
        jobs = parse_cron_jobs(HEADER + "\n" + row)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["id"], "f7510f1f")
        self.assertEqual(jobs[0]["schedule"], "0 3 * * * (exact)")
        self.assertEqual(jobs[0]["lastRun"], "1d ago")
        self.assertEqual(jobs[0]["status"], "running")

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

    def test_junk_lines_skipped(self):
        """Parser contract mirrors parse_cron_jobs: junk rows are skipped,
        never crash (ROW_JUNK sibling behavior)."""
        text = ("\n"                       # empty line
                "no colon here\n"           # unparseable
                "MemTotal:  100 kB\n"
                "EmptyVal:\n"               # colon but no value
                "NotNumber:  abc kB\n")     # non-numeric value
        mem = parse_meminfo(text)
        self.assertEqual(mem, {"MemTotal": 100})

    def test_mb_math_contract(self):
        """main() derives usedMB = (MemTotal - MemAvailable) // 1024."""
        mem = parse_meminfo(self.FIXTURE)
        self.assertEqual((mem["MemTotal"] - mem["MemAvailable"]) // 1024, 8)


if __name__ == "__main__":
    unittest.main()

# ---------- main() integration (fake sh / sessions.json / NOW_MS) ----------

import io as _io
import json as _json
from unittest import mock

import build_dashboard_data as bdd

MEMINFO = (
    "MemTotal:       16384 kB\n"
    "MemFree:         2048 kB\n"
    "MemAvailable:    8192 kB\n"
    "SwapTotal:       4096 kB\n"
    "SwapFree:       1024 kB\n"
)

NOW_MS_FIXED = 1_000_000_000_000  # ms


def _fake_sh_factory(cron_out):
    table = {
        "openclaw cron list 2>/dev/null": cron_out,
        "uptime -p": "up 5 days, 2:14",
        "cat /proc/loadavg": "0.52 0.58 0.59 1/123 4567",
        "df -h /": "Filesystem      Size  Used Avail Use% Mounted on\n"
                   "/dev/vda1        40G   12G   28G  31% /",
        "cat /proc/meminfo": MEMINFO,
        "node --version": "v22.22.1",
        "git log -1 --format='%h %s'": "abc1234 last commit subject",
        "git log -6 --format='%h %s'": "abc1234 c6\nbbb2222 c5",
    }

    def fake_sh(cmd, cwd=None):
        return table.get(cmd, "")

    return fake_sh


class TestShReal(unittest.TestCase):
    """sh() real contract: shell=True, stdout-only, stripped, rc ignored."""

    def test_runs_shell_command_and_strips(self):
        self.assertEqual(bdd.sh("echo '  hi  '"), "hi")

    def test_stdout_only_stderr_discarded(self):
        self.assertEqual(bdd.sh("echo out; echo err 1>&2"), "out")

    def test_nonzero_exit_returns_stdout_no_raise(self):
        self.assertEqual(bdd.sh("echo partial; exit 1"), "partial")
        self.assertEqual(bdd.sh("exit 1"), "")

    def test_cwd_is_honored(self):
        self.assertEqual(
            bdd.sh("pwd", cwd=os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))),
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMainIntegration(unittest.TestCase):
    def setUp(self):
        # snapshot + protect the real generated artifact
        self.out_path = os.path.join(
            os.path.dirname(os.path.abspath(bdd.__file__)),
            "data", "dashboard-data.json")
        self.backup = None
        if os.path.exists(self.out_path):
            with open(self.out_path, "rb") as f:
                self.backup = f.read()

    def tearDown(self):
        if self.backup is not None:
            with open(self.out_path, "wb") as f:
                f.write(self.backup)
        elif os.path.exists(self.out_path):
            os.remove(self.out_path)

    def run_main(self, cron_out, sessions_store):
        payload = _json.dumps(sessions_store)
        real_open = open

        def fake_open(path, *a, **k):
            if "sessions.json" in str(path):
                return _io.StringIO(payload)
            return real_open(path, *a, **k)

        with mock.patch.object(bdd, "sh", new=_fake_sh_factory(cron_out)), \
             mock.patch.object(bdd, "NOW_MS", new=NOW_MS_FIXED), \
             mock.patch("builtins.open", new=fake_open):
            bdd.main()

        with real_open(self.out_path) as f:
            return _json.load(f)

    def _store(self, *entries):
        # entries: (key, model, totalTokens, updatedAtMs)
        return {
            k: {"model": m, "totalTokens": t, "updatedAt": u}
            for k, m, t, u in entries
        }

    def test_cron_summary_counts_and_error_jobs(self):
        cron_out = "\n".join([HEADER, ROW_CRON, ROW_GLUED, ROW_TZ, ROW_EVERY])
        data = self.run_main(
            cron_out,
            self._store(("s1", "m1", 100, NOW_MS_FIXED - 3600_000)))
        cs = data["cronSummary"]
        self.assertEqual(cs["total"], 4)
        self.assertEqual(cs["ok"], 2)       # GLUED + EVERY
        self.assertEqual(cs["error"], 1)    # TZ
        self.assertEqual(cs["running"], 1)  # CRON
        self.assertEqual(cs["errorJobs"], ["cccc4444 (tz-job)"])
        self.assertEqual(len(data["cronJobs"]), 4)

    def test_sessions_active24_window_and_token_sums(self):
        cron_out = HEADER
        store = self._store(
            ("recent-sess", "glm-a", 500, NOW_MS_FIXED - 1 * 3600_000),    # in 24h
            ("edge-sess", "glm-b", 200, NOW_MS_FIXED - 24 * 3600_000),     # boundary: <= 24h counts
            ("stale-sess", "glm-c", 300, NOW_MS_FIXED - 30 * 3600_000),    # out
        )
        data = self.run_main(cron_out, store)
        s = data["sessions"]
        self.assertEqual(s["total"], 3)
        self.assertEqual(s["unique"], 3)
        self.assertEqual(s["active24h"], 2)      # recent + boundary
        self.assertEqual(s["totalTokens"], 1000)
        self.assertEqual(s["active24hTokens"], 700)
        recent_keys = [r["key"] for r in s["recent"]]
        self.assertEqual(recent_keys[0], "recent-sess")  # newest first

    def test_memory_and_disk_math_in_output(self):
        cron_out = HEADER
        data = self.run_main(
            cron_out,
            self._store(("s1", "m1", 0, NOW_MS_FIXED)))
        host = data["system"]["host"]
        self.assertEqual(host["memory"]["totalMB"], 16)
        self.assertEqual(host["memory"]["availableMB"], 8)
        self.assertEqual(host["memory"]["usedMB"], 8)     # (16384-8192)//1024
        self.assertEqual(host["memory"]["freeMB"], 2)
        self.assertEqual(host["memory"]["swapTotalMB"], 4)
        self.assertEqual(host["memory"]["swapUsedMB"], 3)  # (4096-1024)//1024
        disk = host["disk"]
        self.assertEqual(disk["usage"], "31%")
        self.assertEqual(disk["available"], "28G")
        self.assertEqual(host["loadAverage"], "0.52, 0.58, 0.59")

    def test_null_updatedat_does_not_crash_and_counts_stale(self):
        """sessions.json entry with updatedAt:null must not crash the sort
        (model field is or-guarded; updatedAt must be too)."""
        cron_out = HEADER
        store = self._store(
            ("fresh", "glm", 5, NOW_MS_FIXED),
            ("null-ts", "glm", 10, None),
        )
        data = self.run_main(cron_out, store)
        s = data["sessions"]
        self.assertEqual(s["total"], 2)
        self.assertEqual(s["active24h"], 1)   # null-ts treated as epoch → stale
        self.assertEqual(s["totalTokens"], 15)
        self.assertEqual(s["recent"][-1]["key"], "null-ts")  # sorts last

    def test_recent_capped_at_20(self):
        cron_out = HEADER
        store = self._store(*[
            (f"s{i}", "glm", i, NOW_MS_FIXED - i * 1000) for i in range(25)
        ])
        data = self.run_main(cron_out, store)
        self.assertEqual(len(data["sessions"]["recent"]), 20)
        # newest-first ordering
        self.assertEqual(data["sessions"]["recent"][0]["key"], "s0")
        self.assertEqual(data["sessions"]["recent"][19]["key"], "s19")

    def test_git_section_and_written_shape(self):
        cron_out = "\n".join([HEADER, ROW_CRON])
        data = self.run_main(
            cron_out, self._store(("s1", "m1", 1, NOW_MS_FIXED)))
        git = data["git"]
        self.assertEqual(git["lastCommit"], "abc1234 last commit subject")
        self.assertEqual(git["recentCommits"], ["abc1234 c6", "bbb2222 c5"])
        self.assertEqual(data["system"]["gateway"]["status"], "running")
        self.assertEqual(data["cronSummary"]["total"], 1)
        self.assertRegex(data["lastUpdated"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertRegex(data["generatedAt"], r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} CST$")


class TestSummaryBucketsPartition(TestMainIntegration):
    """Contract: cronSummary buckets partition total
    (ok+error+running+other == total); non-dict session entries are
    skipped instead of crashing the build."""

    def test_paused_status_lands_in_other_bucket(self):
        cron_out = "\n".join([HEADER, ROW_CRON, ROW_PAUSED])
        data = self.run_main(
            cron_out, self._store(("s1", "m1", 1, NOW_MS_FIXED)))
        cs = data["cronSummary"]
        self.assertEqual(cs["total"], 2)
        self.assertEqual(cs["running"], 1)
        self.assertEqual(cs["other"], 1)
        self.assertEqual(cs["otherJobs"], ["dddd5555 (paused-job)"])
        # partition invariant
        self.assertEqual(
            cs["ok"] + cs["error"] + cs["running"] + cs["other"], cs["total"])

    def test_all_ok_leaves_other_empty(self):
        cron_out = "\n".join([HEADER, ROW_GLUED])
        data = self.run_main(
            cron_out, self._store(("s1", "m1", 1, NOW_MS_FIXED)))
        cs = data["cronSummary"]
        self.assertEqual(cs["other"], 0)
        self.assertEqual(cs["otherJobs"], [])

    def test_non_dict_session_entries_skipped_not_crash(self):
        cron_out = HEADER
        store = {
            "good": {"model": "glm", "totalTokens": 7,
                     "updatedAt": NOW_MS_FIXED},
            "corrupt-str": "not-a-dict",
            "corrupt-num": 42,
        }
        data = self.run_main(cron_out, store)
        s = data["sessions"]
        self.assertEqual(s["total"], 1)
        self.assertEqual(s["totalTokens"], 7)
        self.assertEqual(s["recent"][0]["key"], "good")


if __name__ == "__main__":
    unittest.main()
