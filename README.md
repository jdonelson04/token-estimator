# TokenEstimator

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Claude Pro](https://img.shields.io/badge/Claude-Pro-blueviolet.svg)](https://claude.ai)
![Version 1.3](https://img.shields.io/badge/Version-1.3-green.svg)

A Claude skill that estimates token cost **before you start a task** — so you can scope it down before it blows your session budget, not after.

## The problem it solves

You ask Claude to find all the unread emails in your 20-year-old inbox and mark them as read. It sounds simple. But Claude has to index every email first, and that indexing alone can exhaust your entire 5-hour session token budget before a single email is marked. You didn't know it would cost that much. Now your session is gone.

TokenEstimator catches this before it happens.

## How it works

The skill reasons about **what Claude would actually do** to complete your task — the execution path — and looks for **token traps**: patterns that are far more expensive than the prompt surface suggests.

### Token trap taxonomy

| Trap | What it is | Example |
|------|-----------|---------|
| **Enumeration** | Must index an unbounded dataset before any useful work can start | Mark all unread emails older than 2020 as read |
| **Reasoning** | Deep synthesis or cross-domain thinking; output may be short but thinking cost is high | Write a 500-word proposal for achieving world peace |
| **Fetch** | Many external sources must be pulled before synthesis | Compare AI regulations across all G20 countries |
| **Iteration** | Unknown number of try/observe/fix cycles; no stopping condition | Debug the performance issue and fix it |

The **deceptive** version of each trap is the hardest case: the prompt *looks* cheap but is expensive. "Find all the TODO comments in our codebase" looks like a one-liner — but it requires reading every file first. The skill is specifically designed to catch these.

### Risk levels

| Status | Token Range | Action |
|--------|-------------|--------|
| ✓ SAFE | < 30K | Proceed now |
| ⚠ TIGHT | 30–38K | Fits, but consider phasing or narrowing |
| ❌ RISKY | ≥ 38K | Scope down — skill offers 3 concrete options |

When the estimate is TIGHT or RISKY and traps are present, the skill runs a **probe** (~1K tokens) before committing — for example, counting emails or files to get a real scope reading rather than guessing.

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

## Usage

```
"Before you start, estimate: [task description]"
"Estimate tokens for: [task]"
"Token check before execution: [task]"
"Can this fit in one session: [task]"
```

### Example outputs

**No trap — SAFE**
```
EXECUTION PATH:
  1. Read user's context (self-contained, no fetching needed)
  2. Draft one-page memo (~1 page output)

TRAPS IDENTIFIED: none

──────────────────────────────────────────────────────
ESTIMATE:  ~3,700 tok (3,300–4,100)  🟢
RISK:      ✓ SAFE
──────────────────────────────────────────────────────
MODEL:     Sonnet
EXECUTION: Proceed now
```

**Enumeration trap — probe fires — RISKY**
```
EXECUTION PATH:
  1. Connect to Gmail
  2. Enumerate mailbox to find emails matching criteria  ← TRAP
  3. Mark matched emails as read (trivial output)

TRAPS IDENTIFIED: enumeration trap
  → Must index entire mailbox before any useful work begins
  → Mailbox size unknown — running probe...

PROBE: ~180,000 emails matching criteria
  → Even at 200 tok/email = 36M tokens — not feasible

──────────────────────────────────────────────────────
ESTIMATE:  >> 44K limit
RISK:      ❌ RISKY
──────────────────────────────────────────────────────
Option A: Process only last 6 months  → ~8K tok ✓
Option B: Process in batches of 500   → ~12K tok/session
Option C: Use Gmail filters directly (no Claude enumeration) → ~0 tok ✓

MODEL:     Haiku — execution is trivial once scoped
EXECUTION: Do not proceed at full scope
```

## Testing & Validation

> ⚠️ **Beta:** The v2 test harness, community results submission, and dashboard are in active beta testing. We're using our own test cases to validate the workflow before opening it more broadly.

### v2 Test framework (current)

The v2 harness evaluates the skill's **reasoning quality** — not just estimate math. It's organized around a 9-cell matrix: trap type × surface deception.

The deceptive column is the key test: does the skill catch expensive traps when the prompt doesn't make them obvious?

```
                  OBVIOUS                    DECEPTIVE ★
  No trap       │ TC-N01–N03  — control    │ n/a
  Enumeration   │ TC-EO01–03  — bounded    │ TC-ED01–03  — unbounded
  Reasoning     │ TC-RO01–03  — openly hard│ TC-RD01–03  — tiny output
  Fetch         │ TC-FO01–03  — count given│ TC-FD01–03  — 1 Q, many src
  Iteration     │ TC-IO01–03  — no stop    │ TC-ID01–03  — hidden cycles
```

Four scoring dimensions per run:
1. **Estimate accuracy** — did actual tokens fall inside the stated band?
2. **Trap identification** — did the skill correctly name the trap type?
3. **Path accuracy** — did the skill describe what Claude would actually do? *(human)*
4. **Option quality** — for RISKY cases, were the scope options concrete? *(human)*

### Running tests

```bash
# Generate a blank results template for a single test case
python3 tests/test_harness_v2.py --template TC-N01 --runs 3

# Score a completed results file
python3 tests/test_harness_v2.py --results tests/results/TC-N01_results.json --report

# Submit results to the community file
python3 tests/test_harness_v2.py --submit tests/results/TC-N01_results.json

# Regenerate the results dashboard
python3 tests/test_harness_v2.py --dashboard

# Roll up all results in a directory
python3 tests/test_harness_v2.py --aggregate tests/results/ --report
```

### Community results

Submitted runs live in `tests/results/community_results.jsonl` — one run per line, append-only. The dashboard (`tests/dashboard.html`) is regenerated from this file and shows trap identification rate by trap type (obvious vs. deceptive), estimate accuracy, and how metrics change across skill versions.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full submission workflow.

### Version history

| Version | Change |
|---------|--------|
| v1.0 | Initial — 4-category routing. Hit rate: 48.6%, RMSE: 152% |
| v1.1 | 5-tier output system, cluster-calibrated anchors. RMSE ~51% (sim) |
| v1.2 | Two-part estimate: output tier + context bucket |
| v1.3 | Execution-path reasoning; trap taxonomy; tiers/buckets internalized |

See [`LEARNINGS.md`](LEARNINGS.md) for root cause analysis of v1.0 failures.

## File structure

```
token-estimator/
├── README.md
├── CONTRIBUTING.md              # How to run tests and submit results
├── LEARNINGS.md                 # v1.0 failure analysis and methodology
├── LICENSE
├── skill/
│   ├── SKILL.md                 # Core skill definition (v1.3)
│   └── manifest.json
└── tests/
    ├── test_harness_v2.py       # Live test scorer + submit + dashboard generator
    ├── test_cases_v2.json       # 27 test cases (trap × deception matrix)
    ├── dashboard.html           # Auto-generated results dashboard
    ├── test_harness.py          # v1 synthetic harness (archived)
    ├── test_cases.json          # v1 35-case suite (archived)
    └── results/
        ├── community_results.jsonl   # Append-only flat file — all submitted runs
        ├── contributors/             # Raw result files by contributor
        └── run_001.json              # v1.0 baseline results (archived)
```

## Skill specs

| Property | Value |
|----------|-------|
| Version | 1.3 |
| Estimation cost | ~2–4K tokens |
| Pro plan target | 44K / 5-hour window |
| Target accuracy | Prevent runaway — not ±2% precision |
| External dependencies | None for estimation; probe uses available tools |

## License

Apache License 2.0 — see [LICENSE](LICENSE)

## Resources

- [Anthropic Skills Guide](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
- [Claude Documentation](https://docs.claude.com)

---

**Version 1.3** — Updated May 2026  
**Status:** Active development — v2 test harness in beta
