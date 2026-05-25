#!/usr/bin/env python3
"""
TokenEstimator Skill v1.3 — Test Harness v2
=============================================
Scores LIVE test results (real Claude executions) across four dimensions:
  1. Estimate accuracy   — did actual token cost fall within the stated band?
  2. Trap identification — did the skill correctly name the trap type(s)?
  3. Path accuracy       — did the skill correctly describe the execution path? [human]
  4. Option quality      — if RISKY, were the scope reduction options actionable? [human]

This is NOT a simulator. The v1.3 skill reasons about execution paths —
that logic cannot be replicated in Python. All scoring happens after real runs.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTENDED WORKFLOW — run cases individually, aggregate over time
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  You do NOT run all 27 prompts at once. Some cases (especially deceptive
  enumeration/iteration) are designed to be expensive — that's the point.
  Pick cases based on what you want to learn:

    Start cheap  → run control cases (TC-N01–N03) to verify no false positives
    Test a trap  → pick one deceptive case (e.g. TC-ED01) and run it fully
    Go wide      → run 1 rep of each cell to get coverage before depth

  Each case produces its own result file. Use --submit to add runs to the
  shared community_results.jsonl, then --dashboard to regenerate the charts.

  Step 1: Generate a blank results template for the case you want to run
            python3 test_harness_v2.py --template TC-ED01 --runs 5

  Step 2: Run the prompt in Claude (skill estimate first, task executes second).
          Fill in the result fields in the generated JSON template.

  Step 3: Submit your completed results to the community file
            python3 test_harness_v2.py --submit tests/results/TC-ED01_results.json

  Step 4: Regenerate the dashboard
            python3 test_harness_v2.py --dashboard

  Step 5: Repeat for other cases. To see all results at once:
            python3 test_harness_v2.py --aggregate tests/results/ --report

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST MATRIX — v1.3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Primary axis:   Trap type         (what makes the task expensive)
Secondary axis: Surface deception (whether the expense is obvious from the prompt)

                  OBVIOUS                    DECEPTIVE
                  (trap visible in prompt)   (looks cheap, is expensive)
  ──────────────┬──────────────────────────┬──────────────────────────
  No trap       │ TC-N01–N03  — control    │ n/a
  Enumeration   │ TC-EO01–03  — bounded    │ TC-ED01–03  — unbounded ★
  Reasoning     │ TC-RO01–03  — openly hard│ TC-RD01–03  — tiny output ★
  Fetch         │ TC-FO01–03  — count given│ TC-FD01–03  — 1 Q, many src ★
  Iteration     │ TC-IO01–03  — no stop    │ TC-ID01–03  — hidden cycles ★
  ──────────────┴──────────────────────────┴──────────────────────────
  ★ = primary stress test for execution-path reasoning
      These cases are the most token-expensive. Run deliberately.

  9 cells · 27 prompts · up to 5 runs each · up to 135 total executions
  (135 is a ceiling, not a target — partial coverage is valid and useful)

Why this matrix (vs. old Tier × Bucket grid):
  The old matrix tested cost accounting accuracy — did the estimate math
  match reality? The new matrix tests reasoning accuracy — did the skill
  correctly identify WHY a task is expensive, especially when the prompt
  doesn't make it obvious? The "deceptive" column is the key innovation.
  A skill that only catches obvious traps is not useful in practice.

Expected outcomes by cell:
  No trap / obvious:         SAFE, no traps flagged (false positive test)
  Enumeration / obvious:     TIGHT, enumeration trap, probe may fire
  Enumeration / deceptive:   RISKY, enumeration trap, probe fires ⚡
  Reasoning / obvious:       TIGHT-RISKY, reasoning trap flagged
  Reasoning / deceptive:     SAFE* (output constrained) BUT trap still named
  Fetch / obvious:           RISKY, fetch trap, source count quantified
  Fetch / deceptive:         TIGHT, fetch trap (skill must infer sources)
  Iteration / obvious:       RISKY, iteration trap, probe fires ⚡
  Iteration / deceptive:     TIGHT, iteration trap (skill must infer cycles)

  * Reasoning/deceptive is the trickiest cell: correct answer is SAFE on
    token cost (output is small) but TRAP IDENTIFIED must still be correct.
    Estimate accuracy and trap identification can diverge here.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
METHODOLOGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Temperature:    Default Claude platform settings (not temperature=0).
                  Reflects real-world conditions; variance is expected and
                  part of what we're measuring.
  Protocol:       Same-session — skill estimate runs first, task executes
                  second in the same session.
  Lurking var:    Estimate-priming effect (Token-Budget-Aware LLM Reasoning,
                  ACL 2025) is documented but not controlled in this phase.
                  A future split test (same-session vs cold-execute) can
                  quantify the effect if it matters.
  n per prompt:   Up to 5 runs recommended. Below frequentist significance
                  threshold (n>30) — treat as directional evidence.
                  Variance prior from CASTILLO et al. (2025): LLM response
                  length shows significant intra-model variability even
                  under fixed decoding parameters.
  Ground truth:   Fully executed — no curated ranges. Token cost measured
                  via Anthropic token counting API per run.
  Human scoring:  path_accuracy and option_quality require human judgment.
                  Fill these fields after reviewing each skill output.

Scoring rubric — path_accuracy_score:
  0 = path description missing, wrong, or misses the expensive step entirely
  1 = path described but expensive step named vaguely or incompletely
  2 = execution path correct AND expensive step explicitly identified

Scoring rubric — option_quality_score (RISKY cases only):
  0 = options missing, generic ("try a smaller scope"), or no token estimates
  1 = options present and specific but missing token estimates
  2 = options concrete, specific, with token estimates for each

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import math
import argparse
from datetime import datetime
from pathlib import Path

DEFAULT_CASES     = "tests/test_cases_v2.json"
DEFAULT_COMMUNITY = "tests/results/community_results.jsonl"
DEFAULT_DASHBOARD = "tests/dashboard.html"


# ─────────────────────────────────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────────────────────────────────

def score_estimate_accuracy(result: dict) -> dict:
    actual    = result.get("actual_tokens")
    est_low   = result.get("skill_estimate_low")
    est_high  = result.get("skill_estimate_high")
    est_point = result.get("skill_estimate_point")

    if actual is None or est_low is None or est_high is None:
        return {"scored": False, "reason": "missing token data"}

    hit       = est_low <= actual <= est_high
    error_pct = round((est_point - actual) / actual * 100, 1) if est_point else None

    return {
        "scored":    True,
        "hit":       hit,
        "error_pct": error_pct,
        "direction": "over" if error_pct and error_pct > 0 else "under"
    }


def score_trap_identification(result: dict, expected_trap: str) -> dict:
    identified = result.get("skill_identified_traps", [])

    if expected_trap == "none":
        correct        = len(identified) == 0
        false_positive = len(identified) > 0
        return {
            "scored":         True,
            "correct":        correct,
            "false_positive": false_positive,
            "expected":       "none",
            "identified":     identified
        }
    else:
        correct = expected_trap in identified
        return {
            "scored":     True,
            "correct":    correct,
            "missed":     not correct,
            "expected":   expected_trap,
            "identified": identified
        }


def score_path_accuracy(result: dict) -> dict:
    score = result.get("path_accuracy_score")
    if score is None:
        return {"scored": False, "reason": "awaiting human scoring"}
    return {
        "scored": True,
        "score":  score,
        "label":  {0: "incorrect", 1: "partial", 2: "correct"}.get(score, "unknown")
    }


def score_option_quality(result: dict, expected_risk: str) -> dict:
    if expected_risk != "RISKY":
        return {"scored": False, "reason": "not applicable"}
    score = result.get("option_quality_score")
    if score is None:
        return {"scored": False, "reason": "awaiting human scoring"}
    return {
        "scored": True,
        "score":  score,
        "label":  {0: "poor", 1: "partial", 2: "good"}.get(score, "unknown")
    }


def score_run(run: dict, test_case: dict) -> dict:
    return {
        "run_id":              run["run_id"],
        "tc_id":               test_case["id"],
        "estimate_accuracy":   score_estimate_accuracy(run),
        "trap_identification": score_trap_identification(run, test_case["trap_type"]),
        "path_accuracy":       score_path_accuracy(run),
        "option_quality":      score_option_quality(run, test_case["expected_risk"]),
    }


def score_all(results_data: dict, cases_data: dict) -> dict:
    cases_by_id = {tc["id"]: tc for tc in cases_data["test_cases"]}
    scored_runs = []

    for run in results_data["runs"]:
        tc = cases_by_id.get(run["tc_id"])
        if tc:
            scored_runs.append(score_run(run, tc))

    n = len(scored_runs)
    if n == 0:
        return {"scored_at": datetime.utcnow().isoformat()+"Z", "n": 0, "summary": {}, "runs": []}

    estimate_hits = [r for r in scored_runs if r["estimate_accuracy"].get("hit")]
    trap_correct  = [r for r in scored_runs if r["trap_identification"].get("correct")]
    false_pos     = [r for r in scored_runs if r["trap_identification"].get("false_positive")]
    errors        = [r["estimate_accuracy"]["error_pct"]
                     for r in scored_runs
                     if r["estimate_accuracy"].get("error_pct") is not None]
    path_scores   = [r["path_accuracy"]["score"]
                     for r in scored_runs if r["path_accuracy"].get("scored")]
    option_scores = [r["option_quality"]["score"]
                     for r in scored_runs if r["option_quality"].get("scored")]

    mean_err = round(sum(errors)/len(errors), 1)                                    if errors else None
    rmse     = round(math.sqrt(sum(e**2 for e in errors)/len(errors)), 1)           if errors else None

    return {
        "scored_at":     datetime.utcnow().isoformat() + "Z",
        "skill_version": results_data.get("skill_version", "1.3"),
        "n":             n,
        "summary": {
            "estimate_hit_rate_pct":   round(len(estimate_hits)/n*100, 1),
            "trap_correct_rate_pct":   round(len(trap_correct)/n*100,  1),
            "false_positive_rate_pct": round(len(false_pos)/n*100,     1),
            "mean_error_pct":          mean_err,
            "rmse_pct":                rmse,
            "mean_path_accuracy":      round(sum(path_scores)/len(path_scores), 2)   if path_scores   else None,
            "mean_option_quality":     round(sum(option_scores)/len(option_scores),2) if option_scores else None,
        },
        "runs": scored_runs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Aggregate scoring (across multiple result files)
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_results(results_dir: Path, cases_data: dict) -> dict:
    """
    Load all *_results.json files in results_dir, score each one, and
    combine into a single report broken out by cell and trap type.
    Skips template files (*_template.json) and already-scored files (*.scored.json).
    """
    result_files = sorted(
        f for f in results_dir.glob("*.json")
        if not f.name.endswith("_template.json")
        and not f.name.endswith(".scored.json")
    )

    if not result_files:
        return {"error": f"No result files found in {results_dir}"}

    cases_by_id = {tc["id"]: tc for tc in cases_data["test_cases"]}
    all_runs    = []

    for fpath in result_files:
        with open(fpath) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        for run in data.get("runs", []):
            tc = cases_by_id.get(run.get("tc_id"))
            if tc:
                scored = score_run(run, tc)
                scored["_cell"]      = tc.get("cell", "unknown")
                scored["_trap_type"] = tc.get("trap_type", "unknown")
                scored["_deceptive"] = tc.get("surface_deceptive", False)
                all_runs.append(scored)

    n = len(all_runs)
    if n == 0:
        return {"error": "No scoreable runs found in result files"}

    def summarize(runs):
        hits    = [r for r in runs if r["estimate_accuracy"].get("hit")]
        correct = [r for r in runs if r["trap_identification"].get("correct")]
        fp      = [r for r in runs if r["trap_identification"].get("false_positive")]
        errors  = [r["estimate_accuracy"]["error_pct"]
                   for r in runs if r["estimate_accuracy"].get("error_pct") is not None]
        path_s  = [r["path_accuracy"]["score"]
                   for r in runs if r["path_accuracy"].get("scored")]
        opt_s   = [r["option_quality"]["score"]
                   for r in runs if r["option_quality"].get("scored")]
        return {
            "n":                      len(runs),
            "estimate_hit_rate_pct":  round(len(hits)/len(runs)*100, 1),
            "trap_correct_rate_pct":  round(len(correct)/len(runs)*100, 1),
            "false_positive_rate_pct":round(len(fp)/len(runs)*100, 1),
            "mean_error_pct":         round(sum(errors)/len(errors), 1)      if errors  else None,
            "rmse_pct":               round(math.sqrt(sum(e**2 for e in errors)/len(errors)), 1) if errors else None,
            "mean_path_accuracy":     round(sum(path_s)/len(path_s), 2)      if path_s  else None,
            "mean_option_quality":    round(sum(opt_s)/len(opt_s), 2)        if opt_s   else None,
        }

    overall  = summarize(all_runs)
    cells    = {}
    for run in all_runs:
        cells.setdefault(run["_cell"], []).append(run)
    by_cell  = {cell: summarize(runs) for cell, runs in sorted(cells.items())}

    obvious   = [r for r in all_runs if not r["_deceptive"]]
    deceptive = [r for r in all_runs if r["_deceptive"]]

    return {
        "aggregated_at":   datetime.utcnow().isoformat() + "Z",
        "files_loaded":    [f.name for f in result_files],
        "total_runs":      n,
        "overall":         overall,
        "by_cell":         by_cell,
        "deception_split": {
            "obvious":   summarize(obvious)   if obvious   else None,
            "deceptive": summarize(deceptive) if deceptive else None,
        },
    }


def print_aggregate_report(agg: dict):
    if "error" in agg:
        print(f"\nError: {agg['error']}"); return

    print("\n" + "="*62)
    print("  TokenEstimator v1.3 — Aggregate Test Report")
    print(f"  Aggregated: {agg['aggregated_at']}")
    print(f"  Files: {len(agg['files_loaded'])}  |  Total runs: {agg['total_runs']}")
    print("="*62)

    def fmt_row(label, s):
        err = s.get("mean_error_pct")
        pa  = s.get("mean_path_accuracy")
        return (
            f"  {label:<30}"
            f"  n={s['n']:<4}"
            f"  hit={s['estimate_hit_rate_pct']:>5.1f}%"
            f"  trap={s['trap_correct_rate_pct']:>5.1f}%"
            f"  err={f'{err:+.0f}%' if err is not None else '—':>5}"
            f"  path={f'{pa:.1f}' if pa is not None else '—':>4}"
        )

    print(fmt_row("OVERALL", agg["overall"]))
    print("\n── By cell ──────────────────────────────────────────────")
    for cell, cs in agg["by_cell"].items():
        print(fmt_row(cell, cs))
    print("\n── Obvious vs Deceptive ─────────────────────────────────")
    ds = agg["deception_split"]
    if ds.get("obvious"):
        print(fmt_row("obvious (trap visible)", ds["obvious"]))
    if ds.get("deceptive"):
        print(fmt_row("deceptive (surface hides trap)", ds["deceptive"]))
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Submit — validate + append runs to community_results.jsonl
# ─────────────────────────────────────────────────────────────────────────────

SUBMIT_REQUIRED_FIELDS = [
    "tc_id", "run_number", "contributor_id", "skill_version", "model_used",
    "skill_identified_traps", "skill_risk",
]


def validate_for_submit(run: dict) -> list:
    errors = []
    for field in SUBMIT_REQUIRED_FIELDS:
        val = run.get(field)
        if val is None or val == "" or val == []:
            errors.append(f"missing or empty: {field}")
    return errors


def flatten_run_for_community(run: dict, tc: dict, scored: dict) -> dict:
    """Flatten a run + its scores into a single JSONL record."""
    ea = scored.get("estimate_accuracy", {})
    ti = scored.get("trap_identification", {})
    return {
        # Identity
        "run_id":               run.get("run_id"),
        "tc_id":                run.get("tc_id"),
        "cell":                 tc.get("cell"),
        "trap_type":            tc.get("trap_type"),
        "surface_deceptive":    tc.get("surface_deceptive"),
        # Contributor
        "contributor_id":       run.get("contributor_id"),
        "skill_version":        run.get("skill_version"),
        "model_used":           run.get("model_used"),
        "session_type":         run.get("session_type"),
        "run_date":             run.get("run_date"),
        # Skill output
        "skill_tier":           run.get("skill_tier"),
        "skill_bucket":         run.get("skill_bucket"),
        "skill_estimate_point": run.get("skill_estimate_point"),
        "skill_estimate_low":   run.get("skill_estimate_low"),
        "skill_estimate_high":  run.get("skill_estimate_high"),
        "skill_risk":           run.get("skill_risk"),
        "skill_identified_traps": run.get("skill_identified_traps", []),
        "skill_probe_fired":    run.get("skill_probe_fired"),
        # Actual cost
        "actual_tokens":        run.get("actual_tokens"),
        "actual_input_tokens":  run.get("actual_input_tokens"),
        "actual_output_tokens": run.get("actual_output_tokens"),
        # Human scores
        "path_accuracy_score":  run.get("path_accuracy_score"),
        "option_quality_score": run.get("option_quality_score"),
        # Derived scores (computed here so dashboard doesn't re-score)
        "estimate_hit":         ea.get("hit"),
        "trap_correct":         ti.get("correct"),
        "false_positive":       ti.get("false_positive", False),
        "error_pct":            ea.get("error_pct"),
    }


def submit_results(results_path: Path, community_path: Path, cases_data: dict, dry_run: bool = False):
    with open(results_path) as f:
        results_data = json.load(f)

    cases_by_id = {tc["id"]: tc for tc in cases_data["test_cases"]}
    runs        = results_data.get("runs", [])

    errors_by_run = {}
    valid_runs    = []
    for run in runs:
        errs = validate_for_submit(run)
        if errs:
            errors_by_run[run.get("run_id", "?")] = errs
        else:
            valid_runs.append(run)

    if errors_by_run:
        print(f"\n⚠  Validation errors — these runs will NOT be submitted:")
        for run_id, errs in errors_by_run.items():
            for e in errs:
                print(f"   {run_id}: {e}")
        if not valid_runs:
            print("No valid runs to submit."); return

    records = []
    for run in valid_runs:
        tc = cases_by_id.get(run.get("tc_id"))
        if not tc:
            print(f"  Warning: tc_id '{run.get('tc_id')}' not found in cases file, skipping")
            continue
        scored = score_run(run, tc)
        records.append(flatten_run_for_community(run, tc, scored))

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Submitting {len(records)} run(s) from {results_path.name}")
    print(f"  → {community_path}")
    print()
    for r in records:
        hit  = "✓" if r.get("estimate_hit") else ("✗" if r.get("actual_tokens") else "—")
        trap = "✓" if r.get("trap_correct") else ("FP" if r.get("false_positive") else "✗")
        print(f"  {r['run_id']:<18}  est={hit}  trap={trap}  contributor={r['contributor_id']}  model={r['model_used']}")

    if not dry_run:
        community_path.parent.mkdir(parents=True, exist_ok=True)
        with open(community_path, "a") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        print(f"\n✓  {len(records)} run(s) appended to {community_path}")
        print("   Run --dashboard to regenerate the results dashboard.")
    else:
        print("\n(dry run — nothing written)")


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard — compute metrics + generate self-contained HTML
# ─────────────────────────────────────────────────────────────────────────────

def _summarize_flat(records: list) -> dict:
    """Summarize a list of flat community_results.jsonl records."""
    n = len(records)
    if n == 0:
        return None
    hits    = [r for r in records if r.get("estimate_hit") is True]
    correct = [r for r in records if r.get("trap_correct") is True]
    fp      = [r for r in records if r.get("false_positive") is True]
    errors  = [r["error_pct"] for r in records if r.get("error_pct") is not None]
    path_s  = [r["path_accuracy_score"]  for r in records if r.get("path_accuracy_score")  is not None]
    opt_s   = [r["option_quality_score"] for r in records if r.get("option_quality_score") is not None]
    return {
        "n":                      n,
        "estimate_hit_rate_pct":   round(len(hits)/n*100, 1),
        "trap_correct_rate_pct":   round(len(correct)/n*100, 1),
        "false_positive_rate_pct": round(len(fp)/n*100, 1),
        "mean_error_pct":          round(sum(errors)/len(errors), 1) if errors else None,
        "rmse_pct":                round(math.sqrt(sum(e**2 for e in errors)/len(errors)), 1) if errors else None,
        "mean_path_accuracy":      round(sum(path_s)/len(path_s), 2) if path_s else None,
        "mean_option_quality":     round(sum(opt_s)/len(opt_s), 2)   if opt_s  else None,
    }


def compute_dashboard_data(community_path: Path) -> dict:
    if not community_path.exists() or community_path.stat().st_size == 0:
        return {"empty": True, "runs": [], "total_runs": 0}

    runs = []
    with open(community_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    runs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    if not runs:
        return {"empty": True, "runs": [], "total_runs": 0}

    TRAP_TYPES = ["enumeration", "reasoning", "fetch", "iteration"]

    # By trap type: obvious vs deceptive
    by_trap_type = {}
    for tt in TRAP_TYPES:
        obvious_recs   = [r for r in runs if r.get("trap_type") == tt and not r.get("surface_deceptive")]
        deceptive_recs = [r for r in runs if r.get("trap_type") == tt and r.get("surface_deceptive")]
        by_trap_type[tt] = {
            "obvious":   _summarize_flat(obvious_recs),
            "deceptive": _summarize_flat(deceptive_recs),
        }

    # By cell
    cells = {}
    for r in runs:
        cells.setdefault(r.get("cell", "unknown"), []).append(r)
    by_cell = {cell: _summarize_flat(recs) for cell, recs in sorted(cells.items())}

    # By skill version
    versions = {}
    for r in runs:
        versions.setdefault(r.get("skill_version", "unknown"), []).append(r)
    by_version = {v: _summarize_flat(recs) for v, recs in sorted(versions.items())}

    # Obvious vs deceptive
    obvious_all   = [r for r in runs if not r.get("surface_deceptive")]
    deceptive_all = [r for r in runs if r.get("surface_deceptive")]

    return {
        "empty":           False,
        "generated_at":    datetime.utcnow().isoformat() + "Z",
        "total_runs":      len(runs),
        "contributors":    sorted(set(r.get("contributor_id", "?") for r in runs)),
        "skill_versions":  sorted(set(r.get("skill_version", "?")  for r in runs)),
        "overall":         _summarize_flat(runs),
        "by_trap_type":    by_trap_type,
        "by_cell":         by_cell,
        "by_version":      by_version,
        "deception_split": {
            "obvious":   _summarize_flat(obvious_all),
            "deceptive": _summarize_flat(deceptive_all),
        },
        "runs": runs,
    }


# The HTML template — __DATA__ is replaced with JSON at generation time.
_DASHBOARD_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TokenEstimator — Community Results</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
  <style>
    :root {
      --bg: #0f1117; --surface: #1a1d27; --surface2: #222638;
      --border: #2d3148; --text: #e2e8f0; --muted: #94a3b8;
      --accent: #6366f1; --green: #22c55e; --red: #ef4444; --yellow: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; padding: 2rem; max-width: 1200px; margin: 0 auto; }
    a { color: var(--accent); text-decoration: none; }
    code { font-family: monospace; background: var(--surface2); padding: 0.1em 0.35em; border-radius: 3px; font-size: 0.85em; }

    .header { margin-bottom: 2rem; }
    .header h1 { font-size: 1.5rem; font-weight: 700; }
    .header .subtitle { color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem; }

    .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
    .metric-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; }
    .metric-label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }
    .metric-value { font-size: 1.9rem; font-weight: 700; line-height: 1.2; margin: 0.3rem 0 0.15rem; }
    .metric-sub { font-size: 0.75rem; color: var(--muted); }

    .charts-row { display: grid; grid-template-columns: 3fr 2fr; gap: 1.5rem; margin-bottom: 2rem; }
    @media (max-width: 820px) { .charts-row { grid-template-columns: 1fr; } }
    .chart-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; }
    .chart-title { font-size: 0.72rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 1rem; }
    .chart-note  { font-size: 0.72rem; color: var(--muted); margin-top: 0.75rem; }

    .section-title { font-size: 0.95rem; font-weight: 600; margin: 2rem 0 0.75rem; }
    .table-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; margin-bottom: 2rem; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    th { text-align: left; padding: 0.55rem 0.85rem; background: var(--surface2); color: var(--muted); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border); white-space: nowrap; }
    td { padding: 0.5rem 0.85rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: var(--surface2); }

    .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .g { background: rgba(34,197,94,.15);  color: var(--green);  }
    .r { background: rgba(239,68,68,.15);  color: var(--red);    }
    .y { background: rgba(245,158,11,.15); color: var(--yellow); }
    .gr{ background: rgba(148,163,184,.1); color: var(--muted);  }

    .deception-split { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 2rem; }
    .split-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; }
    .split-label { font-size: 0.72rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.75rem; }
    .split-stat  { display: flex; justify-content: space-between; padding: 0.2rem 0; font-size: 0.82rem; }
    .split-stat span:last-child { font-weight: 600; }

    .empty-state { text-align: center; padding: 4rem 2rem; color: var(--muted); }
    .empty-state h2 { font-size: 1.2rem; color: var(--text); margin-bottom: 0.5rem; }
    .empty-state p  { margin-top: 0.5rem; line-height: 1.6; }

    footer { margin-top: 2rem; color: var(--muted); font-size: 0.75rem; border-top: 1px solid var(--border); padding-top: 1rem; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }
  </style>
</head>
<body>
  <div class="header">
    <h1>TokenEstimator — Community Results</h1>
    <div class="subtitle" id="subtitle">Loading…</div>
  </div>
  <div id="app"></div>
  <footer>
    <span>Generated by <code>test_harness_v2.py --dashboard</code></span>
    <a href="https://github.com/jdonelson04/token-estimator">github.com/jdonelson04/token-estimator</a>
  </footer>

  <script>
const DATA = __DATA__;

(function () {
  const app = document.getElementById('app');
  const sub = document.getElementById('subtitle');

  // ── Empty state ────────────────────────────────────────────────────────────
  if (DATA.empty) {
    sub.textContent = 'No results submitted yet.';
    app.innerHTML = `<div class="empty-state">
      <h2>No results yet</h2>
      <p>Run a test case and submit it:</p>
      <p style="margin-top:1rem">
        <code>python3 test_harness_v2.py --template TC-N01 --runs 3</code><br><br>
        <code>python3 test_harness_v2.py --submit tests/results/TC-N01_results.json</code><br><br>
        <code>python3 test_harness_v2.py --dashboard</code>
      </p>
    </div>`;
    return;
  }

  const o = DATA.overall;
  sub.textContent = `${DATA.total_runs} run${DATA.total_runs !== 1 ? 's' : ''} · ${DATA.contributors.length} contributor${DATA.contributors.length !== 1 ? 's' : ''} · skill versions: ${DATA.skill_versions.join(', ')} · generated ${DATA.generated_at.slice(0,10)}`;

  // ── Helpers ────────────────────────────────────────────────────────────────
  function pct(v) { return v !== null && v !== undefined ? v + '%' : '—'; }
  function err(v) { return v !== null && v !== undefined ? (v > 0 ? '+' : '') + v + '%' : '—'; }
  function path(v){ return v !== null && v !== undefined ? v + '/2' : '—'; }
  function trapColor(v) {
    if (v === null || v === undefined) return 'var(--muted)';
    return v >= 70 ? 'var(--green)' : v >= 45 ? 'var(--yellow)' : 'var(--red)';
  }
  function badge(hit, fp) {
    if (hit === true)  return '<span class="badge g">✓</span>';
    if (fp)            return '<span class="badge y">FP</span>';
    if (hit === false) return '<span class="badge r">✗</span>';
    return '<span class="badge gr">—</span>';
  }

  // ── Metric cards ───────────────────────────────────────────────────────────
  function card(label, value, sub, color) {
    return `<div class="metric-card">
      <div class="metric-label">${label}</div>
      <div class="metric-value" style="color:${color || 'var(--text)'}">${value}</div>
      ${sub ? `<div class="metric-sub">${sub}</div>` : ''}
    </div>`;
  }

  const errVal = o.mean_error_pct;
  const errColor = errVal === null ? 'var(--muted)' : Math.abs(errVal) <= 20 ? 'var(--green)' : errVal > 0 ? 'var(--red)' : 'var(--yellow)';

  app.innerHTML = `
    <div class="metrics-grid">
      ${card('Trap ID Rate',       pct(o.trap_correct_rate_pct),   `${o.n} total runs`,       trapColor(o.trap_correct_rate_pct))}
      ${card('Estimate Hit Rate',  pct(o.estimate_hit_rate_pct),   'actual tokens in band',   null)}
      ${card('False Positive Rate',pct(o.false_positive_rate_pct), 'no-trap cases flagged',   o.false_positive_rate_pct > 10 ? 'var(--red)' : 'var(--green)')}
      ${card('Mean Error',         err(o.mean_error_pct),          'estimate bias',           errColor)}
      ${card('Path Accuracy',      path(o.mean_path_accuracy),     'human-scored, 0–2',       null)}
      ${card('Contributors',       DATA.contributors.length,       DATA.contributors.join(', ') || '—', null)}
    </div>

    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title">Trap Identification Rate — Obvious vs. Deceptive</div>
        <canvas id="trapChart" height="200"></canvas>
        <div class="chart-note">★ The deceptive column is the primary test of execution-path reasoning. A skill that only catches obvious traps isn't useful.</div>
      </div>
      <div class="chart-card">
        <div class="chart-title">Key Metrics by Skill Version</div>
        <canvas id="versionChart" height="200"></canvas>
        <div class="chart-note">Each point = all runs on that skill version. See if new versions move the needle.</div>
      </div>
    </div>

    <div class="section-title">Obvious vs. Deceptive — Head to Head</div>
    <div class="deception-split" id="deceptionSplit"></div>

    <div class="section-title">Per-Cell Breakdown</div>
    <div class="table-card"><table>
      <thead><tr>
        <th>Cell</th><th>n</th><th>Trap ID %</th><th>Est Hit %</th><th>Mean Err %</th><th>RMSE %</th><th>Path Acc</th>
      </tr></thead>
      <tbody id="cellTbody"></tbody>
    </table></div>

    <div class="section-title">All Runs</div>
    <div class="table-card"><table>
      <thead><tr>
        <th>Run ID</th><th>TC</th><th>Cell</th><th>Contributor</th><th>Skill v</th><th>Model</th><th>Est?</th><th>Trap?</th><th>Err %</th><th>Path</th>
      </tr></thead>
      <tbody id="runsTbody"></tbody>
    </table></div>
  `;

  // ── Trap chart ─────────────────────────────────────────────────────────────
  const TRAP_TYPES  = ['enumeration', 'reasoning', 'fetch', 'iteration'];
  const TRAP_LABELS = ['Enumeration', 'Reasoning', 'Fetch', 'Iteration'];
  const obviousRates   = TRAP_TYPES.map(t => DATA.by_trap_type[t]?.obvious?.trap_correct_rate_pct   ?? null);
  const deceptiveRates = TRAP_TYPES.map(t => DATA.by_trap_type[t]?.deceptive?.trap_correct_rate_pct ?? null);

  new Chart(document.getElementById('trapChart'), {
    type: 'bar',
    data: {
      labels: TRAP_LABELS,
      datasets: [
        { label: 'Obvious',   data: obviousRates,   backgroundColor: 'rgba(99,102,241,0.75)', borderRadius: 4 },
        { label: 'Deceptive ★', data: deceptiveRates, backgroundColor: 'rgba(239,68,68,0.65)', borderRadius: 4 },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        y: { min: 0, max: 100, ticks: { callback: v => v + '%', color: '#94a3b8' }, grid: { color: '#2d3148' } },
        x: { ticks: { color: '#94a3b8' }, grid: { color: 'transparent' } }
      },
      plugins: { legend: { labels: { color: '#e2e8f0', boxRadius: 4 } } }
    }
  });

  // ── Version trend chart ────────────────────────────────────────────────────
  const versions = Object.keys(DATA.by_version).sort();
  new Chart(document.getElementById('versionChart'), {
    type: 'line',
    data: {
      labels: versions.map(v => 'v' + v),
      datasets: [
        { label: 'Trap ID %', data: versions.map(v => DATA.by_version[v]?.trap_correct_rate_pct),  borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,.15)', fill: true,  tension: 0.3, pointRadius: 5 },
        { label: 'Est Hit %', data: versions.map(v => DATA.by_version[v]?.estimate_hit_rate_pct),  borderColor: '#22c55e', backgroundColor: 'transparent',             fill: false, tension: 0.3, pointRadius: 5 },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        y: { min: 0, max: 100, ticks: { callback: v => v + '%', color: '#94a3b8' }, grid: { color: '#2d3148' } },
        x: { ticks: { color: '#94a3b8' }, grid: { color: '#2d3148' } }
      },
      plugins: { legend: { labels: { color: '#e2e8f0', boxRadius: 4 } } }
    }
  });

  // ── Deception split cards ──────────────────────────────────────────────────
  const ds = DATA.deception_split;
  function splitCard(label, s) {
    if (!s) return `<div class="split-card"><div class="split-label">${label}</div><p style="color:var(--muted);font-size:.82rem">No data yet.</p></div>`;
    return `<div class="split-card">
      <div class="split-label">${label}</div>
      <div class="split-stat"><span>Runs</span><span>${s.n}</span></div>
      <div class="split-stat"><span>Trap ID rate</span><span style="color:${trapColor(s.trap_correct_rate_pct)}">${pct(s.trap_correct_rate_pct)}</span></div>
      <div class="split-stat"><span>Estimate hit rate</span><span>${pct(s.estimate_hit_rate_pct)}</span></div>
      <div class="split-stat"><span>Mean error</span><span>${err(s.mean_error_pct)}</span></div>
      <div class="split-stat"><span>Path accuracy</span><span>${path(s.mean_path_accuracy)}</span></div>
    </div>`;
  }
  document.getElementById('deceptionSplit').innerHTML =
    splitCard('Obvious — trap visible in prompt', ds.obvious) +
    splitCard('Deceptive ★ — looks cheap, is expensive', ds.deceptive);

  // ── Cell table ─────────────────────────────────────────────────────────────
  const cellTbody = document.getElementById('cellTbody');
  Object.entries(DATA.by_cell).forEach(([cell, s]) => {
    if (!s) return;
    const tr = cellTbody.insertRow();
    const isDeceptive = cell.includes('deceptive');
    tr.innerHTML = `
      <td>${isDeceptive ? '★ ' : ''}${cell}</td>
      <td>${s.n}</td>
      <td style="font-weight:600;color:${trapColor(s.trap_correct_rate_pct)}">${pct(s.trap_correct_rate_pct)}</td>
      <td>${pct(s.estimate_hit_rate_pct)}</td>
      <td>${err(s.mean_error_pct)}</td>
      <td>${s.rmse_pct !== null && s.rmse_pct !== undefined ? s.rmse_pct + '%' : '—'}</td>
      <td>${path(s.mean_path_accuracy)}</td>
    `;
  });

  // ── Runs table ─────────────────────────────────────────────────────────────
  const runsTbody = document.getElementById('runsTbody');
  [...DATA.runs].reverse().forEach(r => {
    const tr = runsTbody.insertRow();
    tr.innerHTML = `
      <td style="font-family:monospace;font-size:.78rem">${r.run_id || '—'}</td>
      <td style="font-family:monospace;font-size:.78rem"><a href="https://github.com/jdonelson04/token-estimator/blob/main/tests/test_cases_v2.json" title="Look up ${r.tc_id} in test_cases_v2.json">${r.tc_id}</a></td>
      <td style="font-size:.78rem;color:var(--muted)">${r.cell || '—'}</td>
      <td>${r.contributor_id || '—'}</td>
      <td style="font-size:.78rem">${r.skill_version || '—'}</td>
      <td style="font-size:.78rem;color:var(--muted)">${r.model_used || '—'}</td>
      <td>${badge(r.estimate_hit, false)}</td>
      <td>${badge(r.trap_correct, r.false_positive)}</td>
      <td style="font-size:.8rem">${err(r.error_pct)}</td>
      <td style="font-size:.8rem">${path(r.path_accuracy_score)}</td>
    `;
  });
})();
  </script>
</body>
</html>"""


def generate_dashboard_html(community_path: Path) -> str:
    data = compute_dashboard_data(community_path)
    return _DASHBOARD_TEMPLATE.replace("__DATA__", json.dumps(data, indent=None))


# ─────────────────────────────────────────────────────────────────────────────
# Results template generator
# ─────────────────────────────────────────────────────────────────────────────

RUN_TEMPLATE = {
    "run_id":                 None,
    "tc_id":                  None,
    "session_id":             None,
    "run_number":             None,
    "run_date":               None,
    # Contributor metadata (required for --submit)
    "contributor_id":         None,   # GitHub username or handle
    "skill_version":          "1.3",  # which SKILL.md was in use
    "model_used":             None,   # e.g. "claude-sonnet-4-5"
    "session_type":           "same-session",  # "same-session" | "cold-execute"
    # Skill output
    "skill_tier":             None,
    "skill_bucket":           None,
    "skill_estimate_point":   None,
    "skill_estimate_low":     None,
    "skill_estimate_high":    None,
    "skill_risk":             None,
    "skill_identified_traps": [],
    "skill_probe_fired":      None,
    "skill_raw_output":       None,
    # Task execution
    "actual_tokens":          None,
    "actual_input_tokens":    None,
    "actual_output_tokens":   None,
    # Human scoring
    "path_accuracy_score":    None,  # 0 | 1 | 2
    "option_quality_score":   None,  # 0 | 1 | 2  (RISKY cases only)
    "notes":                  None,
}


def generate_template(tc_id: str, n_runs: int, cases_data: dict) -> dict:
    tc = next((c for c in cases_data["test_cases"] if c["id"] == tc_id), None)
    if not tc:
        raise ValueError(f"Test case {tc_id} not found")

    runs = []
    for i in range(1, n_runs + 1):
        run = dict(RUN_TEMPLATE)
        run["run_id"]     = f"{tc_id}-R{i:02d}"
        run["tc_id"]      = tc_id
        run["run_number"] = i
        runs.append(run)

    return {
        "skill_version": "1.3",
        "generated_at":  datetime.utcnow().isoformat() + "Z",
        "test_case":     tc,
        "methodology": {
            "temperature":      "default (Claude platform default)",
            "protocol":         "same-session: skill estimate first, task execution second",
            "n_runs":           n_runs,
            "statistical_note": f"n={n_runs} is directional. Variance prior from CASTILLO et al. (2025).",
            "lurking_variable": "Estimate-priming effect documented but not controlled (see harness header).",
        },
        "runs": runs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Report (single file)
# ─────────────────────────────────────────────────────────────────────────────

def print_report(scored: dict):
    s = scored["summary"]
    print("\n" + "="*60)
    print(f"  TokenEstimator v{scored.get('skill_version','?')} — Live Test Report")
    print(f"  Scored: {scored['scored_at']}")
    print("="*60)
    print(f"\n  Runs scored:          {scored['n']}")
    print(f"  Estimate hit rate:    {s.get('estimate_hit_rate_pct')}%")
    print(f"  Trap correct rate:    {s.get('trap_correct_rate_pct')}%")
    print(f"  False positive rate:  {s.get('false_positive_rate_pct')}%")
    err = s.get('mean_error_pct')
    print(f"  Mean error:           {err:+.1f}%" if err is not None else "  Mean error:           n/a")
    rmse = s.get('rmse_pct')
    print(f"  RMSE:                 {rmse:.1f}%"  if rmse is not None else "  RMSE:                 n/a")
    pa = s.get('mean_path_accuracy')
    print(f"  Mean path accuracy:   {pa:.2f}/2.0" if pa is not None else "  Mean path accuracy:   n/a (awaiting human scoring)")
    oq = s.get('mean_option_quality')
    print(f"  Mean option quality:  {oq:.2f}/2.0" if oq is not None else "  Mean option quality:  n/a (awaiting human scoring)")

    print("\n── Run Detail ──────────────────────────────────────────")
    print(f"  {'Run':<14} {'Est?':<6} {'Trap?':<7} {'Path':<6} {'Err%':>7}")
    for r in scored["runs"]:
        ea   = r["estimate_accuracy"]
        ti   = r["trap_identification"]
        pa_r = r["path_accuracy"]
        est  = "✓" if ea.get("hit") else ("✗" if ea.get("scored") else "—")
        trap = ("✓" if ti.get("correct") else ("FP" if ti.get("false_positive") else "✗"))
        path = str(pa_r.get("score", "—"))
        err  = f"{ea.get('error_pct',0):+.1f}%" if ea.get("error_pct") is not None else "—"
        print(f"  {r['run_id']:<14} {est:<6} {trap:<7} {path:<6} {err:>7}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="TokenEstimator v1.3 Live Test Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a blank results template for one test case (5 run slots)
  python3 test_harness_v2.py --template TC-ED01 --runs 5

  # Score a single completed results file and print a report
  python3 test_harness_v2.py --results tests/results/TC-ED01_results.json --report

  # Submit completed results to the community JSONL file
  python3 test_harness_v2.py --submit tests/results/TC-ED01_results.json

  # Validate without writing (dry run)
  python3 test_harness_v2.py --submit tests/results/TC-ED01_results.json --dry-run

  # Regenerate the results dashboard HTML
  python3 test_harness_v2.py --dashboard

  # Roll up all result files in a directory into one aggregate report
  python3 test_harness_v2.py --aggregate tests/results/ --report
"""
    )
    parser.add_argument("--cases",     default=DEFAULT_CASES,     metavar="FILE",
                        help=f"Path to test_cases_v2.json (default: {DEFAULT_CASES})")
    parser.add_argument("--community", default=DEFAULT_COMMUNITY, metavar="FILE",
                        help=f"Path to community_results.jsonl (default: {DEFAULT_COMMUNITY})")
    parser.add_argument("--template",  default=None, metavar="TC-ID",
                        help="Generate a blank results template for this test case ID")
    parser.add_argument("--runs",      default=5, type=int,
                        help="Number of run slots in the generated template (default: 5)")
    parser.add_argument("--results",   default=None, metavar="FILE",
                        help="Score a single completed results file")
    parser.add_argument("--submit",    default=None, metavar="FILE",
                        help="Validate and append a completed results file to community_results.jsonl")
    parser.add_argument("--dry-run",   action="store_true",
                        help="With --submit: validate only, do not write")
    parser.add_argument("--dashboard", action="store_true",
                        help="Generate the results dashboard HTML from community_results.jsonl")
    parser.add_argument("--dash-out",  default=DEFAULT_DASHBOARD, metavar="FILE",
                        help=f"Dashboard output path (default: {DEFAULT_DASHBOARD})")
    parser.add_argument("--aggregate", default=None, metavar="DIR",
                        help="Score and roll up all result files in a directory")
    parser.add_argument("--output",    default=None, metavar="FILE",
                        help="Where to write scored output (default: auto-named alongside input)")
    parser.add_argument("--report",    action="store_true",
                        help="Print a human-readable report to stdout after scoring")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(f"Error: cases file not found: {cases_path}"); return 1
    with open(cases_path) as f:
        cases_data = json.load(f)

    # ── Generate template ──────────────────────────────────────────────────
    if args.template:
        tmpl = generate_template(args.template, args.runs, cases_data)
        out  = Path(args.output) if args.output else Path(f"tests/results/{args.template}_template.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(tmpl, f, indent=2)
        print(f"Template written to {out}")
        return 0

    # ── Score a single results file ────────────────────────────────────────
    if args.results:
        rpath = Path(args.results)
        if not rpath.exists():
            print(f"Error: results file not found: {rpath}"); return 1
        with open(rpath) as f:
            results_data = json.load(f)
        scored = score_all(results_data, cases_data)
        if args.report:
            print_report(scored)
        out = Path(args.output) if args.output else rpath.with_suffix(".scored.json")
        with open(out, "w") as f:
            json.dump(scored, f, indent=2)
        print(f"Scored results saved to {out}")
        return 0

    # ── Submit to community JSONL ──────────────────────────────────────────
    if args.submit:
        spath = Path(args.submit)
        if not spath.exists():
            print(f"Error: results file not found: {spath}"); return 1
        submit_results(spath, Path(args.community), cases_data, dry_run=args.dry_run)
        return 0

    # ── Generate dashboard ─────────────────────────────────────────────────
    if args.dashboard:
        html = generate_dashboard_html(Path(args.community))
        out  = Path(args.dash_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            f.write(html)
        print(f"Dashboard written to {out}")
        n = compute_dashboard_data(Path(args.community))["total_runs"]
        print(f"  {n} run(s) included")
        return 0

    # ── Aggregate across a directory of result files ────────────────────────
    if args.aggregate:
        agg_dir = Path(args.aggregate)
        if not agg_dir.is_dir():
            print(f"Error: not a directory: {agg_dir}"); return 1
        agg = aggregate_results(agg_dir, cases_data)
        if args.report:
            print_aggregate_report(agg)
        out = Path(args.output) if args.output else agg_dir / "aggregate_report.json"
        with open(out, "w") as f:
            json.dump(agg, f, indent=2)
        print(f"Aggregate report saved to {out}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    exit(main())
