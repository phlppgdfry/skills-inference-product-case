# Launch plan

## Stages

| Stage | Who sees what | Duration | Go criteria to the next stage |
|---|---|---|---|
| 0. Offline | Nobody; CI only | done | Gate green (this repository) |
| 1. Shadow | Profiles generated for 40 Haldane ads, compared with two HR partners' labels; nobody acts on them | 1 week | Real-data precision ≥ 0.9, no distractor kind > 10%, invariance 100% |
| 2. Pilot | Feature flag on for 2 HR partners; every profile reviewed | 4 weeks | Median review ≤ 10 min, accept rate ≥ 90%, no trust incident |
| 3. Haldane | All HR partners; verifier on if the band is large | ongoing | Weekly metrics within SLO |
| 4. Matching | Separate decision after the AI Act work | – | [ai-act.md](../04-quality/ai-act.md) obligations met |

## Feature flags

`skill_profiles` (per customer), `verifier` (per customer and platform), `matching` (off; per customer only after stage 4).

## Rollback

Every profile carries `model_version` and `taxonomy_version`. Rolling back means pointing the service at the previous model file; reviewed profiles are not re-generated. The flag turns the feature off within a minute.

## Communication

- HR partners: a 20-minute walkthrough with the [demo script](../07-stakeholders/demo-script.md) and the [one-pager](../07-stakeholders/one-pager-for-hr.md).
- Works council (Haldane): informed before stage 2, with the AI Act and data notes, even though role profiles do not concern individual employees. It is cheaper than explaining later.
