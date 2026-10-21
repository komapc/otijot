"""Round 2 of Claude's picks (2026-10-21, afternoon): find_candidates.py re-run against the reviewed
mapping, styled Latin and line/shape blocks filtered out, then picked by eye from the sheets.
Appends to proposals.json with source "claude-2"; table.html shows them in blue, round 1 stays orange."""
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "claude-2"
PICKS = {
    "א": "16D5 10CDE A4D7 A360 A3B2 A1FF",
    "ב": "1E808 1611 1612 1001 1A21 1E8CE",
    "ג": "10454 116A4 109A5 1627 16A2E 1599",
    "ד": "0F23 1A2F 112DA 116A1 0506",
    "ה": "1B0A",
    "ו": "16C1 2D4F",
    "ז": "0576 0565 1C69 10543",
    "ח": "AB91 1422 1E2D4 1C98 11715 1DAE",
    "ט": "19C8 13EE 1041E 0573 11291 1BC56",
    "כ": "1450 10423 19D1 1A63 AAE0 1642 16A40 1BC79",
    "ך": "10450 1097 172A 10743 1B5E A8D2",
    "ל": "179A 2CFD 2E2F 1DB4 10A46 AA5D",
    "מ": "A932 1425 1BB7 A73A 16B4 16AB",
    "ם": "10B02 10B03 1B67 0784",
    "נ": "10453 10468 19D2 A491 16F33 31C1",
    "ן": "0719 10462 10458 1963 11238 11C41",
    "ס": "199E 19D0 1C40 104EA 10404 A9D0 1BC44 1A80",
    "ע": "114D4 10480 0AEA 17F5 11137 11599 1CBE",
    "פ": "1013 A9E0 10402 11105 1BC5D 1E11A",
    "ף": "1575 0D67 1682F 16A0D 1D191",
    "צ": "102E7 10B24 11653 16E7E 1041A 16F3B 1B54",
    "ץ": "16F0 1240 102B3 2CE1 10CB2 10449 10560",
    "ק": "104ED AB06 16A7 1C5E 10313 1549 0562 104C4",
    "ר": "16F34 10487 10461 1046E 11058 1BFF 1295",
    "ש": "112C7 1054 16F14 107F 2C89 0C32",
    "ת": "0E84 11A21 A90F 0E01 AA6B 195F",
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
