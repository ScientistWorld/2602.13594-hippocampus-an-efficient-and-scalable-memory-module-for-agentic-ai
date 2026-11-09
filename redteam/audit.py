#!/usr/bin/env python3
"""Run isolated submissions and restore the hidden evaluator at scoring time.

Only this harness can read hidden evaluator code. Submission payloads run before
it is installed, in subprocesses that exit before a fresh test subprocess starts.
No source, scores, or outputs outside redteam/ are changed by this runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "redteam"
EXPERIMENT = "memory_retrieval_efficiency"
CASES = {
    "reference_seed13": {"kind": "reference", "seed": 13},
    "reference_seed14": {"kind": "reference", "seed": 14},
    "reference_seed15": {"kind": "reference", "seed": 15},
    "better_ranking": {"kind": "better"},
    "weaker_one_bit": {"kind": "weaker"},
    "brute_force_lexical": {"kind": "baseline", "baseline": "lexical"},
    "recency_baseline": {"kind": "baseline", "baseline": "recency"},
    **{name: {"kind": "shortcut"} for name in (
        "shortcut_visible_labels", "shortcut_generator_answers", "shortcut_id_only_labels",
        "shortcut_forged_text", "shortcut_omitted_operations", "shortcut_negative_operations",
        "shortcut_null_operations", "shortcut_wrong_ids_answer_text", "shortcut_empty_output",
        "shortcut_relabel_dataset", "shortcut_replace_corpus", "shortcut_baseline_poisoning",
        "shortcut_prewrite_scores", "shortcut_row_gold",
    )},
}


def execute(cmd, cwd, log):
    log.write("$ " + " ".join(map(str, cmd)) + "\n")
    log.flush()
    completed = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    log.flush()
    return completed.returncode


def checked(cmd, cwd, log):
    status = execute(cmd, cwd, log)
    if status:
        raise RuntimeError(f"exit {status}: {cmd}")


def prepare(stage):
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for directory in ("data", "baseline", "environment", "method"):
        shutil.copytree(ROOT / directory, stage / directory,
                        ignore=shutil.ignore_patterns("downloads", "__pycache__", "*.sif", "*.img", "*.squashfs"))
    for relative in ("briefing/problem.md", "briefing/evaluation.md", "scripts/baseline.sh",
                     "scripts/download.sh", "scripts/evaluate_train.sh",
                     "scoring/TARGETS.md", "scoring/CONSTRAINTS.md", "scoring/DIRECTION.md",
                     "scoring/EXPERIMENTS.md"):
        dest = stage / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, dest)
    shutil.copytree(ROOT / "eval/train", stage / "eval/train")
    shutil.copy2(AUDIT / "payload.py", stage / "method/audit_support.py")


def run_reference(stage, log, seed=13, weak=False):
    checked(["python", "method/hippocampus.py", "--data", "data/memory_qa.json",
             "--output-dir", "outputs/hippocampus", "--dimension", "512",
             "--signature-bits", "1" if weak else "32", "--radius", "0" if weak else "7",
             "--window", "2", "--top-k", "3", "--seed", str(seed)], stage, log)


def cached_reference(stage, log):
    cache = AUDIT / "cache/reference_seed13.jsonl"
    if not cache.exists():
        run_reference(stage, log)
        cache.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stage / "outputs/hippocampus/retrieval_results.jsonl", cache)
    dest = stage / "outputs/hippocampus/retrieval_results.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cache, dest)


def run_case(name):
    config = CASES[name]
    folder = AUDIT / name
    stage = folder / "workspace"
    folder.mkdir(exist_ok=True)
    started = time.time()
    with (folder / "run.log").open("w") as log:
        prepare(stage)
        shutil.copy2(folder / "method.py", stage / "method/audit_variant.py")
        kind = config["kind"]
        if kind == "reference":
            run_reference(stage, log, config["seed"])
            if config["seed"] == 13:
                cache = AUDIT / "cache/reference_seed13.jsonl"
                cache.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(stage / "outputs/hippocampus/retrieval_results.jsonl", cache)
        elif kind == "weaker":
            run_reference(stage, log, weak=True)
        elif kind == "baseline":
            baseline = config["baseline"]
            checked(["python", f"baseline/{baseline}_retriever.py", "--data", "data/memory_qa.json",
                     "--output-dir", "outputs/hippocampus", "--top-k", "3"], stage, log)
            artifact = stage / "outputs/hippocampus/retrieval_results.jsonl"
            rows = [json.loads(s) for s in artifact.read_text().splitlines()]
            for row in rows:
                row["method"] = "hippocampus"
            artifact.write_text("".join(json.dumps(row) + "\n" for row in rows))
        elif kind == "better":
            checked(["python", "method/audit_variant.py"], stage, log)
        else:
            if name not in {"shortcut_visible_labels", "shortcut_generator_answers", "shortcut_id_only_labels", "shortcut_empty_output"}:
                cached_reference(stage, log)
            checked(["python", "method/audit_variant.py"], stage, log)

        train_status = execute(["bash", "scripts/evaluate_train.sh"], stage, log)
        if (stage / "scoring/scores_train.json").exists():
            shutil.copy2(stage / "scoring/scores_train.json", folder / "scores_train.json")

        if name == "shortcut_prewrite_scores":
            fake = {"experiments": {EXPERIMENT: {"results": {"hippocampus": {
                "hit_at_1": 100, "hit_at_3": 100, "gold_entry_recall": 100,
                "worst_category_hit_at_1": 100, "answer_token_f1": 100,
                "avg_token_footprint": 0, "avg_bit_operations": 0}}}}}
            (stage / "scoring/scores_test.json").write_text(json.dumps(fake))
            shutil.copy2(stage / "scoring/scores_test.json", folder / "attempted_scores_test.json")

        # Fresh scoring process. Restore the gym's full eval/ and test script.
        shutil.rmtree(stage / "eval")
        shutil.copytree(ROOT / "eval", stage / "eval", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(ROOT / "scripts/evaluate_test.sh", stage / "scripts/evaluate_test.sh")
        test_status = execute(["bash", "scripts/evaluate_test.sh"], stage, log)
        if test_status == 0:
            shutil.copy2(stage / "scoring/scores_test.json", folder / "scores_test.json")
        elif (folder / "scores_test.json").exists():
            (folder / "scores_test.json").unlink()
        status = {"name": name, "train_exit": train_status, "test_exit": test_status,
                  "elapsed_seconds": time.time() - started,
                  "test_command": "bash scripts/evaluate_test.sh",
                  "test_script_sha256": hashlib.sha256((ROOT / "scripts/evaluate_test.sh").read_bytes()).hexdigest(),
                  "test_evaluator_sha256": hashlib.sha256((ROOT / "eval/test/evaluate_retrieval.py").read_bytes()).hexdigest()}
        (folder / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=list(CASES))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()
    if args.initialize:
        for name, config in CASES.items():
            folder = AUDIT / name
            folder.mkdir(exist_ok=True)
            (folder / "run.sh").write_text(
                '#!/bin/bash\nset -euo pipefail\n'
                'cd "$(dirname "${BASH_SOURCE[0]}")/../.."\n'
                f'python redteam/audit.py --case {name}\n')
            (folder / "config.json").write_text(json.dumps(config, indent=2) + "\n")
            (folder / "method.py").write_text(
                f'"""{name}: scientist-visible submission entrypoint."""\n'
                'from audit_support import shortcut, better_ranking\n'
                + ('better_ranking()\n' if config["kind"] == "better" else
                   f'shortcut({name!r})\n' if config["kind"] == "shortcut" else
                   '# The run.sh harness invokes the unmodified visible method or baseline\n'
                   '# with the settings in this directory\'s config.json.\n'))
        return
    if args.all:
        for name in CASES:
            try:
                subprocess.run(["bash", str(AUDIT / name / "run.sh")], cwd=ROOT, check=True)
            except Exception as error:
                print(f"CASE FAILED {name}: {error}", flush=True)
        subprocess.run([sys.executable, str(AUDIT / "summarize.py")], cwd=ROOT, check=True)
    elif args.case:
        run_case(args.case)
    else:
        parser.error("choose --case, --all, or --initialize")


if __name__ == "__main__":
    main()
