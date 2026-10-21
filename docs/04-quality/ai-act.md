# EU AI Act classification

*Working analysis for Orveda's product and legal team, checked on 21 October 2026 against the AI Act as amended by the Digital Omnibus on AI. Not legal advice; legal must confirm dates and scope against the Official Journal text.*

## Roles

- **Orveda is the provider** of SkillDraft (it develops the system and places it on the market under its name).
- **Haldane is a deployer** (it uses the system under its authority for its own HR processes).
- Anthropic, through Amazon Bedrock or the Claude API, is the provider of the **general-purpose AI model** used by the optional verifier.

## Two functions, two risk levels

| Function | Annex III, point 4 | Assessment |
|---|---|---|
| **Role skill profiles** from job descriptions (v1) | 4(a) covers AI used for recruitment or selection, e.g. targeted job ads, filtering applications, evaluating candidates. | It describes a *role*, not a person, and prepares work that an HR partner then reviews. If it falls under 4(a) at all, it fits the Art. 6(3) exception for a **preparatory task**, with no profiling of natural persons. Orveda documents this assessment (Art. 6(4)) and registers it (Art. 49(2)). Treated as **not high-risk, with documented reasoning**. |
| **Matching employees to roles** (phase 2) | 4(a) and 4(b) cover AI that evaluates candidates or informs decisions on promotion, task allocation and work relationships. | It ranks *people* on their skills: profiling of natural persons. Art. 6(3) says such a system is **always high-risk**. |

## What phase 2 needs before it goes live

**Provider (Orveda):** risk management system (Art. 9); data governance for the people data and skill labels (Art. 10); technical documentation (Art. 11, this repository is the start); automatic logging (Art. 12, the feedback and request logs are the basis); instructions for use for deployers (Art. 13); human-oversight design (Art. 14, [ADR-0008](../03-decisions/ADR-0008-people-decide.md)); accuracy, robustness and cybersecurity (Art. 15, the eval gate and the API limits); quality management system (Art. 17); conformity assessment by internal control (Art. 43); registration in the EU database (Art. 49); post-market monitoring (Art. 72).

**Deployer (Haldane):** use according to the instructions, with oversight by trained people (Art. 26(1)–(2)); keep the logs for at least six months (Art. 26(6)); **inform workers' representatives and the affected workers before using it at the workplace** (Art. 26(7)), which in Belgium also meets the information and consultation duty on new technology under collective agreement no. 39; a DPIA under GDPR where required (Art. 26(9)); explain decisions on request (Art. 86).

**Already true for both:** AI literacy for the people who use it (Art. 4, since 2 February 2025).

## Dates (after the Digital Omnibus)

| Date | What applies |
|---|---|
| 2 Feb 2025 | Prohibited practices; AI literacy |
| 2 Aug 2025 | Obligations for general-purpose AI model providers |
| 2 Aug 2026 | Transparency obligations (Art. 50) and most other provisions |
| 2 Dec 2027 | High-risk obligations for Annex III systems (moved from 2 Aug 2026) |

The Annex III date moved, the work did not: the phase 2 obligations above take months, and enterprise buyers ask for them in procurement today.

## GDPR

- Role profiles hold almost no personal data. The contact name in a job ad passes through memory and is never stored or logged.
- Matching processes employee skill data: lawful basis (legitimate interest of the employer, balanced in a DPIA), purpose limitation (internal mobility, not performance evaluation), transparency towards employees, and the right to object.
- Article 22: no decision based solely on automated processing. The match is a list for a person; the API has no decision field.
