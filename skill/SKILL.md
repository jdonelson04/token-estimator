---
name: TokenEstimator
description: Estimate tokens before execution. Prevent session runaway by reasoning about execution path, identifying token traps, and recommending scope before committing. Pro plan target: 44K/5-hour window.
trigger_phrases:
  - "estimate tokens for"
  - "before you start, estimate"
  - "token check before execution"
  - "can this fit in one session"
version: "1.3"
tags: [planning, estimation, efficiency, cowork]
changelog:
  - "v1.3: Execution-path-first reasoning model; trap taxonomy (enumeration/reasoning/fetch/iteration); tier+bucket reframed as output vocabulary not input routing"
  - "v1.2: Two-part estimate (output tier + context bucket); probe for Bucket C/D when TIGHT/RISKY"
  - "v1.1: 5-tier output anchors from 35-case test harness; RMSE 152%→51%"
  - "v1.0: Initial release"
---

## Pseudocode

```
GIVEN user_prompt:

  # Step 1 — reason about execution path
  steps = identify_execution_steps(user_prompt)
  traps = []
  for step in steps:
    if is_enumeration_trap(step):   traps.append(("enumeration", step))
    if is_reasoning_trap(step):     traps.append(("reasoning",   step))
    if is_fetch_trap(step):         traps.append(("fetch",        step))
    if is_iteration_trap(step):     traps.append(("iteration",    step))

  # Step 2 — quantify
  output_cost  = map_to_tier(steps)        # how much Claude will produce
  context_cost = map_to_bucket(traps)      # how much Claude must consume first
  total        = output_cost + context_cost
  band         = [total × (1 - scope_var), total × (1 + scope_var)]
  risk         = classify(total)           # SAFE / TIGHT / RISKY

  # Step 3 — probe if needed
  if traps and risk in [TIGHT, RISKY]:
    probe_result = probe(traps)            # ~1K tokens to get real scope
    total, risk  = recalculate(probe_result)

  # Step 4 — return
  RETURN execution_summary, traps, estimate, risk, model, execution_path
```

Goal: prevent runaway sessions, not maximize precision.
Limit: 44,000 tokens / 5-hour window (Pro plan).

---

## Token Trap Taxonomy

These are the patterns that cause sessions to run over. Identify them in the
execution path before assigning a cost estimate.

### Enumeration trap
Task requires iterating over an unbounded or unknown-size dataset before any
useful work can begin. The dataset size — not the output — drives the cost.

```
signals:
  - "all emails / files / records / messages"
  - "every [item] that matches [condition]"
  - "process the whole [dataset / inbox / repo]"

examples:
  - "mark all unread emails older than 2020 as read"   # must index mailbox first
  - "find every TODO comment across the codebase"       # must read all files first
  - "delete duplicate contacts from my CRM"             # must enumerate all contacts

fix: count first → decide scope → execute on bounded set
```

### Reasoning trap
Task requires deep synthesis, high uncertainty, or many interdependent
considerations. Output may be short but thinking cost is high.

```
signals:
  - open-ended "why", "how should", "what's the best way"
  - cross-domain synthesis with no provided framework
  - architectural or strategic decisions with unknown constraints

examples:
  - "solve world peace in a 1000-word brief"
  - "design the optimal microservices boundary for our system"
  - "explain why our churn rate increased last quarter"

fix: constrain scope, provide starting framework, accept partial answer
```

### Fetch trap
Task requires pulling from many external sources before synthesis can begin.
Source count and document size drive the cost, not the output.

```
signals:
  - "research [N] competitors / countries / frameworks"
  - "gather all documentation on [X]"
  - "look up [many things] and compare"

examples:
  - "compare 10 open-source LLM frameworks on performance and community"
  - "research AI regulation across all G20 countries"

fix: limit source count, or have user provide sources directly (→ Bucket A)
```

### Iteration trap
Task requires multiple cycles of unknown length — try, observe, adjust, repeat.
Neither the number of cycles nor the cost per cycle is predictable upfront.

```
signals:
  - "debug this until it works"
  - "keep refining until I'm happy"
  - "figure out what's wrong with [system]"
  - open-ended troubleshooting with no stopping condition

examples:
  - "fix the performance issue in our API"   # unknown root cause
  - "get the tests passing"                  # unknown number of failures

fix: timebox explicitly, cap iteration count, define a stopping condition
```

---

## Output Vocabulary — Tiers and Buckets

*These are how we express the estimate, not how we route the input.*
*Claude derives tier and bucket from execution path reasoning above.*

### Output tiers — how much Claude will produce

| Tier | Mid | When |
|------|-----|------|
| 1 — Micro | 1,200 | <300 tokens output — answer, email, one-liner |
| 2 — Standard | 3,700 | 300–2K tokens — short doc, snippet, summary |
| 3 — Complex | 9,300 | 2K–5K tokens, or deep reasoning for shorter output |
| 4 — Project | 18,800 | 30+ min of work, many interdependent steps |
| 5 — Full Session | 36,000 | Requires follow-up messages to complete |

### Context buckets — what Claude must consume before starting

| Bucket | Mid | When |
|--------|-----|------|
| A — Provided | 0 | User supplies everything — paste, upload, brief |
| B — Light Fetch | 5,000 | Few lookups — 2–3 sources, files, or API calls |
| C — Deep Research | 17,500 | Many sources (5–10+), full codebase, long corpus |
| D — Iterative/Unknown | 30,000 | Path unknown until Claude starts; enumeration traps |

### Scope variance

| Scope | Variance | Signal |
|-------|----------|--------|
| CRISP — fully specified, format locked | ±10% | 🟢 |
| SEMI-DEFINED — mostly clear, some unknowns | ±15% | 🟡 |
| FUZZY — exploratory, requirements unclear | ±25% | 🔴 |

---

## Estimation Formula

```
total = output_tier.mid + context_bucket.mid
low   = total × (1 - scope_variance)
high  = total × (1 + scope_variance)
```

---

## Risk Classification

```
if total < 30,000:  SAFE  — proceed
if total < 38,000:  TIGHT — fits, consider phasing or narrowing
if total >= 38,000: RISKY — offer scope reduction options
```

---

## Probe Protocol (when traps found AND estimate is TIGHT or RISKY)

```
probe_actions:
  enumeration trap → count items before processing
    "SELECT COUNT(*) WHERE unread AND date < 2020"
    "ls -R | wc -l"
    "find . -name '*.py' | wc -l"

  fetch trap → count sources and estimate avg size
    "how many results does this search return?"
    "what's the avg doc length for these sources?"

  iteration trap → identify stopping condition or cap
    "how many test failures are there currently?"
    "what's the known scope of the bug?"

convert count → token implication → revised estimate
skip if: risk == SAFE  # user can scope themselves
```

---

## Output Template

```
EXECUTION PATH:
  [Plain-English description of what Claude would actually do to answer this]
  [Call out each expensive step explicitly]

TRAPS IDENTIFIED: [none | enumeration / reasoning / fetch / iteration]
  → [specific description of the trap and why it's expensive]

[IF PROBE RAN:]
PROBE: [finding] → [token implication] → revised risk: [SAFE|TIGHT|RISKY]

OUTPUT COST:  Tier [N] — ~[X] tokens  ([description])
CONTEXT COST: Bucket [X] — ~[Y] tokens ([description])
──────────────────────────────────────────────────────
TOTAL:        ~[Z] tokens ([low]–[high])  [🟢|🟡|🔴]
RISK:         [✓ SAFE | ⚠ TIGHT | ❌ RISKY]

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
| Deep exploratory / reasoning trap | Opus | — |
| Complex code / architecture | Opus | Requirements crisp → Sonnet |
| Boilerplate / templated creation | Sonnet | Trivial → Haiku |
| Multi-system execution | Opus | Steps fully specified → Sonnet |

---

## Examples

**Example 1 — No traps, SAFE**
*"Write a one-page memo recommending we switch from Jira to Linear"*

```
EXECUTION PATH:
  1. Read prompt and context (user's own opinion, no fetching needed)
  2. Draft structured memo (~1 page)
  No expensive steps identified.

TRAPS IDENTIFIED: none

OUTPUT COST:  Tier 2 — ~3,700 tok  (short structured doc)
CONTEXT COST: Bucket A — ~0        (self-contained)
TOTAL:        ~3,700 tok (3,300–4,100)  🟢
RISK:         ✓ SAFE
MODEL:        Sonnet — structured writing, no deep reasoning
EXECUTION:    Proceed now
```

**Example 2 — Fetch trap, SAFE (probe skipped)**
*"Research top 5 open-source LLM frameworks and compare on ease of use, performance, community"*

```
EXECUTION PATH:
  1. Search and fetch documentation for each framework (~2–3K tok each)
  2. Synthesize comparison across 5 sources
  3. Write structured comparison (~2K tok output)

TRAPS IDENTIFIED: fetch trap
  → 5 frameworks × ~2–3K tok per source = ~10–15K tok before writing begins
  → Source count is bounded (5), so cost is predictable

OUTPUT COST:  Tier 3 — ~9,300 tok  (detailed comparison)
CONTEXT COST: Bucket C — ~12,000   (5 sources × ~2–3K each)
TOTAL:        ~21,300 tok (18,100–24,500)  🟡
RISK:         ✓ SAFE — fetch trap identified but bounded
MODEL:        Opus — cross-framework judgment
EXECUTION:    Proceed now. To reduce: provide docs directly → drops to ~9,300 tok
```

**Example 3 — Enumeration trap, RISKY → probe fires**
*"Find all unread emails older than 2020 and mark them as read"*

```
EXECUTION PATH:
  1. Connect to Gmail
  2. Enumerate mailbox to find emails matching criteria  ← TRAP
  3. Mark matched emails as read (trivial output)

TRAPS IDENTIFIED: enumeration trap
  → Must index the entire mailbox before any useful work begins
  → Mailbox size unknown — could be thousands or hundreds of thousands of items
  → Running probe to check actual scope...

PROBE: ~180,000 emails in mailbox matching criteria
  → Even at 200 tok/email to index = 36M tokens — not feasible in any session

OUTPUT COST:  Tier 1 — ~1,200 tok  (trivial — just marking items)
CONTEXT COST: Bucket D — effectively unlimited at full scope
TOTAL:        >> 44K limit
RISK:         ❌ RISKY

Option A: Process only last 6 months of unread emails → ~8K tok ✓ SAFE
Option B: Process in batches of 500 emails per session → ~12K tok/session
Option C: Use Gmail filters directly (no Claude enumeration needed) → ~0 tok ✓

MODEL:        Haiku — execution is trivial once scoped; Opus not needed
EXECUTION:    Do not proceed at full scope — the indexing alone exceeds the session limit
```
