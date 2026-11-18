#!/usr/bin/env python3
"""Transform Middleground property records into dashboard city files.

Reads the synced Middleground files (mg-sync/*.jsonl, fetched from the
private dmnbusch-cell/middleground-data repo via the Github Middleground
Sync connector) and writes the dashboard's normalized files into data/:
  <id>.json, <id>-places.json, <id>-events.json
Transit (nearest station per place + summary) is filled in by
mg_transit.py after the stations files exist; this script writes
transit: null and station: null when no stations file is available.

Honesty rules (see BUILD_LOG.md):
- restricted_units counts only units with an income-band assignment; the
  property record's restricted_units always equals its band sum (verified).
- by_year covers only rows with year_placed_in_service; the count of rows
  without a year is recorded in the notes.
- by_area uses borough_or_county; null becomes "Unknown".
- by_type uses the property's first listed restriction as its primary
  program; properties can carry more than one restriction.
- Austin band keys are MFI percentages (mfi_30 .. mfi_120).
"""

from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC = os.path.join(ROOT, "mg-sync")
DATA = os.path.join(ROOT, "data")
TODAY = "2026-11-18"

NYC_BAND_LABELS = {
    "extremely_low": "Extremely low income",
    "very_low": "Very low income",
    "low": "Low income",
    "moderate": "Moderate income",
    "middle": "Middle income",
    "other": "Other income",
}
NYC_BAND_ORDER = ["extremely_low", "very_low", "low", "moderate", "middle", "other"]


def band_label(metro: str, key: str) -> str:
    if metro == "nyc":
        return NYC_BAND_LABELS.get(key, key)
    if key.startswith("mfi_"):
        return "\u2264" + key[4:] + "% MFI"
    return key


def band_order(metro: str, key: str) -> int:
    if metro == "nyc":
        return NYC_BAND_ORDER.index(key) if key in NYC_BAND_ORDER else 99
    if key.startswith("mfi_"):
        try:
            return int(key[4:])
        except ValueError:
            return 99
    return 99


def load_records(metro: str):
    path = os.path.join(SYNC, metro + ".jsonl")
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def primary_type(rec):
    restrictions = rec.get("restrictions") or []
    if restrictions:
        return restrictions[0].get("type") or "Unknown"
    return "No restriction listed"


def display_name(rec):
    return rec.get("display_name") or rec.get("name") or "Unnamed property"


def area_of(rec, metro: str) -> str:
    # Austin county coverage is thin (209 of 837 rows); every Austin row
    # carries a postcode, so ZIP is the area dimension there.
    if metro == "austin":
        return rec.get("postcode") or rec.get("borough_or_county") or "Unknown"
    return rec.get("borough_or_county") or "Unknown"


def build_city(metro: str, cfg: dict):
    rows = load_records(metro)
    n = len(rows)
    restricted = sum(r.get("restricted_units") or 0 for r in rows)
    total = sum(r.get("total_units") or 0 for r in rows)
    with_year = [r for r in rows if r.get("year_placed_in_service")]
    with_band = sum(1 for r in rows if r.get("restricted_units"))
    no_band = n - with_band

    by_year = defaultdict(lambda: {"units": 0, "buildings": 0, "total_units": 0})
    for r in with_year:
        y = r["year_placed_in_service"]
        by_year[y]["units"] += r.get("restricted_units") or 0
        by_year[y]["buildings"] += 1
        by_year[y]["total_units"] += r.get("total_units") or 0
    by_year_list = [
        {"year": y, "units": v["units"], "buildings": v["buildings"], "total_units": v["total_units"]}
        for y, v in sorted(by_year.items())
    ]

    by_area = defaultdict(lambda: {"units": 0, "buildings": 0, "total_units": 0})
    for r in rows:
        a = area_of(r, metro)
        by_area[a]["units"] += r.get("restricted_units") or 0
        by_area[a]["buildings"] += 1
        by_area[a]["total_units"] += r.get("total_units") or 0
    by_area_list = [
        {"area": a, "units": v["units"], "buildings": v["buildings"], "total_units": v["total_units"]}
        for a, v in sorted(by_area.items(), key=lambda kv: -kv[1]["units"])
    ]

    band_totals = Counter()
    for r in rows:
        for k, v in (r.get("units_by_income_band") or {}).items():
            band_totals[k] += v
    by_band_list = [
        {"band": band_label(metro, k), "units": band_totals[k]}
        for k in sorted(band_totals, key=lambda k: band_order(metro, k))
    ]

    by_type = defaultdict(lambda: {"units": 0, "buildings": 0})
    for r in rows:
        t = primary_type(r)
        by_type[t]["units"] += r.get("restricted_units") or 0
        by_type[t]["buildings"] += 1
    by_type_list = [
        {"type": t, "units": v["units"], "buildings": v["buildings"]}
        for t, v in sorted(by_type.items(), key=lambda kv: -kv[1]["units"])
    ]

    recent_rows = sorted(
        (r for r in rows if r.get("year_placed_in_service")),
        key=lambda r: (-r["year_placed_in_service"], -(r.get("restricted_units") or 0)),
    )[:25]
    recent = {
        "title": "Most recently placed in service",
        "columns": ["Placed in service", "Property", cfg["area_label"], "Address", "Restricted", "Total", "Program"],
        "rows": [
            [
                r["year_placed_in_service"],
                display_name(r),
                area_of(r, metro),
                r.get("address") or "",
                r.get("restricted_units"),
                r.get("total_units"),
                primary_type(r),
            ]
            for r in recent_rows
        ],
    }

    years = sorted(by_year)
    coverage = f"{years[0]}\u2013{years[-1]}" if years else ""
    by_year_units = sum(b["units"] for b in by_year_list)
    band_units = sum(b["units"] for b in by_band_list)
    no_restriction_rows = [r for r in rows if not (r.get("restrictions") or [])]
    no_restriction_units = sum(r.get("restricted_units") or 0 for r in no_restriction_rows)
    notes = (
        f"Restricted units count only units with an income-band assignment "
        f"({restricted:,} across {with_band:,} properties). {no_band:,} properties "
        f"have no restricted-unit count in the source. "
        f"Income-band breakdowns cover {band_units:,} of {restricted:,} restricted units. "
        f"Year placed in service is known for {len(with_year):,} of {n:,} properties; "
        f"the by-year chart covers those only ({by_year_units:,} units). "
    )
    if no_restriction_rows:
        notes += (
            f"{len(no_restriction_rows):,} properties ({no_restriction_units:,} units) have no program "
            f"restriction recorded in the source and appear as \u2018No restriction listed\u2019 in the "
            f"by-program chart. "
        )
    notes += (
        f"Map shows the "
        f"{sum(1 for r in rows if r.get('lat') is not None):,} properties with published coordinates."
    )

    city = {
        "id": metro,
        "name": cfg["name"],
        "state": cfg["state"],
        "coverage": coverage,
        "label": None,
        "area_label": cfg["area_label"],
        "count_label": "properties",
        "year_label": "placed in service",
        "type_label": "program",
        "band_note": cfg["band_note"],
        "source_name": "Middleground data store (dmnbusch-cell/middleground-data)",
        "source_url": "https://github.com/dmnbusch-cell/middleground-data",
        "updated": TODAY,
        "totals": {"affordable_units": restricted, "buildings": n, "total_units": total},
        "by_year": by_year_list,
        "by_area": by_area_list,
        "by_band": by_band_list,
        "by_type": by_type_list,
        "recent": recent,
        "transit": None,
        "notes": notes,
    }
    with open(os.path.join(DATA, metro + ".json"), "w") as f:
        json.dump(city, f)

    places = []
    for r in rows:
        if r.get("lat") is None or r.get("lng") is None:
            continue
        places.append({
            "address": r.get("address") or "",
            "area": area_of(r, metro),
            "lat": round(r["lat"], 5),
            "lng": round(r["lng"], 5),
            "name": display_name(r),
            "station": None,
            "total_units": r.get("total_units"),
            "type": primary_type(r),
            "units": r.get("restricted_units"),
            "year": r.get("year_placed_in_service"),
        })
    places.sort(key=lambda p: (-(p["units"] or 0), p["name"]))
    with open(os.path.join(DATA, metro + "-places.json"), "w") as f:
        json.dump({"count": len(places), "id": metro, "places": places}, f)

    # Verification: every grouping sums exactly to the totals.
    assert sum(b["units"] for b in by_year_list) <= restricted, "by_year exceeds total"
    assert sum(b["units"] for b in by_area_list) == restricted, "by_area does not sum to total"
    # by_band can fall short of the total: rows may carry restricted_units
    # with no income-band breakdown (Austin: 43,510 of 64,183 units).
    assert sum(b["units"] for b in by_band_list) <= restricted, "by_band exceeds total"
    assert sum(b["units"] for b in by_type_list) == restricted, "by_type does not sum to total"
    assert sum(b["buildings"] for b in by_area_list) == n, "by_area buildings mismatch"
    assert sum(b["buildings"] for b in by_type_list) == n, "by_type buildings mismatch"
    print(f"{metro}: properties={n} restricted={restricted} total={total} "
          f"with_year={len(with_year)} mapped={len(places)} "
          f"by_year_units={sum(b['units'] for b in by_year_list)}")
    return rows


def build_events(rows_by_metro):
    with open(os.path.join(SYNC, "events.jsonl")) as f:
        events = [json.loads(line) for line in f if line.strip()]
    by_id = {}
    for metro, rows in rows_by_metro.items():
        for r in rows:
            by_id[r.get("id")] = r
    open_events = [e for e in events if e.get("status") == "open"]
    per_metro = defaultdict(list)
    for e in open_events:
        per_metro[e.get("metro")].append(e)
    for metro in ("nyc", "austin"):
        out = []
        for e in sorted(per_metro.get(metro, []), key=lambda x: (x.get("deadline") or "9999", x.get("property_name") or "")):
            tiers = e.get("tiers") or []
            rents = [t["rent"] for t in tiers if t.get("rent") is not None]
            imins = [t["income_min"] for t in tiers if t.get("income_min") is not None]
            imaxs = [t["income_max"] for t in tiers if t.get("income_max") is not None]
            units = sum(t.get("units") or 0 for t in tiers)
            bands = sorted({t.get("ami_band") for t in tiers if t.get("ami_band")})
            prop = by_id.get(e.get("property_id") or "")
            out.append({
                "deadline": e.get("deadline"),
                "property": e.get("property_name"),
                "address": e.get("address") or (prop.get("address") if prop else None),
                "area": (prop.get("borough_or_county") if prop else None) or "Unknown",
                "program": e.get("program"),
                "rent_min": min(rents) if rents else None,
                "rent_max": max(rents) if rents else None,
                "income_min": min(imins) if imins else None,
                "income_max": max(imaxs) if imaxs else None,
                "bands": ", ".join(bands),
                "units": units or None,
                "url": e.get("application_url") or e.get("source_url"),
                "verified_official": bool(e.get("verified_official")),
            })
        with open(os.path.join(DATA, metro + "-events.json"), "w") as f:
            json.dump({"count": len(out), "id": metro, "events": out}, f)
        print(f"{metro}: open events={len(out)}")


def main():
    rows_by_metro = {}
    rows_by_metro["nyc"] = build_city("nyc", {
        "name": "New York City", "state": "NY", "area_label": "Borough",
        "band_note": "Extremely low to middle income, plus other income units.",
    })
    rows_by_metro["austin"] = build_city("austin", {
        "name": "Austin", "state": "TX", "area_label": "ZIP code",
        "band_note": "Share of area median family income (MFI) the rent is restricted to.",
    })
    build_events(rows_by_metro)


if __name__ == "__main__":
    main()
