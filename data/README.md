# Housing dashboard — data repo

One normalized JSON file per city powers the affordable-housing dashboard
at https://housing-dashboard.dmnbusch.workers.dev/.

## How it works

- The data comes from the Middleground data store
  (`dmnbusch-cell/middleground-data`, private), the system of record for
  income-restricted rentals in New York City and Austin. A sync script
  (`scripts/mg_sync.sh`, run on demand) fetches the current property and
  availability files from that repo through the Github Middleground Sync
  connector, transforms them with `scripts/mg_transform.py`, computes
  nearest-station data with `scripts/mg_transit.py`, and pushes the
  resulting files here.
- The Worker reads `data/cities.json` (the registry) and then one file per
  city from this repo, straight from GitHub's raw file server. No redeploy
  is needed when data changes: the registry is cached for 10 minutes and
  city files for 5 minutes, so a new or updated file shows up on the site
  within minutes.
- The frontend renders whatever is in the files: city tabs, KPIs, charts
  (by year, by area, by income band, by program) and the recent table,
  plus the map and the open lotteries & waitlists section. Sections are
  shown only when the city's file has that data.

## Files per city

- `data/<id>.json` — totals, breakdowns, recent table, transit summary.
- `data/<id>-places.json` — mapped properties with coordinates and
  nearest rail station.
- `data/<id>-stations.json` — rail stations for the map layer.
- `data/<id>-events.json` — open lottery and waitlist events.

## Schema — one file per city

```json
{
  "id": "nyc",
  "name": "New York City",
  "state": "NY",
  "source_name": "Middleground data store (dmnbusch-cell/middleground-data)",
  "source_url": "https://github.com/dmnbusch-cell/middleground-data",
  "coverage": "1988–2020",
  "updated": "2026-11-18",
  "count_label": "properties",
  "area_label": "Borough",
  "year_label": "placed in service",
  "type_label": "program",
  "band_note": "Extremely low to middle income, plus other income units.",
  "totals": {
    "affordable_units": 242080,
    "total_units": 490620,
    "buildings": 9833
  },
  "by_year": [
    { "year": 2020, "units": 118, "total_units": 1132, "buildings": 4 }
  ],
  "by_area": [
    { "area": "Bronx", "units": 82572, "buildings": 2742 }
  ],
  "by_band": [
    { "band": "Low income", "units": 85623 }
  ],
  "by_type": [
    { "type": "421a", "units": 50483, "buildings": 2452 }
  ],
  "recent": {
    "title": "Most recently placed in service",
    "columns": ["Placed in service", "Property", "Borough", "Address", "Restricted", "Total", "Program"],
    "rows": [[2020, "LINWOOD PARK APARTMENTS", "Brooklyn", "3002 ATLANTIC AVENUE", 100, 100, "HPD_TermSheet"]]
  },
  "transit": {
    "stations": 445,
    "places_mapped": 7767,
    "within_400m": 4570,
    "within_800m": 6740,
    "pct_within_800m": 86.8,
    "median_distance_m": 348
  },
  "notes": "Anything a reader should know: definitions, quirks, coverage gaps."
}
```

Rules:

- `id` is lowercase with hyphens; the file is `data/<id>.json`.
- `count_label` is the word for what `totals.buildings` counts
  ("properties").
- `area_label` is the word for the geography in `by_area` and in the
  recent table's area column ("Borough", "ZIP code").
- `year_label` and `type_label` are the words the page uses in the
  by-year and by-type headings ("placed in service", "program").
- Any of `by_year`, `by_area`, `by_band`, `by_type` may be `null` when
  the source has no such breakdown; the site hides that section.
  `total_units` may be `null` when the source doesn't report it.
- `recent.columns` must line up with `recent.rows`. The column whose
  header equals `area_label` becomes the filter for the table.
- Numbers must reconcile: `by_area` and `by_type` sum exactly to
  `totals.affordable_units` and their counts sum to `totals.buildings`.
  `by_band` may fall short (units without a band assignment) and
  `by_year` covers only rows with a known year; both gaps are stated
  in `notes`.
- Keep the source's own quirks visible in `notes` (unbanded units,
  unknown years, properties with no program restriction) rather than
  silently fixing them.

## Cities so far

- New York City, NY — Middleground properties (9,833), 1988–2020 by year
  placed in service where known; 68 open lotteries/waitlists.
- Austin, TX — Middleground properties (837), 1991–2018 by year placed
  in service where known; no open events in the feed yet.

Retired: Chicago and Los Angeles were added from their own open-data
portals in Nov 2026 and removed when the dashboard was re-pointed at
Middleground (NYC + Austin only). Their files remain in this repo for
reference but are no longer in `data/cities.json`.
