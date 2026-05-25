# Contributing Test Results

Thanks for helping validate the TokenEstimator skill. This guide covers how to run a test case and submit your results.

## What you're testing

The skill estimates token usage *before* a task runs, so Claude can warn you if a task will blow your session budget. You'll run a prompt through the skill, then actually execute it, record both outcomes, and submit the results.

## Prerequisites

- Python 3.9+
- A Claude account (Pro or API access)
- The Anthropic Python SDK if you want automated token counting: `pip install anthropic`

## Step-by-step

### 1. Pick a test case

Browse `tests/test_cases_v2.json` and pick a case. Good starting points:

| Want to... | Start with |
|---|---|
| Verify no false positives | TC-N01, TC-N02, TC-N03 |
| Test an obvious trap | TC-EO01, TC-RO01, TC-FO01, TC-IO01 |
| Test a deceptive trap (expensive!) | TC-ED01, TC-RD01, TC-FD01, TC-ID01 |

> ⚠️ **Deceptive cases** (TC-ED\*, TC-RD\*, TC-FD\*, TC-ID\*) are designed to be expensive. TC-ED01 in particular (the Gmail case) may not complete at all if your inbox is large — that's the point. Run these intentionally.

### 2. Generate a results template

```bash
python3 tests/test_harness_v2.py --template TC-N01 --runs 3
# → writes tests/results/TC-N01_template.json
```

### 3. Run the test in Claude

For each run slot in the template:

1. **Open a fresh Claude session**
2. **Run the skill estimate first:** Paste the test case prompt and ask Claude to estimate the token cost using the TokenEstimator skill
3. **Then execute the task** in the same session
4. **Record the results** in the template JSON

Key fields to fill:
- `contributor_id` — your GitHub username
- `model_used` — e.g. `claude-sonnet-4-6`
- `skill_version` — use `1.3` unless you're testing a newer version
- `skill_tier`, `skill_bucket`, `skill_estimate_point/low/high`, `skill_risk` — from the skill's output
- `skill_identified_traps` — list of trap names the skill named, e.g. `["enumeration"]`
- `skill_probe_fired` — true/false
- `actual_tokens`, `actual_input_tokens`, `actual_output_tokens` — from the API response or Claude's token counter
- `path_accuracy_score` — your judgment: 0 (wrong), 1 (partial), 2 (correct)
- `option_quality_score` — for RISKY cases only: 0 (poor), 1 (partial), 2 (good)

### 4. Submit your results

```bash
# Dry run first to validate
python3 tests/test_harness_v2.py --submit tests/results/TC-N01_results.json --dry-run

# When it looks good, submit for real
python3 tests/test_harness_v2.py --submit tests/results/TC-N01_results.json
```

This appends your runs to `tests/results/community_results.jsonl`.

### 5. Regenerate the dashboard

```bash
python3 tests/test_harness_v2.py --dashboard
# → open tests/dashboard.html in your browser
```

### 6. Open a PR

Include:
- Your filled-in result file in `tests/results/contributors/<your-username>/`
- The updated `tests/results/community_results.jsonl`
- The regenerated `tests/dashboard.html`

---

## Scoring rubrics

**`path_accuracy_score`** — Did the skill correctly describe what Claude would actually do?
- `0` — Path description missing, wrong, or misses the expensive step entirely
- `1` — Path described but expensive step named vaguely or incompletely
- `2` — Execution path correct AND expensive step explicitly identified

**`option_quality_score`** — For RISKY cases: were the scope reduction options useful?
- `0` — Options missing, generic ("try a smaller scope"), or no token estimates
- `1` — Options present and specific but missing token estimates
- `2` — Options concrete, specific, with token estimates for each

---

## Bring your own prompts

You don't have to use the 27 provided test cases. If you have a prompt that burned your session budget and you want to see if the skill would have caught it, run it through the skill and submit the results. Use `TC-CUSTOM-NN` as the `tc_id` and include the prompt text in your `notes` field.

Community-contributed prompts that reveal new failure modes may be incorporated into future versions of `test_cases_v2.json`.

---

## Questions?

Open an issue on [GitHub](https://github.com/jdonelson04/token-estimator/issues).
