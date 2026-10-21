# ADR-0008: People decide

**Status:** Accepted

## Context
Role profiles feed internal mobility. Ranking employees for jobs is high-risk under the AI Act (Annex III, point 4) and touches GDPR article 22. Interviewees would never delegate "who gets shown for a job".

## Decision
- A profile is a **draft** until a person accepts it; the API says `suggested` and `needs_review`, never `final`.
- Only accepted (`suggested`) skills influence a match; review items do not.
- The match endpoint returns a ranked list with gaps and an explicit note that it supports a decision. There is no "shortlist" or "reject" output.
- Feedback is logged per skill with the model version, so oversight is auditable.

## Consequences
- The product promise is "faster and more consistent review", not "no review".
- Phase 2 (matching) needs the provider and deployer duties in [ai-act.md](../04-quality/ai-act.md) before it goes live.

## How we would know it was wrong
Customers wire the ranking straight into a decision without a person. Contract terms and the API shape (no decision field) are the defence; usage monitoring is the check.

## When to revisit
Not for matching. For role profiles, an "auto-accept above 0.99" option could be discussed once pilot accept rates are known.
