"""Claude's picks from the find_candidates.py contact sheets (reviewed by eye, 2026-10-21).
Writes proposals.json; table.html shows them in orange until accepted or rejected."""
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PICKS = {
    "א": "A3F8 A5EB A57F A3C5 A580 1D554",
    "ב": "1054D 057B 03E8 03E9 2CC8 2CC9 10530 0EA7 1E959",
    "ג": "16A4E 1A72 118D2 0188 19DA 18B7 010B 16AC7",
    "ד": "11155 1129F 160A 160C 160B 1E912 0507 1129A 11C5B 1313",
    "ה": "1BC2 0784 184B 1D190",
    "ו": "0627 07CA 10CFA 10C3E 01C0 2223 0964",
    "ז": "10A21 1E81E 11C56 10535 104A1 09E7 114D1",
    "ח": "10A2D 1D12 16F06 11283 A4A2 10369 13C1 1260 1D62F",
    "ט": "2CD3 1EFD 0AEE 11658 0431 1816 1986 11097 122A 102C9 11D59 ABBE",
    "י": "066B 066C 055B 1FFD",
    "כ": "10A67 10A87 2183 A4DB 0186 03FD 0254 037B 2184 1D10 16ADC 10140 1044B",
    "ך": "10B2D 097D 0294 02A1 1046A A6EB 1E2F6 1E2F1 17D7 1944 10E95",
    "ל": "10B30 222B 0283 0284 029D A7B2 1DA8 AB4D 118C1 1A6D 11160 10455 179C",
    "מ": "10C08 1D441 1D475 1D615 019D 16A9 1D649 17F7",
    "ם": "10441 10419 03F1",
    "נ": "0631 0695 0694 10EB0 10D13 2C79 027A 02E9 31DA 230B A4D9 A838",
    "ן": "10A40 109A3 0283 222B 23D0 1D100 1735 10483",
    "ס": "07C0 10C17 10A52 0D20 0B66 1BB0 2B58 1119C 0D66",
    "ע": "02E0 0194 1102B 10444 116C4 112C0 096A AB98 A8D4 11AD5 11654 A64B",
    "פ": "1E80A 1E80E 1E910 018B 04D9 0259 01DD 2202 1D715 16ADD 1076 11106 0EA7 11AC8",
    "ף": "10D04 10D1B A76C 0192 1D487 1D471 102E4",
    "צ": "1E934 1E912 109AF 04E1 0437 01B7 1DBE 2CC5 0545 A76A 11296 10442 2CCC 0033",
    "ץ": "0444 03C8 1D60 10438 10421 2C47 1D69 0470",
    "ק": "10C19 10C16 10C9A 10CDA 10C37 03F7 03F8 16A6 00FE 01A5 104EC A766",
    "ר": "10A44 1E800 10A87 10D01 10A00 10460 10472 FF8C 118E8 0242 104A7 10423",
    "ש": "1E935 1D626 1D452 1D486 0065 0435 19C9 1971 155E 0E8D 118E7 11ACB 1113A 1781",
    "ת": "A90A 0E17 0E11 0E20 11219 AA80 1116C 116A2 0E95 AAA6 1168F 0E16",
}

mapping = json.loads((ROOT / "mapping.json").read_text(encoding="utf-8"))
out, skipped = {}, 0
for letter, cps in PICKS.items():
    known = {c["cp"] for c in mapping[letter]["candidates"]} | set(mapping[letter].get("rejected", []))
    items = []
    for h in cps.split():
        ch = chr(int(h, 16))
        cp = f"U+{int(h, 16):04X}"
        if cp in known:
            skipped += 1
            continue
        items.append({"char": ch, "cp": cp, "name": unicodedata.name(ch, ""),
                      "bidi": unicodedata.bidirectional(ch), "source": ["claude"]})
    out[letter] = items
(ROOT / "proposals.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(sum(map(len, out.values())), "proposals,", skipped, "already in table")
for L, items in out.items():
    print(L, " ".join(i["char"] for i in items))
