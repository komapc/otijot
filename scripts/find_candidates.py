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

# Round 1 review: Latin look-alikes and math styles got rejected, the rest ranks high only because
# it is a bar or a blob. ASCII, super/subscripts, letterlike, arrows, box drawing, shapes, dingbats,
# CJK compatibility/vertical/small forms, Arabic presentation forms, fullwidth, math alphanumerics,
# legacy computing.
NOT_LETTERS = [(0x0021, 0x007E), (0x2070, 0x209F), (0x2100, 0x21FF), (0x2460, 0x27BF),
               (0x2B00, 0x2BFF), (0xFB50, 0xFDFF), (0xFE10, 0xFE6F), (0xFE70, 0xFEFF),
               (0xFF00, 0xFFEF), (0x1D400, 0x1D7FF), (0x1FB00, 0x1FBFF)]


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
    if any(lo <= cp <= hi for lo, hi in NOT_LETTERS):          # styled Latin, line pieces, shapes
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
        if name.startswith(CURSIVE_FAMILY.replace(" ", "")):   # the reference, not a source of candidates
            continue
        if any(w in name for w in ("Bold", "Black", "Light", "Thin", "Medium", "Italic", "Oblique",
                                   "Condensed", "SemiBold", "ExtraBold")):
            continue
        keep.setdefault(name.split("-")[0], f)
    return list(keep.values())


LETTERLIKE = {"Lu", "Ll", "Lt", "Lo", "Nd", "Nl", "No"}
CURSIVE_FAMILY = "Gveret Levin"   # OFL handwritten Hebrew, https://github.com/AlefAlefAlef/gveret-levin


def cursive_font_file():
    import subprocess
    out = subprocess.run(["fc-list", f"{CURSIVE_FAMILY}:style=Regular", "file"], capture_output=True, text=True).stdout
    files = [line.split(":")[0] for line in out.split("\n") if line.strip()]
    if not files:
        print(f"{CURSIVE_FAMILY} not installed: ranking only against kept candidates", file=sys.stderr)
    return files[0] if files else None


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

    # The letter itself in handwritten Hebrew, stored under a negative key so it never clashes with a codepoint.
    cursive_font = (cursive_font_file(), 0)
    for letter in mapping:
        r = render(letter, cursive_font) if cursive_font[0] else None
        if r:
            glyphs[-ord(letter)] = (r[0], descriptor(r[0]), r[1], cursive_font[0])
    proposals = json.loads((ROOT / "proposals.json").read_text(encoding="utf-8"))

    def distance(cp, ref):
        bm, desc, aspect, _ = glyphs[cp]
        rbm, rdesc, raspect, _ = glyphs[ref]
        d = chamfer((bm, desc), (rbm, rdesc))
        return d * (1 + 0.5 * abs(np.log(aspect / raspect)))   # penalize very different proportions

    ranked = {}
    for letter, entry in mapping.items():
        # Only kept candidates are references; pending proposals and rejections are just excluded.
        refs = [int(c["cp"][2:], 16) for c in entry["candidates"] if not c.get("proposed")]
        refs = [cp for cp in refs if cp in glyphs]
        known = {int(c["cp"][2:], 16) for c in entry["candidates"]}
        known |= {int(cp[2:], 16) for cp in entry.get("rejected", [])}
        known |= {int(p["cp"][2:], 16) for p in proposals.get(letter, [])}
        pool = [cp for cp in glyphs if cp > 0 and cp not in known]
        # Half the list looks like the handwritten letter (new shapes), the rest like the kept candidates.
        picked = []
        if -ord(letter) in glyphs:
            # Scaled to the same box, accents and punctuation match anything; keep real letters and digits.
            letters = [cp for cp in pool if unicodedata.category(chr(cp)) in LETTERLIKE]
            by_cursive = sorted(letters, key=lambda cp: distance(cp, -ord(letter)))
            picked += [(cp, "ktav") for cp in by_cursive[:TOP // 2]]
        if refs:
            by_refs = sorted(pool, key=lambda cp: min(distance(cp, r) for r in refs))
            seen = {cp for cp, _ in picked}
            picked += [(cp, "refs") for cp in by_refs if cp not in seen][:TOP - len(picked)]
        if not picked:
            continue
        ranked[letter] = [{"cp": f"U+{cp:04X}", "char": chr(cp), "via": via,
                           "name": unicodedata.name(chr(cp), ""), "font": Path(glyphs[cp][3]).name}
                          for cp, via in picked]
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
        refs = [c for c in mapping[letter]["candidates"] if not c.get("proposed") and int(c["cp"][2:], 16) in glyphs][:cols - 1]
        rows = 1 + (len(items) + cols - 1) // cols
        img = Image.new("RGB", (cell * cols, cell * rows + 10), "white")
        d = ImageDraw.Draw(img)
        d.text((10, 0), letter, font=heb_font, fill="black")
        ref_cps = ([-ord(letter)] if -ord(letter) in glyphs else []) + [int(c["cp"][2:], 16) for c in refs]
        for i, cp in enumerate(ref_cps[:cols - 1], start=1):
            draw_cell(img, d, glyphs, cp, (i * cell, 0), cell, "#2f6f5e", label_font, "ref")
        for i, it in enumerate(items):
            x, y = (i % cols) * cell, (1 + i // cols) * cell + 10
            tag = f"{i + 1}{'k' if it.get('via') == 'ktav' else ''}"
            draw_cell(img, d, glyphs, int(it["cp"][2:], 16), (x, y), cell, "black", label_font, tag)
        img.save(out / f"{n:02d}.png")


def draw_cell(img, d, glyphs, cp, xy, cell, color, label_font, tag):
    bm = glyphs[cp][0]
    tile = Image.fromarray(np.where(bm, 0, 255).astype(np.uint8)).resize((cell - 30, cell - 30), Image.NEAREST)
    if color != "black":
        tile = Image.merge("RGB", [tile.point(lambda v: v if v else c) for c in (47, 111, 94)])
    img.paste(tile, (xy[0] + 15, xy[1] + 2))
    label = "ktav yad" if cp < 0 else f"{cp:04X}"
    d.text((xy[0] + 4, xy[1] + cell - 26), f"{tag} {label}", font=label_font, fill=color)


if __name__ == "__main__":
    main()
