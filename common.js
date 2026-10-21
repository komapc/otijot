// Shared by index.html and table.html: load the table, transform text.

const DRAFT_KEY = "otijot.draft";
const RLM = "\u200F";
const RLO = "\u202E";
const LRO = "\u202D";
const PDF = "\u202C";
const ZWNJ = "\u200C";

function readDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeDraft(table) {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(table));
  } catch {
    /* private mode etc. — the draft just isn't kept */
  }
}

function clearDraft() {
  try {
    localStorage.removeItem(DRAFT_KEY);
  } catch {}
}

// A local draft (unsaved edits from table.html) wins over mapping.json.
// Codepoints rejected in mapping.json are dropped from the draft too.
async function loadTable() {
  const res = await fetch("mapping.json", { cache: "no-store" });
  const base = await res.json();
  const draft = readDraft();
  if (!draft) return { table: base, fromDraft: false };
  for (const [letter, entry] of Object.entries(draft)) {
    const rejected = new Set([...(entry.rejected || []), ...(base[letter]?.rejected || [])]);
    if (!rejected.size) continue;
    entry.rejected = [...rejected];
    entry.candidates = entry.candidates.filter((c) => !rejected.has(c.cp));
    if (rejected.has(entry.chosen)) entry.chosen = null;
  }
  return { table: draft, fromDraft: true };
}

// Proposals (from proposals.json) stay out of the converter until accepted in table.html.
function usable(entry) {
  return entry ? entry.candidates.filter((c) => !c.proposed) : [];
}

// An explicit `chosen` wins; otherwise the first candidate (candidate order is the priority).
function chosenCandidate(entry) {
  const cands = usable(entry);
  if (!cands.length) return null;
  return cands.find((c) => c.cp === entry.chosen) || cands[0];
}

// Deterministic per (seed, position, letter), so the output doesn't flicker while typing;
// a new seed re-rolls everything.
function randomCandidate(entry, seed, pos) {
  const cands = usable(entry);
  if (!cands.length) return null;
  let h = (seed * 2654435761 + pos * 40503) >>> 0;
  h = Math.imul(h ^ (h >>> 15), 2246822507) >>> 0;
  h = Math.imul(h ^ (h >>> 13), 3266489909) >>> 0;
  return cands[((h ^ (h >>> 16)) >>> 0) % cands.length]; // >>> 0: XOR is signed, a negative index → undefined
}

// Append proposals the table doesn't have yet and that weren't rejected before. Returns how many.
async function mergeProposals(table) {
  let proposals;
  try {
    const res = await fetch("proposals.json", { cache: "no-store" });
    if (!res.ok) return 0;
    proposals = await res.json();
  } catch {
    return 0;
  }
  let added = 0;
  for (const [letter, items] of Object.entries(proposals)) {
    const entry = table[letter];
    if (!entry) continue;
    const seen = new Set([...entry.candidates.map((c) => c.cp), ...(entry.rejected || [])]);
    for (const p of items) {
      if (seen.has(p.cp)) continue;
      entry.candidates.push({ ...p, source: p.source || ["claude"], proposed: true,
                              android: null, ios: null, whatsapp: null });
      seen.add(p.cp);
      added++;
    }
  }
  return added;
}

// Glyphs that are not already right-to-left get wrapped in RLO…PDF one by one,
// so digits and Latin around them keep their normal direction.
// Mirrored neutrals (∫ ⌋ …) would flip at an odd level, so they get LRO instead, fenced by RLM
// so the spaces next to them still resolve to RTL.
// Arabic-type glyphs (Hanifi Rohingya etc.) would join their neighbours; ZWNJ keeps them apart.
function glyphFor(cand) {
  if (cand.bidi === "R") return cand.char;
  if (cand.bidi === "AL") return cand.char + ZWNJ;
  if (/\p{Bidi_Mirrored}/u.test(cand.char)) return RLM + LRO + cand.char + PDF + RLM;
  return RLO + cand.char + PDF;
}

// seed === null → priority mode; a number → random mode.
function transform(text, table, seed = null) {
  if (!text) return "";
  // RLM at both ends of every line: apps pick the paragraph direction from the first strong
  // character (an LTR glyph would make the line LTR), and trailing punctuation would drift right.
  let out = RLM;
  let pos = 0;
  for (const ch of text) {
    const cand = seed === null ? chosenCandidate(table[ch]) : randomCandidate(table[ch], seed, pos);
    out += ch === "\n" ? RLM + "\n" + RLM : cand ? glyphFor(cand) : ch;
    pos++;
  }
  return out + RLM;
}
