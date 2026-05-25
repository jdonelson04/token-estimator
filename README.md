# TokenEstimator

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Claude Pro](https://img.shields.io/badge/Claude-Pro-blueviolet.svg)](https://claude.ai)
![Version 1.2](https://img.shields.io/badge/Version-1.2-green.svg)

A decision-driven estimation framework to prevent token runaway in Claude sessions. Estimate task cost **before execution** to stay within your 44K-token Pro plan window.

## Overview

**Problem:** You start a task in Claude and realize halfway through it's going to blow through your 5-hour session budget.

**Solution:** This skill estimates tokens needed *before* you commit, with options to reduce scope if necessary.

**Goal:** Prevent catastrophic runaway. Not: achieve ±2% precision.

## How It Works

The skill produces a **two-part estimate** — because token cost has two distinct components that need to be sized separately:

**Output cost** — how much Claude will produce (5 tiers, 1.2K–36K tokens)  
**Context cost** — how much Claude must read or fetch before it can start (4 buckets, 0–30K tokens)

Add them together to get the session total. If the total is TIGHT or RISKY *and* the context cost is uncertain, the skill runs a lightweight **probe** (~1K tokens) to get a real scope reading before committing.

### Output Tiers

| Tier | Mid | When |
|------|-----|------|
| 1 — Micro | 1,200 | Short answer, quick email, one-liner |
| 2 — Standard | 3,700 | Short doc, snippet, summary, transform |
| 3 — Complex | 9,300 | Real feature, analysis, presentation, design |
| 4 — Project | 18,800 | Research synthesis, multi-file refactor, pipeline |
| 5 — Full Session | 36,000 | Complete app, full deployment, end-to-end project |

### Context Buckets

| Bucket | Mid | When |
|--------|-----|------|
| A — Provided | 0 | User supplies everything — paste, upload, clear brief |
| B — Light Fetch | 5,000 | Few lookups — 2–3 web pages, files, or API calls |
| C — Deep Research | 17,500 | Many sources (5–10+), full codebase, long corpus |
| D — Iterative/Unknown | 30,000 | Path unknown until Claude starts; open-ended exploration |

### Risk Thresholds

| Status | Token Range | Action |
|--------|-------------|--------|
| ✓ SAFE | < 30K | Proceed now |
| ⚠ TIGHT | 30–38K | Fits, but consider phasing or narrowing |
| ❌ RISKY | ≥ 38K | Scope down or phase — skill offers 3 options |

## Quick Start

### Installation (Claude.ai)

1. Download `skill/SKILL.md`
2. Go to **Settings > Customize > Skills**
3. Click **Add skill** / **Upload**
4. Select `SKILL.md`

### Installation (Claude Code / Git)

```bash
mkdir -p .claude/skills/token-estimator
cp skill/SKILL.md .claude/skills/token-estimator/
```

Skills auto-load from `.claude/skills/` at session start.

## Usage

Trigger with any of these phrases:

```
"Before you start, estimate: [task description]"
"Estimate tokens for: [task]"
"Token check before execution: [task]"
"Can this fit in one session: [task]"
```

### Example Outputs

**Simple task (Tier 2 + Bucket A):**
```
OUTPUT COST:  Tier 2 — ~3,700 tok  (short structured doc)
CONTEXT COST: Bucket A — ~0        (self-contained)
TOTAL:        ~3,700 tok (3,300–4,100)  🟢
RISK:         ✓ SAFE
MODEL:        Sonnet — structured writing, no deep reasoning needed
EXECUTION:    Proceed now
```

**Risky task with probe (Tier 3 + Bucket D):**
```
PROBE: 4,200 tickets found × ~500 tok = ~2.1M tok — not feasible at full scope

OUTPUT COST:  Tier 3 — ~9,300 tok
CONTEXT COST: Bucket D — exceeds session limit at full scope
TOTAL:        >> 44K
RISK:         ❌ RISKY

Option A: Sample 50 recent tickets       → ~25K tok ✓
Option B: Filter to one ticket category  → ~15K tok ✓
Option C: Export CSV, batch across 3–4 sessions

MODEL:        Sonnet — classification/theming
EXECUTION:    Do not proceed at full scope — pick an option above
```

## Testing & Validation

This skill was developed with a formal test harness. Results are published in this repo.

**Baseline (v1.0):** 35-case test suite, ground-truth token ranges  
- Hit rate: 48.6% | Mean error: +75.1% | RMSE: 152.4%  
- Root cause: anchor routing dead ends; no context cost modeling

**v1.1 improvements:** 5-tier output system calibrated from cluster analysis  
- RMSE improved to 51% in simulation

**v1.2 improvements:** Two-part estimate + context buckets + probe protocol  
- Targets hit rate ≥70%, mean error <±20% in live testing (in progress)

See [`LEARNINGS.md`](LEARNINGS.md) for full analysis. See [`tests/`](tests/) to run the harness yourself:

```bash
python3 tests/test_harness.py
```

## File Structure

```
token-estimator/
├── README.md
├── LEARNINGS.md                 # Test results analysis and methodology
├── LICENSE                      # Apache 2.0
├── skill/
│   ├── SKILL.md                 # Core skill definition (v1.2)
│   └── manifest.json
└── tests/
    ├── test_harness.py          # Python test harness
    ├── test_cases.json          # 35 ground-truth test cases
    └── results/
        └── run_001.json         # v1.0 baseline results
```

## Skill Specifications

| Property | Value |
|----------|-------|
| Version | 1.2 |
| Token cost (active) | ~4K tokens |
| Pro plan target | 44K / 5-hour window |
| Target accuracy | ±25% (prevent runaway, not perfection) |
| External dependencies | None for estimation; probe uses available tools |

## Contributing

The test harness makes contributions measurable. To propose a change:

1. Update `skill/SKILL.md`
2. Run `python3 tests/test_harness.py`
3. If hit rate improves, submit a PR with the new `results/` output

Common improvement areas: refine anchor mids from real usage data, improve bucket routing clarity, expand probe examples.

## License

Apache License 2.0 — see [LICENSE](LICENSE)

## Related Resources

- [Anthropic Skills Guide](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
- [Claude Documentation](https://docs.claude.com)

---

**Version 1.2** — Updated May 2026  
**Status:** Active — live prompt testing in progress
