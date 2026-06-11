#!/usr/bin/env python3
"""Evaluate the held-out test slice of memory retrieval artifacts."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


SLICE = "test"
EXPERIMENT = "memory_retrieval_efficiency"
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
MAX_RETRIEVED = 3
TEST_QUESTION_IDS = frozenset(
    {
        "q43", "q58", "q25", "q13", "q19", "q16", "q22", "q55", "q1", "q28", "q34", "q37",
        "q21", "q33", "q9", "q12", "q3", "q63", "q15", "q66", "q30", "q69", "q36", "q48",
        "q23", "q62", "q68", "q44", "q8", "q71", "q35", "q50", "q32", "q38", "q29", "q14",
    }
)


def token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text.lower()))


def normalized_tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def token_f1(prediction: str, answer: str) -> float:
    pred = normalized_tokens(prediction)
    gold = normalized_tokens(answer)
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


def load_gold(path: Path) -> tuple[dict[str, dict], dict[str, dict], set[str], dict[str, int]]:
    dataset = json.loads(path.read_text())
    gold_by_question = {item["question_id"]: item for item in dataset["questions"]}
    entry_by_id: dict[str, dict] = {}
    for conversation in dataset["conversations"]:
        for entry in conversation["entries"]:
            entry_by_id[entry["entry_id"]] = {**entry, "conversation_id": conversation["conversation_id"]}

    selected = set(TEST_QUESTION_IDS)
    unknown = selected - set(gold_by_question)
    if unknown:
        raise ValueError(f"{SLICE} split contains unknown question ids: {sorted(unknown)}")

    category_counts: dict[str, int] = defaultdict(int)
    for item in dataset["questions"]:
        if item["question_id"] in selected:
            category_counts[item.get("category", "unknown")] += 1

    return gold_by_question, entry_by_id, selected, dict(sorted(category_counts.items()))


def read_artifact_rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"empty retrieval file: {path}")
    return rows


def artifact_method_name(path: Path) -> str:
    first_line = path.read_text().splitlines()[0]
    return json.loads(first_line)["method"]


def reference_method_names(path: Path) -> set[str]:
    reference = json.loads(path.read_text())
    return set(reference["experiments"][EXPERIMENT]["results"])


def train_method_names(path: Path) -> list[str]:
    if not path.exists():
        return []
    scores = json.loads(path.read_text())
    results = scores["experiments"][EXPERIMENT]["results"]
    return list(results)


def evaluate_file(
    path: Path,
    gold_by_question: dict[str, dict],
    entry_by_id: dict[str, dict],
    selected_ids: set[str],
) -> dict[str, float]:
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
    gold_entry_recall = 0.0
    answer_f1 = 0.0
    token_footprint = 0
    bit_operations = 0
    category_hits: dict[str, list[int]] = defaultdict(list)
    for row in filtered:
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
        for item in retrieved:
            text = item.get("reconstructed_text", item.get("text", ""))
            token_footprint += token_count(text)
        bit_operations += row.get("bit_operations", 0)

    n = len(filtered)
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
    parser.add_argument("--output", default="scoring/scores_test.json")
    parser.add_argument("--train-scores", default="scoring/scores_train.json")
    parser.add_argument("--reference", default="scoring/reference.json")
    args = parser.parse_args()

    gold_by_question, entry_by_id, selected_ids, category_counts = load_gold(Path(args.data))
    allowed_methods = reference_method_names(Path(args.reference))
    artifacts_by_method: dict[str, Path] = {}
    for artifact in args.artifacts:
        artifact_path = Path(artifact)
        method_name = artifact_method_name(artifact_path)
        if method_name not in allowed_methods:
            continue
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
        results[method_name] = evaluate_file(
            artifacts_by_method[method_name],
            gold_by_question,
            entry_by_id,
            selected_ids,
        )

    scores = {
        "slice": SLICE,
        "experiments": {
            EXPERIMENT: {
                "slice": SLICE,
                "split": {
                    "name": "explicit_balanced_test_slice_v2",
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
