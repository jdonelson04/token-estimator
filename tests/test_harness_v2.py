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

    Start cheap → run control cases (TC-N01–N03) to verify no false positives.
    Test a trap  → pick one deceptive case (e.g. TC-ED01) and run it fully.
    Go wide      → run 1 rep of each cell to get coverage before depth.

  Each case produces its own result file. Use --aggregate to roll them up.

  Step 1: Generate a blank results template for the case you want to run
            python3 test_harness_v2.py --template TC-ED01 --runs 5

  Step 2: Run the prompt in Claude (skill estimate first, then execute the task)
          Fill in the result fields in the generated template file.

  Step 3: Score the completed file
            python3 test_harness_v2.py --results tests/results/TC-ED01_results.json --report

  Step 4: Repeat for other cases. When you have multiple result files:
            python3 test_harness_v2.py --aggregate tests/results/ --report

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST MATRIX — v1.3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Primary axis:   Trap type         (what makes the task expensive)
Secondary axis: Surface deception (whether the expense is obvious from the prompt)

                  OBVIOUS                   DECEPTIVE
                  (trap visible in prompt)  (looks cheap, is expensive)
  ──────────────┬─────────────────────────┬──────────────────────────
  No trap       │ TC-N01–N03  — control   │ n/a
  Enumeration   │ TC-EO01–03  — bounded   │ TC-ED01–03  — unbounded ★
  Reasoning     │ TC-RO01–03  — openly hard│ TC-RD01–03  — tiny output ★
  Fetch         │ TC-FO01–03  — count given│ TC-FD01–03  — 1 Q, many src ★
  Iteration     │ TC-IO01–03  — no stop   │ TC-ID01–03  — hidden cycles ★
  ──────────────┴─────────────────────────┴──────────────────────────
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
        "run_id":             run["run_id"],
        "tc_id":              test_case["id"],
        "estimate_accuracy":  score_estimate_accuracy(run),
        "trap_identification":score_trap_identification(run, test_case["trap_type"]),
        "path_accuracy":      score_path_accuracy(run),
        "option_quality":     score_option_quality(run, test_case["expected_risk"]),
    }


def score_all(results_data: dict, cases_data: dict) -> dict:
    cases_by_id  = {tc["id"]: tc for tc in cases_data["test_cases"]}
    scored_runs  = []

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

    mean_err = round(sum(errors)/len(errors), 1)        if errors        else None
    rmse     = round(math.sqrt(sum(e**2 for e in errors)/len(errors)), 1) if errors else None

    return {
        "scored_at":     datetime.utcnow().isoformat() + "Z",
        "skill_version": results_data.get("skill_version", "1.3"),
        "n":             n,
        "summary": {
            "estimate_hit_rate_pct":  round(len(estimate_hits)/n*100, 1),
            "trap_correct_rate_pct":  round(len(trap_correct)/n*100,  1),
            "false_positive_rate_pct":round(len(false_pos)/n*100,     1),
            "mean_error_pct":         mean_err,
            "rmse_pct":               rmse,
            "mean_path_accuracy":     round(sum(path_scores)/len(path_scores), 2)   if path_scores   else None,
            "mean_option_quality":    round(sum(option_scores)/len(option_scores),2) if option_scores else None,
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
    files_loaded = []

    for fpath in result_files:
        with open(fpath) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        # Score each run in the file and attach it
        for run in data.get("runs", []):
            tc = cases_by_id.get(run.get("tc_id"))
            if tc:
                scored = score_run(run, tc)
                scored["_cell"]      = tc.get("cell", "unknown")
                scored["_trap_type"] = tc.get("trap_type", "unknown")
                scored["_deceptive"] = tc.get("surface_deceptive", False)
                all_runs.append(scored)
        files_loaded.append(fpath.name)

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

    # Overall summary
    overall = summarize(all_runs)

    # By cell
    cells = {}
    for run in all_runs:
        key = run["_cell"]
        cells.setdefault(key, []).append(run)
    by_cell = {cell: summarize(runs) for cell, runs in sorted(cells.items())}

    # Obvious vs deceptive comparison
    obvious   = [r for r in all_runs if not r["_deceptive"]]
    deceptive = [r for r in all_runs if r["_deceptive"]]
    deception_split = {
        "obvious":   summarize(obvious)   if obvious   else None,
        "deceptive": summarize(deceptive) if deceptive else None,
    }

    return {
        "aggregated_at":   datetime.utcnow().isoformat() + "Z",
        "files_loaded":    files_loaded,
        "total_runs":      n,
        "overall":         overall,
        "by_cell":         by_cell,
        "deception_split": deception_split,
    }


def print_aggregate_report(agg: dict):
    if "error" in agg:
        print(f"\nError: {agg['error']}"); return

    print("\n" + "="*62)
    print("  TokenEstimator v1.3 — Aggregate Test Report")
    print(f"  Aggregated: {agg['aggregated_at']}")
    print(f"  Files:      {len(agg['files_loaded'])}  |  Total runs: {agg['total_runs']}")
    print("="*62)

    def fmt_row(label, s):
        err = s.get("mean_error_pct")
        pa  = s.get("mean_path_accuracy")
        return (
            f"  {label:<28}"
            f"  n={s['n']:<4}"
            f"  hit={s['estimate_hit_rate_pct']:>5.1f}%"
            f"  trap={s['trap_correct_rate_pct']:>5.1f}%"
            f"  err={f'{err:+.0f}%' if err is not None else '—':>5}"
            f"  path={f'{pa:.1f}' if pa is not None else '—':>4}"
        )

    s = agg["overall"]
    print(fmt_row("OVERALL", s))

    print("\n── By cell ──────────────────────────────────────────────")
    for cell, cs in agg["by_cell"].items():
        print(fmt_row(cell, cs))

    print("\n── Obvious vs Deceptive ─────────────────────────────────")
    ds = agg["deception_split"]
    if ds.get("obvious"):
        print(fmt_row("obvious (trap visible)", ds["obvious"]))
    if ds.get("deceptive"):
        print(fmt_row("deceptive (surface hides trap)", ds["deceptive"]))

    print(f"\n  Files included:")
    for f in agg["files_loaded"]:
        print(f"    {f}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Results template generator
# ─────────────────────────────────────────────────────────────────────────────

RUN_TEMPLATE = {
    "run_id":                 None,
    "tc_id":                  None,
    "session_id":             None,
    "run_number":             None,
    "run_date":               None,
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
    "path_accuracy_score":    None,
    "option_quality_score":   None,
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
            "lurking_variable": "Estimate-priming effect documented but not controlled (see harness header)."
        },
        "runs": runs
    }


# ─────────────────────────────────────────────────────────────────────────────
# Report
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
        trap = ("✓" if ti.get("correct") else
                ("FP" if ti.get("false_positive") else "✗"))
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
  # Generate a blank results template for one test case
  python3 test_harness_v2.py --template TC-ED01 --runs 5

  # Score a single completed results file and print a report
  python3 test_harness_v2.py --results tests/results/TC-ED01_results.json --report

  # Roll up all result files in a directory into one aggregate report
  python3 test_harness_v2.py --aggregate tests/results/ --report
"""
    )
    parser.add_argument("--cases",     default="tests/test_cases_v2.json",
                        help="Path to test_cases_v2.json (default: tests/test_cases_v2.json)")
    parser.add_argument("--template",  default=None, metavar="TC-ID",
                        help="Generate a blank results template for this test case ID")
    parser.add_argument("--runs",      default=5, type=int,
                        help="Number of run slots in the generated template (default: 5)")
    parser.add_argument("--results",   default=None, metavar="FILE",
                        help="Score a single completed results file")
    parser.add_argument("--aggregate", default=None, metavar="DIR",
                        help="Score and roll up all result files in a directory")
    parser.add_argument("--output",    default=None, metavar="FILE",
                        help="Where to write scored output (default: auto-named alongside input)")
    parser.add_argument("--report",    action="store_true",
                        help="Print a human-readable report after scoring")
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
