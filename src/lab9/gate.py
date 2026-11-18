"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted.
    Return a list of problems (empty = trustworthy).
    """
    import math
    problems: list[str] = []
    # 1. NaN / inf in metric values
    for mid, val in pr.get("metrics", {}).items():
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            problems.append(f"metric {mid} has NaN/inf value")
    # 2. Row count mismatch
    manifest = pr.get("manifest", {})
    rows = pr.get("rows", [])
    expected_items = manifest.get("items") or manifest.get("num_items") or len({r.get("item_id") for r in rows})
    seeds = manifest.get("seeds") or []
    expected_seeds = len(seeds) if isinstance(seeds, list) else (manifest.get("num_seeds") or len({r.get("seed") for r in rows}))
    expected = expected_items * expected_seeds if expected_items and expected_seeds else len(rows)
    if len(rows) != expected:
        problems.append(f"row count {len(rows)} != expected {expected}")
    # 3. Item/seed set mismatch
    def key_set(rpt: dict) -> set[tuple[str, str]]:
        return {(row.get("item_id"), row.get("seed")) for row in rpt.get("rows", [])}
    if key_set(pr) != key_set(base):
        problems.append("PR rows (item_id, seed) differ from baseline")
    # 4. Evaluator failures / missing graded metric values
    if pr.get("evaluator_failures"):
        problems.append("evaluator_failures non‑empty")
    for row in rows:
        for m in spec.get("metrics", []):
            if m.get("grading") and row.get(m["id"]) is None:
                problems.append(f"row {row.get('item_id')} missing graded metric {m['id']}")
    # 5. Ratchet checks against base_spec
    if base_spec:
        # metric thresholds ratchet
        for m in spec.get("metrics", []):
            mid = m["id"]
            base_thr = next((b["threshold"] for b in base_spec.get("metrics", []) if b["id"] == mid), None)
            if base_thr:
                for bound in ("max", "min"):
                    if bound in m.get("threshold", {}) and bound in base_thr:
                        cur = m["threshold"][bound]
                        old = base_thr[bound]
                        if (bound == "max" and cur > old) or (bound == "min" and cur < old):
                            problems.append(f"ratchet violation on {mid}:{bound} (base {old} -> new {cur})")
                base_blocking = next((b.get("blocking") for b in base_spec.get("metrics", []) if b["id"] == mid), None)
                if base_blocking and not m.get("blocking"):
                    problems.append(f"blocking turned off for {mid}")
        # slice spec ratchet
        for sl in spec.get("slices", []):
            name = sl["name"]
            base_sl = next((b for b in (base_spec.get("slices") or []) if b["name"] == name), None)
            if base_sl:
                if sl.get("no_significant_drop") and not base_sl.get("no_significant_drop"):
                    problems.append(f"slice {name} added no_significant_drop flag")
                if sl.get("blocking") and not base_sl.get("blocking"):
                    problems.append(f"slice {name} made non‑blocking")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    import numpy as np
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for sl in spec.get("slices", []):
        name = sl["name"]
        metric = sl["metric"]
        # per‑item values for PR and baseline in this slice
        pr_vals = per_item(pr, metric, slice_name=name)
        base_vals = per_item(base, metric, slice_name=name)
        if not pr_vals:
            continue
        # mean value for PR slice
        pr_mean = float(np.mean(list(pr_vals.values())))
        # min threshold check
        if "min" in sl and pr_mean < sl["min"]:
            blocked.append(f"slice:{name}/{metric}")
            lines.append(f"  slice {name}/{metric} mean {pr_mean:.3f} < min {sl['min']}")
        # paired bootstrap check for no_significant_drop
        if sl.get("no_significant_drop") and pr_vals and base_vals:
            keys = sorted(set(pr_vals) & set(base_vals))
            a = [pr_vals[k] for k in keys]
            b = [base_vals[k] for k in keys]
            d, lo, hi = stats.paired_bootstrap(
                a, b,
                n_resamples=bs.get("n_resamples", 1000),
                rng=bs.get("rng", 2027),
            )
            lines.append(f"  slice {name}/{metric} Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]")
            if hi < 0:
                blocked.append(f"slice:{name}/{metric}")
                lines.append("    → blocked (CI entirely negative)")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
