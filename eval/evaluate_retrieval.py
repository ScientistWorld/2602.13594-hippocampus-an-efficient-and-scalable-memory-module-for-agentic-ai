#!/usr/bin/env python3
"""Evaluate memory retrieval artifacts and write scoring/scores.json."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text.lower()))


def token_f1(prediction: str, answer: str) -> float:
    pred = prediction.lower().split()
    gold = answer.lower().split()
    if not pred or not gold:
        return 0.0
    common = {}
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


def load_gold(path: Path) -> dict[str, dict]:
    dataset = json.loads(path.read_text())
    return {item["question_id"]: item for item in dataset["questions"]}


def evaluate_file(path: Path, gold_by_question: dict[str, dict]) -> dict:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"empty retrieval file: {path}")
    hit_at_1 = 0
    hit_at_k = 0
    answer_f1 = 0.0
    token_footprint = 0
    bit_operations = 0
    for row in rows:
        if row["question_id"] not in gold_by_question:
            raise ValueError(f"unknown question_id in artifact {path}: {row['question_id']}")
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
    n = len(rows)
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
    parser.add_argument("--output", default="scoring/scores.json")
    args = parser.parse_args()

    gold_by_question = load_gold(Path(args.data))
    results = {}
    for artifact in args.artifacts:
        artifact_path = Path(artifact)
        metrics = evaluate_file(artifact_path, gold_by_question)
        method_name = json.loads(artifact_path.read_text().splitlines()[0])["method"]
        results[method_name] = metrics
    scores = {"experiments": {"memory_retrieval_efficiency": {"results": results}}}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scores, indent=2) + "\n")


if __name__ == "__main__":
    main()
