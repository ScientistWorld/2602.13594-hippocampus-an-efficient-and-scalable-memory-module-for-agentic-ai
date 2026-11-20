#!/usr/bin/env python3
"""Hardening check: run variants and shortcuts through the hardened evaluators.

Phase A  hidden test, real workspace: registered retrievers + variants
         (seeds, better, weaker, previous-iteration configuration), with
         per-question dumps for paired comparisons.
Phase B  train split, same retrievers (train/test parity).
Phase C  hidden test, isolated workspace copy: shortcut submissions (some of
         them rewrite data/, scoring/ or the evaluator's label file).
Phase E  hidden test, real workspace: read-only shortcuts that try to reach the
         evaluator's own label file (relative path, absolute path, /proc/<pid>/root,
         unmounting the cover over eval/).
Phase D  summary.json: metrics, validity, cohort-normalised rank deltas,
         paired bootstrap intervals and seed ranges.

Run from the workspace root:  python redteam/hardening/run_hardening.py
"""
from __future__ import annotations

import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "redteam" / "hardening"
RESULTS = HERE / "results"
REGISTRY = ROOT / "scripts" / "retrievers"
EXPERIMENT = "locomo_memory_retrieval"
REFERENCE = "hippocampus"

VARIANT_GROUPS = {
    "registry": sorted(REGISTRY.glob("*.sh")),
    "seeds": [HERE / "retrievers" / f"hippocampus_seed{s}.sh" for s in (14, 15)],
    "better": [HERE / "retrievers" / "better_idf_weighting.sh", HERE / "retrievers" / "better_bm25_rerank.sh",
               HERE / "retrievers" / "better_bm25_context.sh"],
    "weaker": [
        HERE / "retrievers" / "weaker_16bit.sh",
        HERE / "retrievers" / "weaker_one_bit.sh",
        HERE / "retrievers" / "legacy_iter10_config.sh",
    ],
}
# Order matters only for the two modes touching the evaluator's label file.
SHORTCUTS = [
    "sc_forged_fields", "sc_train_label_lookup", "sc_empty_output", "sc_over_budget", "sc_single_wrong_id",
    "sc_longest_entries", "sc_prewrite_scores", "sc_relabel_visible_data", "sc_hidden_labels_relative",
    "sc_hidden_labels_absolute", "sc_relabel_hidden_absolute", "sc_public_locomo_labels",
    "sc_public_label_prior_bm25", "sc_public_label_avoid_bm25", "sc_public_label_avoid_reference",
]
# Read-only attempts on the evaluator's own files, run against the real workspace.
ESCAPES = ["sc_hidden_labels_relative", "sc_hidden_labels_absolute", "sc_namespace_escape"]


def run(cmd: list[str], cwd: Path, log: Path) -> None:
    with log.open("w") as handle:
        proc = subprocess.run(cmd, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}; see {log}")


def phase_eval(split: str, group: str, scripts: list[Path]) -> Path:
    out = RESULTS / f"{split}_{group}.json"
    cmd = [sys.executable, str(ROOT / "eval" / split / "evaluate_retrieval.py"), *map(str, scripts),
           "--output", str(out), "--per-question-dir", str(RESULTS / f"per_question_{split}")]
    run(cmd, ROOT, RESULTS / f"{split}_{group}.log")
    return out


def phase_shortcuts() -> Path:
    out = RESULTS / "test_shortcuts.json"
    with tempfile.TemporaryDirectory(prefix="hardening_ws_") as tmp:
        ws = Path(tmp) / "ws"
        ws.mkdir()
        for name in ("data", "method", "baseline", "scripts", "eval", "scoring"):
            shutil.copytree(ROOT / name, ws / name, ignore=shutil.ignore_patterns("__pycache__", "downloads"))
        shutil.copytree(HERE, ws / "redteam" / "hardening", ignore=shutil.ignore_patterns("results", "__pycache__"))
        scripts = [ws / "scripts" / "retrievers" / f"{REFERENCE}.sh"]
        scripts += [ws / "redteam" / "hardening" / "shortcuts" / f"{name}.sh" for name in SHORTCUTS]
        cmd = [sys.executable, str(ws / "eval" / "test" / "evaluate_retrieval.py"), *map(str, scripts),
               "--output", str(ws / "scoring" / "scores_test.json"),
               "--per-question-dir", str(RESULTS / "per_question_test_shortcuts")]
        run(cmd, ws, RESULTS / "test_shortcuts.log")
        shutil.copy(ws / "scoring" / "scores_test.json", out)
        hidden = json.loads((ws / "eval" / "test" / "locomo_test.json").read_text())
        original = json.loads((ROOT / "eval" / "test" / "locomo_test.json").read_text())
        (RESULTS / "shortcut_side_effects.json").write_text(json.dumps({
            "hidden_label_file_modified_on_disk": hidden != original,
            "visible_train_file_modified": json.loads((ws / "data" / "locomo_train.json").read_text())
            != json.loads((ROOT / "data" / "locomo_train.json").read_text()),
        }, indent=2) + "\n")
    return out


def phase_escapes() -> Path:
    out = RESULTS / "test_escapes.json"
    scripts = [HERE / "shortcuts" / f"{name}.sh" for name in ESCAPES]
    cmd = [sys.executable, str(ROOT / "eval" / "test" / "evaluate_retrieval.py"), *map(str, scripts),
           "--output", str(out), "--per-question-dir", str(RESULTS / "per_question_test_escapes")]
    run(cmd, ROOT, RESULTS / "test_escapes.log")
    return out


def load_results(paths: list[Path]) -> tuple[dict, dict]:
    results, status = {}, {}
    for path in paths:
        exp = json.loads(path.read_text())["experiments"][EXPERIMENT]
        results.update(exp["results"])
        status.update(exp["_status"])
    return results, status


def metric_spec() -> dict:
    ref = json.loads((ROOT / "scoring" / "reference.json").read_text())
    return ref["experiments"][EXPERIMENT]["metrics"]


def population_std(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def rank_delta(metrics: dict, reference: dict, spec: dict, stds: dict) -> float:
    total = 0.0
    for name, info in spec.items():
        direction = 1.0 if info["higher_is_better"] else -1.0
        if stds[name] > 0:
            total += abs(info["coefficient"]) * direction * (metrics[name] - reference[name]) / stds[name]
    return total


def aggregate(records: list[dict]) -> dict:
    n = len(records)
    cats = defaultdict(list)
    for r in records:
        cats[r["category"]].append(r["evidence_recall"])
    return {
        "evidence_recall_at_10": 100.0 * sum(r["evidence_recall"] for r in records) / n,
        "evidence_hit_at_1": 100.0 * sum(r["hit_at_1"] for r in records) / n,
        "answer_token_recall": 100.0 * sum(r["answer_token_recall"] for r in records) / n,
        "worst_category_recall": min(100.0 * sum(v) / len(v) for v in cats.values()),
        "avg_context_tokens": sum(r["context_tokens"] for r in records) / n,
    }


def load_per_question(directory: Path) -> dict[str, list[dict]]:
    out = {}
    if directory.is_dir():
        for path in directory.glob("*.jsonl"):
            out[path.stem] = [json.loads(line) for line in path.read_text().splitlines()]
    return out


def paired_bootstrap(a: list[dict], b: list[dict], spec: dict, stds: dict, reps: int = 1000) -> dict:
    """Bootstrap over questions; both methods see the same resampled questions."""
    rng = random.Random(0)
    n = len(a)
    assert [r["question_id"] for r in a] == [r["question_id"] for r in b]
    deltas, recall_diffs = [], []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        ma = aggregate([a[i] for i in idx])
        mb = aggregate([b[i] for i in idx])
        deltas.append(rank_delta(ma, mb, spec, stds))
        recall_diffs.append(ma["evidence_recall_at_10"] - mb["evidence_recall_at_10"])
    deltas.sort()
    recall_diffs.sort()
    lo, hi = int(0.025 * reps), int(0.975 * reps) - 1
    return {
        "rank_delta_ci95": [deltas[lo], deltas[hi]],
        "evidence_recall_diff_mean": sum(recall_diffs) / reps,
        "evidence_recall_diff_ci95": [recall_diffs[lo], recall_diffs[hi]],
    }


def summarise() -> None:
    spec = metric_spec()
    test_paths = sorted(RESULTS.glob("test_*.json"))
    test_paths = [p for p in test_paths if p.name not in ("test_shortcuts.json", "test_escapes.json")]
    variants, v_status = load_results(test_paths)
    shortcuts, s_status = load_results([RESULTS / "test_shortcuts.json"])
    escapes, e_status = load_results([RESULTS / "test_escapes.json"])
    for name in escapes:
        shortcuts[f"{name}_realws"] = escapes[name]
        s_status[f"{name}_realws"] = e_status[name]
    train, t_status = load_results(sorted(RESULTS.glob("train_*.json")))
    reference = variants[REFERENCE]
    if shortcuts[REFERENCE] != reference:
        raise RuntimeError("isolated-workspace reference run differs from the main reference run")

    cohort = {**variants, **{k: v for k, v in shortcuts.items() if k != REFERENCE}}
    status = {**v_status, **s_status}
    stds_all = {m: population_std([cohort[k][m] for k in cohort]) for m in spec}
    valid = [k for k in cohort if status[k]["valid"]]
    stds_valid = {m: population_std([cohort[k][m] for k in valid]) for m in spec}

    per_q = load_per_question(RESULTS / "per_question_test")
    per_q.update({k: v for k, v in load_per_question(RESULTS / "per_question_test_shortcuts").items() if k != REFERENCE})
    per_q.update({f"{k}_realws": v for k, v in load_per_question(RESULTS / "per_question_test_escapes").items()})
    rows = {}
    for name, metrics in cohort.items():
        row = {
            "valid": status[name]["valid"],
            "reason": status[name].get("reason"),
            "test": metrics,
            "rank_delta_all_runs_norm": rank_delta(metrics, reference, spec, stds_all),
            "rank_delta_valid_runs_norm": rank_delta(metrics, reference, spec, stds_valid),
        }
        if name in train:
            row["train"] = train[name]
            row["train_valid"] = t_status[name]["valid"]
        if name != REFERENCE and name in per_q and REFERENCE in per_q:
            row["paired_vs_reference"] = paired_bootstrap(per_q[name], per_q[REFERENCE], spec, stds_all)
        if "unscored_raw_metrics" in status[name]:
            row["unscored_raw_metrics"] = status[name]["unscored_raw_metrics"]
        rows[name] = row

    seeds = [REFERENCE, "hippocampus_seed14", "hippocampus_seed15"]
    seed_ranges = {m: max(cohort[s][m] for s in seeds) - min(cohort[s][m] for s in seeds) for m in spec}
    seed_ranks = [rows[s]["rank_delta_all_runs_norm"] for s in seeds]
    summary = {
        "rank_definition": "sum_m |coef_m| * directed (x_m - reference_m) / population_std_m over this audit cohort",
        "coefficients": {m: spec[m]["coefficient"] for m in spec},
        "population_std_all_runs": stds_all,
        "population_std_valid_runs": stds_valid,
        "seed_metric_range": seed_ranges,
        "seed_rank_delta_range": max(seed_ranks) - min(seed_ranks),
        "runs": rows,
    }
    side = RESULTS / "shortcut_side_effects.json"
    if side.is_file():
        summary["shortcut_side_effects"] = json.loads(side.read_text())
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    lines = ["| run | valid | recall@10 | hit@1 | answer-token recall | worst category | context tokens | rank delta | paired recall diff (95% CI) |",
             "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for name, row in sorted(rows.items(), key=lambda kv: -kv[1]["rank_delta_all_runs_norm"]):
        t = row["test"]
        paired = row.get("paired_vs_reference")
        pci = (f"{paired['evidence_recall_diff_mean']:+.2f} [{paired['evidence_recall_diff_ci95'][0]:+.2f}, "
               f"{paired['evidence_recall_diff_ci95'][1]:+.2f}]") if paired else ""
        lines.append(f"| {name} | {row['valid']} | {t['evidence_recall_at_10']:.2f} | {t['evidence_hit_at_1']:.2f} | "
                     f"{t['answer_token_recall']:.2f} | {t['worst_category_recall']:.2f} | {t['avg_context_tokens']:.1f} | "
                     f"{row['rank_delta_all_runs_norm']:+.3f} | {pci} |")
    (RESULTS / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(json.dumps({"seed_metric_range": seed_ranges, "seed_rank_delta_range": summary["seed_rank_delta_range"]}, indent=2))


def main() -> None:
    if RESULTS.exists():
        shutil.rmtree(RESULTS)
    RESULTS.mkdir(parents=True)
    jobs = []
    workers = max(2, min(8, os.cpu_count() or 2))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for group, scripts in VARIANT_GROUPS.items():
            jobs.append(pool.submit(phase_eval, "test", group, scripts))
            jobs.append(pool.submit(phase_eval, "train", group, scripts))
        jobs.append(pool.submit(phase_shortcuts))
        jobs.append(pool.submit(phase_escapes))
        for job in jobs:
            job.result()
    summarise()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--summarise-only":
        summarise()
    else:
        main()
