---
name: TokenEstimator
description: Estimate tokens before execution. Prevent session runaway via decision-driven estimation, model recommendations, and scope reduction options. Pro plan target: 44K/5-hour window.
trigger_phrases:
  - "estimate tokens for"
  - "before you start, estimate"
  - "token check before execution"
  - "can this fit in one session"
version: "1.1"
tags: [planning, estimation, efficiency, cowork]
changelog:
  - "v1.1: Added Q4 (output scale); introduced 5-tier anchor system calibrated from 35-case test harness; split execution category; RMSE improved 152%→51%"
  - "v1.0: Initial release"
---

## Executive Summary (Pseudocode)

```
IF user_task_described():
  tier = IDENTIFY_TIER(task_type, output_scale)       ← most important step
  estimate = tier.mid × (1 + dep_buffer)
  band = [estimate × (1-scope_var), estimate × (1+scope_var)]
  
  risk = classify(estimate)
  model = recommend_model(task_type, scope)
  
  RETURN(estimate, band, risk, model, execution_path)
```

---

## Step 1 — Pick a Tier (Most Important Decision)

Think about how much Claude will *produce*, not just what you're asking.

| Tier | Anchor Mid | Examples |
|------|-----------|---------|
| **1 — Micro** | 1,200 tok | Quick Q&A, short email, simple script, one-liner lookup |
| **2 — Standard** | 3,700 tok | Short doc, CSV transform, code snippet, summary, translation |
| **3 — Complex** | 9,300 tok | Code feature, presentation, analysis, legal/security review, design |
| **4 — Project** | 18,800 tok | Research synthesis, multi-file refactor, ETL pipeline, workflow build |
| **5 — Full Session** | 36,000 tok | Complete app build, full deployment pipeline, end-to-end project |

**Quick routing:**
- Will Claude write < 300 tokens of output? → **Tier 1**
- Will Claude write 300–2K tokens? → **Tier 2**
- Will Claude write 2K–5K tokens OR reason deeply for 1K-2K? → **Tier 3**
- Will Claude need 30+ min of work or fetch 5+ sources? → **Tier 4**
- Will this realistically take multiple follow-up messages? → **Tier 5**

---

## Step 2 — Apply Three Modifiers

### 2a. Scope Definition → sets confidence band width

| Scope | Confidence | Band |
|-------|-----------|------|
| CRISP — fully specified, format locked | 🟢 High | ±10% |
| SEMI-DEFINED — mostly clear, some unknowns | 🟡 Medium | ±15% |
| FUZZY — exploratory, requirements unclear | 🔴 Low | ±25% |

### 2b. External Dependencies → adds buffer to anchor mid

| Dependencies | Buffer |
|-------------|--------|
| None — self-contained | +0% |
| Light — 1–3 sources or tool calls | +15% |
| Heavy — 5+ sources, multi-tool flows | +25% |

### 2c. Task Category → informs model recommendation

| Category | Examples |
|----------|---------|
| **Data** | Transform, clean, analyze, retrieve |
| **Exploratory** | Research, reason, investigate |
| **Creation** | Write, generate, build |
| **Execution** | Run tools, automate, deploy |

---

## Estimation Formula

```
base     = tier.mid
buffered = base × (1 + dep_buffer)
point    = buffered

low  = point × (1 - scope_variance)
high = point × (1 + scope_variance)
```

---

## Estimation Output Template

```
TIER: [1–5] | ESTIMATE: ~X tokens (X_low–X_high) | CONFIDENCE: [🟢|🟡|🔴]

BREAKDOWN: [Phase/component breakdown adding to ~X]

RISK: [✓ SAFE <30K | ⚠ TIGHT 30–38K | ❌ RISKY >38K]

IF RISKY:
  Option A: [narrowed scope] → Tier X, ~Y tokens ✓
  Option B: [alt approach]   → Tier X, ~Z tokens ✓
  Option C: [phase it]       → ~A tokens now + ~B in follow-up

MODEL: [Opus|Sonnet|Haiku] | Why: [reasoning] | Downgrade saves: X%

EXECUTION: [proceed now | phase this | scope down first | save for fresh session]
```

---

## Risk Thresholds

| Level | Token Range | Meaning |
|-------|------------|---------|
| ✓ SAFE | < 30K | Comfortable single session |
| ⚠ TIGHT | 30–38K | Fits, minimal buffer — consider phasing |
| ❌ RISKY | > 38K | Likely to hit Pro limit; scope down or phase |

---

## Model Recommendation Table

| Task Type | Output Complexity | Recommended | Downgrade Option | Savings |
|-----------|-----------------|------------|-----------------|---------|
| Data lookup / transform | Low | Haiku | — | — |
| Data analysis | Medium | Sonnet | — | — |
| Research synthesis | High | Opus | Sonnet (structured brief) | 25–35% |
| Deep exploratory | High | Opus | — | — |
| Creation Tier 1–2 | Low | Sonnet | Haiku | 50–65% |
| Creation Tier 3 | Medium | Sonnet | — | — |
| Creation Tier 4–5 | High | Opus | Sonnet (templated) | 25–35% |
| Execution light | Medium | Sonnet | — | — |
| Execution heavy | High | Opus | — | — |

**Rule:** Match model to reasoning demand, not task size. A Tier 5 data pipeline is a Sonnet job; a Tier 3 architecture decision is an Opus job.

---

## Workflow

1. Describe your task → I identify the tier (ask if unclear)
2. I confirm scope, deps, and category with 1–3 quick questions
3. I output estimate with band, risk, model, and execution recommendation
4. If RISKY → I offer 2–3 concrete scope reduction paths with their tier and token count

---

## Constraints

| Constraint | Value |
|-----------|-------|
| Pro plan limit per 5-hour window | 44K tokens |
| Estimation goal | Prevent runaway, not perfection |
| Acceptable estimation error | ±25% |
| SAFE threshold | < 30K |
| TIGHT threshold | 30–38K |
| RISKY threshold | > 38K |

---

## Examples

**Example 1 — Tier 1: Micro output**

> "Estimate: write a professional email declining a vendor proposal"

Tier: 1 (Micro) | Scope: CRISP | Deps: None

```
TIER: 1 | ESTIMATE: ~1,200 tokens (1,080–1,320) | CONFIDENCE: 🟢
BREAKDOWN: Email draft ~1,000 | Minor revisions ~200
RISK: ✓ SAFE
MODEL: Haiku (short creation, no reasoning depth needed; saves 60% vs Sonnet)
EXECUTION: Proceed now
```

**Example 2 — Tier 4: Research project**

> "Research AI regulation across 5 countries, write 2K-word summary"

Tier: 4 (Project) | Scope: SEMI-DEFINED | Deps: Heavy

```
TIER: 4 | ESTIMATE: ~23,500 tokens (20,000–27,000) | CONFIDENCE: 🟡
BREAKDOWN: Web research ~12K | Synthesis ~8K | Writing ~3.5K
RISK: ✓ SAFE (comfortable single session)
MODEL: Opus (cross-jurisdiction reasoning; Sonnet saves 25% if you provide sources)
EXECUTION: Proceed now; narrow to 3 countries if you want more buffer
```

**Example 3 — Tier 5: Full deployment**

> "Set up CI/CD with GitHub Actions, Docker, and AWS ECS for our Node app"

Tier: 5 (Full Session) | Scope: FUZZY | Deps: Heavy

```
TIER: 5 | ESTIMATE: ~45,000 tokens (33,750–56,250) | CONFIDENCE: 🔴
BREAKDOWN: Config authoring ~18K | Iteration/debug ~20K | Testing ~7K
RISK: ❌ RISKY (exceeds Pro window)
Option A: CI + Docker only (skip ECS) → Tier 4, ~20K ✓ SAFE
Option B: Provide existing configs to refine → Tier 3, ~10K ✓ SAFE
Option C: Phase — GH Actions now (~18K), Docker + ECS next session (~22K)
MODEL: Opus (multi-system architecture; fuzzy scope needs judgment)
EXECUTION: Scope down or phase — Option A recommended
```
