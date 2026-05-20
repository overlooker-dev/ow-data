import html
import json
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_FILE = ROOT / "maps_wiki_page.html"
MAPS_JSON = ROOT / "maps.json"
OUT_DIR = ROOT / "map_backgrounds"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s


def main() -> None:
    maps = json.loads(MAPS_JSON.read_text(encoding="utf-8"))
    # lookup: normalized name/alias -> canonical map dict
    lookup = {}
    for m in maps:
        lookup[norm(m["name"])] = m
        for a in m.get("aliases", []):
            lookup.setdefault(norm(a), m)

    page = HTML_FILE.read_text(encoding="utf-8")
    boxes = re.findall(
        r'<li class="gallerybox".*?</li>', page, re.DOTALL
    )
    print(f"Found {len(boxes)} gallery items in HTML")

    # name -> image url
    found = {}
    for box in boxes:
        m = re.search(
            r'<div class="thumb".*?<a href="(https://static\.wikia[^"]+)"'
            r'[^>]*class="mw-file-description image"[^>]*title="([^"]+)"',
            box,
            re.DOTALL,
        )
        if not m:
            continue
        url, title = m.group(1), html.unescape(m.group(2))
        found[norm(title)] = (title, url)

    OUT_DIR.mkdir(exist_ok=True)
    matched, missing = [], []
    for m in maps:
        key = norm(m["name"])
        hit = found.get(key)
        if not hit:
            for a in m.get("aliases", []):
                hit = found.get(norm(a))
                if hit:
                    break
        if hit:
            matched.append((m, hit))
        else:
            missing.append(m["name"])

    print(f"\nMatched {len(matched)} / {len(maps)} maps")
    if missing:
        print(f"No image found for {len(missing)} maps:")
        for name in missing:
            print(f"  - {name}")

    print("\nDownloading...")
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "Mozilla/5.0")]
    for m, (title, url) in matched:
        ext = ".png" if ".png" in url.split("/revision")[0].lower() else ".jpg"
        dest = OUT_DIR / f"{slugify(m['name'])}{ext}"
        try:
            with opener.open(url, timeout=60) as resp:
                data = resp.read()
            dest.write_bytes(data)
            print(f"  OK  {m['name']:32s} -> {dest.name} ({len(data)//1024} KB)")
        except Exception as e:
            print(f"  ERR {m['name']:32s} : {e}")
        time.sleep(0.3)

    print("\nDone.")


if __name__ == "__main__":
    main()
