"""Round 3 of Claude's picks (2026-10-21, evening): find_candidates.py ranked against a handwritten-Hebrew
reference (Gveret Levin, ktav yad) plus the reviewed refs, over a font set widened with recent Noto scripts.
Appends to proposals.json with source "claude-3"; table.html shows them in purple. Scripts new in Unicode 15–16
may not render on phones yet."""
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "claude-3"
PICKS = {
    "א": "1E819 1E2C1",
    "ב": "1C0E 1C10 0789 1025 1009",
    "ג": "11EF0 1E2D0 183B 11C59",
    "ד": "1C42 16A63 A6ED 16A61 A8A2",
    "ה": "1047C 1047A 102EF",
    "ז": "16E51 07E8 16E91",
    "ח": "30AB 16E61",
    "ט": "112B2 11206 11281 A53F 0ED5 16A68 10E61",
    "י": "141F 17F8",
    "כ": "19B1 1041 1065 11118 2D22 AAAB",
    "ך": "AAC2 1045C 0577 1045F 104D2 10B10",
    "ל": "11480 10469 1356 158B 1723 10A81",
    "מ": "A942 A940 A93D A93C 109C7 109A6",
    "ם": "1C0D 1C08 10365 1E2C3",
    "נ": "10D22 078A 10B0C 30CE 104E2 1E2F4 13AB",
    "ן": "A937 2CC6 10465 1BC4F",
    "ס": "1171A 11730 1946 10474 11450",
    "ע": "1E4DE 118DC 1C88",
    "פ": "0ED1 1988 ABBD",
    "ף": "1E2D3 10E65 1036C",
    "צ": "112CA 1702 11F54 0C69 1E4D0",
    "ץ": "10675 10A12 109BE",
    "ק": "2CCF 10A41 10A19 12D6 AB7E 11FD1 A750 10E66",
    "ר": "16F04 1092 2E52 1C84 10A26 16AE5",
    "ש": "10E72 07B1 1E4D4 156B 11F2A 0E22 16B10",
    "ת": "0578 2CA1 10340 1E03D 2E86 0E94 11F14 104BA 158C",
}

mapping = json.loads((ROOT / "mapping.json").read_text(encoding="utf-8"))
proposals = json.loads((ROOT / "proposals.json").read_text(encoding="utf-8"))
added, skipped = 0, 0
for letter, cps in PICKS.items():
    entry = mapping[letter]
    known = {c["cp"] for c in entry["candidates"]} | set(entry.get("rejected", []))
    known |= {p["cp"] for p in proposals.get(letter, [])}
    for h in cps.split():
        ch = chr(int(h, 16))
        cp = f"U+{int(h, 16):04X}"
        if cp in known:
            skipped += 1
            continue
        proposals.setdefault(letter, []).append({"char": ch, "cp": cp, "name": unicodedata.name(ch, ""),
                                                 "bidi": unicodedata.bidirectional(ch), "source": [SOURCE]})
        known.add(cp)
        added += 1
(ROOT / "proposals.json").write_text(json.dumps(proposals, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(added, "proposals added,", skipped, "already known")
for letter in PICKS:
    print(letter, " ".join(p["char"] for p in proposals[letter] if SOURCE in p["source"]))
