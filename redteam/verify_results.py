#!/usr/bin/env python3
"""Lightweight consistency checks on saved audit results; no experiments run."""
import hashlib
import json
from pathlib import Path

from audit import CASES

base = Path(__file__).resolve().parent
root = base.parent
experiment = "memory_retrieval_efficiency"
summary = json.loads((base / "summary.json").read_text())
reference = summary["reference"]
spec = json.loads((base / "rank_specification.json").read_text())["experiments"][experiment]
test_script_hash = hashlib.sha256((root / "scripts/evaluate_test.sh").read_bytes()).hexdigest()
test_evaluator_hash = hashlib.sha256((root / "eval/test/evaluate_retrieval.py").read_bytes()).hexdigest()

for name in CASES:
    folder = base / name
    assert (folder / "run.sh").exists(), name
    status = json.loads((folder / "status.json").read_text())
    assert status["test_command"] == "bash scripts/evaluate_test.sh", name
    assert status["test_script_sha256"] == test_script_hash, name
    assert status["test_evaluator_sha256"] == test_evaluator_hash, name
    if name == "shortcut_null_operations":
        assert status["test_exit"] == status["train_exit"] == 1
        assert not (folder / "scores_test.json").exists()
    else:
        assert status["test_exit"] == status["train_exit"] == 0, name
        score = json.loads((folder / "scores_test.json").read_text())
        assert score["experiments"][experiment]["split"]["question_count"] == 36, name
        assert score["experiments"][experiment]["results"]["hippocampus"] == summary["attempts"][name]["metrics"], name

assert summary["attempts"]["reference_seed13"]["metrics"] == reference
pareto_shortcuts = ["shortcut_visible_labels", "shortcut_generator_answers", "shortcut_forged_text",
                    "shortcut_omitted_operations", "shortcut_negative_operations",
                    "shortcut_relabel_dataset", "shortcut_replace_corpus"]
for name in pareto_shortcuts:
    metrics = summary["attempts"][name]["metrics"]
    oriented = [(metrics[k] - reference[k]) * (1 if c["higher_is_better"] else -1)
                for k, c in spec["metrics"].items()]
    assert min(oriented) >= 0 and max(oriented) > 0, name
    assert summary["attempts"][name]["rank_delta"] > 0, name

ties = ["shortcut_baseline_poisoning", "shortcut_prewrite_scores", "shortcut_row_gold"]
for name in ties:
    assert summary["attempts"][name]["metrics"] == reference, name
assert summary["attempts"]["better_ranking"]["rank_delta"] > summary["seed_rank_range"]
assert -summary["attempts"]["weaker_one_bit"]["rank_delta"] < summary["seed_rank_range"]
assert summary["attempts"]["shortcut_id_only_labels"]["metrics"]["avg_token_footprint"] == 0
assert summary["attempts"]["shortcut_id_only_labels"]["rank_delta"] > summary["attempts"]["better_ranking"]["rank_delta"]

result = {"cases": len(CASES), "successful_hidden_tests": len(summary["attempts"]),
          "expected_failed_hidden_tests": 1,
          "strictly_winning_shortcuts": [name for name, v in summary["attempts"].items()
                                        if name.startswith("shortcut_") and v["rank_delta"] > 0],
          "normalization_independent_pareto_shortcuts": pareto_shortcuts,
          "tie_shortcuts": ties,
          "honest_gain_exceeds_seed_range": True,
          "weaker_ablation_drop_exceeds_seed_range": False,
          "reference_metrics_at_bound": summary["reference_metrics_at_mathematical_bound"],
          "all_checks_passed": True}
(base / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
