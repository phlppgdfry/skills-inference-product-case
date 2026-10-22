// SkillDraft in the browser: a line-for-line port of the Python pipeline (configuration D,
// hashing embedder), so the demo runs any job description you paste without a server.
// tests/js/parity.mjs checks it against the Python output on all 100 test descriptions.
// Mirrors: skilldraft/text.py, taxonomy.py, embed.py, pipeline.py, scorer.py, inclusive.py

const TOKEN = /[a-z0-9+#]+/g;
const SENTENCE_END = /[.!?;](?=\s)/g;
const SECTION_KEYWORDS = [
  ["offer", [["what", "we", "offer"], ["our", "offer"], ["we", "offer"], ["wat", "wij", "bieden"], ["ons", "aanbod"], ["aanbod"], ["benefits"]]],
  ["pref", [["nice", "to", "have"], ["bonus"], ["a", "plus"], ["pluspunten"], ["een", "plus"], ["troeven"]]],
  ["req", [["what", "you", "bring"], ["your", "profile"], ["requirements"], ["profile"], ["jouw", "profiel"], ["profiel"], ["wat", "breng", "je", "mee"], ["vereisten"], ["who", "you", "are"]]],
  ["resp", [["your", "role"], ["responsibilities"], ["what", "you", "will", "do"], ["jouw", "rol"], ["takenpakket"], ["wat", "ga", "je", "doen"], ["functie"]]],
  ["about", [["about"], ["who", "we", "are"], ["over"], ["wie", "zijn", "we"], ["bedrijf"], ["company"]]],
];
export const GOOD_SECTIONS = ["title", "resp", "req", "pref", "unknown", "profile", "experience", "skills", "languages", "education"];
const CV_SECTION_KEYWORDS = [
  ["experience", [["experience"], ["work", "experience"], ["werkervaring"], ["ervaring"], ["employment"]]],
  ["skills", [["skills"], ["vaardigheden"], ["competenties"]]],
  ["languages", [["languages"], ["talen"]]],
  ["education", [["education"], ["courses"], ["opleiding"], ["opleidingen"], ["certificates"]]],
  ["profile", [["profile"], ["about", "me"], ["profiel"], ["over", "mij"], ["summary"]]],
  ["interests", [["interests"], ["hobbies"], ["interesses"], ["hobby", "s"]]],
];
const ASPIRATION_CUES = [["would", "like", "to", "learn"], ["want", "to", "learn"], ["next", "step"], ["hope", "to"],
  ["wil", "graag"], ["volgende", "stap"], ["wil", "leren"]];
const JOB_LINE = /(?:19|20)\d{2}\s*[–-]\s*(?:(?:19|20)\d{2}|now|today|heden|nu)/;
const PREFERRED_CUES = [["a", "plus"], ["bonus"], ["nice"], ["pluspunt"], ["troef"], ["meegenomen"], ["would", "be", "nice"]];
const NEGATION_CUES = new Set(["no", "not", "t", "without", "never", "geen", "niet", "zonder", "hoeft", "nooit"]);
const NEGATION_AFTER_CUES = new Set(["not", "t", "geen", "niet"]);
const NEG_BEFORE = 5, NEG_AFTER = 3;
const REQUIREMENT_NEGATIONS = [["no", "hands"], ["nog", "geen"], ["not", "necessary"], ["not", "required"], ["no", "prior"], ["don", "t", "need"], ["geen", "vereiste"], ["niet", "nodig"], ["hoeft"]];
const YOU = new Set(["you", "your", "je", "jij", "jouw", "u"]);
const WE = new Set(["we", "our", "us", "wij", "onze", "ons"]);
const ASKS = new Set(["expect", "looking", "need", "require", "seek", "verwachten", "zoeken", "vragen"]);
const OFFER_CUES = [["training"], ["course"], ["opleiding"], ["opleidingsbudget"], ["salary"], ["loon"], ["meal", "vouchers"],
  ["maaltijdcheques"], ["company", "car"], ["bedrijfswagen"], ["days", "off"], ["verlofdagen"], ["lessons"], ["lessen"]];
const CONTACT_CUES = [["contact"], ["questions"], ["apply"], ["vragen"], ["solliciteer"], ["neem", "contact"]];
const STOPWORDS = new Set(`a an the and or of to in on at for with by from as is are be will you your we our us it its this that these those
who what which can our than then into across per every each all any our more most very also not no
de het een en of te in op aan voor met door van als is zijn wordt je jij jouw we wij onze ons dit dat deze die
wie wat welke kan dan naar over per elke elk alle meer zeer ook niet geen er`.split(/\s+/));

export function fold(text) {
  let out = "";
  for (const ch of text) {
    const d = ch.normalize("NFKD").replace(/\p{Mn}/gu, "").toLowerCase();
    out += d ? [...d][0] : " ";
  }
  return out;
}

function tokenize(folded, offset = 0) {
  const out = [];
  for (const m of folded.matchAll(TOKEN)) out.push({ text: m[0], start: m.index + offset, end: m.index + m[0].length + offset });
  return out;
}

function contains(words, seq) {
  for (let i = 0; i + seq.length <= words.length; i++) {
    if (seq.every((w, j) => words[i + j] === w)) return true;
  }
  return false;
}

function sectionOf(words, table = SECTION_KEYWORDS) {
  for (const [section, patterns] of table) if (patterns.some((p) => contains(words, p))) return section;
  return null;
}

function isHeading(line, words, table) {
  const s = line.trim();
  if (!words.length || words.length > 6 || ".!?".includes(s.slice(-1)) && s.length) return null;
  return sectionOf(words, table);
}

function splitLine(line, start) {
  const spans = [];
  let s = 0;
  for (const m of line.matchAll(SENTENCE_END)) { spans.push([s, m.index + 1]); s = m.index + 1; }
  spans.push([s, line.length]);
  const out = [];
  for (let [a, b] of spans) {
    while (a < b && (/\s/.test(line[a]) || "-•*·".includes(line[a]))) a++;
    while (b > a && /\s/.test(line[b - 1])) b--;
    if (b > a) out.push([start + a, start + b]);
  }
  return out;
}

function voice(words) {
  if (words.some((w) => YOU.has(w) || ASKS.has(w))) return "you";
  if (words.some((w) => WE.has(w))) return "we";
  return "neutral";
}

export function segment(text, kind = "jd") {
  const cv = kind === "cv";
  const table = cv ? CV_SECTION_KEYWORDS : SECTION_KEYWORDS;
  const folded = fold(text);
  const sentences = [];
  let section = cv ? "header" : "unknown", seenHeading = false, pos = 0, firstLine = true;
  for (const line of text.split("\n")) {
    const start = pos;
    pos += line.length + 1;
    const words = tokenize(folded.slice(start, start + line.length)).map((t) => t.text);
    if (!words.length) continue;
    const heading = isHeading(line, words, table);
    const trimmedEnd = start + line.replace(/\s+$/, "").length;
    if (heading) {
      section = heading; seenHeading = true;
      const a = start + (line.length - line.replace(/^\s+/, "").length);
      sentences.push({ index: sentences.length, start: a, end: trimmedEnd, text: line.trim(), tokens: tokenize(folded.slice(start, start + line.length), start), section: heading, heading: true });
      firstLine = false;
      continue;
    }
    if (firstLine && !cv && words.length <= 8 && !".!?".includes(line.trim().slice(-1))) {
      sentences.push({ index: sentences.length, start, end: trimmedEnd, text: line.trim(), tokens: tokenize(folded.slice(start, start + line.length), start), section: "title", heading: false, voice: "neutral" });
      firstLine = false;
      continue;
    }
    firstLine = false;
    for (const [a, b] of splitLine(line, start)) {
      const toks = tokenize(folded.slice(a, b), a);
      if (!toks.length) continue;
      const w = toks.map((t) => t.text);
      sentences.push({
        index: sentences.length, start: a, end: b, text: text.slice(a, b), tokens: toks, section, heading: false,
        voice: cv ? "neutral" : voice(w), aspiration: cv && ASPIRATION_CUES.some((c) => contains(w, c)), preferredCue: PREFERRED_CUES.some((c) => contains(w, c)), offerCue: OFFER_CUES.some((c) => contains(w, c)),
        contact: CONTACT_CUES.some((c) => contains(w, c)), requirementNegated: REQUIREMENT_NEGATIONS.some((c) => contains(w, c)),
      });
    }
  }
  return [sentences, seenHeading];
}

function negatedAt(tokens, first, last) {
  const before = tokens.slice(Math.max(0, first - NEG_BEFORE), first);
  const after = tokens.slice(last + 1, last + 1 + NEG_AFTER);
  return before.some((t) => NEGATION_CUES.has(t.text)) || after.some((t) => NEGATION_AFTER_CUES.has(t.text));
}

export function detectLanguage(text) {
  const words = tokenize(fold(text)).map((t) => t.text);
  const NL = new Set(["je", "jij", "jouw", "het", "een", "van", "met", "wij", "onze", "ervaring", "kennis", "en"]);
  const EN = new Set(["you", "your", "the", "a", "of", "with", "we", "our", "experience", "knowledge", "and"]);
  const nl = words.filter((w) => NL.has(w)).length, en = words.filter((w) => EN.has(w)).length;
  return nl > en ? "nl" : "en";
}

// ---------------------------------------------------------------- taxonomy
export class Taxonomy {
  constructor(data) {
    this.version = data.version;
    this.skills = data.skills;
    this.byId = Object.fromEntries(this.skills.map((s) => [s.id, s]));
    this.trie = new Map();
    for (const s of this.skills) {
      for (const a of s.aliases) {
        let node = this.trie;
        for (const t of tokenize(fold(a.text))) {
          if (!node.has(t.text)) node.set(t.text, new Map());
          node = node.get(t.text);
        }
        node.set("$", [s.id, a.text, a.ambiguous]);
      }
    }
  }

  profileText(id) {
    const s = this.byId[id];
    return [s.label, ...s.aliases.map((a) => a.text), s.definition.en, s.definition.nl].join(". ");
  }

  match(tokens) {
    const hits = [];
    let i = 0;
    while (i < tokens.length) {
      let node = this.trie, j = i, best = null;
      while (j < tokens.length && node.has(tokens[j].text)) {
        node = node.get(tokens[j].text);
        if (node.has("$")) best = [j, node.get("$")];
        j++;
      }
      if (best) {
        const [last, [id, alias, ambiguous]] = best;
        hits.push({ skillId: id, alias, first: i, last, start: tokens[i].start, end: tokens[last].end, ambiguous });
        i = last + 1;
      } else i++;
    }
    return hits;
  }
}

// ---------------------------------------------------------------- hashing embedder
export function fnv1a(s) {
  let h = 0x811c9dc5;
  for (const byte of new TextEncoder().encode(s)) { h ^= byte; h = Math.imul(h, 0x01000193) >>> 0; }
  return h >>> 0;
}

function features(text) {
  const out = [];
  for (const t of tokenize(fold(text))) {
    const w = t.text;
    if (STOPWORDS.has(w) || w.length < 2) continue;
    out.push([fnv1a("w:" + w), 1.0]);
    const padded = "<" + w + ">";
    for (let i = 0; i < padded.length - 3; i++) out.push([fnv1a("c:" + padded.slice(i, i + 4)), 0.25]);
  }
  return out;
}

export class HashingEmbedder {
  constructor(minSimilarity) { this.name = "hashing-v1"; this.minSimilarity = minSimilarity; this.idf = new Map(); this.defaultIdf = 1; }

  fit(texts) {
    const df = new Map();
    for (const t of texts) for (const k of new Set(features(t).map(([key]) => key))) df.set(k, (df.get(k) || 0) + 1);
    const n = texts.length;
    for (const [k, c] of df) this.idf.set(k, Math.log((n + 1) / (c + 1)) + 1);
    this.defaultIdf = Math.log(n + 1) + 1;
  }

  encode(texts) {
    return texts.map((text) => {
      const v = new Map();
      for (const [k, w] of features(text)) v.set(k, (v.get(k) || 0) + w);
      for (const [k, x] of v) v.set(k, (x >= 1 ? 1 + Math.log(x) : x) * (this.idf.has(k) ? this.idf.get(k) : this.defaultIdf));
      let sq = 0;
      for (const x of v.values()) sq += x * x;
      const norm = Math.sqrt(sq);
      if (!norm) return new Map();
      for (const [k, x] of v) v.set(k, x / norm);
      return v;
    });
  }

  similarity(a, b) {
    if (a.size > b.size) [a, b] = [b, a];
    let s = 0;
    for (const [k, x] of a) if (b.has(k)) s += x * b.get(k);
    return s;
  }
}

// ---------------------------------------------------------------- personal data (skilldraft/pii.py)
export const MASK = "•";
const PII_PATTERNS = [
  ["email", /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g],
  ["national_id", /\b\d{2}\.\d{2}\.\d{2}-\d{3}\.\d{2}\b/g],
  ["birthdate", /\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}\b/g],
  ["phone", /(?:\+32\s?|0)4\d{2}(?:[\s./]?\d{2}){3}\b|(?:\+32\s?|0)\d{1,2}(?:[\s./]?\d{2,3}){3}\b/g],
  ["address", /\b[A-Z][a-zà-ÿ]+(?:straat|laan|weg|plein|steenweg|dreef|lei|kaai|street|road|avenue)\s\d{1,4}[a-z]?,?\s\d{4}\s[A-Z][a-zà-ÿ-]+/g],
];
const NAME_WORD = /^(?:[A-Z][a-zà-ÿ']+(?:-[A-Z][a-zà-ÿ']+)*|[Vv]an|[Dd]e|[Dd]er|[Ee]l|[Ll]e|[Bb]en)$/;

function firstLineName(text) {
  let pos = 0;
  for (const line of text.split("\n")) {
    if (line.trim()) {
      const words = line.trim().split(/\s+/);
      if (words.length >= 2 && words.length <= 4 && words.every((w) => NAME_WORD.test(w)) && /[A-Z]/.test(words[0][0])) {
        const start = pos + line.length - line.replace(/^\s+/, "").length;
        return [start, start + line.trim().length];
      }
      return null;
    }
    pos += line.length + 1;
  }
  return null;
}

export function maskPii(text) {
  let spans = [];
  const name = firstLineName(text);
  if (name) {
    const value = text.slice(name[0], name[1]);
    let i = text.indexOf(value);
    while (i >= 0) { spans.push({ kind: "name", start: i, end: i + value.length, rank: -1 }); i = text.indexOf(value, i + 1); }
  }
  PII_PATTERNS.forEach(([kind, re], rank) => { for (const m of text.matchAll(re)) spans.push({ kind, start: m.index, end: m.index + m[0].length, rank }); });
  spans.sort((a, b) => a.start - b.start || a.rank - b.rank || b.end - a.end);
  const merged = [];
  for (const s of spans) {
    if (merged.length && s.start < merged[merged.length - 1].end) { merged[merged.length - 1].end = Math.max(merged[merged.length - 1].end, s.end); continue; }
    merged.push({ ...s });
  }
  const chars = [...text];
  const counts = {};
  for (const s of merged) {
    for (let i = s.start; i < s.end; i++) if (!/\s/.test(chars[i])) chars[i] = MASK;
    counts[s.kind] = (counts[s.kind] || 0) + 1;
  }
  return [chars.join(""), Object.fromEntries(Object.entries(counts).sort())];
}

// ---------------------------------------------------------------- coded language
const LEXICON = [
  ["age", ["young", "and", "dynamic"], "Describe the team's way of working instead of its age: 'an energetic team that moves fast'."],
  ["age", ["young", "dynamic"], "Describe the way of working instead of age."],
  ["age", ["digital", "native"], "Name the skill: 'comfortable with digital tools'."],
  ["age", ["jong", "en", "dynamisch"], "Beschrijf de manier van werken, niet de leeftijd: 'een energiek team'."],
  ["age", ["jong", "dynamisch"], "Beschrijf de manier van werken, niet de leeftijd."],
  ["age", ["maximaal", "#", "jaar"], "Een leeftijdsgrens is in België verboden, tenzij wettelijk vereist."],
  ["age", ["maximum", "#", "years", "old"], "An age limit is unlawful in Belgium unless the law requires it."],
  ["gender", ["he"], "Address the candidate as 'you'."],
  ["gender", ["she"], "Address the candidate as 'you'."],
  ["gender", ["guy"], "Use a neutral word: 'person', 'colleague'."],
  ["gender", ["salesman"], "Use 'salesperson' or 'sales representative'."],
  ["gender", ["hij"], "Spreek de kandidaat aan met 'je'."],
  ["gender", ["vakman"], "Gebruik 'vakkracht' of 'vakspecialist'."],
  ["origin", ["native", "speaker"], "Ask for the level you need: 'fluent (C1) Dutch'."],
  ["origin", ["native", "speakers"], "Ask for the level you need: 'fluent (C1)'."],
  ["origin", ["moedertaal"], "Vraag het niveau dat je nodig hebt: 'vlot Nederlands (C1)'."],
];

export function checkLanguage(text) {
  const toks = tokenize(fold(text));
  const words = toks.map((t) => t.text);
  const flags = [];
  let i = 0;
  while (i < words.length) {
    let hit = null;
    for (const [category, pattern, suggestion] of LEXICON) {
      const n = pattern.length;
      const win = words.slice(i, i + n);
      if (win.length === n && pattern.every((p, j) => p === win[j] || (p === "#" && /^\d+$/.test(win[j])))) {
        if (!hit || n > hit[1].length) hit = [category, pattern, suggestion];
      }
    }
    if (hit) {
      const n = hit[1].length, start = toks[i].start, end = toks[i + n - 1].end;
      flags.push({ category: hit[0], start, end, quote: text.slice(start, end), suggestion: hit[2] });
      i += n;
    } else i++;
  }
  return flags;
}

// ---------------------------------------------------------------- pipeline (configuration D)
const r6 = (x) => Math.round(x * 1e6) / 1e6;
const sigmoid = (z) => (z >= 0 ? 1 / (1 + Math.exp(-z)) : Math.exp(z) / (1 + Math.exp(z)));

function effectiveSection(s) {
  if (s.preferredCue && ["unknown", "req", "resp"].includes(s.section)) return "pref";
  if (s.section === "unknown") {
    if (s.offerCue) return "offer";
    if (s.voice === "we") return "about";
  }
  return s.section;
}

function featureVector(c, hasHeadings, names) {
  const live = c.evidence.filter((e) => !e.negated);
  const good = (e) => GOOD_SECTIONS.includes(e.section);
  const exact = live.filter((e) => e.kind === "exact");
  const sem = live.filter((e) => e.kind === "semantic");
  const exactGood = exact.some(good);
  let bestSem = null;
  for (const e of sem.filter(good)) if (!bestSem || e.similarity > bestSem.similarity) bestSem = e;
  const ranked = [...live].sort((a, b) => (a.kind !== "exact") - (b.kind !== "exact") || (!good(a)) - (!good(b)) || b.similarity - a.similarity);
  const best = ranked[0];
  const f = {
    exact_good: exactGood ? 1 : 0,
    exact_bad: exact.length && !exactGood ? 1 : 0,
    negated: !live.length && c.evidence.some((e) => e.negated) ? 1 : 0,
    sem_good: bestSem ? bestSem.similarity : 0,
    sem_margin: bestSem ? bestSem.margin : 0,
    ambiguous_only: exact.length && exact.every((e) => e.ambiguous) ? 1 : 0,
    mentions: Math.log1p(live.length),
    in_pref: best && best.section === "pref" ? 1 : 0,
    in_title: exact.some((e) => e.section === "title") ? 1 : 0,
    company_voice: live.length && live.every((e) => e.voice === "we") ? 1 : 0,
    no_headings: hasHeadings ? 0 : 1,
  };
  return names.map((n) => r6(f[n]));
}

function importance(c) {
  const live = c.evidence.filter((e) => !e.negated && GOOD_SECTIONS.includes(e.section));
  return live.length && live.every((e) => e.section === "pref") ? "preferred" : "required";
}

export class Pipeline {
  constructor(taxonomyData, model, kind = "jd") {
    this.kind = kind;
    this.taxonomy = new Taxonomy(taxonomyData);
    this.model = model;
    this.embedder = new HashingEmbedder(model.min_similarity);
    this.skillIds = this.taxonomy.skills.map((s) => s.id);
    const texts = this.skillIds.map((id) => this.taxonomy.profileText(id));
    this.embedder.fit(texts);
    this.skillVectors = this.embedder.encode(texts);
  }

  analyse(text) {
    const [sentences, hasHeadings] = segment(text, this.kind);
    const flagged = this.kind === "jd" ? checkLanguage(text).map((f) => [f.start, f.end]) : [];
    const body = sentences.filter((s) => !s.heading && !flagged.some(([a, b]) => a < s.end && s.start < b));
    const vectors = this.embedder.encode(body.map((s) => s.text));
    const cands = new Map();
    const get = (id) => { if (!cands.has(id)) cands.set(id, { skillId: id, evidence: [] }); return cands.get(id); };
    body.forEach((s, i) => {
      const section = effectiveSection(s);
      for (const h of this.taxonomy.match(s.tokens)) {
        get(h.skillId).evidence.push({ kind: "exact", start: h.start, end: h.end, sentence: s.index, section,
          negated: negatedAt(s.tokens, h.first, h.last) || !!s.aspiration, ambiguous: h.ambiguous, similarity: 0, margin: 0, voice: s.voice });
      }
      if (s.section === "title" || s.contact || !GOOD_SECTIONS.includes(section)) return;
      const sims = this.skillIds.map((id, k) => [this.embedder.similarity(vectors[i], this.skillVectors[k]), id])
        .sort((a, b) => b[0] - a[0] || (a[1] < b[1] ? 1 : a[1] > b[1] ? -1 : 0));
      for (let rank = 0; rank < 2; rank++) {
        const [sim, id] = sims[rank];
        if (sim < this.embedder.minSimilarity) break;
        const other = rank === 0 ? sims[1][0] : sims[0][0];
        get(id).evidence.push({ kind: "semantic", start: s.start, end: s.end, sentence: s.index, section,
          negated: s.requirementNegated || !!s.aspiration, ambiguous: false, similarity: r6(sim), margin: r6(sim - other), voice: s.voice });
      }
    });
    for (const c of cands.values()) c.features = featureVector(c, hasHeadings, this.model.features);
    const excluded = new Set(sentences.filter((s) => !s.heading && !body.includes(s)).map((s) => s.index));
    return { text, sentences, hasHeadings, candidates: cands, excluded };
  }

  infer(rawText) {
    const t0 = performance.now();
    let text = rawText, redactions = null;
    if (this.kind === "cv") [text, redactions] = maskPii(rawText);
    const a = this.analyse(text);
    const m = this.model;
    const skills = [];
    for (const c of a.candidates.values()) {
      let z = 0;
      c.features.forEach((x, k) => { z += m.weights[k] * x; });
      const p = sigmoid(m.bias + z);
      const status = p >= m.accept_at ? "suggested" : p >= m.review_at ? "needs_review" : null;
      if (!status) continue;
      const good = (e) => GOOD_SECTIONS.includes(e.section);
      const live = c.evidence.filter((e) => !e.negated)
        .sort((x, y) => (x.kind !== "exact") - (y.kind !== "exact") || (!good(x)) - (!good(y)) || y.similarity - x.similarity || x.start - y.start);
      const s = this.taxonomy.byId[c.skillId];
      skills.push({ id: c.skillId, label: s.label, status, importance: this.kind === "cv" ? "held" : importance(c), confidence: Math.round(p * 1000) / 1000,
        evidence: live.slice(0, 3).map((e) => ({ start: e.start, end: e.end, quote: text.slice(e.start, e.end), kind: e.kind, section: e.section, sentence: e.sentence })) });
    }
    skills.sort((x, y) => (x.status !== "suggested") - (y.status !== "suggested") || (x.importance !== "required") - (y.importance !== "required")
      || y.confidence - x.confidence || (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
    const covered = new Set(skills.flatMap((s) => s.evidence.map((e) => e.sentence)));
    const meta = { config: "D", taxonomy_version: this.taxonomy.version, embedder: this.embedder.name, model_version: m.version, kind: this.kind,
      language: detectLanguage(text), latency_ms: Math.round((performance.now() - t0) * 100) / 100 };
    if (this.kind === "cv") {
      const unmapped = a.sentences.filter((s) => !s.heading && s.section === "experience" && !covered.has(s.index) && !s.requirementNegated && !s.aspiration && !JOB_LINE.test(s.text))
        .map((s) => ({ start: s.start, end: s.end, text: s.text }));
      return { skills, unmapped_sentences: unmapped, redactions, meta, masked_text: text };
    }
    const uncovered = a.sentences.filter((s) => !s.heading && ["req", "resp"].includes(s.section) && !covered.has(s.index) && !s.requirementNegated && !a.excluded.has(s.index))
      .map((s) => ({ start: s.start, end: s.end, text: s.text }));
    return { skills, uncovered_requirements: uncovered, language_flags: checkLanguage(text),
      meta: { config: "D", taxonomy_version: this.taxonomy.version, embedder: this.embedder.name, model_version: m.version,
        language: detectLanguage(text), latency_ms: Math.round((performance.now() - t0) * 100) / 100 } };
  }
}
