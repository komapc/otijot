"""Find glyphs that look like the current candidates of each Hebrew letter.

Renders every codepoint covered by the installed fonts, normalizes the ink to a small bitmap and
ranks it against the letter's existing candidates (they were picked by eye, so they stand in for
the cursive shape). Output: work/ranked.json and per-letter contact sheets in work/sheets/ for a
human (or Claude) to review. Nothing here writes mapping.json or proposals.json.
"""
import json
import sys
import unicodedata
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTCollection, TTFont
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
SIZE = 32          # normalized bitmap side
RENDER = 96        # render size in px
TOP = 60           # candidates kept per letter

SKIP_CATEGORIES = {"Cc", "Cf", "Cs", "Co", "Cn", "Zs", "Zl", "Zp", "Mn", "Me"}

# Samaritan, Mandaic, Imperial Aramaic, Palmyrene, Nabataean, Hatran, Phoenician, Manichaean,
# Parthian/Pahlavi, Sogdian, Chorasmian, Elymaic.
ARAMAIC_FAMILY = [(0x0800, 0x085F), (0x10840, 0x108FF), (0x10900, 0x1091F), (0x10AC0, 0x10AFF),
                  (0x10B40, 0x10BAF), (0x10F00, 0x10F6F), (0x10FB0, 0x10FFF)]


def skip(cp: int) -> bool:
    if 0x0590 <= cp <= 0x05FF or 0xFB1D <= cp <= 0xFB4F:      # Hebrew itself
        return True
    if 0x3400 <= cp <= 0x9FFF or 0x20000 <= cp <= 0x3FFFF:    # CJK ideographs: too dense
        return True
    if 0xAC00 <= cp <= 0xD7AF or 0xF900 <= cp <= 0xFAFF:      # Hangul syllables, compat ideographs
        return True
    if 0x1F000 <= cp <= 0x1FAFF:                              # emoji & pictographs
        return True
    if 0x13000 <= cp <= 0x1345F or 0x14400 <= cp <= 0x1467F:  # hieroglyphs: pictures, not letters
        return True
    if 0x12000 <= cp <= 0x1254F:                              # cuneiform
        return True
    if any(lo <= cp <= hi for lo, hi in ARAMAIC_FAMILY):       # look like print Hebrew, not cursive
        return True
    return unicodedata.category(chr(cp)) in SKIP_CATEGORIES


def font_files():
    import subprocess
    out = subprocess.run(["fc-list", "--format", "%{file}\n"], capture_output=True, text=True).stdout
    files = sorted(set(out.split()))
    # Prefer regular weights; one file per family is enough.
    keep = {}
    for f in files:
        name = Path(f).stem
        if any(w in name for w in ("Bold", "Black", "Light", "Thin", "Medium", "Italic", "Oblique",
                                   "Condensed", "SemiBold", "ExtraBold")):
            continue
        keep.setdefault(name.split("-")[0], f)
    return list(keep.values())


def coverage():
    """codepoint -> first font file that has it (Noto first)."""
    cmap = {}
    files = sorted(font_files(), key=lambda f: (0 if "noto" in f.lower() else 1, f))
    for f in files:
        try:
            fonts = TTCollection(f).fonts if f.endswith(".ttc") else [TTFont(f, lazy=True)]
            ImageFont.truetype(f, RENDER)   # bitmap-only fonts (color emoji etc.) can't scale
        except Exception:
            continue
        for i, font in enumerate(fonts):
            try:
                table = font.getBestCmap() or {}
            except Exception:
                continue
            for cp in table:
                if cp not in cmap and not skip(cp):
                    cmap[cp] = (f, i)
    return cmap


_font_cache = {}


def render(ch: str, font_ref):
    f, idx = font_ref
    key = (f, idx)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(f, RENDER, index=idx)
        except OSError:
            _font_cache[key] = None
    font = _font_cache[key]
    if font is None:
        return None
    img = Image.new("L", (RENDER * 2, RENDER * 2), 0)
    ImageDraw.Draw(img).text((RENDER // 2, RENDER // 2), ch, fill=255, font=font)
    a = np.asarray(img) > 100
    ys, xs = np.nonzero(a)
    if len(xs) < 12:
        return None
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = a.shape
    side = max(h, w)
    sq = np.zeros((side, side), bool)
    sq[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = a
    small = np.asarray(Image.fromarray(sq.astype(np.uint8) * 255).resize((SIZE, SIZE), Image.BILINEAR)) > 60
    return small, w / h


def descriptor(bitmap):
    blur = gaussian_filter(bitmap.astype(float), 1.2)
    blur /= np.linalg.norm(blur) + 1e-9
    dist = distance_transform_edt(~bitmap)
    return blur, dist


def chamfer(a, b):
    """Symmetric mean distance from ink of one to ink of the other (0 = identical)."""
    (ba, da), (bb, db) = a[1], b[1]
    ia, ib = a[0], b[0]
    return (db[ia].mean() + da[ib].mean()) / 2


def main():
    mapping = json.loads((ROOT / "mapping.json").read_text(encoding="utf-8"))
    WORK.mkdir(exist_ok=True)
    print("scanning fonts…", file=sys.stderr)
    cov = coverage()
    print(f"{len(cov)} codepoints", file=sys.stderr)

    glyphs = {}
    for n, (cp, ref) in enumerate(cov.items()):
        r = render(chr(cp), ref)
        if r:
            bm, aspect = r
            glyphs[cp] = (bm, descriptor(bm), aspect, ref[0])
        if n % 5000 == 0:
            print(f"  rendered {n}", file=sys.stderr)

    ranked = {}
    for letter, entry in mapping.items():
        refs = [int(c["cp"][2:], 16) for c in entry["candidates"]]
        refs = [cp for cp in refs if cp in glyphs]
        known = {int(c["cp"][2:], 16) for c in entry["candidates"]}
        if not refs:
            continue
        scores = []
        for cp, (bm, (blur, dist), aspect, _) in glyphs.items():
            if cp in known:
                continue
            best = 1e9
            for r in refs:
                rbm, (rblur, rdist), raspect, _ = glyphs[r]
                d = chamfer((bm, (blur, dist)), (rbm, (rblur, rdist)))
                d *= 1 + 0.5 * abs(np.log(aspect / raspect))   # penalize very different proportions
                best = min(best, d)
            scores.append((best, cp))
        scores.sort()
        ranked[letter] = [{"cp": f"U+{cp:04X}", "char": chr(cp), "score": round(s, 3),
                           "name": unicodedata.name(chr(cp), ""), "font": Path(glyphs[cp][3]).name}
                          for s, cp in scores[:TOP]]
        print(letter, " ".join(x["char"] for x in ranked[letter][:15]), file=sys.stderr)

    (WORK / "ranked.json").write_text(json.dumps(ranked, ensure_ascii=False, indent=1), encoding="utf-8")
    sheets(mapping, ranked, glyphs)


def sheets(mapping, ranked, glyphs):
    out = WORK / "sheets"
    out.mkdir(exist_ok=True)
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    heb_font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf", 90)
    cell, cols = 120, 10
    for n, (letter, items) in enumerate(ranked.items()):
        refs = [c for c in mapping[letter]["candidates"] if int(c["cp"][2:], 16) in glyphs][:cols - 1]
        rows = 1 + (len(items) + cols - 1) // cols
        img = Image.new("RGB", (cell * cols, cell * rows + 10), "white")
        d = ImageDraw.Draw(img)
        d.text((10, 0), letter, font=heb_font, fill="black")
        for i, c in enumerate(refs, start=1):
            draw_cell(img, d, glyphs, int(c["cp"][2:], 16), (i * cell, 0), cell, "#2f6f5e", label_font, "ref")
        for i, it in enumerate(items):
            x, y = (i % cols) * cell, (1 + i // cols) * cell + 10
            draw_cell(img, d, glyphs, int(it["cp"][2:], 16), (x, y), cell, "black", label_font, str(i + 1))
        img.save(out / f"{n:02d}.png")


def draw_cell(img, d, glyphs, cp, xy, cell, color, label_font, tag):
    bm = glyphs[cp][0]
    tile = Image.fromarray(np.where(bm, 0, 255).astype(np.uint8)).resize((cell - 30, cell - 30), Image.NEAREST)
    if color != "black":
        tile = Image.merge("RGB", [tile.point(lambda v: v if v else c) for c in (47, 111, 94)])
    img.paste(tile, (xy[0] + 15, xy[1] + 2))
    d.text((xy[0] + 4, xy[1] + cell - 26), f"{tag} {cp:04X}", font=label_font, fill=color)


if __name__ == "__main__":
    main()
