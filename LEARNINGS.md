# TokenEstimator Skill — Test Results & Learnings

**Skill version tested:** v1.0  
**Test run:** 2026-05-25  
**Test cases:** 35 (covering all 4 categories × 3 scope levels × 3 dependency levels)  
**Harness:** `tests/test_harness.py` | **Cases:** `tests/test_cases.json`

---

## Executive Summary

The v1.0 skill has a **48.6% hit rate** (95% CI: 33–64%) against ground-truth token ranges — roughly coin-flip accuracy. It overestimates on 74.3% of cases (p=0.003, statistically significant bias). The mean error is **+75.1%**, meaning the skill's point estimates are, on average, 75% higher than actual token usage.

The `exploratory` category is the only one that performs acceptably (100% hit, +30% mean bias). The `data` category fails completely (0% hit, +134% mean bias). These are not calibration failures — they are routing failures.

---

## Findings

### Finding 1: The Anchor Routing System Has Dead Ends

The skill defines 8 anchor buckets in its estimation table, but its 3-question decision matrix only reaches 4 of them reliably. Two anchors — `simple_qa` (mid: 1,250 tokens) and `document_short` (mid: 4,500 tokens) — are effectively unreachable given the current routing logic.

**Impact:** Every "data + crisp + none" task collapses into `data_processing` (mid: 5,000), regardless of whether the task is a 650-token Q&A or an 8,000-token survey analysis. A simple factual question receives an estimate of 5,000 tokens — a **669% overestimate**.

**Root cause:** The decision matrix asks *what kind* of task it is but never asks *how big* the output is. Output size is the single strongest predictor of token usage across all categories.

---

### Finding 2: The `data` Category is Structurally Broken

Category results:
| Category | Hit Rate | Mean Error | Std Dev |
|----------|----------|------------|---------|
| exploratory | 100% | +30.3% | ±19.7% |
| creation | 50% | +56.5% | ±103.2% |
| execution | 40% | +105.2% | ±90.3% |
| **data** | **0%** | **+133.5%** | **±215.1%** |

The `data` category covers tasks ranging from 650 tokens (Q&A) to 9,000 tokens (survey analysis of 150 open-ended responses). A single anchor mid of 5,000 cannot represent this 14× range. The category needs to be split by output type, not collapsed.

---

### Finding 3: The `execution` Category Anchor is Badly Miscalibrated

The skill routes all `execution` tasks to the `full_project` anchor (mid: 37,000 tokens). But 3 of the 5 execution test cases had actuals of 14,000–25,000 tokens — tasks like "set up a workflow" or "build a data pipeline." Only a full end-to-end app build (TC008: 40,000 actual) actually belongs in the `full_project` bucket.

The 37,000-token anchor, multiplied by dependency buffers, produced estimates of ~50,000 tokens for tasks that consumed 14,000. This is a **256% overestimate** — and since it pushes estimates above the Pro plan limit, it would cause the skill to falsely flag RISKY for tasks that easily fit in one session.

---

### Finding 4: The `exploratory` Category is Well-Calibrated (with a caveat)

Exploratory tasks achieved 100% hit rate with +30.3% mean bias. The anchors for research synthesis (mid: 15,000) and deep exploratory (mid: 25,000) are close to real-world usage. The caveat: the wide confidence bands for fuzzy/exploratory tasks (±20–25%) are doing a lot of work here — they effectively hide a consistent overestimation bias of ~30%. The skill is technically "hitting" but is still pointing users toward conserving session tokens unnecessarily.

---

### Finding 5: Confidence Signals Are Inverted

The scope confidence signals (🟢 crisp, 🟡 semi-defined, 🔴 fuzzy) are intended to communicate prediction quality. The actual results are opposite:

| Scope | Hit Rate | Mean Error |
|-------|----------|------------|
| 🔴 fuzzy | **100%** | +49.0% |
| 🟡 semi-defined | **54.5%** | +60.3% |
| 🟢 crisp | **31.6%** | +90.5% |

Crisp (🟢 "high confidence") tasks perform *worst*. This is because crisp routing produces narrow confidence bands, and those narrow bands fail to capture the actual value when the anchor is wrong. Fuzzy tasks succeed not because estimation is accurate, but because their wide bands (±25%) are forgiving enough to cover the overestimate.

The skill is, paradoxically, *more reliable* (higher hit rate) on the tasks it claims *less confidence* in.

---

### Finding 6: Dependency Buffers Are Too Aggressive for Execution Tasks

The heavy dependency buffer (+35%) is applied multiplicatively on top of an already-inflated anchor. For TC017 (workflow automation, heavy deps): `37,000 × 1.35 = 49,950` estimated vs. 14,000 actual. The buffer logic assumes the base anchor is correct — if the anchor is wrong, the buffer amplifies the error.

---

## Proposed Improvements for v1.1

### 1. Add a 4th Question: Output Scale

```
Q4. What's the expected output size?
  MICRO  — single answer, short doc, snippet (<300 tokens output)
  MEDIUM — page-length output, moderate code (300–2K tokens output)  
  LARGE  — multi-page, complex code, full document (2K+ tokens output)
```

This single question enables routing to `simple_qa` and `document_short` anchors, which are currently unreachable. It is the most impactful single change.

### 2. Split the `data` Category into Sub-Types

| Sub-type | Anchor mid | Example tasks |
|----------|------------|---------------|
| data-lookup | 1,500 | Q&A, retrieval, simple list |
| data-transform | 4,000 | CSV cleaning, format conversion |
| data-analysis | 9,000 | Multi-metric analysis, NLP theming |

### 3. Split the `execution` Category

| Sub-type | Anchor mid | Example tasks |
|----------|------------|---------------|
| execution-light | 14,000 | Workflow setup, refactor, ETL script |
| execution-heavy | 37,000 | Full app build, multi-system deploy |

### 4. Recalibrate Anchor Midpoints Based on Test Results

| Anchor | v1.0 mid | Observed mean | Recommended v1.1 mid |
|--------|----------|---------------|----------------------|
| simple_qa | 1,250 | 975 | 1,000 |
| data_processing | 5,000 | 4,717 (excl. outliers) | 4,500 |
| code_feature | 5,500 | 4,200 | 4,000 |
| complex_artifact | 11,500 | 8,500 | 9,000 |
| research_synthesis | 15,000 | 16,000 | 15,500 |
| deep_exploratory | 25,000 | 20,333 | 22,000 |
| execution (light) | — | 14,000–15,000 | 14,000 |
| full_project | 37,000 | 36,000–40,000 | 37,000 (keep) |

### 5. Reduce Dependency Buffer for Light Dependencies

The current 15–20% buffer (mid: 17.5%) for "light" deps is reasonable. The 30–40% buffer (mid: 35%) for "heavy" deps is applied too broadly — it was designed for research-heavy tasks but gets applied to execution tasks where the bottleneck is code generation, not web fetching. Recommendation: scope the heavy buffer to `exploratory` category only; use 20% for `execution` + heavy deps.

---

## Statistical Notes

- **n=35** is sufficient to detect the observed bias (p=0.003) but gives wide confidence intervals on subgroup analyses (category n=5–14). Version 2.0 of the harness should target n=50+ with at least 12 cases per category.
- **Anchor routing** was inferred heuristically in the test harness (not specified per test case). Per-case `anchor_key` fields should be added to `test_cases.json` in a future version so the harness precisely mirrors what a human would do when consulting the skill.
- **Ground truth ranges** are derived from the skill's own anchor table and published benchmarks, not from live API measurements. A future test should measure actual token consumption via the Anthropic token counting API for a subset of cases.

---

## Summary Table

| Metric | v1.0 Result | Target for v1.1 |
|--------|-------------|-----------------|
| Overall hit rate | 48.6% | ≥70% |
| Mean error bias | +75.1% | <±20% |
| Data category hit rate | 0% | ≥60% |
| Execution category hit rate | 40% | ≥65% |
| Confidence signal alignment | Inverted | Monotonic (🟢 > 🟡 > 🔴) |
| RMSE | 152.4% | <60% |
