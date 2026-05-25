# TokenEstimator

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Claude Pro](https://img.shields.io/badge/Claude-Pro-blueviolet.svg)](https://claude.ai)
![Version 1.0](https://img.shields.io/badge/Version-1.0-green.svg)

A decision-driven estimation framework to prevent token runaway in Claude sessions. Estimate task complexity **before execution** to stay within your 44K-token Pro plan window.

## Overview

**Problem:** You start a task in Claude and realize halfway through it's going to blow through your 5-hour session budget.

**Solution:** This skill estimates tokens needed *before* you commit, with option to reduce scope if necessary.

**Key:** Prevent catastrophic runaway, not achieve ±2% precision. ~15% variance is acceptable.

## Features

✓ **3-Decision Estimation Framework** — Classifies tasks by category, scope clarity, and dependencies  
✓ **Structured Output** — Token estimate with confidence level, risk classification, and phase breakdown  
✓ **Model Recommendations** — Suggests Opus/Sonnet/Haiku with token savings analysis  
✓ **Scope Reduction** — Offers 2-3 alternatives if estimate exceeds safe limits  
✓ **Pro Plan Optimized** — Built for 44K token / 5-hour window constraint  

## Quick Start

### Installation (Claude.ai)

1. **Download** this repo or just the `skill/SKILL.md` file
2. Go to **Settings > Customize > Skills**
3. Click **"Add skill"** / **"Upload"**
4. Select `SKILL.md`
5. Done — use the trigger phrases below

### Installation (Claude Code / Git)

```bash
# In your project repo
mkdir -p .claude/skills/token-estimator
cp skill/SKILL.md .claude/skills/token-estimator/

git add .claude/skills/
git commit -m "Add TokenEstimator skill"
```

Skills auto-load from `.claude/skills/` at session start.

## Usage

Trigger the skill with any of these phrases:

```
"Before you start, estimate: [task description]"
"Estimate tokens for: [task]"
"Token check before execution: [task]"
"Can this fit in one session: [task]"
```

## How It Works

### Example

**You:** "Before you start, estimate: research AI regulation across 5 countries, write 2K-word summary"

**Skill response:**
```
ESTIMATE: ~28K tokens (24-32K) | CONFIDENCE: 🟡 Medium ±15%

BREAKDOWN: Research 10K | Synthesis 12K | Writing 4K | Buffer 2K
TOTAL: 28K

RISK: ⚠ TIGHT (within window, limited buffer)

MODEL: Opus (exploration needs reasoning depth; Sonnet saves 20-25%)

EXECUTION: Doable one session; narrow research scope, plan 1 refinement pass
```

### Decision Framework

The skill asks 3 questions (if not obvious):

| Decision | Options | Profile |
|----------|---------|---------|
| **Task Category** | Data, Exploratory, Creation, Execution | Affects token profile |
| **Scope Definition** | CRISP, SEMI-DEFINED, FUZZY | Affects confidence level |
| **Dependencies** | Self-contained, Light, Heavy | Affects buffer size |

### Risk Thresholds

| Status | Token Range | Action |
|--------|-------------|--------|
| ✓ SAFE | < 30K | Execute now |
| ⚠ TIGHT | 30-38K | Fits, but consider phasing |
| ❌ RISKY | > 38K | Reduce scope or defer |

## Accuracy & Philosophy

- **Variance:** ±15% is normal and acceptable
- **Goal:** Prevent runaway (estimate 5K → actual 40K), not micro-optimize (estimate 25K → actual 28K ✓)
- **Trade-off:** Spend 1-2K tokens on estimation to save 30K+ on course correction

## File Structure

```
token-estimator/
├── README.md                    # This file
├── LICENSE                      # Apache 2.0
├── .gitignore
└── skill/
    ├── SKILL.md                 # Core skill definition (optimized for ~5K tokens)
    └── manifest.json            # Metadata & distribution info
```

## Skill Specifications

- **Name:** TokenEstimator
- **Version:** 1.0
- **Token Cost (idle):** ~100 tokens (metadata only)
- **Token Cost (active):** ~5K tokens (when loaded)
- **Pro Plan Target:** 44K tokens per 5-hour window
- **Accuracy:** ±15% variance
- **Dependencies:** None (pure estimation, no external calls)

## Sharing

### Share with a colleague (Pro Plan)
1. Download `skill/SKILL.md`
2. Send to colleague
3. They upload it to Settings > Customize > Skills

### Share with your team (GitHub)
Commit to your team's repo:
```
team-repo/
├── .claude/
│   └── skills/
│       └── token-estimator/
│           └── SKILL.md
```

### Publish to Anthropic Skills (Public)
- Fork this repo
- Customize as needed
- Submit PR to [anthropics/skills](https://github.com/anthropics/skills)

## Documentation

- **SKILL.md** — Complete skill definition with decision matrices, model selection table, estimation anchors, and pseudocode executive summary
- **manifest.json** — Metadata, use cases, and distribution info

## License

Apache License 2.0 — see [LICENSE](LICENSE) file

## Contributing

Improvements welcome! Common enhancements:
- Refine estimation anchors based on real usage data
- Add task-specific estimation models
- Expand model recommendations
- Improve decision matrix clarity

## Support & Feedback

This skill was designed for **preventing token runaway, not achieving perfect accuracy**. If you:
- Find estimation consistently off by >20%, report it
- Have ideas for decision points, suggest them
- Want to customize for specific task types, fork it

## Related Resources

- [Anthropic Skills Guide](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
- [Claude Documentation](https://docs.claude.com)
- [Claude Skills Repository](https://github.com/anthropics/skills)

---

**Version 1.0** — Created May 2026  
**Status:** Active & maintained  
**Use Case:** Token budget management for Cowork and Claude.ai users
