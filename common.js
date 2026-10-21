// Shared by index.html and table.html: load the table, transform text.

const DRAFT_KEY = "otijot.draft";
const RLO = "‮";
const PDF = "‬";

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
async function loadTable() {
  const draft = readDraft();
  if (draft) return { table: draft, fromDraft: true };
  const res = await fetch("mapping.json", { cache: "no-store" });
  return { table: await res.json(), fromDraft: false };
}

// An explicit `chosen` wins; otherwise the first candidate (candidate order is the priority).
function chosenCandidate(entry) {
  if (!entry || !entry.candidates.length) return null;
  return entry.candidates.find((c) => c.cp === entry.chosen) || entry.candidates[0];
}

// Deterministic per (seed, position, letter), so the output doesn't flicker while typing;
// a new seed re-rolls everything.
function randomCandidate(entry, seed, pos) {
  if (!entry || !entry.candidates.length) return null;
  let h = (seed * 2654435761 + pos * 40503) >>> 0;
  h = Math.imul(h ^ (h >>> 15), 2246822507) >>> 0;
  h = Math.imul(h ^ (h >>> 13), 3266489909) >>> 0;
  return entry.candidates[(h ^ (h >>> 16)) % entry.candidates.length];
}

// Glyphs that are not already right-to-left get wrapped in RLO…PDF one by one,
// so digits and Latin around them keep their normal direction.
function glyphFor(cand) {
  const rtl = cand.bidi === "R" || cand.bidi === "AL";
  return rtl ? cand.char : RLO + cand.char + PDF;
}

// seed === null → priority mode; a number → random mode.
function transform(text, table, seed = null) {
  let out = "";
  let pos = 0;
  for (const ch of text) {
    const cand = seed === null ? chosenCandidate(table[ch]) : randomCandidate(table[ch], seed, pos);
    out += cand ? glyphFor(cand) : ch;
    pos++;
  }
  return out;
}
