import json, os, glob
from collections import defaultdict

DIR = os.path.dirname(os.path.abspath(__file__))

CPCB_STATIONS = {
    "1553": "Bapuji Nagar", "1554": "Hebbal", "1555": "Hombegowda Nagar",
    "1556": "Jayanagar 5th Block", "1558": "Silk Board", "162": "BTM Layout",
    "163": "Peenya", "164": "BWSSB Kadabesanahalli", "165": "City Railway Stn",
    "166": "Sanegurava Halli", "5678": "RVCE-Mailasandra",
}

def load_data(pattern):
    all_data = {}
    for f in glob.glob(os.path.join(DIR, pattern)):
        try:
            with open(f) as fh:
                d = json.load(fh)
            if d.get("data"):
                all_data[d["id"]] = d
        except:
            pass
    return all_data

# Load all March data
cpcb_mar = load_data("cpcb_*_mar2026.json")
airnet_mar = load_data("airnet_*_mar2026.json")

print(f"Loaded: {len(cpcb_mar)} CPCB + {len(airnet_mar)} Airnet stations\n")

# ---- Combined city-wide daily averages ----
daily = defaultdict(lambda: {"pm25": [], "pm10": [], "temp": [], "humid": []})

for datasets in [cpcb_mar, airnet_mar]:
    for sid, d in datasets.items():
        for day in d["data"]:
            date = day["date"]
            for key in ["pm25", "pm10", "temp", "humid"]:
                if day.get(key) is not None:
                    daily[date][key].append(day[key])

def avg(lst):
    return sum(lst) / len(lst) if lst else None

print("=" * 80)
print("COMBINED CITY-WIDE DAILY AVERAGES (CPCB + Airnet, March 2026)")
print("=" * 80)
print(f"{'Date':<14} {'PM2.5':>7} {'PM10':>7} {'Temp':>6} {'Humid':>6} {'#PM25':>6}")
print("-" * 50)

march_data = []
for date in sorted(daily.keys()):
    d = daily[date]
    pm25 = avg(d["pm25"])
    pm10 = avg(d["pm10"])
    temp = avg(d["temp"])
    humid = avg(d["humid"])
    n = len(d["pm25"])
    march_data.append({"date": date, "pm25": pm25, "pm10": pm10, "temp": temp, "humid": humid, "n": n})
    print(f"{date:<14} {pm25:>7.1f} {pm10:>7.1f} {temp:>6.1f} {humid:>6.1f} {n:>6}")

# ---- Day-over-day changes ----
print("\n" + "=" * 80)
print("DAY-OVER-DAY PM2.5 CHANGES (biggest swings)")
print("=" * 80)

changes = []
for i in range(1, len(march_data)):
    prev = march_data[i-1]
    curr = march_data[i]
    if prev["pm25"] and curr["pm25"]:
        delta = curr["pm25"] - prev["pm25"]
        pct = (delta / prev["pm25"]) * 100
        changes.append((curr["date"], delta, pct, curr["pm25"], curr.get("temp"), curr.get("humid")))

changes.sort(key=lambda x: abs(x[1]), reverse=True)
print(f"\n{'Date':<14} {'Delta':>8} {'%Chg':>7} {'PM2.5':>7} {'Temp':>6} {'Humid':>6}")
print("-" * 55)
for date, delta, pct, pm25, temp, humid in changes[:15]:
    temp_s = f"{temp:>6.1f}" if temp else "   N/A"
    humid_s = f"{humid:>6.1f}" if humid else "   N/A"
    print(f"{date:<14} {delta:>+8.1f} {pct:>+6.1f}% {pm25:>7.1f} {temp_s} {humid_s}")

# ---- Correlation: temperature/humidity vs PM2.5 ----
print("\n" + "=" * 80)
print("WEATHER vs POLLUTION CORRELATION")
print("=" * 80)

pm25_vals = [d["pm25"] for d in march_data if d["pm25"] and d["temp"]]
temp_vals = [d["temp"] for d in march_data if d["pm25"] and d["temp"]]
humid_vals = [d["humid"] for d in march_data if d["pm25"] and d["humid"]]
pm25_h = [d["pm25"] for d in march_data if d["pm25"] and d["humid"]]

def correlation(x, y):
    n = len(x)
    mx, my = sum(x)/n, sum(y)/n
    num = sum((xi-mx)*(yi-my) for xi, yi in zip(x, y))
    den = (sum((xi-mx)**2 for xi in x) * sum((yi-my)**2 for yi in y)) ** 0.5
    return num / den if den else 0

if pm25_vals and temp_vals:
    r_temp = correlation(pm25_vals, temp_vals)
    print(f"  PM2.5 vs Temperature: r = {r_temp:+.3f}")

if pm25_h and humid_vals:
    r_humid = correlation(pm25_h, humid_vals)
    print(f"  PM2.5 vs Humidity:    r = {r_humid:+.3f}")

# ---- Weekly pattern (weekday vs weekend) ----
print("\n" + "=" * 80)
print("WEEKDAY vs WEEKEND PM2.5")
print("=" * 80)

from datetime import datetime
weekday_vals = []
weekend_vals = []
for d in march_data:
    if d["pm25"] is None:
        continue
    dt = datetime.strptime(d["date"], "%Y-%m-%d")
    if dt.weekday() < 5:
        weekday_vals.append(d["pm25"])
    else:
        weekend_vals.append(d["pm25"])

if weekday_vals and weekend_vals:
    print(f"  Weekday avg: {sum(weekday_vals)/len(weekday_vals):.1f} µg/m³ ({len(weekday_vals)} days)")
    print(f"  Weekend avg: {sum(weekend_vals)/len(weekend_vals):.1f} µg/m³ ({len(weekend_vals)} days)")

# ---- Identify the key episodes ----
print("\n" + "=" * 80)
print("KEY EPISODES IDENTIFIED")
print("=" * 80)

episodes = [
    ("Mar 1-8", "Early month spike", [d for d in march_data if "2026-03-01" <= d["date"] <= "2026-03-08"]),
    ("Mar 9-12", "Mid-month moderate", [d for d in march_data if "2026-03-09" <= d["date"] <= "2026-03-12"]),
    ("Mar 16-20", "Clean air window", [d for d in march_data if "2026-03-16" <= d["date"] <= "2026-03-20"]),
    ("Mar 23", "One-day resurgence", [d for d in march_data if d["date"] == "2026-03-23"]),
    ("Mar 27-29", "Marathahalli bridge closure", [d for d in march_data if "2026-03-27" <= d["date"] <= "2026-03-29"]),
]

for label, desc, days in episodes:
    if not days:
        continue
    pm25s = [d["pm25"] for d in days if d["pm25"]]
    temps = [d["temp"] for d in days if d["temp"]]
    humids = [d["humid"] for d in days if d["humid"]]
    print(f"\n  {label} — {desc}")
    if pm25s:
        print(f"    PM2.5: avg={sum(pm25s)/len(pm25s):.1f}, range={min(pm25s):.1f}-{max(pm25s):.1f}")
    if temps:
        print(f"    Temp:  avg={sum(temps)/len(temps):.1f}°C")
    if humids:
        print(f"    Humid: avg={sum(humids)/len(humids):.1f}%")
