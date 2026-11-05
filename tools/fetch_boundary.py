import json
import os
import sys
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://overpass-api.de/api/interpreter"
UA = "USST-Campus3D/1.0 (educational; contact: local)"

QUERY = """
[out:json][timeout:90];
(
  relation(2411142);
  relation(2410532);
);
out geom;
"""


def run(query):
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


for attempt in range(5):
    try:
        result = run(QUERY)
        break
    except Exception as exc:
        print("retry", attempt, exc, file=sys.stderr)
        time.sleep(10 * (attempt + 1))
else:
    sys.exit("all retries failed")

os.makedirs("data", exist_ok=True)
with open("data/campus_boundary.json", "w", encoding="utf-8") as fh:
    json.dump(result, fh, ensure_ascii=False, separators=(",", ":"))

for el in result.get("elements", []):
    tags = el.get("tags", {})
    print("REL", el["id"], tags.get("name"), "members:", len(el.get("members", [])))
    outer = [m for m in el.get("members", []) if m.get("role") == "outer" and m.get("geometry")]
    print("  outer ways:", len(outer), "points:", sum(len(m["geometry"]) for m in outer))