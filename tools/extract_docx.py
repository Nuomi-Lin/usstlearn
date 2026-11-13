import html
import re
import sys
import zipfile


def extract(src, dst):
    with zipfile.ZipFile(src) as z:
        names = [n for n in z.namelist() if n.startswith("word/document")]
        if not names:
            raise SystemExit("no word/document.xml")
        xml = z.read(names[0]).decode("utf-8", "ignore")

    xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    xml = xml.replace("</w:p>", "\n")
    xml = re.sub(r"<[^>]+>", "", xml)
    text = html.unescape(xml)

    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("paragraphs:", len(lines))
    print("chars:", sum(len(x) for x in lines))


if __name__ == "__main__":
    extract(sys.argv[1], sys.argv[2])