---
name: TokenEstimator
description: Estimate tokens before execution. Prevent session runaway via decision-driven estimation, model recommendations, and scope reduction options. Pro plan target: 44K/5-hour window.
trigger_phrases:
  - "estimate tokens for"
  - "before you start, estimate"
  - "token check before execution"
  - "can this fit in one session"
version: "1.2"
tags: [planning, estimation, efficiency, cowork]
changelog:
  - "v1.2: Two-part estimate (output tier + context bucket); probe for Bucket C/D when TIGHT/RISKY"
  - "v1.1: 5-tier output anchors from 35-case test harness; RMSE 152%→51%"
  - "v1.0: Initial release"
---

## Pseudocode

```
total = output_tier.mid + context_bucket.mid
band  = [total × (1 - scope_var), total × (1 + scope_var)]
risk  = SAFE if total < 30K | TIGHT if < 38K | RISKY if >= 38K

if (risk in [TIGHT, RISKY]) and (context in [C, D]):
    run_probe()        # ~1K tokens to get real scope reading
    recalculate(total, risk)

if risk == RISKY:
    offer_scope_options(3)

recommend_model(task_type, scope)
recommend_execution_path(risk)
```

Goal: prevent runaway sessions, not maximize precision.
Limit: 44,000 tokens / 5-hour window (Pro plan).

---

## Step 1 — Output Tier

*Question: How much will Claude produce?*

| Tier | Mid | When |
|------|-----|------|
| 1 — Micro | 1,200 | <300 tokens output — answer, email, one-liner |
| 2 — Standard | 3,700 | 300–2K tokens — short doc, snippet, summary, transform |
| 3 — Complex | 9,300 | 2K–5K tokens, or deep reasoning for shorter output |
| 4 — Project | 18,800 | 30+ min of work, many interdependent steps |
| 5 — Full Session | 36,000 | Requires follow-up messages to complete |

---

## Step 2 — Context Bucket

*Question: What must Claude read or fetch before it can start?*

| Bucket | Mid | When |
|--------|-----|------|
| A — Provided | 0 | User supplies everything — paste, upload, clear brief |
| B — Light Fetch | 5,000 | Few lookups — 2–3 web pages, files, or API calls |
| C — Deep Research | 17,500 | Many sources (5–10+), full codebase, long corpus |
| D — Iterative/Unknown | 30,000 | Path unknown until Claude starts; open-ended exploration |

---

## Step 3 — Scope Variance

| Scope | Variance | Signal |
|-------|----------|--------|
| CRISP — fully specified, format locked | ±10% | 🟢 |
| SEMI-DEFINED — mostly clear, some unknowns | ±15% | 🟡 |
| FUZZY — exploratory, requirements unclear | ±25% | 🔴 |

---

## Step 4 — Probe (Bucket C or D, when TIGHT or RISKY only)

Spend ≈1,000 tokens to get a real scope reading before committing.

```
probe_actions:
  - count records/files/messages before processing
  - convert count → token implication
  - recalculate total and re-classify risk

examples:
  - "4,200 Zendesk tickets × ~500 tok each = 2.1M tok — not one session"
  - "82 files avg 200 lines = ~65K tok to read in full"
  - "3,400 emails × 200 tok = 680K tok"

skip_if: risk == SAFE  # user can scope themselves
```

---

## Output Template

```
OUTPUT COST:  Tier [N] — ~[X] tokens  ([description])
CONTEXT COST: Bucket [X] — ~[Y] tokens ([description])
──────────────────────────────────────────────────────
TOTAL:        ~[Z] tokens ([low]–[high])  [🟢|🟡|🔴]
RISK:         [✓ SAFE | ⚠ TIGHT | ❌ RISKY]

[IF PROBE RAN:]
PROBE: [finding] → [token implication] → revised risk: [SAFE|TIGHT|RISKY]

[IF RISKY:]
Option A: [narrowed scope]  → ~[tok] ✓
Option B: [alt approach]    → ~[tok] ✓
Option C: [phased plan]     → ~[tok] now + ~[tok] follow-up

MODEL:     [Opus|Sonnet|Haiku] — [reason]
EXECUTION: [proceed now | phase | scope down | save for fresh session]
```

---

## Model Selection

*Match to reasoning demand, not task size.*

| Task | Model | Downgrade if |
|------|-------|-------------|
| Lookup / transform / classify | Haiku | — |
| Analysis / structured writing | Sonnet | — |
| Research synthesis | Opus | Sources already provided → Sonnet |
| Deep exploratory | Opus | — |
| Complex code / architecture | Opus | Requirements crisp → Sonnet |
| Boilerplate / templated creation | Sonnet | Trivial → Haiku |
| Multi-system execution | Opus | Steps fully specified → Sonnet |

---

## Examples

**Tier 2 + Bucket A → SAFE**
*"Write a one-page memo recommending we switch from Jira to Linear"*
```
OUTPUT COST:  Tier 2 — ~3,700 tok  (short structured doc)
CONTEXT COST: Bucket A — ~0        (self-contained)
TOTAL:        ~3,700 tok (3,300–4,100)  🟢
RISK:         ✓ SAFE
MODEL:        Sonnet — structured writing, no deep reasoning
EXECUTION:    Proceed now
```

**Tier 3 + Bucket C → SAFE (probe skipped)**
*"Research top 5 open-source LLM frameworks and compare on ease of use, performance, community"*
```
OUTPUT COST:  Tier 3 — ~9,300 tok  (detailed comparison)
CONTEXT COST: Bucket C — ~12,000   (5 sources × ~2–3K each)
TOTAL:        ~21,300 tok (18,100–24,500)  🟡
RISK:         ✓ SAFE
MODEL:        Opus — cross-framework judgment
EXECUTION:    Proceed now
```

**Tier 3 + Bucket D → RISKY → probe fires**
*"Review all support tickets closed in the last 6 months and identify top themes"*
```
PROBE: 4,200 tickets found × ~500 tok = ~2.1M tok — not feasible at full scope

OUTPUT COST:  Tier 3 — ~9,300 tok
CONTEXT COST: Bucket D — exceeds session limit at full scope
TOTAL:        >> 44K
RISK:         ❌ RISKY

Option A: Sample 50 recent tickets       → ~25K tok ✓
Option B: Filter to one ticket category  → ~15K tok ✓
Option C: Export CSV, batch across 3–4 sessions

MODEL:        Sonnet — classification/theming; Opus not needed
EXECUTION:    Do not proceed at full scope — pick an option above
```
