# User stories and acceptance criteria

Personas from the [interviews](interview-synthesis.md): **Hanne**, HR business partner (reviews profiles); **Koen**, plant manager (consumes profiles, approves the role); **Ines**, Orveda integration engineer (calls the API from the customer's HRIS).

Acceptance criteria are written so a test or an eval can check them. Where one does, the last column says which.

## Epic 1: Draft a skill profile

**US-1.1** As Hanne, I want a draft skill profile from a pasted job description, so that I edit instead of write.

```gherkin
Given a job description in Dutch or English of at most 20,000 characters
When I ask for a skill profile
Then I get a list of skills, each with a taxonomy id, a label, "required" or "nice to have", and a confidence
And every skill points at the sentence it came from
And the answer arrives in under 1 second for 95% of requests
```
Checked by: `tests/test_pipeline.py::test_every_suggestion_points_at_the_text`, `tests/test_api.py`, latency gate in `evals/thresholds.json`.

**US-1.2** As Hanne, I want skills the system is unsure about shown separately, so that I spend my attention where it is needed.

```gherkin
Given a draft profile
Then skills with confidence ≥ the accept threshold are shown as "suggested"
And skills between the review and accept thresholds are shown as "please check"
And at least 1 in 4 "please check" items on the dev set is a real skill
```
Checked by: `skilldraft/scorer.py::pick_thresholds`, `evals/run.py` (review band precision).

**US-1.3** As Koen, I do not want skills that the company merely mentions, so that I can trust the profile.

```gherkin
Given a job description that mentions a skill only in "about us", "what we offer", or as "not required"
Then that skill is not suggested in more than 10% of such cases, for each kind
```
Checked by: distractor rate in the release gate.

**US-1.4** As Hanne, I want sentences the system could not map to any skill listed, so that I can add what it missed or ask for a new taxonomy skill.

Checked by: `uncovered_requirements` in the API; `missed_but_flagged_uncovered` in the eval report.

## Epic 2: Review and feedback

**US-2.1** As Hanne, I want to accept, reject or add a skill with one action, so that the profile is final and the system learns.

```gherkin
Given a profile returned with request id R
When I accept or reject a skill that R returned, or add any taxonomy skill
Then the verdict is stored with R, the skill id and the model version, and without the job description text
And a verdict on a skill R did not return is refused (409)
```
Checked by: `tests/test_api.py::test_profile_and_feedback_loop`.

## Epic 3: Fair and clear language

**US-3.1** As Hanne, I want coded wording flagged with a neutral alternative, so that our ads do not exclude people.

```gherkin
Given a job description with a phrase from the coded-language lexicon (age, gender, origin)
Then the phrase is flagged with its category and a suggestion
And neutral text produces no flags
```

**US-3.2** As Haldane's DPO, I want proof that personal wording does not change the skills, so that the profile does not depend on who wrote the ad or who the contact person is.

```gherkin
Given a job description and a copy that only changes a pronoun, a contact name or adds age-coded wording
Then the two profiles are identical: same skills, statuses, importance and confidence
```
Checked by: counterfactual invariance (release gate: 100%).

## Epic 4: Internal mobility (behind a flag, phase 2)

**US-4.1** As Hanne, I want a ranked list of employees whose skills fit a reviewed role profile, with the gaps per person, so that I can start conversations about internal moves.

```gherkin
Given a role profile and a list of employees with skill ids
Then employees are ranked by weighted coverage of the role's suggested skills
And each row shows matched skills, gaps, and gaps that are close to a skill the person has
And skills still waiting for review do not influence the ranking
And the response states that the ranking supports a decision and is not one
```
Checked by: `tests/test_inclusive_match.py`, `tests/test_api.py::test_matches`.

## Not in scope (and said so in the backlog)

Inferring skills of *employees* from CVs or HR records; automated shortlisting; French job descriptions (taxonomy aliases first); importance on a 1–5 scale.
