# Risk register

Likelihood and impact 1–3. Score = L × I. Reviewed weekly; the top five go into the weekly update.

| # | Risk | L | I | Score | Mitigation | Early signal | Owner |
|---|---|---|---|---|---|---|---|
| R1 | Described skills are much harder to find on real ads than on generated ones (H2) | 3 | 3 | 9 | Shadow run on 40 labelled real ads before the pilot; encoder behind an interface; uncovered sentences shown to reviewers | Real-data paraphrase recall < 50% | AI product engineer |
| R2 | One absurd suggestion breaks reviewer trust (H4) | 2 | 3 | 6 | Accept threshold at 95% dev precision; ambiguity and company-voice features; distractor gate | Pilot reject rate of suggested > 10% | AI product engineer |
| R3 | Review screen is the bottleneck, not the model (H3) | 2 | 3 | 6 | Usability test in M5; keyboard-first flow | Review time > 20 min with good precision | Frontend + PM |
| R4 | Phase 2 matching is high-risk under the AI Act; obligations underestimated | 2 | 3 | 6 | Separate release; obligations list in ai-act.md; legal review before build | Sales promises matching for Q1 | PM |
| R5 | Taxonomy gaps for Haldane-specific skills | 3 | 2 | 6 | Uncovered-requirements report per batch; monthly taxonomy release | Uncovered sentences per profile > 2 | Taxonomy owner |
| R6 | Verifier cost or latency on Bedrock | 1 | 2 | 2 | Only the review band goes to the LLM; effort low; can be switched off | Cost per profile > budget | AI product engineer |
| R7 | Dutch quality drops with a new encoder | 2 | 2 | 4 | Language parity gate | EN/NL gap > 0.05 in CI | AI product engineer |
| R8 | Job description text leaks into logs or feedback | 1 | 3 | 3 | Never logged by design; test asserts feedback rows have no text | Log review finds text | Backend |
| R9 | Generated-data evals give false confidence | 3 | 2 | 6 | Labelled as such everywhere; real-data report is a go/no-go gate (M7) | Real-data numbers far below offline | AI product engineer |
