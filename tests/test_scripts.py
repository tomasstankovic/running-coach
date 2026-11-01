#!/usr/bin/env python3
"""Behaviour tests for the skill's scripts, on fictional data only.

Run from the repository root:  python3 -m unittest discover -s tests -v
Standard library only. Each test runs a script the way Claude does (a subprocess with a JSON
file) or calls a pure function, and checks the coaching rule it implements.
"""
import json
import math
import pathlib
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skills" / "running-coach" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import paces  # noqa: E402
import season_plan  # noqa: E402
import tp_structure  # noqa: E402


def run(script, *args, expect_ok=True):
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True)
    if expect_ok and proc.returncode not in (0, 1):
        raise AssertionError(f"{script} crashed:\n{proc.stderr}")
    return proc


class Help(unittest.TestCase):
    def test_every_script_prints_help(self):
        for script in sorted(SCRIPTS.glob("*.py")):
            proc = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"{script.name} --help failed: {proc.stderr[-300:]}")
            proc = subprocess.run([sys.executable, str(script), "power", "--help"] if script.name == "paces.py" else
                                  [sys.executable, str(script), "--help"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, script.name)


class TempDir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, data):
        path = self.dir / name
        path.write_text(json.dumps(data))
        return path


class Paces(TempDir):
    def test_percent_is_of_threshold_speed(self):
        thr = paces.parse_pace("4:10")
        self.assertAlmostEqual(paces.pct_from_pace(thr, paces.parse_pace("4:00")), 104.2, places=1)
        self.assertAlmostEqual(paces.pace_from_pct(thr, 80), 312.5, places=1)

    def test_threshold_from_half_marathon_is_faster_than_race_pace(self):
        out = run("paces.py", "race", "--distance", 21.0975, "--time", "1:34:20").stdout
        self.assertIn("4:2", out)  # threshold ~4:20-4:29/km, never slower than the race pace

    def test_vickers_model1_matches_published_example(self):
        # 10k in 50:00 at 30 miles a week -> ~246 min (Vickers & Vertosick 2016, worked example)
        t = paces.vickers_model1(10000, 3000, 30)
        self.assertAlmostEqual(t / 60, 246, delta=1.5)

    def test_power_zones_and_rftp_estimate(self):
        out = run("paces.py", "power", "--effort-watts", 400, "--effort-minutes", 94, "95-100").stdout
        self.assertIn("rFTP ≈ 416 W", out)
        self.assertIn("Threshold   374–416", out)
        self.assertIn("95 % = 395 W", out)

    def test_volume_models_are_slower_than_riegel_at_low_volume(self):
        riegel = 3000 * (42.195 / 10) ** 1.06
        self.assertGreater(paces.vickers_model1(10000, 3000, 20), riegel)


class CheckWeek(TempDir):
    def history(self, longest=15.0, scale=1.0):
        hist, d0 = [], date(2026, 10, 5)
        for wk in range(4):
            for day, km, mn in [(1, 8, 48), (3, 10, 60), (6, longest - 3 + wk, 75 + 5 * wk)]:
                hist.append({"date": str(d0 + timedelta(days=7 * wk + day)), "sport": "Run",
                             "duration_actual": mn * scale / 60, "distance_actual_km": km})
        return hist

    def plan(self, long_km, long_min=95, race=False):
        return [{"date": "2026-11-03", "type": "easy", "minutes": 50, "km": 8},
                {"date": "2026-11-04", "type": "threshold", "minutes": 55, "km": 10},
                {"date": "2026-11-06", "type": "easy", "minutes": 45, "km": 7},
                {"date": "2026-11-08", "type": "race" if race else "long", "minutes": long_min, "km": long_km}]

    def check(self, plan, scale=1.0, **extra):
        data = {"week_role": "build", "today": "2026-11-01", "history": self.history(scale=scale),
                "plan": plan, **extra}
        proc = run("check_week.py", self.write("week.json", data))
        return proc.returncode, proc.stdout

    def test_long_run_over_ten_percent_fails(self):
        code, out = self.check(self.plan(17))  # 30-day longest is 15 km
        self.assertEqual(code, 1)
        self.assertIn("longer than the longest run of the last 30 days", out)

    def test_long_run_within_ten_percent_passes_spike_check(self):
        _, out = self.check(self.plan(16.4))
        self.assertIn("no run is more than 10 % longer", out)
        self.assertIn("Longest allowed run", out)

    def test_race_is_exempt_but_reported(self):
        _, out = self.check(self.plan(21.1, race=True))
        self.assertIn("race is", out)
        self.assertNotIn("FAIL  2026-11-08", out)

    def test_weekly_jump_over_twenty_percent_fails(self):
        big = [dict(w, minutes=w["minutes"] * 1.6) for w in self.plan(16)]
        code, out = self.check(big)
        self.assertEqual(code, 1)
        self.assertIn("hard limit +20 %", out)

    def test_cautious_mode_uses_ten_percent(self):
        # last week 297 min (> 4 h, so no small-step exemption); this plan is 333 min (+12 %)
        plan = [dict(w, minutes=m) for w, m in zip(self.plan(15), (75, 82, 60, 116))]
        _, normal = self.check(plan, scale=1.5)
        _, cautious = self.check(plan, scale=1.5, cautious=True)
        self.assertIn("OK    volume +12 %", normal)
        self.assertIn("WARN  volume +12 %", cautious)

    def test_small_step_allowed_only_at_low_volume(self):
        plan = [dict(w, minutes=m) for w, m in zip(self.plan(15), (50, 55, 40, 77))]  # +24 min on 198
        _, out = self.check(plan, cautious=True)
        self.assertIn("OK    volume +12 %", out)

    def test_back_to_back_hard_days_fail(self):
        plan = self.plan(15)
        plan[2] = {"date": "2026-11-05", "type": "intervals", "minutes": 50, "km": 9}
        code, out = self.check(plan)
        self.assertEqual(code, 1)
        self.assertIn("hard days back to back", out)


class SeasonPlan(TempDir):
    SPEC = {"title": "Test", "lang": "en", "start": "2026-11-09", "current": {"km": 40, "long_km": 14},
            "runs_per_week": 5, "easy_pace": "6:00", "peak_km": 65, "rhythm": 3,
            "races": [{"name": "Half", "date": "2027-03-14", "distance_km": 21.1, "priority": "B"},
                      {"name": "Marathon", "date": "2027-04-25", "distance_km": 42.2, "priority": "A"}]}

    def test_long_run_never_jumps_more_than_ten_percent(self):
        weeks = season_plan.generate(dict(self.SPEC))["weeks"]
        longest = 14
        for w in weeks:
            if w["role"] in ("race", "race-B"):
                continue
            self.assertLessEqual(w["long_km"], round(longest * 1.10) + 0.5, w["week_start"])
            longest = max(longest, w["long_km"])

    def test_phases_end_with_taper_race_recovery(self):
        weeks = season_plan.generate(dict(self.SPEC))["weeks"]
        roles = [w["role"] for w in weeks]
        self.assertEqual(roles[-5:], ["taper", "taper", "race", "recovery", "recovery"])
        self.assertIn("race-B", roles)

    def test_marathon_reaches_thirty_km(self):
        weeks = season_plan.generate(dict(self.SPEC))["weeks"]
        self.assertGreaterEqual(max(w["long_km"] for w in weeks if w["role"] != "race"), 30)

    def test_low_volume_half_warns_about_short_long_runs(self):
        spec = {"start": "2027-02-01", "current": {"km": 22, "long_km": 10}, "runs_per_week": 3,
                "easy_pace": "6:00", "peak_km": 28,
                "races": [{"name": "Half", "date": "2027-03-28", "distance_km": 21.1, "priority": "A"}]}
        warnings = season_plan.generate(spec)["warnings"]
        self.assertTrue(any("aim for ~18 km" in w for w in warnings), warnings)

    def test_replan_keeps_earlier_weeks(self):
        plan = season_plan.generate(dict(self.SPEC))
        plan["weeks"][0]["actual_km"] = 39.5
        path = self.write("plan.json", plan)
        out = self.dir / "plan2.json"
        run("season_plan.py", "replan", path, "--from", "2026-12-07", "--current-km", 30, "--note", "flu",
            "--out", out)
        new = json.loads(out.read_text())
        self.assertEqual(new["weeks"][0]["actual_km"], 39.5)
        self.assertEqual(new["changes"][-1]["text"], "flu")
        self.assertEqual(new["weeks"][0]["week_start"], "2026-11-09")


class Readiness(TempDir):
    def series(self, drop_from=None):
        rows = []
        for i in range(56):
            hrv = 55 + (3 if i % 2 else -3)
            rhr = 50 + (1 if i % 3 == 0 else 0)
            if drop_from is not None and i >= drop_from:
                hrv, rhr = 38, 55
            rows.append({"date": str(date(2026, 9, 1) + timedelta(days=i)), "hrv": hrv, "rhr": rhr, "sleep_h": 7.5})
        return rows

    def test_stable_values_are_green(self):
        out = run("readiness.py", self.write("m.json", self.series())).stdout
        self.assertIn(": GREEN", out)

    def test_four_days_below_band_is_red_with_volume_cut(self):
        out = run("readiness.py", self.write("m.json", self.series(drop_from=50))).stdout
        self.assertIn(": RED", out)
        self.assertIn("cut volume ~25 %", out)

    def test_brief_and_trend_outputs(self):
        path = self.write("m.json", self.series())
        brief = run("readiness.py", path, "--brief").stdout
        self.assertRegex(brief, r"^2026-10-26 GREEN: .*HRV 7d")
        trend = json.loads(run("readiness.py", path, "--trend", 14).stdout)
        self.assertTrue(trend and {"date", "verdict", "hrv7", "band_lo", "band_hi"} <= set(trend[-1]))

    def test_short_history_is_not_judged(self):
        out = run("readiness.py", self.write("m.json", self.series()[:15])).stdout
        self.assertIn("not judged", out)


class TpStructure(unittest.TestCase):
    def test_km_workout_totals_and_units(self):
        spec = {"threshold_pace": "4:10", "unit": "km", "metric": "pace", "steps": [
            {"name": "WU", "km": 2.5, "pct": [68, 76], "class": "warmUp", "pace": "6:00"},
            {"repeat": 5, "steps": [{"name": "1 km", "km": 1, "pct": [102, 104]},
                                    {"name": "jog", "seconds": 120, "pct": [55, 66], "class": "rest", "pace": "6:40"}]},
            {"name": "CD", "km": 1.5, "pct": [62, 70], "class": "coolDown", "pace": "6:10"}]}
        out = tp_structure.build(spec)
        sw = out["structured_workout"]
        self.assertEqual(sw["primaryLengthMetric"], "distance")
        self.assertEqual(sw["structure"][1]["steps"][0]["length"], {"value": 1000, "unit": "meter"})
        self.assertEqual(out["distance_km"], 10.5)
        self.assertEqual(out["duration_minutes"], 54)
        self.assertEqual(sw["structure"][-1]["end"], 10500)

    def test_hr_workout_needs_pace_for_km(self):
        with self.assertRaises(ValueError):
            tp_structure.build({"unit": "km", "metric": "hr",
                                "steps": [{"name": "easy", "minutes": 60, "pct": [75, 83]}]})


def session(*steps):
    """Laps the way a watch records a structured workout: (kind, step, km, seconds, avg HR, max HR)."""
    laps, t = [], 0
    for kind, step, km, secs, hr, hrmax in steps:
        laps.append({"Intensity": kind, "WorkoutStepIndex": step, "TotalDistance": round(km, 2),
                     "TotalTimerTime": secs, "AveragePace": secs / km, "NormalizedGradedPace": secs / km,
                     "AverageHeartRate": hr, "MaximumHeartRate": hrmax, "MinimumHeartRate": hr - 25,
                     "startOffsetSeconds": t, "stopOffsetSeconds": t + secs})
        t += secs
    return {"totals": {"Duration": t}, "lapData": laps, "data": []}


class AnalyzeSession(TempDir):
    def laps(self):
        laps, t = [], 0
        def lap(kind, dist, secs, hr, hrmax, hrmin=None):
            nonlocal t
            laps.append({"Intensity": kind, "TotalDistance": dist, "TotalTimerTime": secs,
                         "AveragePace": secs / dist if dist else 0, "NormalizedGradedPace": secs / dist if dist else 0,
                         "AverageHeartRate": hr, "MaximumHeartRate": hrmax, "MinimumHeartRate": hrmin or hr - 20,
                         "startOffsetSeconds": t})
            t += secs
        lap("Warmup", 2.5, 900, 130, 140)
        for i in range(5):
            lap("Active", 1.0, 246 - i, 163 + i, 170 + i)
            lap("Rest", 0.3, 120, 140, 160, 125)
        lap("Cooldown", 1.5, 540, 132, 140)
        return {"totals": {}, "lapData": laps, "data": []}

    def test_intervals_report_evenness_and_hr(self):
        out = run("analyze_session.py", self.write("a.json", self.laps()), "--lthr", 174,
                  "--threshold-pace", "4:10").stdout
        self.assertIn("Structured session: 5 reps in 1 kind", out)
        self.assertIn("pace variation", out)
        self.assertIn("LTHR 174", out)

    def test_json_row_for_intervals(self):
        data = dict(self.laps(), startTimestamp="2026-10-28T11:15:14")
        row = json.loads(run("analyze_session.py", self.write("a.json", data), "--json", "--title", "5x1k").stdout)
        self.assertEqual((row["date"], row["kind"], row["reps"], row["title"]), ("2026-10-28", "intervals", 5, "5x1k"))

    def test_auto_laps_inside_a_rep_are_joined(self):
        # 2 x 10 min tempo; the watch's 1-km auto-lap splits each rep into three laps
        steps = [("Warmup", 0, 2.5, 900, 128, 136)]
        for _ in range(2):
            steps += [("Active", 1, 1.0, 266, 152, 158), ("Active", 1, 1.0, 265, 160, 165),
                      ("Active", 1, 0.26, 69, 163, 166), ("Rest", 2, 0.4, 180, 135, 160)]
        steps += [("Cooldown", 4, 1.7, 600, 133, 139)]
        out = run("analyze_session.py", self.write("t.json", session(*steps)), "--lthr", 174).stdout
        self.assertIn("Structured session: 2 reps in 1 kind", out)
        self.assertIn("2 x 2.26 km (~10:00)", out)
        row = json.loads(run("analyze_session.py", self.write("t.json", session(*steps)), "--json").stdout)
        self.assertEqual((row["kind"], row["reps"]), ("intervals", 2))

    def test_easy_build_up_is_not_a_rep(self):
        # 2 km in Z2 as an Active step, then 8 x 1 km
        steps = [("Warmup", 0, 1.0, 370, 125, 132), ("Active", 1, 2.0, 700, 136, 141)]
        for _ in range(8):
            steps += [("Active", 2, 1.0, 254, 164, 172), ("Rest", 3, 0.1, 90, 140, 165)]
        out = run("analyze_session.py", self.write("e.json", session(*steps)), "--threshold-pace", "4:10").stdout
        self.assertIn("easy part: 2.0 km", out)
        self.assertIn("8 reps in 1 kind", out)
        out = run("analyze_session.py", self.write("e.json", session(*steps))).stdout  # no threshold given
        self.assertIn("8 reps in 1 kind", out)

    def test_mixed_reps_are_judged_by_kind(self):
        # 2 km + 1 km + 2 x 400 m at different paces: no fade or "pushed" verdict across kinds
        steps = [("Warmup", 0, 1.5, 500, 120, 130),
                 ("Active", 2, 1.0, 290, 140, 146), ("Active", 2, 1.0, 290, 146, 150), ("Rest", 3, 0.2, 180, 120, 150),
                 ("Active", 5, 1.0, 260, 154, 160), ("Rest", 6, 0.1, 120, 125, 158),
                 ("Active", 8, 0.4, 96, 150, 160), ("Rest", 9, 0.1, 60, 140, 160),
                 ("Active", 8, 0.4, 96, 152, 162), ("Rest", 9, 0.1, 60, 140, 160)]
        out = run("analyze_session.py", self.write("m.json", session(*steps))).stdout
        self.assertIn("4 reps in 3 kind", out)
        self.assertNotIn("faster than the first", out)

    def test_nested_sets_are_one_kind(self):
        # 4 x (4 x 30 s / 45 s): each set has its own step indexes on the watch
        steps = [("Warmup", 0, 1.0, 330, 125, 135)]
        for block in range(4):
            for _ in range(4):
                steps += [("Active", 2 + 4 * block, 0.127, 30, 160, 168), ("Rest", 3 + 4 * block, 0.16, 45, 162, 168)]
            steps += [("Rest", 5 + 4 * block, 0.35, 150, 140, 160)]
        out = run("analyze_session.py", self.write("n.json", session(*steps))).stdout
        self.assertIn("16 reps in 1 kind", out)
        self.assertIn("16 x 0.13 km", out)
        self.assertIn("pace (or power), not HR", out)
        self.assertNotIn("Steady run", out)

    def test_strides_after_an_easy_run(self):
        steps = [("Warmup", 0, 6.0, 2100, 128, 140)]
        for _ in range(6):
            steps += [("Active", 1, 0.083, 20, 138, 145), ("Rest", 2, 0.19, 70, 135, 148)]
        data = self.write("st.json", session(*steps))
        out = run("analyze_session.py", data).stdout
        self.assertIn("Strides: 6 x 0.08 km", out)
        self.assertIn("Steady run", out)
        self.assertEqual(json.loads(run("analyze_session.py", data, "--json").stdout)["kind"], "steady")

    def test_short_rep_pace_uses_lap_average_pace(self):
        # lap distances are rounded to 10 m; 30 s over 0.127 km is 3:56/km, not 30 s / 0.13 km = 3:51
        steps = [("Warmup", 0, 1.0, 330, 125, 135)]
        for _ in range(4):
            steps += [("Active", 1, 0.127, 30, 160, 168), ("Rest", 2, 0.3, 90, 150, 165)]
        out = run("analyze_session.py", self.write("p.json", session(*steps))).stdout
        self.assertIn("3:56", out)

    def test_steady_run_decoupling_from_series(self):
        series = []
        for i in range(0, 4200, 5):
            hr = 135 if i < 2400 else 140
            series.append({"time": i, "HeartRate": hr, "NGP": 6.0})
        data = {"totals": [{"name": "Duration", "value": 4200}, {"name": "Distance", "value": 11.7},
                           {"name": "NGP", "value": 6.0}, {"name": "Avg heart rate", "value": 137},
                           {"name": "El. Gain", "value": 40}],
                "lapData": [{"Intensity": "Interval", "TotalDistance": 1, "TotalTimerTime": 360}] * 11,
                "data": series}
        out = run("analyze_session.py", self.write("s.json", data), "--easy-cap", 145).stdout
        self.assertIn("Steady run", out)
        self.assertIn("decoupling after warm-up", out)
        self.assertIn("efficiency factor", out)


class PageDocs(TempDir):
    def test_rows_become_batch_writes(self):
        rows = [{"date": f"2026-10-{d:02d}", "hrv7": 50} for d in range(1, 61) if d <= 31] * 2
        rows = [dict(r, date=f"{r['date']}-{i}") for i, r in enumerate(rows)]  # 62 unique ids
        out = run("page_docs.py", self.write("rows.json", rows), "--collection", "trends", "--id", "date",
                  "--out-dir", self.dir / "docs").stdout
        batches = json.loads(out)
        self.assertEqual([len(b) for b in batches], [50, 12])
        self.assertTrue(pathlib.Path(batches[0][0]["file_path"]).exists())
        self.assertEqual(batches[0][0]["collection"], "trends")


class Terrain(TempDir):
    def test_classes(self):
        runs = [{"date": "2026-10-01", "km": 10, "elev_m": 30, "kind": "quality"},
                {"date": "2026-10-02", "km": 10, "elev_m": 180, "kind": "easy"},
                {"date": "2026-10-03", "km": 10, "elev_m": 600, "kind": "long"}]
        out = run("terrain.py", self.write("t.json", runs)).stdout
        self.assertIn("flat", out)
        self.assertIn("rolling", out)
        self.assertIn("mountain", out)


class ExportIcs(TempDir):
    def test_events_and_floating_times(self):
        plan = {"plan": [{"date": "2026-11-03", "title": "Easy 8 km", "minutes": 50, "km": 8},
                         {"date": "2026-11-04", "type": "rest", "title": "Rest"},
                         {"date": "2026-11-05", "title": "Intervals", "minutes": 60, "km": 11}]}
        out = self.dir / "p.ics"
        run("export_ics.py", self.write("p.json", plan), "--out", out, "--time", "07:00")
        text = out.read_text()
        self.assertEqual(text.count("BEGIN:VEVENT"), 2)
        self.assertIn("DTSTART:20261103T070000", text)
        self.assertNotIn("Easy 8 km · 8 km", text)


class HistorySummary(TempDir):
    def test_finds_peak_and_break(self):
        rows, ctl = [], 20.0
        for i in range(200):
            d = date(2026, 1, 1) + timedelta(days=i)
            tss = 0 if 100 <= i < 115 else 60
            ctl += (tss - ctl) / 42
            rows.append({"date": str(d), "tss": tss, "ctl": round(ctl, 1), "atl": 0, "tsb": 0})
        out = run("history_summary.py", "--fitness", self.write("f.json", {"daily_data": rows})).stdout
        self.assertTrue("Peak" in out or "peak" in out)
        self.assertIn("break", out.lower())


if __name__ == "__main__":
    unittest.main()
