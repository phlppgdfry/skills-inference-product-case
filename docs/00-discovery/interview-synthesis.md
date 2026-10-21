# Interview synthesis

*The interviews are synthetic: written to show how the method works, not transcripts of real people. Names are roles, not persons.*

Six 30-minute interviews, two weeks before the spike. Same guide each time: walk me through the last profile you made; what did you do when you were unsure; what happened next; what would you never let a tool do.

| # | Who | One-line takeaway |
|---|---|---|
| I1 | HR business partner, Haldane (production sites) | "I don't want a list of fifty skills. I want the eight that matter and to see why." |
| I2 | HR business partner, Haldane (head office) | "Our job descriptions are half marketing. The 'about us' part is not the job." |
| I3 | External consultant who writes the profiles today | "I spend most of the time on vocabulary: is 'heftruck' the same as 'reach truck'? Then I second-guess myself." |
| I4 | Plant manager, Haldane Ghent | "If it says my maintenance techs need Python, I stop trusting it." |
| I5 | Orveda customer success manager | "Customers churn on the *first* bad profile they see, not on the average one." |
| I6 | Orveda data scientist | "We can extract skills; we can't yet say how sure we are, so everything looks equally confident." |

## Patterns (affinity map, condensed)

**1. Trust breaks on one obvious mistake (I1, I4, I5).** A single absurd suggestion (Python for a maintenance technician, SAP because the company runs SAP) costs more trust than five missed skills. → *Precision of what we show matters more than recall of what we find.* This became the accept threshold rule: 95% precision on dev ([ADR-0003](../03-decisions/ADR-0003-calibrated-score-and-review-band.md)).

**2. "Why" is the feature (I1, I3, I6).** Every interviewee wanted to see the sentence behind a skill. Reviewing a suggestion with evidence is a glance; without, it is re-reading the job description. → *Evidence is mandatory* ([ADR-0004](../03-decisions/ADR-0004-evidence-or-nothing.md)).

**3. Vocabulary, not judgment, is the slow part (I3).** Mapping "heftruck", "reachtruck" and "forklift licence" to one skill is what the consultant spends time on. → *A shared taxonomy with bilingual aliases is the core asset* ([ADR-0001](../03-decisions/ADR-0001-taxonomy-grounded-output.md)).

**4. The job description is not all job (I2).** About-us, the offer, "no experience with X needed", and contact lines all mention skills that are not required. → *Distractor rate is an explicit eval* ([eval plan](../04-quality/eval-plan.md)).

**5. Importance matters, but coarsely (I1).** Nobody wanted a 1–5 scale; "required" vs "nice to have" was enough. → *Two levels of importance, read from sections and cues.*

**6. Some things people will never delegate (I1, I2, I4).** Who gets shown for a job. → *The match ranks; a person decides* ([ADR-0008](../03-decisions/ADR-0008-people-decide.md)).

## What surprised us

- Nobody asked for "AI". They asked for consistency and speed. The LLM ended up as a narrow verifier, not the engine ([ADR-0002](../03-decisions/ADR-0002-llm-verifies-never-invents.md)).
- HR raised coded language themselves (I2): "half our ads still say 'young and dynamic'". That turned into a small feature with an outsized reception in the demo ([one-pager](../07-stakeholders/one-pager-for-hr.md)).
