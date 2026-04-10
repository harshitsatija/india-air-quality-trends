import json
import os
from collections import defaultdict

DIR = os.path.dirname(os.path.abspath(__file__))

# Station names from latest data
STATIONS = {
    "1553": "Bapuji Nagar",
    "1554": "Hebbal",
    "1555": "Hombegowda Nagar",
    "1556": "Jayanagar 5th Block",
    "1558": "Silk Board",
    "162": "BTM Layout",
    "163": "Peenya",
    "164": "BWSSB Kadabesanahalli",
    "165": "City Railway Station",
    "166": "Sanegurava Halli",
    "5678": "RVCE-Mailasandra",
    "5681": "Kasturi Nagar",
    "5686": "Shivapura Peenya",
}

def load_monthly(station_id, month_file):
    path = os.path.join(DIR, month_file)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            d = json.load(f)
        return d.get("data", [])
    except:
        return None

# ---- Aggregate city-wide daily PM2.5 for March 2026 ----
print("=" * 70)
print("BENGALURU - CITY-WIDE DAILY PM2.5 AVERAGES (March 2026)")
print("=" * 70)

daily_pm25 = defaultdict(list)
daily_pm10 = defaultdict(list)
daily_no2 = defaultdict(list)
daily_o3 = defaultdict(list)
daily_temp = defaultdict(list)

for sid in STATIONS:
    data = load_monthly(sid, f"cpcb_{sid}_mar2026.json")
    if not data:
        continue
    for day in data:
        date = day["date"]
        if day.get("pm25") is not None:
            daily_pm25[date].append(day["pm25"])
        if day.get("pm10") is not None:
            daily_pm10[date].append(day["pm10"])
        if day.get("no2") is not None:
            daily_no2[date].append(day["no2"])
        if day.get("o3") is not None:
            daily_o3[date].append(day["o3"])
        if day.get("temp") is not None:
            daily_temp[date].append(day["temp"])

print(f"\n{'Date':<14} {'PM2.5':>7} {'PM10':>7} {'NO2':>7} {'O3':>7} {'Temp':>6} {'#Stn':>5}")
print("-" * 60)

march_pm25_vals = []
for date in sorted(daily_pm25.keys()):
    avg_pm25 = sum(daily_pm25[date]) / len(daily_pm25[date])
    avg_pm10 = sum(daily_pm10.get(date, [0])) / max(len(daily_pm10.get(date, [1])), 1)
    avg_no2 = sum(daily_no2.get(date, [0])) / max(len(daily_no2.get(date, [1])), 1)
    avg_o3 = sum(daily_o3.get(date, [0])) / max(len(daily_o3.get(date, [1])), 1)
    avg_temp = sum(daily_temp.get(date, [0])) / max(len(daily_temp.get(date, [1])), 1)
    n = len(daily_pm25[date])
    march_pm25_vals.append((date, avg_pm25, n))
    print(f"{date:<14} {avg_pm25:>7.1f} {avg_pm10:>7.1f} {avg_no2:>7.1f} {avg_o3:>7.1f} {avg_temp:>6.1f} {n:>5}")

# ---- Identify spikes and dips ----
print("\n" + "=" * 70)
print("ANOMALY DETECTION - PM2.5 Spikes & Dips")
print("=" * 70)

if march_pm25_vals:
    values = [v[1] for v in march_pm25_vals]
    mean = sum(values) / len(values)
    std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5

    print(f"\nMarch mean PM2.5: {mean:.1f} µg/m³")
    print(f"Std deviation: {std:.1f}")
    print(f"WHO 24h guideline: 15 µg/m³")
    print(f"India NAAQS 24h: 60 µg/m³")

    print("\n--- Days > 1 std above mean ---")
    for date, val, n in march_pm25_vals:
        if val > mean + std:
            print(f"  SPIKE: {date} → PM2.5 = {val:.1f} ({val - mean:+.1f} from mean)")

    print("\n--- Days > 1 std below mean ---")
    for date, val, n in march_pm25_vals:
        if val < mean - std:
            print(f"  DIP:   {date} → PM2.5 = {val:.1f} ({val - mean:+.1f} from mean)")

# ---- Per-station comparison for March ----
print("\n" + "=" * 70)
print("PER-STATION MARCH AVERAGES")
print("=" * 70)
print(f"\n{'Station':<25} {'PM2.5':>7} {'PM10':>7} {'NO2':>7} {'O3':>7}")
print("-" * 55)

for sid, name in sorted(STATIONS.items(), key=lambda x: x[1]):
    data = load_monthly(sid, f"cpcb_{sid}_mar2026.json")
    if not data:
        continue
    pm25_vals = [d["pm25"] for d in data if d.get("pm25") is not None]
    pm10_vals = [d["pm10"] for d in data if d.get("pm10") is not None]
    no2_vals = [d["no2"] for d in data if d.get("no2") is not None]
    o3_vals = [d["o3"] for d in data if d.get("o3") is not None]

    avg_pm25 = sum(pm25_vals) / len(pm25_vals) if pm25_vals else None
    avg_pm10 = sum(pm10_vals) / len(pm10_vals) if pm10_vals else None
    avg_no2 = sum(no2_vals) / len(no2_vals) if no2_vals else None
    avg_o3 = sum(o3_vals) / len(o3_vals) if o3_vals else None

    pm25_s = f"{avg_pm25:>7.1f}" if avg_pm25 else "    N/A"
    pm10_s = f"{avg_pm10:>7.1f}" if avg_pm10 else "    N/A"
    no2_s = f"{avg_no2:>7.1f}" if avg_no2 else "    N/A"
    o3_s = f"{avg_o3:>7.1f}" if avg_o3 else "    N/A"
    print(f"{name:<25} {pm25_s} {pm10_s} {no2_s} {o3_s}")

# ---- Feb vs March comparison ----
print("\n" + "=" * 70)
print("MONTH-OVER-MONTH: FEB vs MARCH 2026 (city-wide PM2.5)")
print("=" * 70)

for month_label, suffix in [("Feb 2026", "feb2026"), ("Mar 2026", "mar2026"), ("Apr 2026 (partial)", "apr2026")]:
    all_vals = []
    for sid in STATIONS:
        data = load_monthly(sid, f"cpcb_{sid}_{suffix}.json")
        if not data:
            continue
        for day in data:
            if day.get("pm25") is not None:
                all_vals.append(day["pm25"])
    if all_vals:
        avg = sum(all_vals) / len(all_vals)
        mx = max(all_vals)
        mn = min(all_vals)
        print(f"  {month_label:<22} mean={avg:>6.1f}  max={mx:>6.1f}  min={mn:>6.1f}  readings={len(all_vals)}")
    else:
        print(f"  {month_label:<22} No data")
