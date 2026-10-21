"""Seed mapping.json with candidate glyphs. `chosen` stays empty — we pick by hand in table.html."""
import json
import unicodedata
from pathlib import Path

LETTERS = "אבגדהוזחטיכךלמםנןסעפףצץקרשת"

# Prior art, by codepoint. kobi-site: pakala.vip/jad (heb-jad.js, Oct 2025).
KOBI_SITE = {
    "א": "10A32", "ב": "10A31", "ג": "1A71", "ד": "10A45", "ה": "1BC4", "ו": "10858",
    "ז": "10D08", "ח": "10A83", "ט": "2CD2", "י": "144A", "כ": "10D0A", "ך": "0E45",
    "ל": "0286", "מ": "10ACD", "ם": "10B19", "נ": "10883", "ן": "007C", "ס": "1092C",
    "ע": "0264", "פ": "10B1F", "ף": "20B0", "צ": "10B7D", "ץ": "10410", "ק": "10502",
    "ר": "10A2C", "ש": "AAC0", "ת": "1089E",
}

# kobi-sheet: "Hebrew-Fake-Cursive-only-R2L" Google Sheet (all tabs merged).
KOBI_SHEET = {
    "א": "1085E 10ADD 10880 A5EA 10518 10527 30E1 2D4B 03F0",
    "ב": "10C18 07F6 1817 19D3 10D10",
    "ג": "1088C 10B6D 1E90E 1E954 154D",
    "ד": "1085C 1092E 0F22",
    "ה": "2CFB 1BC37 1606 14F6 2E05 25DD",
    "ו": "10B25 1050E 10D31 02DB",
    "ז": "10A21 084F 10C09 10B66 10F37 10523 10491 0296",
    "ח": "10A24 10A90",
    "ט": "080B AA89 1EFC 096E 10E1 10497 0ED2",
    "י": "02B9",
    "כ": "10B0E 10922 10AEC 10CD9 10C99 10C23 10C06 0810",
    "ך": "0294 1548 0241",
    "מ": "10B14 10C07 A93E",
    "ם": "10AEF",
    "נ": "10B0C 10AD4 10895 10891 10B61 10B62 10F39 10EA0",
    "ן": "10B26 10B30 10B78",
    "ס": "1E827 10EA6 10516 10D30",
    "ע": "10EA7 1E937 1E958 10501 1051F 1041C 0263 13C8",
    "פ": "1E808 1E809 10D36",
    "ף": "10C5 10D0C",
    "צ": "10B22 10B24 10A22 10A15 10B63 021C 021D 025C 0292",
    "ץ": "1050B 03C6",
    "ק": "10852 10A2F",
    "ר": "10850",
    "ש": "10B1E 1E920 03F1 0727 1F765 0C7F",
}

# mark-2025-10-17: Mark's picks from the WhatsApp thread.
MARK = {
    "א": "A5EA", "ב": "0EA5", "ג": "19D1 1A71", "ה": "1BC4", "ט": "0ED2", "כ": "0DCF",
    "ל": "0286 27C6", "ע": "0B6A", "פ": "1001 17E6", "ף": "0BBF", "ץ": "20B0",
    "ש": "AAC0", "ת": "0E81",
}


def candidate(cp: str, source: str) -> dict:
    ch = chr(int(cp, 16))
    return {
        "char": ch,
        "cp": f"U+{int(cp, 16):04X}",
        "name": unicodedata.name(ch, ""),
        "bidi": unicodedata.bidirectional(ch),
        "source": [source],
        "android": None,
        "ios": None,
        "whatsapp": None,
    }


def main() -> None:
    table = {}
    for letter in LETTERS:
        cands: dict[str, dict] = {}
        for source, data in (("kobi-site", KOBI_SITE), ("kobi-sheet", KOBI_SHEET),
                             ("mark-2025-10-17", MARK)):
            for cp in data.get(letter, "").split():
                key = f"U+{int(cp, 16):04X}"
                if key in cands:
                    cands[key]["source"].append(source)
                else:
                    cands[key] = candidate(cp, source)
        table[letter] = {"chosen": None, "candidates": list(cands.values())}
    out = Path(__file__).resolve().parent.parent / "mapping.json"
    out.write_text(json.dumps(table, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{out}: {sum(len(v['candidates']) for v in table.values())} candidates")


if __name__ == "__main__":
    main()
