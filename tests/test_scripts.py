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

    def test_run_off_the_agreed_days_fails(self):
        code, out = self.check(self.plan(15), days=["tue", "wed", "sat", "sun"])  # plan has Fri
        self.assertEqual(code, 1)
        self.assertIn("run on fri 2026-11-06, which is not one of this week's training days", out)

    def test_runs_on_agreed_days_pass_with_slovak_names(self):
        _, out = self.check(self.plan(15), days=["Ut", "Streda", "Piatok", "Ne"])
        self.assertIn("OK    all runs on this week's training days (tue, wed, fri, sun)", out)

    def test_missing_days_warns(self):
        _, out = self.check(self.plan(15))
        self.assertIn("WARN  no \"days\" given", out)

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
        self.assertEqual((trend[-1]["reasons"], trend[-1]["hrv_state"]), ([], "inside"))

    def test_trend_rows_carry_reason_codes(self):
        trend = json.loads(run("readiness.py", self.write("m.json", self.series(drop_from=50)), "--trend", 3).stdout)
        self.assertEqual(trend[-1]["hrv_state"], "below")
        self.assertIn("hrv_low_4d", trend[-1]["reasons"])

    def test_sleep_debt_counts_after_a_good_night(self):
        rows = self.series()
        for r, h in zip(rows[-4:], [5.4, 5.2, 5.6, 7.4]):
            r["sleep_h"] = h
        a = json.loads(run("readiness.py", self.write("m.json", rows), "--json").stdout)
        self.assertEqual((a["verdict"], a["reasons"]), ("AMBER", ["sleep_debt"]))

    def test_two_short_nights_are_not_debt(self):
        rows = self.series()
        for r, h in zip(rows[-4:], [5.4, 7.2, 5.6, 7.4]):
            r["sleep_h"] = h
        a = json.loads(run("readiness.py", self.write("m.json", rows), "--json").stdout)
        self.assertEqual(a["verdict"], "GREEN")

    def test_life_stress_four_or_more_is_a_flag(self):
        path = self.write("m.json", self.series())
        calm = json.loads(run("readiness.py", path, "--stress", 3, "--json").stdout)
        heavy = json.loads(run("readiness.py", path, "--stress", 4, "--json").stdout)
        self.assertEqual((calm["verdict"], calm["stress"]), ("GREEN", 3))
        self.assertEqual((heavy["verdict"], heavy["reasons"]), ("AMBER", ["life_stress"]))

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

    def test_steps_keep_their_own_unit(self):
        spec = {"threshold_pace": "4:10", "unit": "km", "metric": "pace", "steps": [
            {"name": "WU 12 min", "minutes": 12, "pct": [68, 76], "class": "warmUp", "pace": "6:00"},
            {"repeat": 3, "steps": [{"name": "stride", "seconds": 20, "pct": [115, 125], "class": "warmUp"},
                                    {"name": "jog", "seconds": 40, "pct": [55, 66], "class": "warmUp", "pace": "6:40"}]},
            {"repeat": 6, "steps": [{"name": "1 km", "km": 1, "pct": [98, 100]},
                                    {"name": "jog 75 s", "seconds": 75, "pct": [55, 66], "class": "rest", "pace": "6:40"}]},
            {"name": "CD 2 km", "km": 2, "pct": [62, 70], "class": "coolDown", "pace": "6:10"}]}
        out = tp_structure.build(spec)
        sw = out["structured_workout"]
        units = [[s["length"] for s in block["steps"]] for block in sw["structure"]]
        self.assertEqual(units, [
            [{"value": 720, "unit": "second"}],
            [{"value": 20, "unit": "second"}, {"value": 40, "unit": "second"}],
            [{"value": 1000, "unit": "meter"}, {"value": 75, "unit": "second"}],
            [{"value": 2000, "unit": "meter"}]])
        self.assertEqual(sw["primaryLengthMetric"], "distance")
        self.assertEqual(out["duration_minutes"], 60)
        self.assertEqual(out["distance_km"], 11.7)
        self.assertEqual(sw["polyline"][-1][0], 1.0)
        # a time-primary workout keeps the 1 km reps in metres too
        spec["unit"] = "time"
        sw = tp_structure.build(spec)["structured_workout"]
        self.assertEqual(sw["structure"][2]["steps"][0]["length"], {"value": 1000, "unit": "meter"})
        self.assertEqual(sw["primaryLengthMetric"], "duration")
        self.assertEqual(sw["structure"][-1]["end"], 3608)

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


class Durability(unittest.TestCase):
    def series(self, fade):
        # 2 h steady at 5:00/km NGP, HR 140 -> 140 + fade over the run
        return [{"time": t, "HeartRate": 140 + fade * t / 7200, "NGP": 5.0} for t in range(0, 7201, 10)]

    def test_late_fade_is_measured(self):
        import analyze_session
        flat = analyze_session.durability(self.series(0))
        fading = analyze_session.durability(self.series(12))
        self.assertAlmostEqual(flat[0], 0, places=1)
        self.assertGreater(fading[0], 4)
        self.assertIsNone(analyze_session.durability(self.series(0)[:400]))   # under 90 min


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

    def test_marathon_fade_after_km_30(self):
        # a fictional marathon: 30 km at 4:40, then 12.2 km at 5:10 (auto-laps, no workout steps)
        laps = [{"TotalDistance": 1.0, "TotalTimerTime": 280 if k < 30 else 310, "AverageHeartRate": 152}
                for k in range(42)] + [{"TotalDistance": 0.195, "TotalTimerTime": 60, "AverageHeartRate": 155}]
        data = {"totals": {"Distance": 42.195, "Duration": sum(l["TotalTimerTime"] for l in laps)}, "lapData": laps, "data": []}
        out = run("analyze_session.py", self.write("m.json", data)).stdout
        self.assertIn("pace to km 30 4:40/km", out)
        self.assertIn('"steady_pace": "4:40"', out)
        row = json.loads(run("analyze_session.py", self.write("m.json", data), "--json").stdout)
        self.assertEqual(row["steady_pace"], 280)
        self.assertGreater(row["fade_pct"], 9)

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


class Forecast(TempDir):
    """forecast.py on a fictional runner: a 10k and a half this autumn, ~40 km a week."""

    def inp(self, **extra):
        base = {"today": "2026-11-01", "weekly_km": 40, "training_pace": "5:40",
                "results": [{"date": "2026-10-11", "km": 10, "time": "45:00", "kind": "race", "name": "10k"},
                            {"date": "2026-10-25", "km": 21.0975, "time": "1:40:00", "kind": "race", "name": "HM"}]}
        base.update(extra)
        return base

    def plan(self, km, tss=None):
        weeks = [{"week_start": (date(2026, 11, 2) + timedelta(weeks=i)).isoformat(), "km": km, "tss": tss} for i in range(26)]
        races = [{"name": "Spring M", "date": "2027-04-25", "distance_km": 42.195, "priority": "A", "goal": "3:15:00"}]
        return str(self.write("plan.json", {"spec": {"races": races}, "weeks": weeks}))

    def rows(self, data):
        return {r["id"]: r for r in json.loads(run("forecast.py", self.write("f.json", data), "--json").stdout)}

    def test_current_form_follows_the_races(self):
        rows = self.rows(self.inp())
        ten, half = rows["2026-11-01_now_10"], rows["2026-11-01_now_21.0975"]
        self.assertLess(abs(ten["mid"] - 2700), 60)        # close to the 45:00 just run
        self.assertLess(abs(half["mid"] - 6000), 90)       # close to the 1:40 just run
        self.assertLessEqual(half["low"], half["mid"])
        self.assertLessEqual(half["mid"], half["high"])

    def test_marathon_uses_volume_not_riegel(self):
        out = run("forecast.py", self.write("f.json", self.inp())).stdout
        self.assertIn("too fast without marathon volume", out)
        mar = self.rows(self.inp())["2026-11-01_now_42.195"]
        riegel = 6000 * (42.195 / 21.0975) ** 1.06
        self.assertGreater(mar["mid"], riegel)

    def test_old_results_are_ignored(self):
        old = self.inp(results=[{"date": "2026-03-01", "km": 10, "time": "45:00", "kind": "race"}], weekly_km=None)
        out = run("forecast.py", self.write("f.json", old)).stdout
        self.assertIn("not enough data", out)

    def test_plan_volume_moves_the_marathon_forecast(self):
        low = self.rows(self.inp(plan=self.plan(40)))
        high = self.rows(self.inp(plan=self.plan(65)))
        key = "2026-11-01_2027-04-25_42.195"
        self.assertLess(high[key]["mid"], low[key]["mid"])
        self.assertEqual(high[key]["goal"], 3 * 3600 + 15 * 60)

    def test_goal_verdict_and_heat(self):
        races = [{"name": "Summer HM", "date": "2027-06-20", "distance_km": 21.0975, "goal": "1:30:00", "temp_c": 25}]
        out = run("forecast.py", self.write("f.json", self.inp(races=races))).stdout
        self.assertIn("out of reach", out)
        self.assertIn("25 °C", out)
        cool = self.rows(self.inp(races=[dict(races[0], temp_c=12)]))["2026-11-01_2027-06-20_21.0975"]
        hot = self.rows(self.inp(races=races))["2026-11-01_2027-06-20_21.0975"]
        self.assertGreater(hot["mid"], cool["mid"])

    def test_threshold_disagreement_is_flagged(self):
        out = run("forecast.py", self.write("f.json", self.inp(threshold_pace="4:05"))).stdout
        self.assertIn("the threshold predicts", out)

    def test_workout_efforts_are_a_floor_only(self):
        data = self.inp(results=[{"date": "2026-10-20", "km": 5, "time": "21:00", "kind": "effort"}], weekly_km=None)
        out = run("forecast.py", self.write("f.json", data)).stdout
        self.assertIn("5 km", out)
        self.assertIn("Marathon", out)
        self.assertIn("not enough data", out)   # no marathon from a 5 km workout effort

    def history(self):
        return [{"date": "2025-04-06", "km": 21.0975, "time": "1:36:00", "weekly_km": 55, "ctl": 50},
                {"date": "2025-05-04", "km": 42.195, "time": "3:28:00", "weekly_km": 58, "ctl": 52},
                {"date": "2024-10-13", "km": 10, "time": "44:30", "weekly_km": 40, "ctl": 36}]

    def test_projection_needs_ctl_and_planned_tss(self):
        key = "2026-11-01_2027-04-25_42.195"
        self.assertNotIn("proj_mid", self.rows(self.inp(plan=self.plan(60, 300), history=self.history()))[key])
        self.assertNotIn("proj_mid", self.rows(self.inp(plan=self.plan(60), history=self.history(), ctl=35))[key])

    def test_projection_follows_the_planned_load(self):
        key = "2026-11-01_2027-04-25_42.195"
        light = self.rows(self.inp(plan=self.plan(45, 230), history=self.history(), ctl=35, weekly_tss=210))[key]
        heavy = self.rows(self.inp(plan=self.plan(65, 330), history=self.history(), ctl=35, weekly_tss=210))[key]
        self.assertLessEqual(heavy["proj_low"], heavy["proj_mid"])
        self.assertLessEqual(heavy["proj_mid"], heavy["proj_high"])
        self.assertLess(heavy["proj_mid"], light["proj_mid"])
        out = run("forecast.py", self.write("f.json", self.inp(plan=self.plan(65, 330), history=self.history(), ctl=35))).stdout
        self.assertIn("if the plan happens", out)
        self.assertIn("marathon/half ratio", out)

    def test_projection_rescales_the_plans_tss(self):
        # plan estimates 3.5 TSS/km, the runner does 7: the projection must say it rescaled
        data = self.inp(plan=self.plan(60, 210), history=self.history(), ctl=35, weekly_tss=280)
        out = run("forecast.py", self.write("f.json", data)).stdout
        self.assertIn("plan TSS x 1.40", out)
        self.assertIn("-> 42 on race day", out)   # 210 TSS a week x 1.4 / 7 days, not 30

    def test_projection_without_weekly_tss_keeps_the_plans_tss(self):
        # CTL x 7 lags behind the load in a build: it must not shrink the plan
        out = run("forecast.py", self.write("f.json", self.inp(plan=self.plan(60, 350), history=self.history(), ctl=25))).stdout
        self.assertIn("no weekly_tss", out)
        self.assertNotIn("plan TSS x", out)
        self.assertIn("-> 50 on race day", out)   # 350 / 7 = 50 a day, reached over ~25 weeks

    def marathon_rows(self, steady=None, checks=None):
        history = [dict(h) for h in self.history()]
        if steady:
            history[1]["steady_pace"] = steady
        data = self.inp(plan=self.plan(60, 330), history=history, ctl=35, weekly_tss=230,
                        **({"checks": checks} if checks else {}))
        return self.rows(data)["2026-11-01_2027-04-25_42.195"]

    def test_a_faded_marathon_widens_the_projection_and_starts_at_half_the_fade(self):
        plain, faded = self.marathon_rows(), self.marathon_rows(steady="4:45")   # 3:28 run, 4:45/km to km 30
        self.assertLess(faded["proj_mid"], plain["proj_mid"])
        self.assertLess(faded["proj_low"], plain["proj_low"])                      # fast end: no fade
        self.assertAlmostEqual(faded["proj_high"], plain["proj_high"], delta=60)   # slow end: the fade comes back
        none_yet = self.marathon_rows(steady="4:45", checks=[{"race": "2027-04-25", "date": "2027-03-07", "name": "30 km",
                                                              "result": "planned"}])
        self.assertEqual(none_yet["proj_mid"], faded["proj_mid"])

    def test_marathon_checks_move_the_middle(self):
        checks = lambda *r: [{"race": "2027-04-25", "date": f"2027-03-{7 + 7 * i:02d}", "name": f"long run {i}", "result": x}
                             for i, x in enumerate(r)]
        start = self.marathon_rows(steady="4:45", checks=checks("planned", "planned", "planned", "planned"))
        held = self.marathon_rows(steady="4:45", checks=checks("held", "held", "planned", "planned"))
        all_held = self.marathon_rows(steady="4:45", checks=checks("held", "held", "held", "held"))
        faded = self.marathon_rows(steady="4:45", checks=checks("faded", "planned", "planned", "planned"))
        self.assertLess(held["proj_mid"], start["proj_mid"])
        self.assertLess(all_held["proj_mid"], held["proj_mid"])
        self.assertGreater(faded["proj_mid"], start["proj_mid"])
        self.assertLessEqual(all_held["proj_low"], all_held["proj_mid"])

    def test_milestones_come_from_the_plan(self):
        # the plan's milestones of the marathon are its checks; a verdict on target counts as held
        def rows(actual):
            weeks = [{"week_start": (date(2026, 11, 2) + timedelta(weeks=i)).isoformat(), "km": 60, "tss": 330,
                      "key_sessions": []} for i in range(26)]
            for i, d in enumerate(("2027-02-14", "2027-03-07", "2027-03-21", "2027-04-04")):
                week = next(w for w in weeks if w["week_start"] <= d < (date.fromisoformat(w["week_start"]) + timedelta(days=7)).isoformat())
                week["key_sessions"].append({"id": f"m{i}", "date": d, "slot": "long", "type": "mp_long", "title": f"long run {i}",
                                             "milestone": True, "race": "2027-04-25", "actual": actual if i < 2 else None})
            spec = {"races": [{"name": "Spring M", "date": "2027-04-25", "distance_km": 42.195, "priority": "A"}]}
            history = [dict(h) for h in self.history()]
            history[1]["steady_pace"] = "4:45"
            plan = str(self.write("plan.json", {"spec": spec, "weeks": weeks}))
            return self.rows(self.inp(plan=plan, history=history, ctl=35, weekly_tss=230))["2026-11-01_2027-04-25_42.195"]
        planned, held = rows(None), rows({"verdict": "on"})
        self.assertLess(held["proj_mid"], planned["proj_mid"])
        self.assertGreater(rows({"verdict": "on", "check": "faded"})["proj_mid"], planned["proj_mid"])   # the review's check wins

    def test_race_pace_checks_move_the_half_and_the_marathon_built_on_it(self):
        races = [{"name": "Spring HM", "date": "2027-03-21", "distance_km": 21.0975, "goal": "1:38:00"},
                 {"name": "Spring M", "date": "2027-04-25", "distance_km": 42.195, "goal": "3:25:00"}]
        def rows(*results):
            checks = [{"race": "2027-03-21", "date": f"2027-02-{5 + 7 * i:02d}", "name": f"HM pace {i}", "result": r}
                      for i, r in enumerate(results)]
            history = [{"date": "2026-02-15", "km": 21.0975, "time": "1:44:00", "weekly_km": 45, "ctl": 40},
                       {"date": "2026-03-28", "km": 21.0975, "time": "1:38:00", "weekly_km": 60, "ctl": 52}]
            data = self.inp(plan=self.plan(60, 330), history=history, ctl=35, weekly_tss=230, races=races, checks=checks)
            r = self.rows(data)
            return r["2026-11-01_2027-03-21_21.0975"], r["2026-11-01_2027-04-25_42.195"]
        (h0, m0), (h1, m1), (h2, m2) = rows("planned", "planned"), rows("held", "held"), rows("faded", "faded")
        self.assertLess(h1["proj_mid"], h0["proj_mid"])
        self.assertGreater(h2["proj_mid"], h0["proj_mid"])
        self.assertLess(m1["proj_mid"], m0["proj_mid"])     # the marathon is built on the half

    def test_projection_credits_a_runner_faster_at_a_lower_ctl(self):
        # last spring 1:36 at CTL 40 and 1:32 at CTL 50; today already 1:34 at CTL 30
        history = [{"date": "2026-02-15", "km": 21.0975, "time": "1:36:00", "weekly_km": 45, "ctl": 40},
                   {"date": "2026-03-28", "km": 21.0975, "time": "1:32:00", "weekly_km": 60, "ctl": 50}]
        races = [{"name": "Spring HM", "date": "2027-04-03", "distance_km": 21.0975, "goal": "1:30:00"}]
        data = self.inp(results=[{"date": "2026-10-25", "km": 21.0975, "time": "1:34:00", "kind": "race"}],
                        plan=self.plan(60, 350), history=history, ctl=30, weekly_tss=240, weekly_km=40, races=races)
        row = self.rows(data)["2026-11-01_2027-04-03_21.0975"]
        out = run("forecast.py", self.write("f.json", data)).stdout
        self.assertIn("per CTL point (with today's level / earlier races alone)", out)
        self.assertLess(row["proj_mid"], 5520)                 # back at CTL ~50: faster than the 1:32 run there
        self.assertLessEqual(row["proj_low"], row["proj_mid"])
        self.assertLessEqual(row["proj_mid"], row["proj_high"])


class KeySessions(TempDir):
    """season_plan.py roadmap / actuals --sessions / retarget on a fictional marathon season."""
    SPEC = {"title": "Test", "lang": "en", "start": "2026-11-09", "current": {"km": 40, "long_km": 15},
            "runs_per_week": 5, "easy_pace": "6:00", "peak_km": 65,
            "races": [{"name": "Half", "date": "2027-03-21", "distance_km": 21.1, "priority": "B", "goal": "1:38:00"},
                      {"name": "Marathon", "date": "2027-04-25", "distance_km": 42.2, "priority": "A", "goal": "3:25:00"}]}

    def plan(self, *extra, spec=None):
        path = self.write("plan.json", season_plan.generate(dict(spec or self.SPEC)))
        proc = run("season_plan.py", "roadmap", path, "--threshold-pace", "4:25", "--lthr", 168, *extra, "--out", path)
        return path, json.loads(path.read_text()), proc.stderr

    @staticmethod
    def sessions(plan):
        return [s for w in plan["weeks"] for s in w.get("key_sessions", [])]

    def test_threshold_ladder_adds_reps_then_length(self):
        _, plan, _ = self.plan()
        q1 = [s["title"] for w in plan["weeks"] if w["phase"] == "base" and w["role"] == "build"
              for s in w["key_sessions"] if s["slot"] == "q1"]
        self.assertEqual(q1[:5], ["5x 1 km at threshold", "6x 1 km at threshold", "7x 1 km at threshold",
                                  "3x 2 km at threshold", "4x 2 km at threshold"])
        first = next(s for s in self.sessions(plan) if s["title"] == "5x 1 km at threshold")
        self.assertEqual(first["target"]["pace"], "4:25–4:30")
        self.assertEqual(first["date"], "2026-11-10")              # Tuesday by default

    def test_marathon_milestones(self):
        _, plan, _ = self.plan()
        ms = [s for s in self.sessions(plan) if s["milestone"]]
        half = [s for s in ms if s["race"] == "2027-03-21"]
        mara = [s for s in ms if s["race"] == "2027-04-25"]
        self.assertEqual(len(half) + len(mara), len(ms))             # every milestone is on a race's road
        self.assertTrue(4 <= len(half) <= 6 and 4 <= len(mara) <= 6, (len(half), len(mara)))
        self.assertFalse(any(s["type"] == "race" for s in ms))       # a race is the end of its road
        self.assertTrue(any(s["type"] in ("test", "hm_pace") for s in half))
        self.assertTrue(all(s["slot"] == "long" for s in mara))
        self.assertEqual(sum(1 for s in mara if s.get("fuel")), 1)
        cont = next(s for s in ms if s["type"] == "mp")
        days_out = (date(2027, 4, 25) - date.fromisoformat(cont["date"])).days
        self.assertTrue(14 <= days_out <= 28, cont["date"])
        self.assertTrue(18 <= cont["target"]["mp_km"] <= 23)
        self.assertEqual(cont["target"]["pace"], "4:50–4:53")      # the 3:25 goal pace
        week_before = (date.fromisoformat(cont["date"]) - timedelta(days=7)).isoformat()
        self.assertNotIn(week_before[:10], [s["date"] for s in self.sessions(plan) if s["type"] in ("mp", "mp_long")])
        self.assertTrue(any(s["type"] == "test" for s in ms))

    def test_goal_beyond_the_threshold_is_capped_and_reported(self):
        spec = json.loads(json.dumps(self.SPEC))
        spec["races"][1]["goal"] = "3:05:00"
        _, plan, err = self.plan(spec=spec)
        self.assertIn("faster than the threshold supports", err)
        mp = next(s for s in self.sessions(plan) if s["type"] == "mp_long")
        self.assertEqual(mp["target"]["pace"], "4:35–4:38")         # ~4:37 = 4:25 x 1.075 / 1.03, not the 4:23 goal pace

    def test_fewer_runs_drop_the_second_quality_session(self):
        _, plan, _ = self.plan("--runs", 4)
        self.assertFalse([s for s in self.sessions(plan) if s["slot"] == "q2"])

    def actuals(self, path, *extra):
        rows = [{"date": "2026-11-10", "km": 11, "minutes": 58, "kind": "intervals", "reps": 5, "rep_km": 1.0,
                 "rep_pace": 267, "rep_max_hr": 166},
                {"date": "2026-11-17", "km": 11, "minutes": 60, "kind": "intervals", "reps": 6, "rep_km": 1.0,
                 "rep_pace": 280, "rep_max_hr": 175}]
        hist = self.write("hist.json", {"workouts": []})
        proc = run("season_plan.py", "actuals", path, "--history", hist, "--sessions", self.write("rows.json", rows),
                   "--today", "2026-11-23", *extra, "--out", path)
        return json.loads(path.read_text()), proc.stderr

    def test_results_are_judged_and_a_hold_back_only_proposed(self):
        path, _, _ = self.plan()
        plan, err = self.actuals(path)
        by_date = {s["date"]: s for s in self.sessions(plan) if s["slot"] == "q1"}
        self.assertEqual(by_date["2026-11-10"]["actual"]["verdict"], "on")
        self.assertEqual(by_date["2026-11-17"]["actual"]["verdict"], "under")    # slow and over the HR cap
        hills = next(s for s in self.sessions(plan) if s["date"] == "2026-11-20")
        self.assertEqual(hills["status"], "missed")
        # the coach decides (heat, hills, travel...): nothing moves on its own
        self.assertEqual(by_date["2026-11-24"]["title"], "7x 1 km at threshold")
        self.assertIn("PROPOSE", err)
        self.assertIn("repeat that step next time (6x 1 km at threshold)", err)

    def test_hold_back_applies_when_the_coach_says_so(self):
        path, _, _ = self.plan()
        plan, _ = self.actuals(path, "--hold-back")
        by_date = {s["date"]: s for s in self.sessions(plan) if s["slot"] == "q1"}
        self.assertEqual(by_date["2026-11-24"]["title"], "6x 1 km at threshold")  # repeated, not 7x
        self.assertEqual(by_date["2026-11-24"]["status"], "adjusted")
        self.assertTrue(any("held back" in c["text"] for c in plan["changes"]))

    def test_default_draft_keeps_its_own_rules(self):
        path, plan, _ = self.plan()
        proc = run("season_plan.py", "check-roadmap", path)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        # quality waits 3 days after the half (Sunday 21 March), big marathon-pace runs alternate
        after = [s for s in self.sessions(plan) if s["type"] != "long" and "2027-03-22" <= s["date"] <= "2027-03-24"]
        self.assertFalse(after)
        big = [s["date"] for s in self.sessions(plan) if s["type"] in ("mp", "mp_long") and s["target"].get("mp_km", 0) >= 14]
        self.assertTrue(all((date.fromisoformat(b) - date.fromisoformat(a)).days > 8 for a, b in zip(big, big[1:])), big)

    def test_check_catches_the_coachs_mistakes(self):
        path, plan, _ = self.plan()
        week = next(w for w in plan["weeks"] if w["week_start"] == "2027-03-22")   # the week after the half
        week["key_sessions"].insert(0, {"id": "2027-03-23-q1", "date": "2027-03-23", "slot": "q1", "type": "threshold",
                                        "title": "4x 2 km", "target": {"pct": [97, 99], "pace": "4:00–4:05"},
                                        "basis": [97, 99], "milestone": False, "status": "planned", "actual": None, "note": ""})
        path.write_text(json.dumps(plan))
        proc = run("season_plan.py", "check-roadmap", path)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("2 day(s) after", proc.stdout)            # Tuesday after a Sunday half
        self.assertIn("doesn't match", proc.stdout)             # hand-written pace
        run("season_plan.py", "retarget", path, "--out", path)  # fills the pace from the basis
        self.assertNotIn("doesn't match", run("season_plan.py", "check-roadmap", path).stdout)

    def test_retarget_without_a_new_threshold_only_fills_targets(self):
        path, plan, _ = self.plan()
        week = plan["weeks"][1]
        week["key_sessions"].append({"id": "x", "date": week["week_start"], "slot": "q2", "type": "tempo",
                                     "title": "coach's own: 3x 10 min by HR on the hill", "target": {},
                                     "basis": [92, 95], "milestone": False, "status": "planned", "actual": None,
                                     "note": "no flat ground on Monday"})
        path.write_text(json.dumps(plan))
        run("season_plan.py", "retarget", path, "--today", "2026-11-01", "--out", path)
        plan = json.loads(path.read_text())
        mine = next(s for s in self.sessions(plan) if s["id"] == "x")
        self.assertEqual(mine["target"]["pace"], "4:39–4:48")
        self.assertFalse(plan.get("changes"))                   # nothing re-targeted, nothing logged

    def test_retarget_moves_future_paces_and_logs_it(self):
        path, _, _ = self.plan()
        proc = run("season_plan.py", "retarget", path, "--threshold-pace", "4:20", "--today", "2026-11-12", "--out", path)
        plan = json.loads(path.read_text())
        by_date = {s["date"]: s for s in self.sessions(plan)}
        self.assertEqual(by_date["2026-11-10"]["target"]["pace"], "4:25–4:30")   # past: unchanged
        self.assertEqual(by_date["2026-11-17"]["target"]["pace"], "4:20–4:25")
        self.assertIn("threshold 4:25 -> 4:20", proc.stderr)
        self.assertIn("re-targeted", plan["changes"][-1]["text"])

    def test_half_marathon_pace_doesnt_drop_into_the_specific_phase(self):
        spec = {"title": "T", "lang": "en", "start": "2026-11-09", "current": {"km": 35, "long_km": 14},
                "runs_per_week": 4, "easy_pace": "6:30", "peak_km": 50,
                "races": [{"name": "Half", "date": "2027-03-14", "distance_km": 21.1, "priority": "A", "goal": "1:45:00"}]}
        _, plan, _ = self.plan(spec=spec)
        hm = [s["title"] for w in plan["weeks"] if w["role"] == "build" for s in w["key_sessions"]
              if s["slot"] == "q1" and s["type"] == "hm_pace" and not s["milestone"]]
        km = [int(t.split("x")[0]) * float(t.split("x ")[1].split(" km")[0]) if "x " in t else float(t.split(" km")[0]) for t in hm]
        self.assertEqual(km, sorted(km), hm)                    # never less half-marathon-pace work than before

    def test_replan_keeps_the_roadmap(self):
        path, _, _ = self.plan()
        run("season_plan.py", "replan", path, "--from", "2027-01-04", "--current-km", 45, "--out", path)
        plan = json.loads(path.read_text())
        self.assertTrue(all(w.get("key_sessions") for w in plan["weeks"] if w["role"] != "recovery"))
        self.assertIn("roadmap", plan)


class Zones(TempDir):
    """zones.py: one table of training zones, and proposals from new evidence (fictional runner)."""

    @staticmethod
    def band(label, lo, hi):
        return {"label": label, "minimum": lo, "maximum": hi}

    def tp_blocks(self):
        thr = 1000 / 260                                     # 4:20/km
        ratios = [("Zone 1", .5995, .7599), ("Zone 2", .7599, .8711), ("Zone X", .8711, .9294), ("Zone 3", .9294, 1.0),
                  ("Zone Y", 1.0, 1.0204), ("Zone 4", 1.0204, 1.1521), ("Zone 5", 1.1521, 1000 / thr)]
        hr = [("Zone 1", 121, 136), ("Zone 2", 136, 152), ("Zone X", 152, 159), ("Zone 3", 159, 168),
              ("Zone Y", 168, 171), ("Zone 4", 171, 177), ("Zone 5", 177, 255)]
        return {"speedZones": [{"threshold": 4.0, "workoutTypeId": 0, "zones": []},
                               {"threshold": thr, "workoutTypeId": 3,
                                "zones": [self.band(l, a * thr, b * thr) for l, a, b in ratios]}],
                "heartRateZones": [{"threshold": 168, "maximumHeartRate": 186, "restingHeartRate": 50, "workoutTypeId": 0,
                                    "zones": [self.band(*z) for z in hr]}],
                "powerZones": [{"threshold": 300, "workoutTypeId": 0,
                                "zones": [self.band("1", 0, 165), self.band("2", 166, 225), self.band("3", 226, 2000)]}]}

    def test_table_from_thresholds(self):
        out = run("zones.py", "show", "--threshold-pace", "4:20", "--lthr", 168, "--lang", "sk").stdout
        self.assertTrue(out.startswith("Tréningové zóny"))
        z3 = next(l for l in out.splitlines() if l.startswith("Z3"))
        self.assertIn("4:20–4:40", z3)
        self.assertIn("159–168", z3)
        self.assertIn("Ľahký beh: tep do 139", out)

    def test_table_from_trainingpeaks_prefers_the_run_set(self):
        path = self.write("zones.json", self.tp_blocks())
        docs = json.loads(run("zones.py", "show", "--tp-settings", path, "--json", "--date", "2026-11-02").stdout)
        cur = next(d for d in docs if d["id"] == "current")
        self.assertEqual(cur["threshold_pace"], "4:20")      # the run set, not the general 4:10
        self.assertEqual(len(cur["rows"]), 7)
        self.assertEqual(cur["rows"][-1]["hr_hi"], None)     # TP's 255 means "and above"
        self.assertEqual(cur["power"][-1]["w_hi"], None)
        self.assertEqual(cur["lthr"], 168)
        self.assertTrue(any(d["id"] == "2026-11-02" for d in docs))   # a history entry for the page

    def test_any_trainingpeaks_method_reads_the_same_way(self):
        blocks = self.tp_blocks()
        friel = [("Zone 1: Recovery", 0, 142), ("Zone 2: Aerobic", 143, 150), ("Zone 3: Tempo", 151, 158),
                 ("Zone 4: SubThreshold", 159, 167), ("Zone 5A: SuperThreshold", 168, 171),
                 ("Zone 5B: Aerobic Capacity", 172, 178), ("Zone 5C: Anaerobic Capacity", 179, 255)]
        blocks["heartRateZones"][0]["zones"] = [self.band(*z) for z in friel][:6] + [self.band(*friel[6])]
        blocks["heartRateZones"][0]["zones"].insert(0, self.band("Zone 0", 0, 100))   # 8 HR bands vs 7 pace bands
        cur = json.loads(run("zones.py", "show", "--tp-settings", self.write("z.json", blocks), "--json").stdout)[0]
        self.assertEqual(cur["method"], "80/20")                      # from the pace set
        self.assertEqual(len(cur["hr_rows"]), 8)                      # HR in its own table
        five_a = next(r for r in cur["hr_rows"] if r["name"].startswith("Zone 5A"))
        self.assertEqual(five_a["use"], "threshold")                  # 168-171 at LTHR 168
        self.assertIn("easy", next(r for r in cur["hr_rows"] if r["name"].startswith("Zone 2"))["use"])

    def test_daniels_paces_match_his_tables(self):
        out = run("zones.py", "show", "--method", "daniels", "--race", "10=41:21").stdout   # VDOT 50
        self.assertIn("VDOT 50.0", out)
        self.assertIn("4:15", next(l for l in out.splitlines() if l.startswith("T ")))      # T 6:51/mile
        self.assertIn("4:31", next(l for l in out.splitlines() if l.startswith("M ")))      # M 3:10:49

    def test_heart_rate_reserve_zones(self):
        out = run("zones.py", "show", "--method", "hrr", "--max-hr", 186, "--rest-hr", 50).stdout
        self.assertIn("132–145", next(l for l in out.splitlines() if l.strip().startswith("Z2")))

    def test_aerobic_threshold_from_decoupling(self):
        runs = [{"minutes": 75, "avg_hr": 138, "decoupling": 2.1, "gain_per_km": 6},
                {"minutes": 90, "avg_hr": 142, "decoupling": 3.8, "gain_per_km": 8},
                {"minutes": 70, "avg_hr": 149, "decoupling": 6.9, "gain_per_km": 5},
                {"minutes": 60, "avg_hr": 151, "decoupling": 8.0, "gain_per_km": 25},     # hilly: ignored
                {"minutes": 30, "avg_hr": 150, "decoupling": 1.0, "gain_per_km": 3}]      # short: ignored
        out = json.loads(run("zones.py", "lt1", self.write("runs.json", runs), "--lthr", 168, "--json").stdout)
        self.assertEqual(out["runs"], 3)
        self.assertEqual(out["estimate"], 146)
        self.assertEqual(out["suggested_cap"], 142)                   # proven, not the guess above it
        self.assertEqual(out["default_cap"], 139)

    def test_the_watch_detection_counts_as_evidence(self):
        out = self.suggest(device=[{"date": "2026-10-30", "source": "Garmin", "threshold_pace": "4:15", "lthr": 170}])
        self.assertLess(out["pace"][0], 260)
        self.assertEqual(out["lthr"][0], 170)
        self.assertIn("Garmin", out["pace"][1])

    def evidence(self, **extra):
        base = {"today": "2026-11-02", "current": {"threshold_pace": "4:25", "lthr": 166, "max_hr": 186, "rest_hr": 50,
                                                   "set_on": "2026-07-20"}}
        base.update(extra)
        return self.write("ev.json", base)

    def suggest(self, **extra):
        return json.loads(run("zones.py", "suggest", self.evidence(**extra), "--json").stdout)

    def test_flat_half_proposes_threshold_lthr_and_max_hr(self):
        out = self.suggest(races=[{"date": "2026-10-25", "km": 21.0975, "time": "1:31:40", "avg_hr": 171, "flat": True}],
                           max_hr_seen=[{"date": "2026-10-25", "hr": 190}])
        self.assertLess(out["pace"][0], 265)                  # faster than 4:25
        self.assertEqual(out["lthr"][0], 171)
        self.assertEqual(out["max_hr"][0], 190)

    def test_small_changes_and_bad_races_change_nothing(self):
        out = self.suggest(races=[{"date": "2026-10-25", "km": 10, "time": "43:05", "flat": True},   # = 4:25 threshold
                                  {"date": "2026-10-11", "km": 21.0975, "time": "1:30:00", "flat": False}])
        self.assertIsNone(out["pace"])
        self.assertTrue(any("confirmed" in n for n in out["notes"]))
        self.assertTrue(any("hilly or hot" in n for n in out["notes"]))

    def test_disagreeing_sources_are_not_averaged(self):
        out = self.suggest(tests=[{"date": "2026-10-20", "minutes": 30, "km": 6.6, "hr_last20": 168}],
                           races=[{"date": "2026-10-25", "km": 21.0975, "time": "1:31:40", "flat": True}])
        self.assertIsNone(out["pace"])
        self.assertTrue(any("disagree" in n for n in out["notes"]))

    def test_sessions_hint_and_old_zones_ask_for_a_retest(self):
        hint = self.suggest(sessions=[{"date": "2026-10-14", "rep_pace": 255, "rep_max_hr": 162},
                                      {"date": "2026-10-28", "rep_pace": 254, "rep_max_hr": 163}])
        self.assertIsNone(hint["pace"])                       # a hint, not a number
        self.assertTrue(any("probably faster" in n for n in hint["notes"]))
        old = self.suggest()
        self.assertTrue(any("retest" in n for n in old["notes"]))


class RacePlan(TempDir):
    """race_plan.py and weather.py on a fictional half marathon (no network: weather given)."""

    def gpx(self):
        pts = []
        for i in range(0, 2111):
            km = i / 100
            ele = 200 + (25 * min(1, max(0, km - 6)) if km < 14 else 25 * max(0, 1 - (km - 14)))
            pts.append(f'<trkpt lat="{48.15 + km / 111.0:.6f}" lon="17.1"><ele>{ele:.1f}</ele></trkpt>')
        path = self.dir / "c.gpx"
        path.write_text('<?xml version="1.0"?><gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
                        + "".join(pts) + "</trkseg></trk></gpx>")
        return path

    def plan(self, **extra):
        cfg = {"race": {"name": "City Half", "date": "2027-04-03", "start": "10:00", "distance_km": 21.0975},
               "forecast": {"low": 5330, "mid": 5420, "high": 5540}, "goal": "1:29:30", "course_gpx": str(self.gpx()),
               "aid_km": [5, 10, 15, 20], "weight_kg": 70, "gut_trained_gph": 60, "weather": {"temp_c": 10, "dew_c": 4,
                                                                                                "source": "forecast"}}
        cfg.update(extra)
        return json.loads(run("race_plan.py", self.write("r.json", cfg), "--json", "--no-weather").stdout)

    def test_splits_follow_the_course_and_add_up(self):
        out = self.plan()
        self.assertEqual(out["target"], "1:29:30")
        self.assertEqual(out["splits"][-1]["cum"], "1:29:30")
        by_km = {s["km"]: s for s in out["splits"]}
        self.assertGreater(by_km[7]["grade"], 2)             # the climb
        self.assertGreater(paces.parse_pace(by_km[7]["pace"]), paces.parse_pace(by_km[3]["pace"]))
        self.assertLess(paces.parse_pace(by_km[15]["pace"]), paces.parse_pace(by_km[3]["pace"]))
        self.assertEqual(out["climb_m"], 25)

    def test_weather_typed_in_is_shown(self):
        cfg = {"race": {"name": "T", "date": "2027-04-03", "distance_km": 21.0975}, "goal": "1:35:00",
               "weather": {"temp_c": 21, "dew_c": 16}}
        out = run("race_plan.py", self.write("g.json", cfg), "--no-weather").stdout
        self.assertIn("Weather: 21 °C, dew point 16 °C (given)", out)
        self.assertIn("slower for the heat", out)

    def test_heat_moves_the_range_and_a_fast_goal_is_capped(self):
        warm = self.plan(weather={"temp_c": 25, "dew_c": 17, "source": "forecast"}, goal="1:27:00")
        self.assertEqual(warm["heat_pct"], [4.0, 4.0])        # humid: the upper end of 2 x (1-2 %)
        self.assertNotEqual(warm["target"], "1:27:00")        # the fast end of the range, not the goal
        self.assertEqual(warm["verdict"], "out")

    def test_fuelling_is_capped_by_the_gut_and_matched_to_aid_stations(self):
        m = self.plan(race={"name": "M", "date": "2027-05-02", "start": "09:00", "distance_km": 42.195},
                      forecast={"low": 12000, "mid": 12300, "high": 12700}, goal="3:25:00", course_gpx=None,
                      aid_km=[5, 10, 15, 20, 25, 30, 35, 40], gut_trained_gph=60)
        self.assertEqual(m["gph"], 60)                        # 60-90 g/h for a marathon, capped at 60
        self.assertGreaterEqual(len(m["fuel"]), 7)
        self.assertTrue(all(f["aid_km"] is None or abs(f["aid_km"] - f["km"]) <= 1 for f in m["fuel"]))
        self.assertEqual(m["pre"]["load"], [700, 840])         # 10-12 g/kg for 70 kg
        half = self.plan()                                    # ~90 min: the gels alone fall short of the rate
        self.assertEqual(half["carbs_total_g"], round(half["gph"] * paces.parse_time(half["target"]) / 3600))
        self.assertEqual(half["drink_carbs_g"], half["carbs_total_g"] - 25 * len(half["fuel"]))
        self.assertGreater(half["drink_carbs_g"], 0)

    def test_heat_rule(self):
        import weather
        self.assertEqual(weather.heat_pct({"temp_c": 12}), (0.0, 0.0))
        self.assertEqual(weather.heat_pct({"temp_c": 20, "dew_c": 8}), (1.0, 2.0))
        self.assertEqual(weather.heat_pct({"source": "climate", "temp_c": 12, "temp_p75_c": 20}), (1.0, 2.0))


class HealthLog(TempDir):
    def note(self, day, *args):
        n = json.loads(run("health_log.py", "note", *args).stdout)
        n["date"] = day
        return n

    def read(self, notes):
        return json.loads(run("health_log.py", "read", self.write("n.json", {"notes": notes}), "--today", "2026-11-02",
                              "--json").stdout)

    def test_note_format_round_trips(self):
        n = self.note("2026-11-01", "--type", "pain", "--part", "left calf", "--score", "3", "--when", "during")
        self.assertEqual(n["title"], "Pain: left calf 3/10")
        self.assertIn("rc: type=pain; part=left calf; score=3", n["description"])
        issue = self.read([n])["issues"][0]
        self.assertEqual((issue["level"], issue["score"]), ("easy", 3))

    def test_rising_pain_means_stop_and_resolved_is_quiet(self):
        notes = [self.note(d, "--type", "pain", "--part", "calf", "--score", str(sc), "--status", st)
                 for d, sc, st in (("2026-10-25", 2, "new"), ("2026-10-28", 3, "worse"), ("2026-10-31", 4, "worse"))]
        notes += [self.note("2026-10-10", "--type", "pain", "--part", "knee", "--score", "2"),
                  self.note("2026-10-14", "--type", "pain", "--part", "knee", "--score", "0", "--status", "resolved")]
        issues = {i.get("part"): i for i in self.read(notes)["issues"]}
        self.assertEqual(issues["calf"]["level"], "stop")
        self.assertFalse(issues["knee"]["active"])

    def test_fever_means_no_running(self):
        out = self.read([self.note("2026-11-01", "--type", "illness", "--symptoms", "flu", "--fever")])
        ill = next(i for i in out["issues"] if i["type"] == "illness")
        self.assertEqual(ill["level"], "stop")
        self.assertTrue(any(i["type"] == "note" for i in out["issues"]))   # see a doctor if chest pain...

    def test_other_notes_are_ignored(self):
        self.assertEqual(self.read([{"date": "2026-11-01", "title": "Running coach profile", "description": "x"}])["issues"], [])


class BlockReport(TempDir):
    def test_block_summary(self):
        plan = season_plan.generate(dict(KeySessions.SPEC))
        for w in plan["weeks"][:3]:
            w["actual_km"] = w["km"] * 0.8
        path = self.write("plan.json", plan)
        sessions = self.write("s.json", [{"date": "2026-11-15", "kind": "steady", "ef": 1.2, "durability": 5.5},
                                         {"date": "2026-11-29", "kind": "steady", "ef": 1.24, "durability": 4.0}])
        out = json.loads(run("block_report.py", path, "--from", "2026-11-09", "--to", "2026-11-23",
                             "--sessions", sessions, "--json").stdout)
        self.assertEqual(out["weeks"], 3)
        self.assertEqual(out["pct"], 80)
        self.assertTrue(any("80 %" in t for t in out["takeaways"]))
        self.assertEqual(out["durability"], [5.5, 4.0])     # the block runs to Sunday 29 Nov


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
