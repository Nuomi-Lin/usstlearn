import json
import os
import sys
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://overpass-api.de/api/interpreter"
UA = "USST-Campus3D/1.0 (educational; contact: local)"
BBOX = "31.2820,121.5360,31.3040,121.5620"

QUERY = f"""
[out:json][timeout:120];
(
  way["building"]({BBOX});
  relation["building"]({BBOX});
  way["highway"]({BBOX});
  way["waterway"]({BBOX});
  way["natural"="water"]({BBOX});
  relation["natural"="water"]({BBOX});
  way["leisure"~"pitch|track|park|garden"]({BBOX});
  way["landuse"~"grass|forest|meadow|village_green"]({BBOX});
  way["amenity"~"university|school|parking"]({BBOX});
);
out geom 20000;
"""


def run(query):
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=240) as resp:
        return resp.read().decode("utf-8")


raw = None
for attempt in range(5):
    try:
        raw = run(QUERY)
        print("fetched bytes:", len(raw))
        break
    except Exception as exc:
        print("retry", attempt, exc, file=sys.stderr)
        time.sleep(10 * (attempt + 1))
if raw is None:
    sys.exit("all retries failed")

data = json.loads(raw)
os.makedirs("data", exist_ok=True)
with open("data/osm_campus_raw.json", "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))

from collections import Counter

counts = Counter()
for el in data.get("elements", []):
    tags = el.get("tags", {})
    if "building" in tags:
        k = "building"
    elif tags.get("natural") == "water":
        k = "water"
    elif "waterway" in tags:
        k = "waterway"
    elif "highway" in tags:
        k = "highway:" + tags["highway"]
    elif "leisure" in tags:
        k = "leisure:" + tags["leisure"]
    elif "landuse" in tags:
        k = "landuse:" + tags["landuse"]
    elif "amenity" in tags:
        k = "amenity:" + tags["amenity"]
    else:
        k = "other"
    counts[k] += 1

print("elements:", len(data.get("elements", [])))
for k, v in counts.most_common():
    print(f"  {k}: {v}")