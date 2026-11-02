#!/usr/bin/env python3
"""Weather for a run or a race: the forecast (up to 16 days ahead) or, further out, the typical
weather of that day from the last 10 years. Open-Meteo, no key. Only the place's coordinates
are sent (the race venue, or the runner's town for the morning brief), never anything else.

Usage:
  weather.py --lat 50.08 --lon 14.42 --date 2027-04-03 --start 10:00 --hours 1.5 [--json]

Prints temperature, dew point, wind and rain over the hours of the run, the source (forecast or
climate), and the heat adjustment the skill uses: above 15 °C, 1-2 % slower per 5 °C, the upper
end when humid (dew point 15 °C or more) [S39].
"""
import argparse
import json
import statistics
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

FORECAST = "https://api.open-meteo.com/v1/forecast"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FIELDS = "temperature_2m,dew_point_2m,wind_speed_10m,precipitation"
FORECAST_DAYS = 16
CLIMATE_YEARS, CLIMATE_SPAN = 10, 3          # years back, days either side
HEAT_FROM, HEAT_PER_5C, HUMID_DEW = 15, (1.0, 2.0), 15


def get(url, params):
    with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=15) as r:
        return json.load(r)


def hours_of(data, day, start_h, hours):
    """Hourly rows of `day` from start_h over the run's duration (inclusive of the last hour)."""
    h = data.get("hourly") or {}
    out = []
    for i, t in enumerate(h.get("time", [])):
        dt = datetime.fromisoformat(t)
        if dt.date().isoformat() == day and start_h <= dt.hour <= start_h + max(0, int(round(hours + 0.49)) - 1):
            out.append({k: h[k][i] for k in ("temperature_2m", "dew_point_2m", "wind_speed_10m", "precipitation")
                        if h.get(k) and h[k][i] is not None})
    return out


def summary(rows):
    if not rows:
        return None
    pick = lambda k: [r[k] for r in rows if k in r]
    return {"temp_c": round(statistics.mean(pick("temperature_2m")), 1),
            "temp_max_c": round(max(pick("temperature_2m")), 1),
            "dew_c": round(statistics.mean(pick("dew_point_2m")), 1) if pick("dew_point_2m") else None,
            "wind_kmh": round(statistics.mean(pick("wind_speed_10m"))) if pick("wind_speed_10m") else None,
            "rain_mm": round(sum(pick("precipitation")), 1) if pick("precipitation") else None}


def weather(lat, lon, day, start="09:00", hours=1.0, today=None):
    """{'source': 'forecast'|'climate', ...summary} or {'source': None, 'error': ...}."""
    today = today or date.today()
    start_h = int(start.split(":")[0])
    d = date.fromisoformat(day)
    try:
        if 0 <= (d - today).days < FORECAST_DAYS:
            data = get(FORECAST, {"latitude": lat, "longitude": lon, "hourly": FIELDS, "timezone": "auto",
                                  "start_date": day, "end_date": day})
            s = summary(hours_of(data, day, start_h, hours))
            return dict(s or {}, source="forecast") if s else {"source": None, "error": "no forecast rows"}
        temps, dews, winds = [], [], []
        for back in range(1, CLIMATE_YEARS + 1):
            try:
                past = d.replace(year=d.year - back)
            except ValueError:                       # 29 February
                past = d.replace(year=d.year - back, day=28)
            if past >= today:
                continue
            lo, hi = past - timedelta(days=CLIMATE_SPAN), past + timedelta(days=CLIMATE_SPAN)
            data = get(ARCHIVE, {"latitude": lat, "longitude": lon, "hourly": FIELDS, "timezone": "auto",
                                 "start_date": lo.isoformat(), "end_date": hi.isoformat()})
            for k in range(-CLIMATE_SPAN, CLIMATE_SPAN + 1):
                s = summary(hours_of(data, (past + timedelta(days=k)).isoformat(), start_h, hours))
                if s:
                    temps.append(s["temp_c"])
                    dews.append(s["dew_c"]) if s["dew_c"] is not None else None
                    winds.append(s["wind_kmh"]) if s["wind_kmh"] is not None else None
        if not temps:
            return {"source": None, "error": "no climate rows"}
        temps.sort()
        return {"source": "climate", "temp_c": round(statistics.median(temps), 1),
                "temp_p75_c": round(temps[int(len(temps) * 0.75)], 1), "temp_range_c": [temps[0], temps[-1]],
                "dew_c": round(statistics.median(dews), 1) if dews else None,
                "wind_kmh": round(statistics.median(winds)) if winds else None, "samples": len(temps)}
    except Exception as e:          # offline, API change: the plan goes on without weather
        return {"source": None, "error": str(e)}


def heat_pct(w):
    """(low, high) % slower for the heat, the upper end when humid; (0, 0) at 15 °C or below."""
    if not w or w.get("temp_c") is None:
        return 0.0, 0.0
    t = w.get("temp_p75_c") if w.get("source") == "climate" else w["temp_c"]
    steps = max(0.0, (t - HEAT_FROM) / 5)
    lo, hi = HEAT_PER_5C[0] * steps, HEAT_PER_5C[1] * steps
    if (w.get("dew_c") or 0) >= HUMID_DEW:
        lo = hi
    return round(lo, 1), round(hi, 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--start", default="09:00")
    ap.add_argument("--hours", type=float, default=1.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    w = weather(a.lat, a.lon, a.date, a.start, a.hours)
    w["heat_pct"] = list(heat_pct(w))
    if a.json:
        print(json.dumps(w, ensure_ascii=False))
        return
    if not w.get("source"):
        sys.exit(f"no weather: {w.get('error')}")
    what = "forecast" if w["source"] == "forecast" else f"typical for the date, {w['samples']} days in 10 years"
    extra = f", warm days {w['temp_p75_c']} °C" if w["source"] == "climate" else ""
    print(f"{a.date} {a.start}, {a.hours:g} h: {w['temp_c']} °C{extra}, dew point {w.get('dew_c')} °C, "
          f"wind {w.get('wind_kmh')} km/h ({what})")
    lo, hi = w["heat_pct"]
    print("heat: no adjustment" if not hi else f"heat: {lo:g}-{hi:g} % slower than in cool weather")


if __name__ == "__main__":
    main()
