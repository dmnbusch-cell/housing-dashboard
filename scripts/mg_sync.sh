#!/bin/bash
# mg_sync.sh — sync the dashboard from the Middleground data store.
#
# 1. Fetch the current property, availability and program files from the
#    private dmnbusch-cell/middleground-data repo (Github Middleground
#    Sync connector, read-only PAT).
# 2. Transform them into the dashboard's city/places/events files.
# 3. Compute nearest-station data and transit summaries.
# 4. Push the resulting files to the public housing-dashboard data repo.
#
# The raw Middleground files (mg-sync/, incl. the 59 MB nyc.jsonl) are
# never pushed: only the transformed dashboard files in the manifest.
# Usage: bash scripts/mg_sync.sh "commit message"
set -euo pipefail

ROOT="$HOME/workspace/housing-dashboard"
FETCH="$HOME/workspace/custom-connectors/custom.github-middleground-sync/bin/mg_fetch.py"
MSG="${1:-Sync dashboard data from Middleground}"
SYNC_RECORD="$HOME/workspace/housing-dashboard.muse-github-snapshot-sync.json"

cd "$ROOT"
mkdir -p mg-sync

echo "== fetch =="
python3 "$FETCH" fetch data/properties/nyc.jsonl --out mg-sync/nyc.jsonl
python3 "$FETCH" fetch data/properties/austin.jsonl --out mg-sync/austin.jsonl
python3 "$FETCH" fetch data/availability/events.jsonl --out mg-sync/events.jsonl
python3 "$FETCH" fetch registry/programs.yaml --out mg-sync/programs.yaml

echo "== transform =="
python3 scripts/mg_transform.py
python3 scripts/mg_transit.py

echo "== push =="
MANIFEST="$(mktemp)"
printf 'data/cities.json\0data/nyc.json\0data/austin.json\0data/nyc-places.json\0data/austin-places.json\0data/austin-stations.json\0data/nyc-events.json\0data/austin-events.json\0data/README.md\0scripts/mg_transform.py\0scripts/mg_transit.py\0scripts/mg_sync.sh\0' > "$MANIFEST"
# Record the repo head before pushing (sync-record ritual).
/opt/hatch/bin/github call-read-tool --name list_commits --arguments-json '{"owner": "dmnbusch-cell", "repo": "housing-dashboard", "sha": "main", "per_page": 1}' > /tmp/mg-push-head.json
/opt/hatch/bin/github push-files --owner dmnbusch-cell --repo housing-dashboard --branch main --message "$MSG" --source-dir "$ROOT" --paths-file "$MANIFEST"
echo "Push complete. Update the sync record with the new head SHA from the push output."
rm -f "$MANIFEST"
