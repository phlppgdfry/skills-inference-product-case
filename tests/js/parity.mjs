// The browser port must give the same profiles as Python on every test description and CV.
//   node tests/js/parity.mjs
// Fixtures: tests/js/parity.json and parity.cv.json, written by scripts/build.py from the Python pipeline.
import { readFileSync } from "node:fs";
import { Pipeline } from "../../site/assets/skilldraft.mjs";

const root = new URL("../../", import.meta.url);
const read = (p) => readFileSync(new URL(p, root), "utf8");
const taxonomy = JSON.parse(read("site/data/taxonomy.json"));
const rows = (p) => Object.fromEntries(read(p).trim().split("\n").map((l) => JSON.parse(l)).map((j) => [j.id, j]));

function check(label, pipe, docs, expected, extra) {
  let failures = 0;
  for (const exp of expected) {
    const out = pipe.infer(docs[exp.id].text);
    const got = out.skills.map((s) => [s.id, s.status, s.importance, s.confidence, s.evidence[0].start]);
    const same = got.length === exp.skills.length && got.every((g, i) => {
      const e = exp.skills[i];
      return g[0] === e[0] && g[1] === e[1] && g[2] === e[2] && Math.abs(g[3] - e[3]) <= 0.002 && g[4] === e[4];
    }) && extra(out, exp);
    if (!same) {
      failures++;
      if (failures <= 3) console.log(`✗ ${exp.id}\n  python ${JSON.stringify(exp.skills)}\n  js     ${JSON.stringify(got)}`);
    }
  }
  console.log(failures ? `${label}: ${failures}/${expected.length} differ` : `${label}: ${expected.length}/${expected.length} identical`);
  return failures;
}

const jd = check("job descriptions", new Pipeline(taxonomy, JSON.parse(read("site/data/model.json"))), rows("data/job_descriptions.jsonl"),
  JSON.parse(read("tests/js/parity.json")), (o, e) => o.uncovered_requirements.length === e.uncovered && o.language_flags.length === e.flags);
const cv = check("CVs", new Pipeline(taxonomy, JSON.parse(read("site/data/model.cv.json")), "cv"), rows("data/cvs.jsonl"),
  JSON.parse(read("tests/js/parity.cv.json")), (o, e) => o.unmapped_sentences.length === e.unmapped && JSON.stringify(o.redactions) === JSON.stringify(e.redactions));
process.exit(jd + cv ? 1 : 0);
