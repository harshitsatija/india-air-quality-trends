import json
from datetime import datetime, timedelta

with open('blr_30day_combined.json') as f:
    data = json.load(f)

# Filter out days with very few stations (unreliable)
data = [d for d in data if d['n_stations'] >= 10]

avg = lambda vals: sum(vals)/len(vals) if vals else None
pm25_vals = [d['pm25'] for d in data if d['pm25']]
mean_pm25 = avg(pm25_vals)
std_pm25 = (sum((v - mean_pm25)**2 for v in pm25_vals) / len(pm25_vals)) ** 0.5

print("=" * 75)
print("BENGALURU — TREND DETECTION (Mar 7 – Apr 7, 2026)")
print("=" * 75)
print(f"\nBaseline: PM2.5 mean = {mean_pm25:.1f} µg/m³, std = {std_pm25:.1f}")
print(f"WHO 24h guideline: 15 µg/m³ | India NAAQS: 60 µg/m³")

# ---- TREND 1: Detect sustained runs (3+ days above/below mean) ----
print("\n" + "=" * 75)
print("DETECTED EPISODES")
print("=" * 75)

episodes = []
i = 0
while i < len(data):
    if data[i]['pm25'] is None:
        i += 1
        continue

    # Check for spike runs
    if data[i]['pm25'] > mean_pm25 + 0.5 * std_pm25:
        start = i
        while i < len(data) and data[i]['pm25'] and data[i]['pm25'] > mean_pm25:
            i += 1
        end = i - 1
        if end - start >= 1:  # at least 2 days
            days = data[start:end+1]
            episodes.append(('SPIKE', days))
        continue

    # Check for dip runs
    if data[i]['pm25'] < mean_pm25 - 0.5 * std_pm25:
        start = i
        while i < len(data) and data[i]['pm25'] and data[i]['pm25'] < mean_pm25:
            i += 1
        end = i - 1
        if end - start >= 1:
            days = data[start:end+1]
            episodes.append(('DIP', days))
        continue

    i += 1

# Also detect single-day jumps (>30% day-over-day)
for i in range(1, len(data)):
    prev, curr = data[i-1], data[i]
    if prev['pm25'] and curr['pm25'] and prev['pm25'] > 0:
        pct = (curr['pm25'] - prev['pm25']) / prev['pm25'] * 100
        if abs(pct) > 35:
            episodes.append(('JUMP' if pct > 0 else 'DROP', [prev, curr]))

# Deduplicate and sort by date
seen_dates = set()
unique_episodes = []
for typ, days in episodes:
    key = (typ, days[0]['date'])
    if key not in seen_dates:
        seen_dates.add(key)
        unique_episodes.append((typ, days))

unique_episodes.sort(key=lambda x: x[1][0]['date'])

# ---- Analyze each episode ----
trends = []

for idx, (typ, days) in enumerate(unique_episodes):
    trend = {
        'id': idx + 1,
        'type': typ,
        'start': days[0]['date'],
        'end': days[-1]['date'],
        'days': days,
        'hypotheses': [],
    }

    pm25s = [d['pm25'] for d in days if d['pm25']]
    pm10s = [d['pm10'] for d in days if d['pm10']]
    no2s = [d['no2'] for d in days if d['no2']]
    so2s = [d['so2'] for d in days if d['so2']]
    o3s = [d['o3'] for d in days if d['o3']]
    temps = [d['temp'] for d in days if d['temp']]
    humids = [d['humid'] for d in days if d['humid']]

    avg_pm25 = avg(pm25s)
    avg_pm10 = avg(pm10s)
    avg_humid = avg(humids)
    avg_temp = avg(temps)
    avg_no2 = avg(no2s)
    avg_so2 = avg(so2s)
    avg_o3 = avg(o3s)

    trend['avg_pm25'] = avg_pm25
    trend['avg_pm10'] = avg_pm10

    # --- Data-driven hypotheses ---

    # 1. PM2.5/PM10 ratio → source type
    if avg_pm25 and avg_pm10:
        ratio = avg_pm25 / avg_pm10
        trend['ratio'] = ratio
        if ratio < 0.35:
            trend['hypotheses'].append(f"[SOURCE] PM2.5/PM10 ratio = {ratio:.2f} (low). Coarse particles dominate → likely road dust or construction activity.")
        elif ratio > 0.55:
            trend['hypotheses'].append(f"[SOURCE] PM2.5/PM10 ratio = {ratio:.2f} (high). Fine particles dominate → likely combustion (vehicles, burning).")

    # 2. Humidity correlation
    if avg_humid:
        if typ == 'DIP' and avg_humid > 60:
            trend['hypotheses'].append(f"[WEATHER] Humidity averaged {avg_humid:.0f}% during this period (vs 55% baseline). Likely rainfall washout effect.")
        elif typ in ('SPIKE', 'JUMP') and avg_humid < 45:
            trend['hypotheses'].append(f"[WEATHER] Humidity dropped to {avg_humid:.0f}% (dry conditions). Low moisture = no rain washout + more dust resuspension.")

    # 3. Temperature anomaly
    if avg_temp:
        temp_mean = avg([d['temp'] for d in data if d['temp']])
        if abs(avg_temp - temp_mean) > 1.5:
            direction = "dropped" if avg_temp < temp_mean else "rose"
            trend['hypotheses'].append(f"[WEATHER] Temperature {direction} to {avg_temp:.1f}°C (vs {temp_mean:.1f}°C average). {'Suggests storm/rain event.' if avg_temp < temp_mean else 'Hot stagnant air traps pollutants.'}")

    # 4. NO2 signal (traffic)
    if avg_no2:
        no2_mean = avg([d['no2'] for d in data if d['no2']])
        if avg_no2 > no2_mean * 1.2:
            trend['hypotheses'].append(f"[TRAFFIC] NO2 elevated at {avg_no2:.0f} µg/m³ (vs {no2_mean:.0f} baseline). Suggests increased vehicle activity or traffic congestion.")
        elif avg_no2 < no2_mean * 0.8:
            trend['hypotheses'].append(f"[TRAFFIC] NO2 low at {avg_no2:.0f} µg/m³ (vs {no2_mean:.0f} baseline). Reduced traffic — possibly weekend, holiday, or road closure.")

    # 5. SO2 signal (industrial)
    if avg_so2:
        so2_mean = avg([d['so2'] for d in data if d['so2']])
        if avg_so2 > so2_mean * 1.3:
            trend['hypotheses'].append(f"[INDUSTRIAL] SO2 elevated at {avg_so2:.1f} µg/m³ (vs {so2_mean:.1f} baseline). Industrial activity spike or power generation increase.")

    # 6. O3 signal (photochemical)
    if avg_o3:
        o3_mean = avg([d['o3'] for d in data if d['o3']])
        if avg_o3 > o3_mean * 1.3:
            trend['hypotheses'].append(f"[PHOTOCHEMICAL] Ozone high at {avg_o3:.0f} µg/m³ (vs {o3_mean:.0f} baseline). Strong sunlight + NOx → photochemical smog.")

    # 7. Day-of-week pattern
    dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in days]
    weekdays = [dt.strftime('%A') for dt in dates]
    if all(dt.weekday() >= 5 for dt in dates):
        trend['hypotheses'].append(f"[PATTERN] Episode falls entirely on weekend ({', '.join(weekdays)}). Weekend traffic/activity pattern.")

    # 8. Multi-day sustained trend
    if len(days) >= 4:
        trend['hypotheses'].append(f"[SUSTAINED] {len(days)}-day episode — not a one-off event. Likely driven by persistent weather pattern or ongoing activity.")

    trends.append(trend)

# ---- Print results ----
for t in trends:
    label = f"{'🔴' if t['type'] in ('SPIKE','JUMP') else '🟢'} Trend #{t['id']}: {t['type']}"
    date_range = f"{t['start']} → {t['end']}" if t['start'] != t['end'] else t['start']

    print(f"\n{label}")
    print(f"  Period: {date_range} ({len(t['days'])} days)")
    print(f"  PM2.5: {t['avg_pm25']:.0f} µg/m³ (baseline: {mean_pm25:.0f})")
    if t.get('avg_pm10'):
        print(f"  PM10:  {t['avg_pm10']:.0f} µg/m³ | Ratio: {t.get('ratio', 0):.2f}")

    print(f"  Data-driven hypotheses:")
    if t['hypotheses']:
        for h in t['hypotheses']:
            print(f"    → {h}")
    else:
        print(f"    → No strong signal detected in pollutant/weather data")

    print(f"  🔍 News search needed for: {t['start']} Bengaluru events")

# Save for next step
with open('blr_trends.json', 'w') as f:
    json.dump([{
        'id': t['id'], 'type': t['type'], 'start': t['start'], 'end': t['end'],
        'avg_pm25': t['avg_pm25'], 'avg_pm10': t.get('avg_pm10'),
        'hypotheses': t['hypotheses'],
        'search_query': f"Bengaluru {t['start']} {t['end']} events weather"
    } for t in trends], f, indent=2)

print(f"\n\n{'='*75}")
print(f"TOTAL: {len(trends)} trends detected")
print(f"{'='*75}")
PYEOF