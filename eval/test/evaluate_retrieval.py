#!/usr/bin/env python3
"""Evaluate the held-out test slice of memory retrieval artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


SLICE = "test"
EXPERIMENT = "memory_retrieval_efficiency"
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
SPLIT_SEED = "memory-retrieval-eval-split-v1"


def token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text.lower()))


def token_f1(prediction: str, answer: str) -> float:
    pred = prediction.lower().split()
    gold = answer.lower().split()
    if not pred or not gold:
        return 0.0
    common: dict[str, int] = {}
    for tok in pred:
        common[tok] = common.get(tok, 0) + 1
    overlap = 0
    for tok in gold:
        if common.get(tok, 0) > 0:
            common[tok] -= 1
            overlap += 1
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred)
    recall = overlap / len(gold)
    return 2 * precision * recall / (precision + recall)


def split_key(question_id: str) -> str:
    payload = f"{SPLIT_SEED}|{question_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_gold(path: Path) -> tuple[dict[str, dict], set[str], dict[str, int]]:
    dataset = json.loads(path.read_text())
    gold_by_question = {item["question_id"]: item for item in dataset["questions"]}
    by_category: dict[str, list[dict]] = defaultdict(list)
    for item in dataset["questions"]:
        by_category[item.get("category", "unknown")].append(item)

    selected: set[str] = set()
    category_counts: dict[str, int] = {}
    for category, items in sorted(by_category.items()):
        ordered = sorted(items, key=lambda item: (split_key(item["question_id"]), item["question_id"]))
        midpoint = len(ordered) // 2
        test_items = ordered[midpoint:]
        selected.update(item["question_id"] for item in test_items)
        category_counts[category] = len(test_items)

    return gold_by_question, selected, category_counts


def read_artifact_rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"empty retrieval file: {path}")
    return rows


def artifact_method_name(path: Path) -> str:
    first_line = path.read_text().splitlines()[0]
    return json.loads(first_line)["method"]


def train_method_names(path: Path) -> list[str]:
    if not path.exists():
        return []
    scores = json.loads(path.read_text())
    results = scores["experiments"][EXPERIMENT]["results"]
    return list(results)


def evaluate_file(path: Path, gold_by_question: dict[str, dict], selected_ids: set[str]) -> dict[str, float]:
    rows = read_artifact_rows(path)
    filtered: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        question_id = row["question_id"]
        if question_id not in gold_by_question:
            raise ValueError(f"unknown question_id in artifact {path}: {question_id}")
        if question_id not in selected_ids:
            continue
        if question_id in seen:
            raise ValueError(f"duplicate {SLICE} question_id in artifact {path}: {question_id}")
        seen.add(question_id)
        filtered.append(row)

    missing = sorted(selected_ids - seen, key=lambda qid: int(qid[1:]) if qid[1:].isdigit() else qid)
    if missing:
        preview = ", ".join(missing[:8])
        raise ValueError(f"artifact {path} is missing {len(missing)} {SLICE} questions: {preview}")

    hit_at_1 = 0
    hit_at_k = 0
    answer_f1 = 0.0
    token_footprint = 0
    bit_operations = 0
    for row in filtered:
        gold_item = gold_by_question[row["question_id"]]
        retrieved = row.get("retrieved", [])
        gold = set(gold_item["gold_entry_ids"])
        ids = [item["entry_id"] for item in retrieved]
        hit_at_1 += int(bool(ids and ids[0] in gold))
        hit_at_k += int(bool(gold.intersection(ids)))
        joined = " ".join(item.get("reconstructed_text", item.get("text", "")) for item in retrieved)
        answer_f1 += token_f1(joined, gold_item["answer"])
        token_footprint += sum(token_count(item.get("reconstructed_text", item.get("text", ""))) for item in retrieved)
        bit_operations += row.get("bit_operations", 0)

    n = len(filtered)
    return {
        "hit_at_1": 100.0 * hit_at_1 / n,
        "hit_at_3": 100.0 * hit_at_k / n,
        "answer_token_f1": 100.0 * answer_f1 / n,
        "avg_token_footprint": token_footprint / n,
        "avg_bit_operations": bit_operations / n,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", nargs="+", required=True)
    parser.add_argument("--data", default="data/memory_qa.json")
    parser.add_argument("--output", default="scoring/scores_test.json")
    parser.add_argument("--train-scores", default="scoring/scores_train.json")
    args = parser.parse_args()

    gold_by_question, selected_ids, category_counts = load_gold(Path(args.data))
    artifacts_by_method: dict[str, Path] = {}
    for artifact in args.artifacts:
        artifact_path = Path(artifact)
        method_name = artifact_method_name(artifact_path)
        if method_name in artifacts_by_method:
            raise ValueError(f"multiple artifacts declare method {method_name!r}")
        artifacts_by_method[method_name] = artifact_path

    requested_methods = train_method_names(Path(args.train_scores))
    if requested_methods:
        missing = [method for method in requested_methods if method not in artifacts_by_method]
        if missing:
            raise ValueError(
                "missing artifacts for methods present in train scores: " + ", ".join(missing)
            )
        methods_to_score = requested_methods
    else:
        methods_to_score = sorted(artifacts_by_method)

    results: dict[str, dict[str, float]] = {}
    for method_name in methods_to_score:
        results[method_name] = evaluate_file(artifacts_by_method[method_name], gold_by_question, selected_ids)

    scores = {
        "slice": SLICE,
        "experiments": {
            EXPERIMENT: {
                "slice": SLICE,
                "split": {
                    "seed": SPLIT_SEED,
                    "question_count": len(selected_ids),
                    "category_counts": category_counts,
                },
                "results": results,
            }
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
