import json
import math
import os

LAT0, LON0 = 31.2949258, 121.5501948
MX = 111320.0 * math.cos(math.radians(LAT0))
MZ = 110540.0


def project(lat, lon):
    return ((lon - LON0) * MX, -(lat - LAT0) * MZ)


def rdp(points, eps=1.2):
    if len(points) < 4:
        return points

    def perp(p, a, b):
        ax, ay = a
        bx, by = b
        px, py = p
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def simplify(pts):
        if len(pts) < 3:
            return pts
        dmax, idx = 0.0, 0
        for i in range(1, len(pts) - 1):
            d = perp(pts[i], pts[0], pts[-1])
            if d > dmax:
                dmax, idx = d, i
        if dmax > eps:
            left = simplify(pts[: idx + 1])
            right = simplify(pts[idx:])
            return left[:-1] + right
        return [pts[0], pts[-1]]

    return simplify(points)


def assemble(ways):
    ways = [[tuple(p) for p in w] for w in ways if len(w) >= 2]
    if not ways:
        return []
    rings, used = [], [False] * len(ways)
    for i in range(len(ways)):
        if used[i]:
            continue
        ring = list(ways[i])
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j in range(len(ways)):
                if used[j]:
                    continue
                w = ways[j]
                if ring[-1] == w[0]:
                    ring.extend(w[1:])
                elif ring[-1] == w[-1]:
                    ring.extend(list(reversed(w))[1:])
                elif ring[0] == w[-1]:
                    ring = w[:-1] + ring
                elif ring[0] == w[0]:
                    ring = list(reversed(w))[:-1] + ring
                else:
                    continue
                used[j] = True
                changed = True
        rings.append(ring)
    rings.sort(key=lambda r: -abs(sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))))
    return rings


def in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1):
            inside = not inside
    return inside


def area(poly):
    s = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


with open("data/campus_boundary.json", encoding="utf-8") as fh:
    boundary_raw = json.load(fh)

campus_polys = []
for rel in boundary_raw["elements"]:
    ways = []
    for m in rel.get("members", []):
        if m.get("type") == "way" and m.get("role") in ("outer", "") and m.get("geometry"):
            ways.append([project(p["lat"], p["lon"]) for p in m["geometry"]])
    for ring in assemble(ways):
        ring = rdp(ring, 1.0)
        if len(ring) >= 3 and area(ring) > 200:
            campus_polys.append(ring)

with open("data/osm_campus_raw.json", encoding="utf-8") as fh:
    raw = json.load(fh)

elements = raw["elements"]

HIST = {
    "思雷堂", "思孟堂", "思伊堂", "思裴堂", "怀德堂", "馥赉堂", "音乐堂", "大礼堂",
    "刘湛恩故居", "艾德蒙堂", "思福堂", "格致堂", "湛恩纪念图书馆", "藏书楼",
}

HEIGHT_BY_NAME = {
    "湛恩纪念图书馆": 26, "科技大楼": 32, "先进制造技术大楼": 30, "综合楼 A 座": 24,
    "综合楼 B 座": 24, "综合楼 C 座": 24, "综合楼 D 座": 24, "机械工程学院 / 学生创业中心": 22,
    "管理学院": 22, "环境与建筑学院": 20, "第一教学楼": 18, "大礼堂": 15, "音乐堂": 13,
    "室内体育馆": 14, "体育文化活动中心": 16, "刘湛恩故居": 9, "申一宿舍": 28,
    "第一办公楼 (思雷堂)": 13, "第二办公楼 (思孟堂)": 13, "第三宿舍 (思裴堂)": 12,
    "第四宿舍 (思伊堂)": 12, "第五宿舍 (怀德堂)": 12, "第六宿舍 (留学生公寓) (馥赉堂)": 12,
}

KIND_H = {
    "dormitory": 20, "university": 16, "school": 15, "library": 22, "restaurant": 9,
    "hospital": 22, "residential": 24, "apartments": 24, "construction": 11,
    "roof": 4, "yes": 11, "house": 6, "garage": 4, "garages": 4, "shed": 4,
    "kindergarten": 10, "office": 18, "commercial": 16, "retail": 12,
}


def poly_of(el):
    if el["type"] == "way":
        pts = [project(p["lat"], p["lon"]) for p in el.get("geometry", [])]
        return rdp(pts, 1.0)
    members = [m for m in el.get("members", []) if m.get("type") == "way" and m.get("role") in ("outer", "") and m.get("geometry")]
    ways = [[project(p["lat"], p["lon"]) for p in m["geometry"]] for m in members]
    rings = assemble(ways)
    return rdp(rings[0], 1.0) if rings else []


buildings = []
for el in elements:
    tags = el.get("tags", {})
    if "building" not in tags:
        continue
    poly = poly_of(el)
    if len(poly) < 3 or area(poly) < 10:
        continue
    name = tags.get("name") or ""
    kind = tags.get("building")
    if kind in ("university", "school"):
        kind = "university" if (tags.get("amenity") == "university" or kind == "university") else "school"
    levels = tags.get("building:levels")
    try:
        levels = float(levels)
    except (TypeError, ValueError):
        levels = None

    if name in HEIGHT_BY_NAME:
        h = HEIGHT_BY_NAME[name]
    elif levels:
        h = min(levels * 3.3 + 1.2, 90)
    else:
        h = KIND_H.get(kind, 12)

    cx = sum(p[0] for p in poly) / len(poly)
    cz = sum(p[1] for p in poly) / len(poly)
    inside = any(in_poly((cx, cz), cp) for cp in campus_polys)
    if not inside and area(poly) < 400:
        continue

    buildings.append({
        "id": el["id"],
        "n": name,
        "k": kind,
        "h": round(h, 1),
        "a": round(area(poly)),
        "p": [[round(x, 1), round(z, 1)] for x, z in poly],
        "c": [round(cx, 1), round(cz, 1)],
        "in": 1 if inside else 0,
        "hist": 1 if name in HIST else 0,
    })

ROAD_W = {
    "trunk": 26, "trunk_link": 12, "primary": 22, "primary_link": 12, "secondary": 17,
    "secondary_link": 10, "tertiary": 13, "tertiary_link": 8, "residential": 9,
    "living_street": 8, "unclassified": 8, "service": 5, "pedestrian": 7,
    "footway": 2.6, "cycleway": 3.2, "steps": 3, "path": 2.2, "track": 3.5,
    "proposed": 8,
}

roads = []
for el in elements:
    tags = el.get("tags", {})
    hw = tags.get("highway")
    if not hw or el["type"] != "way":
        continue
    pts = [project(p["lat"], p["lon"]) for p in el.get("geometry", [])]
    if len(pts) < 2:
        continue
    pts = rdp(pts, 0.8)
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    inside = any(in_poly((cx, cz), cp) for cp in campus_polys)
    roads.append({
        "k": hw,
        "w": ROAD_W.get(hw, 8),
        "p": [[round(x, 1), round(z, 1)] for x, z in pts],
        "in": 1 if inside else 0,
    })

WATER_W = {"river": 260, "canal": 34, "stream": 12, "drain": 8, "ditch": 6}
CLIP = (-1150.0, -1000.0, 1250.0, 1350.0)


def clip_seg(p0, p1, box):
    xmin, ymin, xmax, ymax = box
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    u1, u2 = 0.0, 1.0
    for pi, qi in ((-dx, x0 - xmin), (dx, xmax - x0), (-dy, y0 - ymin), (dy, ymax - y0)):
        if pi == 0:
            if qi < 0:
                return None
        else:
            r = qi / pi
            if pi < 0:
                u1 = max(u1, r)
            else:
                u2 = min(u2, r)
    if u1 > u2:
        return None
    return ((x0 + u1 * dx, y0 + u1 * dy), (x0 + u2 * dx, y0 + u2 * dy))


def clip_polyline(points, box):
    out, cur = [], []
    for i in range(len(points) - 1):
        seg = clip_seg(points[i], points[i + 1], box)
        if not seg:
            if len(cur) >= 2:
                out.append(cur)
            cur = []
            continue
        a, b = seg
        if not cur:
            cur = [a, b]
        elif abs(cur[-1][0] - a[0]) < 0.5 and abs(cur[-1][1] - a[1]) < 0.5:
            cur.append(b)
        else:
            if len(cur) >= 2:
                out.append(cur)
            cur = [a, b]
    if len(cur) >= 2:
        out.append(cur)
    return out


waters = []
for el in elements:
    tags = el.get("tags", {})
    ww = tags.get("waterway")
    if not ww or el["type"] != "way":
        continue
    pts = [project(p["lat"], p["lon"]) for p in el.get("geometry", [])]
    if len(pts) < 2:
        continue
    if tags.get("name") == "黄浦江":
        width = 380
    elif tags.get("name") in ("复兴岛运河", "虬江"):
        width = 36
    elif tags.get("name") == "东走马塘":
        width = 22
    else:
        width = WATER_W.get(ww, 10)
    for part in clip_polyline(pts, CLIP):
        part = rdp(part, 2.0)
        if len(part) < 2:
            continue
        waters.append({
            "n": tags.get("name") or "",
            "w": width,
            "p": [[round(x, 1), round(z, 1)] for x, z in part],
        })

greens, pitches, tracks, parking = [], [], [], []
for el in elements:
    tags = el.get("tags", {})
    if el["type"] != "way":
        continue
    leisure = tags.get("leisure")
    landuse = tags.get("landuse")
    amenity = tags.get("amenity")
    if not (leisure in ("park", "garden", "pitch", "track") or landuse in ("grass", "meadow", "forest", "village_green") or amenity == "parking"):
        continue
    pts = [project(p["lat"], p["lon"]) for p in el.get("geometry", [])]
    if len(pts) < 3:
        continue
    pts = rdp(pts, 1.2)
    if area(pts) < 30:
        continue
    item = {
        "s": tags.get("sport") or "",
        "p": [[round(x, 1), round(z, 1)] for x, z in pts],
    }
    if leisure == "track":
        tracks.append(item)
    elif leisure == "pitch":
        pitches.append(item)
    elif amenity == "parking":
        parking.append(item)
    else:
        greens.append(item)

xs = [p[0] for cp in campus_polys for p in cp]
zs = [p[1] for cp in campus_polys for p in cp]

scene = {
    "meta": {
        "center": [LAT0, LON0],
        "bounds": [round(min(xs)), round(min(zs)), round(max(xs)), round(max(zs))],
        "buildings": len(buildings),
        "named": sum(1 for b in buildings if b["n"]),
        "source": "OpenStreetMap contributors (ODbL)",
    },
    "campus": [[[round(x, 1), round(z, 1)] for x, z in cp] for cp in campus_polys],
    "buildings": buildings,
    "roads": roads,
    "waters": waters,
    "greens": greens,
    "pitches": pitches,
    "tracks": tracks,
    "parking": parking,
}

os.makedirs("data", exist_ok=True)
with open("data/campus_scene.js", "w", encoding="utf-8") as fh:
    fh.write("window.CAMPUS_SCENE=")
    json.dump(scene, fh, ensure_ascii=False, separators=(",", ":"))
    fh.write(";\n")

print("campus polygons:", len(campus_polys))
print("bounds(x,z):", scene["meta"]["bounds"])
print("buildings:", len(buildings), "named:", scene["meta"]["named"], "inside:", sum(b["in"] for b in buildings))
print("roads:", len(roads), "waters:", len(waters), "greens:", len(greens), "pitches:", len(pitches), "tracks:", len(tracks), "parking:", len(parking))
print("file KB:", round(os.path.getsize("data/campus_scene.js") / 1024))