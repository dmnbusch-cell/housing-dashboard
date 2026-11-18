#!/usr/bin/env python3
"""Nearest rail station per mapped place + transit summary.

Reads data/<id>-places.json and data/<id>-stations.json, fills each place's
`station` (nearest by straight-line haversine distance), and writes the
transit summary into data/<id>.json. Re-run after any places or stations
change. Rail only; distances are as the crow flies, not walking distance.
"""

from __future__ import annotations

import json
import math
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def run(metro: str):
    with open(os.path.join(DATA, metro + "-places.json")) as f:
        places_doc = json.load(f)
    with open(os.path.join(DATA, metro + "-stations.json")) as f:
        stations_doc = json.load(f)
    stations = stations_doc["stations"]
    distances = []
    within_400 = within_800 = 0
    no_station = 0
    for p in places_doc["places"]:
        best = None
        best_d = float("inf")
        for s in stations:
            d = haversine_m(p["lat"], p["lng"], s["lat"], s["lng"])
            if d < best_d:
                best_d, best = d, s
        if best is None or best_d > 5000:
            p["station"] = None
            no_station += 1
            continue
        dist = int(round(best_d))
        p["station"] = {
            "distance_m": dist,
            "lines": best.get("lines") or [],
            "name": best["name"],
            "station_id": str(best["id"]),
        }
        distances.append(dist)
        if dist <= 400:
            within_400 += 1
        if dist <= 800:
            within_800 += 1
    with open(os.path.join(DATA, metro + "-places.json"), "w") as f:
        json.dump(places_doc, f)
    mapped = len(places_doc["places"])
    summary = {
        "stations": len(stations),
        "places_mapped": mapped,
        "within_400m": within_400,
        "within_800m": within_800,
        "pct_within_800m": round(100.0 * within_800 / mapped, 1) if mapped else 0.0,
        "median_distance_m": int(statistics.median(distances)) if distances else None,
    }
    with open(os.path.join(DATA, metro + ".json")) as f:
        city = json.load(f)
    city["transit"] = summary
    with open(os.path.join(DATA, metro + ".json"), "w") as f:
        json.dump(city, f)
    print(f"{metro}: stations={len(stations)} mapped={mapped} "
          f"within_800m={within_800} ({summary['pct_within_800m']}%) "
          f"median={summary['median_distance_m']}m no_station_within_5km={no_station}")


if __name__ == "__main__":
    for metro in ("nyc", "austin"):
        run(metro)
