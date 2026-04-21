"""Fetch Mar + Apr 2026 monthly data for all 10 metro cities."""
import json, subprocess, os

SIGN = "URLPrefix=aHR0cHM6Ly9vYXEubm90Zi5pbi92MS8=&Expires=1776839810&KeyName=prod-key-1&Signature=khgBxxpdoFvoqgkKUazpXC9mm6s="

START_DATE = "2026-03-10"
END_DATE = "2026-04-21"

CITIES = {
    "delhi": "Delhi",
    "mumbai": "Mumbai",
    "bengaluru": "Bengaluru",
    "chennai": "Chennai",
    "hyderabad": "Hyderabad",
    "kolkata": "Kolkata",
    "pune": "Pune",
    "ahmedabad": "Ahmedabad",
    "jaipur": "Jaipur",
    "lucknow": "Lucknow",
}

os.makedirs("city_data", exist_ok=True)

for city_key, city_name in CITIES.items():
    print(f"\n{'='*50}")
    print(f"Fetching {city_name}...")

    # Get station list from existing city_data snapshot
    with open(f"city_data/{city_key}.json") as f:
        stations = json.load(f)["stations"]

    print(f"  {len(stations)} CPCB stations")

    city_stations = []
    for s in stations:
        sid = s["id"]
        sname = s["name"]

        # Fetch Mar and Apr monthly aggregates
        mar_data = None
        apr_data = None

        for month, label in [("03", "mar"), ("04", "apr")]:
            url = f"https://oaq.notf.in/v1/provider=cpcb/history/aggregates/{sid}/monthly_2026_{month}.json?{SIGN}"
            result = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
            try:
                d = json.loads(result.stdout)
                if d.get("data"):
                    if label == "mar":
                        mar_data = d["data"]
                    else:
                        apr_data = d["data"]
            except:
                pass

        combined = []
        if mar_data:
            combined += [d for d in mar_data if d["date"] >= START_DATE]
        if apr_data:
            combined += [d for d in apr_data if d["date"] <= END_DATE]

        if combined:
            city_stations.append({
                "id": sid,
                "name": sname,
                "lat": s.get("lat"),
                "lon": s.get("lon"),
                "data": combined,
            })

    print(f"  {len(city_stations)} stations with data")

    # Save
    with open(f"city_data/{city_key}.json", "w") as f:
        json.dump({
            "city": city_name,
            "key": city_key,
            "stations": city_stations,
        }, f)

print("\n\nDone! All cities fetched.")
