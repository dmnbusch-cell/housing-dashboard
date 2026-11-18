# Housing dashboard — data repo

One normalized JSON file per city powers the nationwide affordable-housing
dashboard at https://housing-dashboard.dmnbusch.workers.dev/.

## How it works

- The Worker reads `data/cities.json` (the registry) and then one file per
  city from this repo, straight from GitHub's raw file server. No redeploy
  is needed when data changes: the registry is cached for 10 minutes and
  city files for 1 hour, so a new or updated file shows up on the site
  within the hour.
- The frontend renders whatever is in the files: city tabs, KPIs, charts
  (by year, by area, by income band, by type, by stage) and the recent
  table. Sections are shown only when the city's file has that data.

## Adding a city

1. Find the city's open-data source (affordable-housing production,
   developments, or projects list).
2. Copy `data/nyc.json` as a template and fill it in, following the schema
   below. Numbers must reconcile: every grouping (by year, by area, by
   type, by band) must sum to `totals.affordable_units`, and the counts
   must sum to `totals.buildings`.
3. Add one line to `data/cities.json`.
4. Commit. The city appears on the dashboard automatically.

## Schema — one file per city

```json
{
  "id": "nyc",
  "name": "New York City",
  "state": "NY",
  "source_name": "NYC HPD — Affordable Housing Production by Building",
  "source_url": "https://data.cityofnewyork.us/...",
  "coverage": "2014–present",
  "updated": "2026-11-17",
  "count_label": "buildings",
  "area_label": "Borough",
  "totals": {
    "affordable_units": 320946,
    "total_units": 445588,
    "buildings": 9551
  },
  "by_year": [
    { "year": 2014, "units": 19629, "total_units": 27895, "buildings": 734 }
  ],
  "by_area": [
    { "area": "Bronx", "units": 106661, "buildings": 2630 }
  ],
  "by_band": [
    { "band": "Low income", "units": 108968 }
  ],
  "by_type": [
    { "type": "New Construction", "units": 131448, "buildings": null }
  ],
  "by_stage": [
    { "type": "In-Service", "units": 31879, "buildings": 587 }
  ],
  "recent": {
    "title": "Recently completed buildings",
    "columns": ["Completed", "Project", "Borough", "Address", "Affordable", "Total", "Type"],
    "rows": [["2026-08-21", "THE BARNETT", "Queens", "50-25 BARNETT AVENUE", 185, 185, "New Construction"]]
  },
  "notes": "Anything a reader should know: definitions, quirks, merges."
}
```

Rules:

- `id` is lowercase with hyphens; the file is `data/<id>.json`.
- `count_label` is the word for what `totals.buildings` counts
  ("buildings", "developments", "sites").
- `area_label` is the word for the geography in `by_area` and in the
  recent table's area column ("Borough", "Community area",
  "Council district").
- Any of `by_year`, `by_area`, `by_band`, `by_type`, `by_stage` may be
  `null` when the source has no such breakdown; the site hides that
  section. `total_units` may be `null` when the source doesn't report it.
- `recent.columns` must line up with `recent.rows`. The column whose
  header equals `area_label` becomes the filter for the table.
- Keep the source's own quirks visible in `notes` (merged duplicate
  labels, dropped rows, undated units) rather than silently fixing them.

## Cities so far

- New York City, NY — NYC HPD, Affordable Housing Production by Building
  (hg8x-zxpr), 2014–present.
- Chicago, IL — City of Chicago, Affordable Rental Housing Developments
  (s6ha-ppgi), current inventory, no dates in the source.
- Los Angeles, CA — LAHD Affordable Housing Projects List, 2003 to Present
  (mymu-zi3s), by funding date.

San Francisco is still open: no affordable-housing dataset turned up in
its open-data catalog under that name; a "housing pipeline" or
"inclusionary housing" dataset would be the next place to look.
