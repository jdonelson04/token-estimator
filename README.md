# TokenEstimator

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Claude Pro](https://img.shields.io/badge/Claude-Pro-blueviolet.svg)](https://claude.ai)
![Version 1.3](https://img.shields.io/badge/Version-1.3-green.svg)

**A Claude skill that checks your work before you start it.**

Claude Pro gives you roughly 44,000 tokens per five-hour session. Most tasks fit comfortably. Some look simple but quietly consume your entire budget before producing anything useful. TokenEstimator spots those before you commit.

---

## What it does

When you describe a task, TokenEstimator maps out what Claude would actually have to *do* to complete it — not what the output looks like, but the work required to get there. It then checks that execution path for patterns known to cause runaway token usage, gives you a rough cost estimate, and tells you whether to proceed, phase the work, or rethink the approach entirely.

The output is deliberately rough. The goal isn't ±5% precision — it's giving you enough signal to make a good decision before you spend a token.

The skill works best on prompts that are already well-formed — clear inputs, clear scope, clear expected output. If you know what you're asking for and how you'd recognize a good answer, the skill can reason accurately about what it will take to get there. Vague or exploratory prompts are harder to estimate reliably, and the skill will tell you so. Tightening the prompt before running the estimate is usually worth doing anyway.


---

## The traps it catches

Most budget blowouts come from one of four patterns. The skill is designed to recognize all of them, including the versions that hide inside an innocent-looking prompt.

### Enumeration
Claude has to read or process a large dataset before it can do anything useful. The output might be trivial — a list, a set of labels, a batch of edits — but the *input* is enormous and must be consumed first.

Common examples: searching an entire mailbox, scanning a full codebase, processing all records in a database.

The deceptive version: *"Find all the TODO comments in our repo and prioritize them."* Sounds like a quick list. Requires reading every file first.

### Reasoning
The thinking required to produce a good answer is much larger than the answer itself. A constrained output format doesn't constrain the cognitive work behind it.

Common examples: strategic decisions with many interdependent tradeoffs, causal analysis with limited data, synthesis across conflicting sources.

The deceptive version: *"In one paragraph, explain why our churn rate went up last quarter."* One paragraph of output. Potentially hours of reasoning across business, product, and market factors to get there responsibly.

### Fetch
Claude needs to gather information from many external sources before synthesis can begin. The number of sources — and their size — drives the cost, not what you're ultimately asking for.

Common examples: competitive research across many companies, regulatory analysis across many jurisdictions, technology comparisons across many options.

The deceptive version: *"What's the best ORM for our stack in 2025?"* Sounds like one question. A thorough answer requires checking documentation, community sentiment, and recent benchmarks for five or six frameworks.

### Iteration
The task has no defined stopping condition. Claude will try, observe, adjust, and repeat — but neither the number of cycles nor the cost per cycle is predictable upfront.

Common examples: open-ended debugging, copy refinement until it "sounds right," getting a test suite to pass when failure count is unknown.

The deceptive version: *"There's a flaky test in CI that fails about 30% of the time. Fix it."* Sounds like one fix. Flakiness often requires multiple diagnostic cycles to even identify the root cause.

---

## What you get back

For any prompt, the skill returns:

**Execution path** — a plain-English description of what Claude would actually do, with expensive steps called out explicitly.

**Traps identified** — which of the four patterns are present, and specifically why they're expensive for this task.

**Estimate** — a token range with a risk level:
- ✓ **SAFE** (< 30K) — proceed
- ⚠ **TIGHT** (30–38K) — fits within one session, but worth considering whether to phase
- ❌ **RISKY** (≥ 38K) — likely to exceed the session budget; skill offers three concrete scope-reduction options

**Probe** — for TIGHT or RISKY estimates where scope is unknown, the skill first spends ~1K tokens to get a real measurement (counting emails, files, records, test failures) before making a recommendation. A small upfront cost that prevents a much larger wasted one.

**Model recommendation** — which Claude model is appropriate for the task, matched to reasoning demand rather than output size.

### Example — no trap

*"Write a one-page memo recommending we switch our project management tool from Jira to Linear."*

```
EXECUTION PATH:
  1. Read the user's framing and stated reasons (self-contained)
  2. Draft a structured memo (~1 page)
  No expensive steps identified.

TRAPS IDENTIFIED: none

──────────────────────────────────────────────────────
ESTIMATE:  ~3,700 tok (3,300–4,100)  🟢
RISK:      ✓ SAFE
──────────────────────────────────────────────────────
MODEL:     Sonnet — structured writing, no deep reasoning required
EXECUTION: Proceed now
```

### Example — enumeration trap, probe fires

*"Find all unread emails older than January 2020 and mark them as read."*

```
EXECUTION PATH:
  1. Connect to Gmail
  2. Enumerate mailbox to find matching emails  ← TRAP
  3. Mark matched emails as read

TRAPS IDENTIFIED: enumeration trap
  → Entire mailbox must be indexed before any email can be marked
  → Dataset size unknown — running probe to check scope

PROBE: ~180,000 emails match the criteria
  → At ~200 tok/email to index = ~36M tokens. Not feasible in any session.

──────────────────────────────────────────────────────
ESTIMATE:  >> 44K limit
RISK:      ❌ RISKY
──────────────────────────────────────────────────────
Option A: Limit to the last 6 months of unread mail → ~8K tok ✓
Option B: Process in batches of 500 emails per session → ~12K tok/session
Option C: Use a Gmail filter rule directly — no Claude enumeration needed → ~0 tok ✓

MODEL:     Haiku — the actual work is trivial once scope is defined
EXECUTION: Do not proceed at full scope. Choose an option above.
```

---

## Installation

### Claude.ai

1. Download `skill/SKILL.md`
2. Go to **Settings → Customize → Skills → Add skill**
3. Upload `SKILL.md`

### Claude Code / Git

```bash
mkdir -p .claude/skills/token-estimator
cp skill/SKILL.md .claude/skills/token-estimator/
```

### Trigger phrases

```
"Before you start, estimate: [task]"
"Estimate tokens for: [task]"
"Token check before execution: [task]"
"Can this fit in one session: [task]"
```

---

## Testing & Validation

> ⚠️ **Beta:** The v2 test harness, community results submission, and dashboard are in active beta. We're validating the workflow with our own test cases before opening it broadly.

### How the skill is tested

The v2 test framework evaluates reasoning quality — not just whether the token estimate is in range, but whether the skill correctly identified *why* a task is expensive, even when the prompt makes it look cheap.

Test cases are organized around a 9-cell matrix: **trap type × surface deception**.

```
                  OBVIOUS                    DECEPTIVE ★
  No trap       │ TC-N01–N03  — control    │ n/a
  Enumeration   │ TC-EO01–03  — bounded    │ TC-ED01–03  — unbounded
  Reasoning     │ TC-RO01–03  — openly hard│ TC-RD01–03  — tiny output
  Fetch         │ TC-FO01–03  — count given│ TC-FD01–03  — 1 Q, many src
  Iteration     │ TC-IO01–03  — no stop    │ TC-ID01–03  — hidden cycles
```

The deceptive column (★) is the primary stress test — these are the cases where the prompt gives no surface signal that anything expensive is about to happen. A skill that only flags obvious traps isn't useful in practice.

Each run is scored on four dimensions:
1. **Estimate accuracy** — did actual tokens fall inside the stated band?
2. **Trap identification** — did the skill correctly name the trap type?
3. **Path accuracy** — did the skill describe the actual execution path? *(human)*
4. **Option quality** — for RISKY cases, were the scope-reduction options concrete? *(human)*

### Running the harness

```bash
# Generate a blank results template for one test case
python3 tests/test_harness_v2.py --template TC-N01 --runs 3

# Score a completed results file
python3 tests/test_harness_v2.py --results tests/results/TC-N01_results.json --report

# Submit results to the community file
python3 tests/test_harness_v2.py --submit tests/results/TC-N01_results.json

# Regenerate the dashboard
python3 tests/test_harness_v2.py --dashboard

# Aggregate all results in a directory
python3 tests/test_harness_v2.py --aggregate tests/results/ --report
```

### Community results

All submitted runs are stored in `tests/results/community_results.jsonl` — one JSON record per line, append-only. The dashboard (`tests/dashboard.html`) is regenerated from this file and shows trap identification rate by cell, estimate accuracy, and how metrics shift across skill versions over time.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full submission workflow.

### Version history

| Version | Change |
|---------|--------|
| v1.0 | Initial — 4-category routing. Hit rate: 48.6%, RMSE: 152% |
| v1.1 | 5-tier output system, cluster-calibrated anchors. RMSE ~51% (sim) |
| v1.2 | Two-part estimate: output tier + context bucket |
| v1.3 | Execution-path reasoning; trap taxonomy; tiers/buckets internalized as calibration constants |

See [`LEARNINGS.md`](LEARNINGS.md) for the full root cause analysis of v1.0 failures.

---

## File structure

```
token-estimator/
├── README.md
├── CONTRIBUTING.md              # How to run tests and submit results
├── LEARNINGS.md                 # v1.0 failure analysis and methodology
├── LICENSE
├── skill/
│   ├── SKILL.md                 # The skill itself (v1.3)
│   └── manifest.json
└── tests/
    ├── test_harness_v2.py       # Live test scorer + submit + dashboard generator
    ├── test_cases_v2.json       # 27 test cases (trap × deception matrix)
    ├── dashboard.html           # Auto-generated results dashboard
    ├── test_harness.py          # v1 synthetic harness (archived)
    ├── test_cases.json          # v1 35-case suite (archived)
    └── results/
        ├── community_results.jsonl   # All submitted runs, append-only
        ├── contributors/             # Raw result files by contributor
        └── run_001.json              # v1.0 baseline (archived)
```

---

## Skill specs

| Property | Value |
|----------|-------|
| Version | 1.3 |
| Estimation cost | ~2–4K tokens |
| Pro plan target | 44K / 5-hour window |
| Accuracy goal | Catch runaway before it happens — not ±2% precision |
| Dependencies | None for estimation; probe uses available connector tools |

## License

Apache License 2.0 — see [LICENSE](LICENSE)

## Resources

- [Anthropic Skills Guide](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
- [Claude Documentation](https://docs.claude.com)

---

**Version 1.3** — Updated May 2026  
**Status:** Active development — v2 test harness in beta
