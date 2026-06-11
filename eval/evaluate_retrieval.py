#!/usr/bin/env python3
"""Evaluate memory retrieval artifacts and write scoring/scores.json."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
MAX_RETRIEVED = 3


def token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text.lower()))


def token_f1(prediction: str, answer: str) -> float:
    pred = TOKEN_RE.findall(prediction.lower())
    gold = TOKEN_RE.findall(answer.lower())
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


def load_gold(path: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    dataset = json.loads(path.read_text())
    gold_by_question = {item["question_id"]: item for item in dataset["questions"]}
    entry_by_id: dict[str, dict] = {}
    for conversation in dataset["conversations"]:
        for entry in conversation["entries"]:
            entry_by_id[entry["entry_id"]] = {**entry, "conversation_id": conversation["conversation_id"]}
    return gold_by_question, entry_by_id


def evaluate_file(path: Path, gold_by_question: dict[str, dict], entry_by_id: dict[str, dict]) -> dict:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"empty retrieval file: {path}")
    hit_at_1 = 0
    hit_at_k = 0
    gold_entry_recall = 0.0
    answer_f1 = 0.0
    token_footprint = 0
    bit_operations = 0
    category_hits: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        if row["question_id"] not in gold_by_question:
            raise ValueError(f"unknown question_id in artifact {path}: {row['question_id']}")
        gold_item = gold_by_question[row["question_id"]]
        retrieved = row.get("retrieved", [])
        if len(retrieved) > MAX_RETRIEVED:
            raise ValueError(
                f"artifact {path} returns {len(retrieved)} entries for {row['question_id']}; "
                f"maximum allowed is {MAX_RETRIEVED}"
            )
        gold = set(gold_item["gold_entry_ids"])
        ids = [item["entry_id"] for item in retrieved]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate retrieved entry_id for {row['question_id']} in artifact {path}")
        for entry_id in ids:
            if entry_id not in entry_by_id:
                raise ValueError(f"unknown retrieved entry_id for {row['question_id']} in artifact {path}: {entry_id}")
            if entry_by_id[entry_id]["conversation_id"] != gold_item["conversation_id"]:
                raise ValueError(
                    f"cross-conversation retrieval for {row['question_id']} in artifact {path}: {entry_id}"
                )
        top1_hit = int(bool(ids and ids[0] in gold))
        any_hit = int(bool(gold.intersection(ids)))
        hit_at_1 += top1_hit
        hit_at_k += any_hit
        gold_entry_recall += len(gold.intersection(ids)) / len(gold)
        category_hits[gold_item.get("category", "unknown")].append(top1_hit)
        joined = " ".join(item.get("reconstructed_text", item.get("text", "")) for item in retrieved)
        answer_f1 += token_f1(joined, gold_item["answer"])
        token_footprint += sum(token_count(item.get("reconstructed_text", item.get("text", ""))) for item in retrieved)
        bit_operations += row.get("bit_operations", 0)
    n = len(rows)
    worst_category_hit_at_1 = min(
        (100.0 * sum(values) / len(values) for values in category_hits.values()),
        default=0.0,
    )
    return {
        "hit_at_1": 100.0 * hit_at_1 / n,
        "hit_at_3": 100.0 * hit_at_k / n,
        "gold_entry_recall": 100.0 * gold_entry_recall / n,
        "answer_token_f1": 100.0 * answer_f1 / n,
        "worst_category_hit_at_1": worst_category_hit_at_1,
        "avg_token_footprint": token_footprint / n,
        "avg_bit_operations": bit_operations / n,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", nargs="+", required=True)
    parser.add_argument("--data", default="data/memory_qa.json")
    parser.add_argument("--output", default="scoring/scores.json")
    args = parser.parse_args()

    gold_by_question, entry_by_id = load_gold(Path(args.data))
    results = {}
    for artifact in args.artifacts:
        artifact_path = Path(artifact)
        metrics = evaluate_file(artifact_path, gold_by_question, entry_by_id)
        method_name = json.loads(artifact_path.read_text().splitlines()[0])["method"]
        results[method_name] = metrics
    scores = {"experiments": {"memory_retrieval_efficiency": {"results": results}}}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scores, indent=2) + "\n")


if __name__ == "__main__":
    main()
