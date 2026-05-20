import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BG_DIR = ROOT / "map_backgrounds"
SRC_DIR = BG_DIR / "_source"
WIDTHS = [1920, 1280, 640, 320]
QUALITY = 82


def main() -> None:
    SRC_DIR.mkdir(exist_ok=True)

    # Move originals into _source/ (idempotent).
    for f in BG_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            dest = SRC_DIR / f.name
            shutil.move(str(f), str(dest))

    sources = sorted(p for p in SRC_DIR.iterdir() if p.is_file())
    print(f"{len(sources)} source images")

    for w in WIDTHS:
        (BG_DIR / str(w)).mkdir(exist_ok=True)

    total = 0
    for src in sources:
        im = Image.open(src)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        ow, oh = im.size
        slug = src.stem
        sizes = []
        for w in WIDTHS:
            tw = min(w, ow)  # never upscale
            th = round(oh * tw / ow)
            variant = im.resize((tw, th), Image.LANCZOS)
            out = BG_DIR / str(w) / f"{slug}.webp"
            variant.save(out, "WEBP", quality=QUALITY, method=6)
            kb = out.stat().st_size / 1024
            sizes.append(f"{w}:{tw}x{th}/{kb:.0f}KB")
            total += 1
        print(f"  {slug:36s} src {ow}x{oh}  ->  " + "  ".join(sizes))

    print(f"\nWrote {total} webp files across {len(WIDTHS)} widths.")


if __name__ == "__main__":
    main()
