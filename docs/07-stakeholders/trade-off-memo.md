# Trade-off memo: how many "please check" items should a reviewer see?

**To:** Product manager, HR pilot lead. **From:** AI product engineer. **Decision needed:** confirm the review-band rule before the pilot.

## The trade-off in one sentence

Every skill the system is unsure about can be **shown and asked** (costs the reviewer a few seconds each, catches more real skills) or **left out** (no cost, but the reviewer has to notice what is missing).

## What the data says

The first version asked about everything that might be a skill. It reached 95% coverage, but it showed 2.1 questions per profile, and only about 1 in 18 was a real skill. Reviewers would learn to click them all away within a day, which is worse than not asking.

The current rule asks only when at least 1 in 4 questions is a real skill (on the dev set). Result on the test set:

| | Questions per profile | Real skills among them | Coverage (suggested + questions) |
|---|---|---|---|
| First version | 2.1 | 5.7% | 0.967 |
| **Current rule** | <!--n:D.review_per_jd-->0.3<!--/n--> | <!--n:D.review_precision-->16.7%<!--/n--> | <!--n:D.recall_with_review-->0.959<!--/n--> |

We give up less than one point of coverage and remove most of the noise. On the test set the band is <!--n:D.review_precision-->16.7%<!--/n--> real, below the 1 in 4 it reached on dev: with only <!--n:D.review_per_jd-->0.3<!--/n--> items per profile the band is small, so its precision moves a lot between samples. The pilot measures it on real ads before we tune further. The skills we still miss are partly visible anyway: for <!--n:D.missed_flagged-->45.7%<!--/n--> of them, the sentence shows up under "not linked to a skill".

## A second dial: how far to stretch for described skills

How similar a sentence must be before it counts as describing a skill (dev set):

| Floor | F1 | Coverage with questions | Questions per profile | Described skills found |
|---|---|---|---|---|
| 0.05 | <!--n:sweep.0.05.f1-->0.938<!--/n--> | <!--n:sweep.0.05.rwr-->0.938<!--/n--> | <!--n:sweep.0.05.review-->0.5<!--/n--> | <!--n:sweep.0.05.para-->69.7%<!--/n--> |
| **0.08 (chosen)** | <!--n:sweep.0.08.f1-->0.940<!--/n--> | <!--n:sweep.0.08.rwr-->0.938<!--/n--> | <!--n:sweep.0.08.review-->0.3<!--/n--> | <!--n:sweep.0.08.para-->71.6%<!--/n--> |
| 0.12 | <!--n:sweep.0.12.f1-->0.932<!--/n--> | <!--n:sweep.0.12.rwr-->0.913<!--/n--> | <!--n:sweep.0.12.review-->0.0<!--/n--> | <!--n:sweep.0.12.para-->65.1%<!--/n--> |

Every row keeps the profile unchanged under the fairness tests; that is a hard condition, not part of the trade-off.

## Recommendation

Keep the current rule and the chosen floor for the pilot. Measure two things in week one: how long a "please check" item takes to answer, and how often reviewers add a skill we did not show. If questions are answered in under 5 seconds and additions stay above one per profile, lower the bar to 1 in 5. If reviewers skip the questions, raise it.

## What I need from you

A yes, or a different target for "questions per profile" from the HR side. One line in the thread is enough.
