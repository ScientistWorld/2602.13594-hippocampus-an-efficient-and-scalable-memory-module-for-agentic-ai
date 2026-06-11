#!/usr/bin/env python3
"""Simple recency baseline for long-memory retrieval.

This approximates lightweight memory systems that prefer the most recent
conversation entries without building a semantic index.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text.lower()))


def run(args: argparse.Namespace) -> None:
    dataset = json.loads(Path(args.data).read_text())
    entries_by_conversation = {}
    total_storage = 0
    for conversation in dataset["conversations"]:
        conv_entries = []
        for entry in conversation["entries"]:
            total_storage += len(entry["text"].encode("utf-8"))
            conv_entries.append({**entry, "conversation_id": conversation["conversation_id"]})
        entries_by_conversation[conversation["conversation_id"]] = conv_entries

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "retrieval_results.jsonl").open("w") as f:
        for item in dataset["questions"]:
            start = time.perf_counter()
            entries = entries_by_conversation[item["conversation_id"]]
            ranked = sorted(entries, key=lambda entry: (entry["session"], entry["timestamp"], entry["entry_id"]), reverse=True)[
                : args.top_k
            ]
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
                        "token_count": token_count(entry["text"]),
                    }
                )
            row = {
                "method": "recency_baseline",
                "question_id": item["question_id"],
                "conversation_id": item["conversation_id"],
                "question": item["question"],
                "answer": item["answer"],
                "gold_entry_ids": item["gold_entry_ids"],
                "retrieved": retrieved,
                "search_time_s": time.perf_counter() - start,
                "signature_comparisons": 0,
                "bit_operations": len(entries),
                "token_footprint": sum(entry["token_count"] for entry in retrieved),
                "storage_bytes": total_storage,
            }
            f.write(json.dumps(row) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/memory_qa.json")
    parser.add_argument("--output-dir", default="outputs/recency_baseline")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
