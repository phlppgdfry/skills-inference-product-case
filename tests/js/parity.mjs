// The browser port must give the same profiles as Python on every test description.
//   node tests/js/parity.mjs
// Fixture: tests/js/parity.json, written by scripts/build.py from the Python pipeline.
import { readFileSync } from "node:fs";
import { Pipeline } from "../../site/assets/skilldraft.mjs";

const root = new URL("../../", import.meta.url);
const read = (p) => readFileSync(new URL(p, root), "utf8");
const pipe = new Pipeline(JSON.parse(read("site/data/taxonomy.json")), JSON.parse(read("site/data/model.json")));
const jds = Object.fromEntries(read("data/job_descriptions.jsonl").trim().split("\n").map((l) => JSON.parse(l)).map((j) => [j.id, j]));
const expected = JSON.parse(read("tests/js/parity.json"));

let failures = 0;
for (const exp of expected) {
  const out = pipe.infer(jds[exp.id].text);
  const got = out.skills.map((s) => [s.id, s.status, s.importance, s.confidence, s.evidence[0].start]);
  const same = got.length === exp.skills.length && got.every((g, i) => {
    const e = exp.skills[i];
    return g[0] === e[0] && g[1] === e[1] && g[2] === e[2] && Math.abs(g[3] - e[3]) <= 0.002 && g[4] === e[4];
  }) && out.uncovered_requirements.length === exp.uncovered && out.language_flags.length === exp.flags;
  if (!same) {
    failures++;
    if (failures <= 3) console.log(`✗ ${exp.id}\n  python ${JSON.stringify(exp.skills)}\n  js     ${JSON.stringify(got)}`);
  }
}
console.log(failures ? `parity: ${failures}/${expected.length} differ` : `parity: ${expected.length}/${expected.length} identical`);
process.exit(failures ? 1 : 0);
