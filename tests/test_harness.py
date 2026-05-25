#!/usr/bin/env python3
"""
TokenEstimator Skill v1.0 — Test Harness
=========================================
Tests the estimation accuracy of the TokenEstimator skill by applying its
decision matrix programmatically to each test case and comparing the output
against ground-truth token ranges.

Metrics produced:
  - Hit rate: % of cases where actual_midpoint falls within the estimate's
    stated confidence band
  - Directional bias: does the skill over- or under-estimate on average?
  - Calibration: are confidence signals (🟢/🟡/🔴) predictive of accuracy?
  - Category breakdown: which task types perform worst?
  - Variance accuracy: are stated ± ranges actually achieved?

Usage:
  python3 tests/test_harness.py
  python3 tests/test_harness.py --output tests/results/run_001.json
"""

import json
import math
import argparse
from datetime import datetime
from pathlib import Path
from typing import Literal

# ─────────────────────────────────────────────────────────────────────────────
# Skill estimation logic — faithfully reproduced from SKILL.md v1.0
# ─────────────────────────────────────────────────────────────────────────────

# Base estimates (tokens) from the "Estimation Anchors" table in SKILL.md
BASE_ANCHORS = {
    "simple_qa":         {"low": 500,   "high": 2000,  "mid": 1250},
    "document_short":    {"low": 3000,  "high": 6000,  "mid": 4500},
    "data_processing":   {"low": 2000,  "high": 8000,  "mid": 5000},
    "research_synthesis":{"low": 10000, "high": 20000, "mid": 15000},
    "code_feature":      {"low": 3000,  "high": 8000,  "mid": 5500},
    "complex_artifact":  {"low": 8000,  "high": 15000, "mid": 11500},
    "deep_exploratory":  {"low": 15000, "high": 35000, "mid": 25000},
    "full_project":      {"low": 30000, "high": 44000, "mid": 37000},
}

# Decision matrix — variance multipliers from SKILL.md
CATEGORY_VARIANCE = {
    "data":        0.10,
    "exploratory": 0.20,
    "creation":    0.10,
    "execution":   0.25,
}

SCOPE_VARIANCE = {
    "crisp":        0.10,
    "semi-defined": 0.15,
    "fuzzy":        0.25,
}

DEP_BUFFER = {
    "none":  0.00,
    "light": 0.175,  # midpoint of 15-20%
    "heavy": 0.35,   # midpoint of 30-40%
}

SCOPE_CONFIDENCE = {
    "crisp":        "green",
    "semi-defined": "yellow",
    "fuzzy":        "red",
}

# Skill's risk thresholds
RISK_SAFE  = 30000
RISK_TIGHT = 38000


def map_to_anchor(category: str, scope: str, external_deps: str, task_description: str) -> dict:
    """
    Determine which anchor bucket a task falls into.
    This mirrors the implicit categorisation a human would do when using the skill.
    We encode this mapping per test case via the 'anchor_key' field; if not present,
    we infer it from category + scope.
    """
    # Heuristic inference from category + scope
    if category == "data" and scope == "crisp":
        return BASE_ANCHORS["data_processing"]
    if category == "data":
        return BASE_ANCHORS["data_processing"]
    if category == "exploratory" and scope == "fuzzy":
        return BASE_ANCHORS["deep_exploratory"]
    if category == "exploratory":
        return BASE_ANCHORS["research_synthesis"]
    if category == "creation" and scope == "crisp":
        return BASE_ANCHORS["code_feature"]
    if category == "creation" and scope == "semi-defined":
        return BASE_ANCHORS["complex_artifact"]
    if category == "creation" and scope == "fuzzy":
        return BASE_ANCHORS["complex_artifact"]
    if category == "execution" and scope in ("semi-defined", "fuzzy"):
        return BASE_ANCHORS["full_project"]
    return BASE_ANCHORS["complex_artifact"]


def estimate(tc: dict) -> dict:
    """Apply the skill's estimation formula to a test case."""
    category = tc["category"]
    scope    = tc["scope"]
    deps     = tc["external_deps"]

    anchor = map_to_anchor(category, scope, deps, tc.get("task_description", ""))
    base   = anchor["mid"]

    # Combined variance: category + scope (additive, per skill logic)
    total_variance = CATEGORY_VARIANCE[category] + SCOPE_VARIANCE[scope]

    # Dependency buffer applied to base before variance bands
    buffered_base = base * (1 + DEP_BUFFER[deps])

    # Final estimate
    point_estimate = buffered_base

    # Confidence band
    low  = point_estimate * (1 - total_variance)
    high = point_estimate * (1 + total_variance)

    # Risk classification
    if point_estimate < RISK_SAFE:
        risk = "SAFE"
    elif point_estimate < RISK_TIGHT:
        risk = "TIGHT"
    else:
        risk = "RISKY"

    return {
        "point_estimate": round(point_estimate),
        "low":  round(low),
        "high": round(high),
        "variance": total_variance,
        "confidence": SCOPE_CONFIDENCE[scope],
        "risk": risk,
        "anchor_used": anchor,
        "dep_buffer_applied": DEP_BUFFER[deps],
    }


def score(tc: dict, est: dict) -> dict:
    """Score a single test case against ground truth."""
    actual  = tc["actual_midpoint"]
    gt_low  = tc["ground_truth_range"][0]
    gt_high = tc["ground_truth_range"][1]

    est_low  = est["low"]
    est_high = est["high"]
    point    = est["point_estimate"]

    # Hit: does actual_midpoint fall within the estimate's stated band?
    hit = est_low <= actual <= est_high

    # Directional error: positive = overestimate, negative = underestimate
    error_abs   = point - actual
    error_pct   = error_abs / actual

    # Overlap between estimated range and ground truth range
    overlap_low  = max(est_low,  gt_low)
    overlap_high = min(est_high, gt_high)
    overlap      = max(0, overlap_high - overlap_low)
    gt_span      = gt_high - gt_low
    est_span     = est_high - est_low
    union        = (gt_high - gt_low) + (est_high - est_low) - overlap
    iou          = overlap / union if union > 0 else 0.0

    return {
        "hit": hit,
        "error_abs": error_abs,
        "error_pct": round(error_pct * 100, 1),
        "iou": round(iou, 3),
        "actual_in_gt_range": gt_low <= actual <= gt_high,
    }


def run_harness(test_cases: list[dict]) -> dict:
    """Run the full test suite and return structured results."""
    results = []
    for tc in test_cases:
        est    = estimate(tc)
        scored = score(tc, est)
        results.append({
            "id":    tc["id"],
            "label": tc["label"],
            "category": tc["category"],
            "scope":    tc["scope"],
            "deps":     tc["external_deps"],
            "actual_midpoint":    tc["actual_midpoint"],
            "ground_truth_range": tc["ground_truth_range"],
            "estimate": est,
            "score":   scored,
            "notes":   tc.get("notes", ""),
        })

    # ── Aggregate metrics ──────────────────────────────────────────────────────
    n = len(results)
    hits = [r for r in results if r["score"]["hit"]]
    misses = [r for r in results if not r["score"]["hit"]]

    hit_rate = len(hits) / n

    errors_pct = [r["score"]["error_pct"] for r in results]
    mean_error = sum(errors_pct) / n
    overestimates  = [r for r in results if r["score"]["error_pct"] > 0]
    underestimates = [r for r in results if r["score"]["error_pct"] < 0]

    iou_scores = [r["score"]["iou"] for r in results]
    mean_iou = sum(iou_scores) / n

    # RMSE of error %
    rmse = math.sqrt(sum(e**2 for e in errors_pct) / n)

    # ── Category breakdown ─────────────────────────────────────────────────────
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "hits": 0, "errors": []}
        categories[cat]["total"] += 1
        if r["score"]["hit"]:
            categories[cat]["hits"] += 1
        categories[cat]["errors"].append(r["score"]["error_pct"])

    cat_summary = {}
    for cat, data in categories.items():
        cat_summary[cat] = {
            "hits": data["hits"],
            "hit_rate_pct": round(data["hits"] / data["total"] * 100, 1),
            "mean_error_pct": round(sum(data["errors"]) / len(data["errors"]), 1),
            "n": data["total"],
        }

    # ── Scope / confidence breakdown ───────────────────────────────────────────
    scopes = {}
    for r in results:
        sc = r["scope"]
        if sc not in scopes:
            scopes[sc] = {"total": 0, "hits": 0, "errors": []}
        scopes[sc]["total"] += 1
        if r["score"]["hit"]:
            scopes[sc]["hits"] += 1
        scopes[sc]["errors"].append(r["score"]["error_pct"])

    scope_summary = {}
    for sc, data in scopes.items():
        scope_summary[sc] = {
            "hits": data["hits"],
            "hit_rate_pct": round(data["hits"] / data["total"] * 100, 1),
            "mean_error_pct": round(sum(data["errors"]) / len(data["errors"]), 1),
            "n": data["total"],
        }

    # ── Biggest misses ─────────────────────────────────────────────────────────
    sorted_by_error = sorted(results, key=lambda r: abs(r["score"]["error_pct"]), reverse=True)
    worst_5 = [{"id": r["id"], "label": r["label"],
                "error_pct": r["score"]["error_pct"],
                "estimate": r["estimate"]["point_estimate"],
                "actual":   r["actual_midpoint"]}
               for r in sorted_by_error[:5]]

    return {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "skill_version": "1.0",
        "n": n,
        "summary": {
            "hit_rate_pct":        round(hit_rate * 100, 1),
            "hits":                len(hits),
            "misses":              len(misses),
            "mean_error_pct":      round(mean_error, 1),
            "overestimate_count":  len(overestimates),
            "underestimate_count": len(underestimates),
            "mean_iou":            round(mean_iou, 3),
            "rmse_error_pct":      round(rmse, 1),
        },
        "category_breakdown": cat_summary,
        "scope_breakdown":    scope_summary,
        "worst_misses":       worst_5,
        "all_results":        results,
    }


def print_report(report: dict):
    """Pretty-print a human-readable summary."""
    s = report["summary"]
    print("\n" + "="*60)
    print(f"  TokenEstimator Skill v{report['skill_version']} — Test Report")
    print(f"  Run: {report['run_at']}")
    print("="*60)
    print(f"\n  Test cases:     {report['n']}")
    print(f"  Hit rate:       {s['hit_rate_pct']}%  ({s['hits']} hits, {s['misses']} misses)")
    print(f"  Mean error:     {s['mean_error_pct']:+.1f}%  (+ = overestimate)")
    print(f"  RMSE:           {s['rmse_error_pct']:.1f}%")
    print(f"  Mean IoU:       {s['mean_iou']:.3f}  (range overlap quality)")
    print(f"  Overestimates:  {s['overestimate_count']}   Underestimates: {s['underestimate_count']}")

    print("\n── Category Breakdown ──────────────────────────────────")
    for cat, d in report["category_breakdown"].items():
        bar = "✓" * d["hits"] + "✗" * (d["n"] - d["hits"])
        print(f"  {cat:<14} hit={d['hit_rate_pct']:5.1f}%  bias={d['mean_error_pct']:+6.1f}%  [{bar}]")

    print("\n── Scope / Confidence Breakdown ────────────────────────")
    icons = {"crisp": "🟢", "semi-defined": "🟡", "fuzzy": "🔴"}
    for sc, d in report["scope_breakdown"].items():
        icon = icons.get(sc, "?")
        print(f"  {icon} {sc:<14} hit={d['hit_rate_pct']:5.1f}%  bias={d['mean_error_pct']:+6.1f}%  n={d['n']}")

    print("\n── 5 Worst Misses ──────────────────────────────────────")
    for w in report["worst_misses"]:
        direction = "OVER" if w["error_pct"] > 0 else "UNDER"
        print(f"  [{w['id']}] {w['label'][:38]:<38}")
        print(f"         est={w['estimate']:>6,}  actual={w['actual']:>6,}  error={w['error_pct']:+.1f}% ({direction})")

    print("\n── All Results ─────────────────────────────────────────")
    print(f"  {'ID':<7} {'Label':<36} {'Est':>7} {'Act':>6} {'Err%':>6} {'Hit'}")
    print(f"  {'-'*7} {'-'*36} {'-'*7} {'-'*6} {'-'*6} {'-'*3}")
    for r in report["all_results"]:
        hit_sym = "✓" if r["score"]["hit"] else "✗"
        print(f"  {r['id']:<7} {r['label'][:36]:<36} "
              f"{r['estimate']['point_estimate']:>7,} "
              f"{r['actual_midpoint']:>6,} "
              f"{r['score']['error_pct']:>+6.1f}% {hit_sym}")
    print()


def main():
    parser = argparse.ArgumentParser(description="TokenEstimator Skill Test Harness")
    parser.add_argument("--cases",  default="tests/test_cases.json", help="Path to test cases JSON")
    parser.add_argument("--output", default=None, help="Path to save JSON results")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(f"Error: test cases file not found at {cases_path}")
        return 1

    with open(cases_path) as f:
        data = json.load(f)

    test_cases = data["test_cases"]
    report = run_harness(test_cases)
    print_report(report)

    # Save JSON results
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  Results saved to {out_path}")
    else:
        # Default output path
        out_path = Path("tests/results/run_latest.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  Results saved to {out_path}")

    return 0


if __name__ == "__main__":
    exit(main())
