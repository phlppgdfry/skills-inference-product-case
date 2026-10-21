# ADR-0003: Calibrated score, accept threshold, review band

**Status:** Accepted

## Context
Interview pattern 1: one absurd suggestion costs more trust than five misses. Pattern 2: reviewers want to know where to look.

## Options
1. **Rules only** (config B). Precise, misses every described skill.
2. **Fixed similarity threshold** (config C). Finds described skills, lets noise through.
3. **Learned, calibrated score** over readable features, with two thresholds picked on dev.

## Decision
Option 3. A logistic regression over 11 features (`skilldraft/scorer.py`); weights are printed in the [model card](../04-quality/model-card.md).
- **accept_at**: the lowest score whose accepted set reaches 95% precision on dev (now <!--n:accept_at-->0.425<!--/n-->).
- **review_at**: the lowest score at which the band [review_at, accept_at) still has at least 1 real skill in 4 on dev (now <!--n:review_at-->0.344<!--/n-->).

The second rule replaced a first version that aimed for 95% recall *with* review. That version put 2.1 items per description in the band, of which only 5.7% were real skills: a review queue people learn to ignore.

## Consequences
- Test: precision <!--n:D.precision-->0.963<!--/n-->, recall <!--n:D.recall-->0.953<!--/n-->, <!--n:D.review_per_jd-->0.3<!--/n--> review items per description, recall with review <!--n:D.recall_with_review-->0.959<!--/n-->. ECE <!--n:ece-->0.061<!--/n-->.
- Thresholds are part of the model file and its version.
- Logistic regression is enough because the features carry the knowledge; a bigger model would need more labels than we have.

## How we would know it was wrong
Pilot accept rate of suggested skills < 90%, or reviewers reject most "please check" items.

## When to revisit
When feedback produces a few thousand labelled candidates: try gradient-boosted trees or a small neural head (the PyTorch trainer is ready), and keep whichever is better calibrated, not whichever has the highest F1.
