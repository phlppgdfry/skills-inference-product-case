# Problem brief

*Fictional setting. Orveda is an invented HR-tech scale-up in Ghent that sells a skills-intelligence platform; Haldane Group is an invented Belgian industrial group (6,200 employees, 11 sites). Neither is a real company, and this case was not made for or with any real company. Interviews and business numbers are illustrative and labelled as such.*

## The ask, as it arrived

> "Customers keep telling us that building skill profiles for their roles takes forever, and that the profiles they end up with are wrong. Can we use AI to fix that? Haldane wants to start their internal mobility programme in Q1." — Product manager, Orveda, in a Slack thread

That sentence holds at least four different problems, and the first job is to find out which one is worth solving.

| Reading of the ask | What it would mean to build | Open question |
|---|---|---|
| "Takes forever" is about **writing** profiles | Draft a skill profile from the job description so a person edits instead of writes | How long does it take today, and who does it? |
| "Wrong" is about **vocabulary** | Every customer calls the same skill something else; map it to one taxonomy | Is the problem the words, or the judgment? |
| "Wrong" is about **importance** | Profiles list everything as equally important | Do users care about required vs nice-to-have? |
| Internal mobility is the **real goal** | Match employees to roles | Are role profiles the bottleneck for matching, or employee profiles? |

## What discovery found (summary)

Six interviews ([synthesis](interview-synthesis.md)) and a look at 40 of Haldane's real job descriptions (simulated here by the generated set) pointed to one problem worth solving first:

**HR business partners at Haldane need a skill profile for 1,400 roles before internal mobility can start. Today an external consultant writes them at roughly 45 minutes a role (illustrative). The profiles disagree with each other because each author uses their own words, and nobody can tell where a skill came from.**

The opportunity is not "AI writes skill profiles". It is: **a draft profile that a person can check in a few minutes, because every suggested skill is a taxonomy skill, comes with the sentence that justifies it, and says how sure it is.**

## What we will not build first

- An employee-side skills profile (inferring what a *person* can do) **as the first release**. It is the more valuable product and the higher-risk one under the AI Act. It is built second, behind a feature flag, with personal data masked before anything reads the CV ([ADR-0010](../03-decisions/ADR-0010-person-profiles-mask-first.md), [ai-act.md](../04-quality/ai-act.md)).
- A free-text "skills generator". It produces words, not taxonomy skills, and every customer would get a different vocabulary ([spike report](../01-prototype/spike-report.md)).
- Automated matching decisions. The match is a ranked list for a person to look at ([ADR-0008](../03-decisions/ADR-0008-people-decide.md)).

## Constraints that shape the solution

- Job descriptions arrive in **Dutch and English** (and French later). One taxonomy, both languages.
- Haldane's HR team will **review every profile** before it is used. The product must make that review fast, not skip it.
- Job descriptions contain company boilerplate, benefits and sometimes coded language ("young and dynamic team"). Those must not turn into skills.
- Data stays in the EU; LLM calls, if any, go through the customer's approved provider (Amazon Bedrock in eu-central-1 for Haldane).
