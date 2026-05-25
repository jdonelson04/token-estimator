---
name: TokenEstimator
description: Estimate tokens before execution. Prevent session runaway via decision-driven estimation, model recommendations, and scope reduction options. Pro plan target: 44K/5-hour window.
trigger_phrases:
  - "estimate tokens for"
  - "before you start, estimate"
  - "token check before execution"
  - "can this fit in one session"
version: "1.0"
tags: [planning, estimation, efficiency, cowork]
---

## Executive Summary (Pseudocode)

```
IF user_task_described():
  GATHER_DECISIONS(task_category, scope_clarity, external_deps)
  
  estimate = calculate_estimate(category, clarity, deps)
  risk_level = classify(estimate)
  
  IF risk_level == "SAFE" (<30K):
    RECOMMEND("execute now")
  ELIF risk_level == "TIGHT" (30-38K):
    RECOMMEND("fits but tight; consider phasing")
  ELSE:  // RISKY (>38K)
    OFFER_SCOPE_REDUCTION_OPTIONS(3)
  
  model = recommend_model(category, clarity)
  RETURN(estimate, confidence, model, execution_path)
```

---

## Decision Matrix

| Decision | Options | Profile | Variance |
|----------|---------|---------|----------|
| **1. Task Category** | Data (process/analyze) | Predictable | ±10% |
| | Exploratory (research/reason) | Medium | ±20% |
| | Creation (generate output) | Predictable | ±10% |
| | Execution (workflows/tools) | High | ±25% |
| **2. Scope Definition** | CRISP (fully spec'd) | 🟢 High conf | ±10% |
| | SEMI-DEFINED (mostly clear) | 🟡 Medium conf | ±15% |
| | FUZZY (exploratory) | 🔴 Low conf | ±25% |
| **3. External Dependencies** | Self-contained (no research) | Buffer: 0% | Fast |
| | Light (1-2 sources/calls) | Buffer: 15-20% | Moderate |
| | Heavy (5+ sources, complex flows) | Buffer: 30-40% | High variance |

---

## Estimation Output Template

```
ESTIMATE: ~X tokens (X-20% to X+20%) | CONFIDENCE: [🟢|🟡|🔴]

BREAKDOWN: Phase1: ~A | Phase2: ~B | Phase3: ~C | Buffer: ~D | TOTAL: ~X

RISK: [✓ SAFE <30K | ⚠ TIGHT 30-38K | ❌ RISKY >38K]

IF RISKY:
  Option A: [narrowed scope] → ~X tokens
  Option B: [alt approach] → ~Y tokens  
  Option C: [phased execution] → ~Z tokens (+ follow-up)

MODEL: [Opus|Sonnet|Haiku] | Savings if switched: X%

EXECUTION: [proceed now | phase this | scope down first | save for fresh session]
```

---

## Model Selection Table

| Category | Reasoning Depth | Safe Choice | Safe If | Downgrade To | Savings |
|----------|-----------------|------------|---------|--------------|---------|
| Data transform | Low | Sonnet | Well-defined | Haiku | 50-65% |
| Exploratory research | High | Opus | Has unknowns | — | — |
| Creation (creative) | High | Opus | Nuanced output | Sonnet (templated) | 25-35% |
| Creation (templated) | Low | Sonnet | Spec'd format | Haiku | 50-65% |
| Code (complex logic) | High | Opus | Architectural decisions | — | — |
| Code (boilerplate) | Low | Sonnet | Clear requirements | — | 30-40% |
| Simple Q&A | Low | Haiku | Straightforward | — | 60-75% |
| Retrieval/list-making | Low | Haiku | No analysis needed | — | 60-75% |

**Default rule:** Start with Opus. Step down only if task is obviously routine/templated/low-reasoning.

---

## Estimation Anchors (Quick Baseline)

| Task | Range | Conditions |
|------|-------|-----------|
| Simple Q&A | 500-2K | No research |
| Document (<1K words) | 3-6K | Format locked |
| Data processing | 2-8K | Depends on volume |
| Research synthesis (5-10 src) | 10-20K | Heavy input |
| Single code feature | 3-8K | Complexity varies |
| Complex artifact | 8-15K | Multi-phase |
| Deep exploratory | 15-35K | High variance |
| Full Cowork project | 30-44K | Plan phasing |

---

## Workflow

1. You describe task → I ask for Decision 1, 2, 3 (if unclear)
2. I estimate with breakdown, confidence, risk flag
3. If RISKY → offer 2-3 scope reduction paths
4. Recommend model with trade-offs
5. Recommend execution path (now, phase, reduce, or defer)

---

## Constraints

| Constraint | Value |
|-----------|-------|
| Pro plan limit per 5-hour window | 44K tokens |
| Acceptable variance | ±15% |
| Estimation goal | Prevent runaway, not perfection |
| SAFE threshold | < 30K tokens |
| TIGHT threshold | 30-38K tokens |
| RISKY threshold | > 38K tokens |
| Win: estimate 25K, actual | ~28K ✓ |
| Loss: estimate 5K, actual | ~40K ✗ |

**Note:** This skill estimates only. For exact token counts, use Anthropic's token counting API.

---

## Mini Example

**You:** "Estimate: research AI regulation across 5 countries, write 2K-word summary"

**My questions:** Category? Exploratory ✓ | Scope? Semi-defined ✓ | Deps? Heavy ✓

**My response:**
```
ESTIMATE: ~28K (24-32K) | CONFIDENCE: 🟡 Medium ±15%
BREAKDOWN: Research ~10K | Synthesis ~12K | Writing ~4K | Buffer ~2K
RISK: ⚠ TIGHT (within window, limited buffer)
MODEL: Opus (explorations needs reasoning depth; Sonnet saves 20-25%)
EXECUTION: Doable one session; narrow research scope, plan 1 refinement pass
```
