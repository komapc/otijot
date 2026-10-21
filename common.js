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

function chosenCandidate(entry) {
  if (!entry || !entry.chosen) return null;
  return entry.candidates.find((c) => c.cp === entry.chosen) || null;
}

// Glyphs that are not already right-to-left get wrapped in RLO…PDF one by one,
// so digits and Latin around them keep their normal direction.
function glyphFor(cand) {
  const rtl = cand.bidi === "R" || cand.bidi === "AL";
  return rtl ? cand.char : RLO + cand.char + PDF;
}

function transform(text, table) {
  let out = "";
  for (const ch of text) {
    const cand = chosenCandidate(table[ch]);
    out += cand ? glyphFor(cand) : ch;
  }
  return out;
}
