#!/usr/bin/env python3
"""Report raw hidden metrics and cohort-standardized rank, without unit errors."""
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPERIMENT = "memory_retrieval_efficiency"
spec = json.loads((ROOT / "rank_specification.json").read_text())["experiments"][EXPERIMENT]
reference = json.loads((ROOT / "reference_scores_test.json").read_text())["experiments"][EXPERIMENT]["results"]["hippocampus"]
scores = {}
for path in sorted(ROOT.glob("*/scores_test.json")):
    metrics = json.loads(path.read_text())["experiments"][EXPERIMENT]["results"]["hippocampus"]
    if all(math.isfinite(v) for v in metrics.values()):
        scores[path.parent.name] = metrics
spread = {k: statistics.pstdev([reference[k]] + [s[k] for s in scores.values()]) for k in spec["metrics"]}

def rank(metrics):
    return spec["weight"] * sum(
        abs(conf["coefficient"]) * (1 if conf["higher_is_better"] else -1)
        * (metrics[k] - reference[k]) / (spread[k] or 1)
        for k, conf in spec["metrics"].items())

rows = {}
for name, metrics in scores.items():
    row = {"rank_delta": rank(metrics), "metrics": metrics}
    rows[name] = row
    (ROOT / name / "rank.json").write_text(json.dumps(row, indent=2) + "\n")
seed_metrics = {k: scores[k] for k in ("reference_seed13", "reference_seed14", "reference_seed15") if k in scores}
summary = {
    "rank_definition": "experiment weight * sum(abs(coefficient) * oriented improvement / audit cohort population stddev)",
    "normalization_population": "all successful audit submissions plus the frozen reference; actual future rank depends on its population",
    "reference": reference,
    "metric_population_stddev": spread,
    "attempts": rows,
    "seed_metric_ranges": {m: max(v[m] for v in seed_metrics.values()) - min(v[m] for v in seed_metrics.values())
                           for m in reference} if seed_metrics else {},
    "seed_rank_range": max(map(rank, seed_metrics.values())) - min(map(rank, seed_metrics.values())) if seed_metrics else None,
    "reference_metrics_at_mathematical_bound": [k for k, v in reference.items()
        if (spec["metrics"][k]["higher_is_better"] and v >= 100)
        or (not spec["metrics"][k]["higher_is_better"] and v <= 0)],
}
(ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
for name, row in rows.items():
    print(name, f'{row["rank_delta"]:+.6f}', json.dumps(row["metrics"], sort_keys=True))
