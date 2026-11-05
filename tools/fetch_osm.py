import json
import sys
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://overpass-api.de/api/interpreter"
UA = "USST-Campus3D/1.0 (educational; contact: local)"

QUERY = """
[out:json][timeout:60];
nwr["name"~"上海理工大学"](31.15,121.40,31.35,121.62);
out center tags 60;
"""


def run(query):
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


for attempt in range(4):
    try:
        result = run(QUERY)
        break
    except Exception as exc:
        print("retry", attempt, exc, file=sys.stderr)
        time.sleep(8 * (attempt + 1))
else:
    sys.exit("all retries failed")

for el in result.get("elements", []):
    tags = el.get("tags", {})
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lon = el.get("lon") or el.get("center", {}).get("lon")
    print(f"{el['type']}/{el['id']} | {tags.get('name')} | {tags.get('name:en','')} | {lat},{lon} | {tags.get('amenity','')}{tags.get('building','')}{tags.get('landuse','')}")