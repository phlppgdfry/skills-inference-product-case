# Opportunity solution tree

Outcome first, then the opportunities the interviews surfaced, then candidate solutions, then the experiment that tests each one. Crossed-out branches were considered and parked, with the reason.

```mermaid
flowchart TD
    O["Outcome: Haldane can start internal mobility in Q1<br/>(1,400 role profiles reviewed and trusted)"]
    O --> P1["Writing a profile takes too long"]
    O --> P2["Profiles are inconsistent across authors"]
    O --> P3["Reviewers can't see where a skill came from"]
    O --> P4["Job descriptions carry noise and coded language"]
    P1 --> S1["Draft profile from the job description"]
    P2 --> S2["One bilingual taxonomy; output only taxonomy ids"]
    P3 --> S3["Evidence span + calibrated confidence per skill"]
    P4 --> S4["Section-aware extraction + coded-language checker"]
    P1 --> S5["~~Free-text LLM skill generator~~<br/>parked: produces words, not skills"]
    P2 --> S6["~~Customer-specific taxonomies~~<br/>parked: kills cross-customer comparison"]
    S1 --> E1["Spike: label match vs alias match vs semantic, on 100 test descriptions"]
    S3 --> E2["Calibration eval: does 0.9 mean 90%?"]
    S4 --> E3["Distractor and counterfactual evals"]
    S1 --> E4["Pilot: time per reviewed profile, before vs after (planned)"]
```

| Opportunity | Evidence it is real | Size (illustrative) | Chosen solution | Test |
|---|---|---|---|---|
| Writing takes too long | I3: ~45 min per role; 1,400 roles | ~1,050 consultant hours | Draft profile | Pilot H3 ([hypotheses](hypotheses.md)) |
| Inconsistent vocabulary | I3, I6 | every profile | Taxonomy-grounded output | Spike: A vs B |
| No "why" | I1, I3, I6 | every review | Evidence + confidence | Evidence accuracy, ECE |
| Noise in job descriptions | I2, I4 | ~1 in 2 descriptions has a distractor | Sections, negation, company voice | Distractor rate |
| Coded language | I2 | ~1 in 5 descriptions (generated set) | Lexicon checker | Checker recall, false alarms |
