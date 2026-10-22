# ADR-0010: Person profiles: mask first, ask consent, never rank

**Status:** Accepted (behind the `person_profiles` flag; off by default outside dev)

## Context
Role profiles answer "what does the job need". Internal mobility also needs "what can this person do", and the richest source is a CV. That is personal data, and inferring skills of people is profiling under the AI Act (always high-risk for Annex III, point 4, see [ai-act.md](../04-quality/ai-act.md)). The interviews were clear that "who gets shown for a job" stays with people.

## Options
1. **Same pipeline on raw CV text.** Fast to build; names, addresses and birth dates flow through every step and can end up in quotes, logs and feedback.
2. **Mask personal data first, then the same pipeline with CV sections and its own scorer.** Personal data never reaches matching, scoring or the response.
3. **Ask people to tick skills from the taxonomy themselves.** No inference risk, but slow and incomplete; still useful as the review step.

## Decision
Option 2, with option 3 as the review:
- `skilldraft/pii.py` masks name (first line and every repeat), address, phone, e-mail, birth date and national register number **with the same length** ("•"), so evidence offsets stay valid and no quote can contain personal data. The response reports counts per kind, never values.
- CVs get their own sections (experience, skills, languages, education; interests do not count), aspiration sentences ("I would like to learn X", "Ik wil graag X leren") are never evidence, and a separate scorer is trained on CVs.
- `POST /v1/person-profiles` requires `consent: true`, is behind a feature flag, stores nothing, and returns a draft (`importance: held`) for the person to check.
- `POST /v1/development-plans` turns a reviewed role profile and a person's skills into coverage and ordered gaps. It never compares people with each other.

## Consequences
- Test CVs: personal-data spans masked <!--n:cv.pii_masked-->100%<!--/n--> of <!--n:cv.pii_spans-->262<!--/n-->, values found in any response <!--n:cv.pii_leaks-->0<!--/n-->; profile unchanged with another name or a birth year 30 years apart <!--n:cv.invariance-->100%<!--/n-->. Gated in CI.
- Masking makes name and age invariance hold **by construction**: the pipeline cannot see them.
- The patterns were written for these CVs. A real deployment needs a labelled sample of real CVs per language and a masking recall target before the flag goes on.
- A year on its own ("1988") is not masked; it is too often a diploma or project year. A known gap, tested as such.

## How we would know it was wrong
A real-CV sample shows personal data surviving the mask, or employees say the draft profile misrepresents them more often than it helps (measured by their own corrections).

## When to revisit
Before switching the flag on for any customer: complete the provider duties in ai-act.md, and replace the regex patterns with a tested NER model if real CVs need it.
