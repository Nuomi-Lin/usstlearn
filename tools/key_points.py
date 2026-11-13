import re

SRC = r"tools\military_text.txt"
DST = r"tools\key_points.txt"

NOISE = re.compile(r"^(［|（第|\(第|\d+$|图\s*\d|表\s*\d)")
HEAD = re.compile(r"^第[一二三四五六七八九十百]+[章节]")


def clean(lines, start, limit=8):
    picked = []
    j = start
    while j < len(lines) and len(picked) < limit:
        s = lines[j].strip()
        if HEAD.match(s) and len(s) < 40:
            break
        if s and not NOISE.match(s) and len(s) > 8:
            picked.append(s)
        j += 1
    return picked


with open(SRC, encoding="utf-8") as f:
    lines = [x.rstrip() for x in f]

out = []
for i, line in enumerate(lines):
    s = line.strip()
    if HEAD.match(s) and len(s) < 40:
        out.append("")
        out.append("### " + s)
        for p in clean(lines, i + 1):
            out.append(p)

with open(DST, "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print("sections:", sum(1 for x in out if x.startswith("### ")))
print("lines:", len(out))