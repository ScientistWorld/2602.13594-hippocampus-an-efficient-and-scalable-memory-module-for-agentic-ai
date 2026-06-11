#!/usr/bin/env python3
"""Method-agnostic lexical baseline for the memory QA benchmark."""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from collections import Counter
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
STOP = {"which", "what", "did", "for", "the", "at", "on", "use", "used", "by", "should", "be", "and", "a"}


def tokenize(text: str) -> list[str]:
    return [tok for tok in TOKEN_RE.findall(text.lower()) if tok not in STOP]


def run(args: argparse.Namespace) -> None:
    dataset = json.loads(Path(args.data).read_text())
    entries = []
    for conversation in dataset["conversations"]:
        for entry in conversation["entries"]:
            tokens = tokenize(entry["text"])
            entries.append({**entry, "conversation_id": conversation["conversation_id"], "tokens": tokens})
    df = Counter()
    for entry in entries:
        df.update(set(entry["tokens"]))
    n = len(entries)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "retrieval_results.jsonl").open("w") as f:
        for item in dataset["questions"]:
            start = time.perf_counter()
            q_tokens = tokenize(item["question"])
            q_counts = Counter(q_tokens)
            scored = []
            operations = 0
            for entry in entries:
                if entry["conversation_id"] != item["conversation_id"]:
                    continue
                e_counts = Counter(entry["tokens"])
                score = 0.0
                for tok, q_count in q_counts.items():
                    operations += 1
                    if tok in e_counts:
                        idf = math.log((n + 1) / (df[tok] + 1)) + 1.0
                        score += q_count * e_counts[tok] * idf
                scored.append((score, entry))
            ranked = [entry for score, entry in sorted(scored, key=lambda x: (-x[0], x[1]["entry_id"]))[: args.top_k]]
            retrieved = []
            for entry in ranked:
                retrieved.append(
                    {
                        "entry_id": entry["entry_id"],
                        "conversation_id": entry["conversation_id"],
                        "session": entry["session"],
                        "speaker": entry["speaker"],
                        "timestamp": entry["timestamp"],
                        "text": entry["text"],
                        "reconstructed_text": entry["text"].lower(),
                        "token_count": len(entry["tokens"]),
                    }
                )
            row = {
                "method": "lexical_baseline",
                "question_id": item["question_id"],
                "conversation_id": item["conversation_id"],
                "question": item["question"],
                "answer": item["answer"],
                "gold_entry_ids": item["gold_entry_ids"],
                "retrieved": retrieved,
                "search_time_s": time.perf_counter() - start,
                "signature_comparisons": 0,
                "bit_operations": operations * 32,
                "token_footprint": sum(item["token_count"] for item in retrieved),
                "storage_bytes": sum(len(entry["text"].encode("utf-8")) for entry in entries),
            }
            f.write(json.dumps(row) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/memory_qa.json")
    parser.add_argument("--output-dir", default="outputs/lexical_baseline")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
